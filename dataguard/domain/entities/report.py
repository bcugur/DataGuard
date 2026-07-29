"""ValidationReport aggregate root.

Collects all CheckResults for a single validation run and computes
the aggregate quality verdict.

Design
------
- Aggregate root: ValidationReport owns and controls its CheckResults.
  External code adds results via add_result(); direct list mutation is not
  exposed.
- overall_status is derived, not stored: it is computed from the results
  list on every access, ensuring consistency without synchronisation.
- Serialisation helpers (to_dict) make it easy for writers to render
  the report without coupling the domain to any specific output format.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dataguard.domain.entities.check_result import CheckResult
from dataguard.shared.types import OverallStatus, RulesPath, Score, SourcePath


@dataclass
class ValidationReport:
    """Aggregate root for a single validation run.

    A ValidationReport is created once per ``dataguard validate`` invocation.
    Results are added incrementally as each rule is executed. Once all rules
    have run, the report provides computed aggregates and the overall verdict.

    Attributes:
        report_id: Unique UUID for this validation run.
        source_path: Path to the data file that was validated.
        rules_path: Path to the YAML file that defined the rules.
        executed_at: UTC timestamp when the validation started.

    Note:
        Do not access ``_results`` directly. Use ``add_result()`` and the
        computed properties instead.
    """

    source_path: SourcePath
    rules_path: RulesPath
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    executed_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    _results: list[CheckResult] = field(default_factory=list, repr=False)

    # ── Mutation ───────────────────────────────────────────────────────────

    def add_result(self, result: CheckResult) -> None:
        """Append a CheckResult produced by a rule execution.

        Args:
            result: The result of running one QualityRule.
        """
        self._results.append(result)

    # ── Computed aggregates ────────────────────────────────────────────────

    @property
    def results(self) -> list[CheckResult]:
        """Return a read-only copy of all check results."""
        return list(self._results)

    @property
    def total_rules(self) -> int:
        """Return the total number of rules executed."""
        return len(self._results)

    @property
    def passed_rules(self) -> int:
        """Return the number of rules whose status is 'passed'."""
        return sum(1 for r in self._results if r.passed)

    @property
    def failed_rules(self) -> int:
        """Return the number of rules whose status is 'failed'."""
        return sum(1 for r in self._results if r.failed)

    @property
    def skipped_rules(self) -> int:
        """Return the number of rules whose status is 'skipped'."""
        return sum(1 for r in self._results if r.status == "skipped")

    @property
    def blocking_failures(self) -> list[CheckResult]:
        """Return failed rules with severity='error' (block overall pass)."""
        return [r for r in self._results if r.is_blocking_failure]

    @property
    def overall_score(self) -> Score:
        """Return the mean quality score across all executed rules.

        Returns 1.0 when no rules have been executed (vacuously true).
        """
        if not self._results:
            return 1.0
        return sum(r.score for r in self._results) / len(self._results)

    @property
    def overall_status(self) -> OverallStatus:
        """Derive the aggregate validation verdict.

        Returns:
            'failed' if any blocking failure (severity=error) exists.
            'passed' otherwise.
        """
        return "failed" if self.blocking_failures else "passed"

    @property
    def source_name(self) -> str:
        """Return only the filename portion of the source path."""
        return Path(self.source_path).name

    # ── Serialisation ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, object]:
        """Serialise the report to a plain Python dictionary.

        The structure is stable and intended for JSON output by writers.
        Dates are formatted as ISO-8601 strings.

        Returns:
            A dict suitable for ``json.dumps()``.
        """
        return {
            "report_id": self.report_id,
            "source_path": self.source_path,
            "rules_path": self.rules_path,
            "executed_at": self.executed_at.isoformat(),
            "summary": {
                "overall_status": self.overall_status,
                "overall_score": round(self.overall_score, 4),
                "total_rules": self.total_rules,
                "passed_rules": self.passed_rules,
                "failed_rules": self.failed_rules,
                "skipped_rules": self.skipped_rules,
            },
            "results": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "rule_type": r.rule_type,
                    "column": r.column,
                    "status": r.status,
                    "score": round(r.score, 4),
                    "threshold": round(r.threshold, 4),
                    "failed_count": r.failed_count,
                    "total_count": r.total_count,
                    "severity": r.severity,
                    "message": r.message,
                }
                for r in self._results
            ],
        }

    def __repr__(self) -> str:
        return (
            f"ValidationReport(id='{self.report_id[:8]}…', "
            f"source='{self.source_name}', "
            f"status='{self.overall_status}', "
            f"rules={self.total_rules})"
        )
