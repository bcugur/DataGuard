"""CheckResult value object.

Represents the outcome of executing a single QualityRule against a Dataset.
This is an immutable value object — it is created once by a rule's check()
method and never mutated.

Design
------
- frozen=True: results are facts; they must not be changed after creation.
- score and threshold are stored together so a result is self-contained —
  no external reference is needed to determine pass/fail.
- failed_count / total_count enable downstream reporters to show
  precise, actionable failure counts.
"""

from __future__ import annotations

from dataclasses import dataclass

from dataguard.shared.types import (
    CheckStatus,
    ColumnName,
    RuleId,
    RuleName,
    Score,
    Severity,
    Threshold,
)


@dataclass(frozen=True)
class CheckResult:
    """Immutable outcome of executing one quality rule.

    Attributes:
        rule_id: Identifier of the rule that produced this result.
        rule_name: Human-readable name of the rule.
        rule_type: Category of the rule (completeness, uniqueness, validity).
        column: The primary column that was checked. None for multi-column rules.
        status: Whether the rule passed, failed, or was skipped.
        score: Achieved quality score in [0.0, 1.0].
        threshold: Minimum score that was required for the rule to pass.
        failed_count: Number of rows/values that violated the rule.
        total_count: Total number of rows/values that were evaluated.
        severity: Impact level of this rule (copied from QualityRule).
        message: Human-readable explanation of the result.

    Raises:
        ValueError: If ``score`` or ``threshold`` is outside [0.0, 1.0].
        ValueError: If ``failed_count`` > ``total_count``.
    """

    rule_id: RuleId
    rule_name: RuleName
    rule_type: str
    column: ColumnName | None
    status: CheckStatus
    score: Score
    threshold: Threshold
    failed_count: int
    total_count: int
    severity: Severity
    message: str
    failed_row_indices: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        """Enforce value object invariants."""
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(
                f"score must be in [0.0, 1.0], got {self.score} "
                f"(rule: '{self.rule_id}')."
            )
        if not (0.0 <= self.threshold <= 1.0):
            raise ValueError(
                f"threshold must be in [0.0, 1.0], got {self.threshold} "
                f"(rule: '{self.rule_id}')."
            )
        if self.failed_count > self.total_count:
            raise ValueError(
                f"failed_count ({self.failed_count}) cannot exceed "
                f"total_count ({self.total_count}) for rule '{self.rule_id}'."
            )

    # ── Convenience properties ─────────────────────────────────────────────

    @property
    def passed(self) -> bool:
        """Return True if the rule passed."""
        return self.status == "passed"

    @property
    def failed(self) -> bool:
        """Return True if the rule failed."""
        return self.status == "failed"

    @property
    def is_blocking_failure(self) -> bool:
        """Return True if this is a failed, error-severity result.

        Blocking failures cause the overall ValidationReport to be 'failed'.
        """
        return self.failed and self.severity == "error"

    @property
    def pass_rate(self) -> float:
        """Return the fraction of values that passed (1.0 − failure rate).

        Returns 1.0 if total_count is zero (vacuously true).
        """
        if self.total_count == 0:
            return 1.0
        return (self.total_count - self.failed_count) / self.total_count

    def __repr__(self) -> str:
        return (
            f"CheckResult(rule='{self.rule_name}', status='{self.status}', "
            f"score={self.score:.3f}, threshold={self.threshold:.3f})"
        )
