"""CompletenessRule — checks for NULL / empty values in a column.

A column is considered "complete" if the fraction of non-null, non-empty
values meets or exceeds the configured threshold.

Definition of "missing":
    - Python None
    - Empty string ''
    - Whitespace-only string (e.g. '   ')

Score formula:
    score = (total_count - missing_count) / total_count

Example YAML:
    - id: rule_001
      name: email_completeness
      type: completeness
      column: email
      threshold: 0.95
      severity: error
"""

from __future__ import annotations

from dataguard.domain.entities.check_result import CheckResult
from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.rules.base import AbstractQualityRule
from dataguard.shared.types import Threshold


class CompletenessRule(AbstractQualityRule):
    """Validates that a column has sufficiently few missing values.

    A value is considered missing if it is None, an empty string, or a
    whitespace-only string. The rule passes when the non-missing fraction
    (completeness score) is >= the configured threshold.

    Attributes:
        rule_type: Always ``'completeness'``. Used by the rule registry
            to select this executor for completeness-type rules.
    """

    rule_type: str = "completeness"

    def _execute(
        self,
        rule: QualityRule,
        dataset: Dataset,
        threshold: Threshold,
    ) -> CheckResult:
        """Count missing values and compute the completeness score.

        Args:
            rule: The completeness rule definition. ``rule.column`` is
                guaranteed to exist in ``dataset`` by the base class.
            dataset: The dataset to evaluate.
            threshold: Resolved minimum completeness score.

        Returns:
            CheckResult with the completeness score and pass/fail verdict.
        """
        column: str = rule.column  # type: ignore[assignment]
        # column presence is pre-validated by AbstractQualityRule.check()

        values = dataset.get_column_values(column)
        total_count = len(values)

        if total_count == 0:
            return self._build_result(
                rule=rule,
                column=column,
                score=1.0,
                threshold=threshold,
                failed_count=0,
                total_count=0,
                message="Column has no rows — vacuously complete.",
            )

        failed_row_indices = tuple(i for i, v in enumerate(values) if self._is_missing(v))
        missing_count = len(failed_row_indices)
        score = (total_count - missing_count) / total_count

        status = self._determine_status(score, threshold)
        message = self._build_message(
            column=column,
            missing_count=missing_count,
            total_count=total_count,
            score=score,
            threshold=threshold,
            status=status,
        )

        return self._build_result(
            rule=rule,
            column=column,
            score=score,
            threshold=threshold,
            failed_count=missing_count,
            total_count=total_count,
            message=message,
            failed_row_indices=failed_row_indices,
        )

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _is_missing(value: object) -> bool:
        """Return True if a value is considered missing.

        A value is missing when it is:
        - None
        - An empty string ('')
        - A string consisting solely of whitespace

        Args:
            value: Any value from a dataset column.

        Returns:
            bool: True if the value counts as missing.
        """
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

    @staticmethod
    def _build_message(
        column: str,
        missing_count: int,
        total_count: int,
        score: float,
        threshold: float,
        status: str,
    ) -> str:
        """Compose a human-readable result message.

        Args:
            column: Name of the checked column.
            missing_count: Number of missing values found.
            total_count: Total number of values checked.
            score: Achieved completeness score.
            threshold: Required minimum score.
            status: 'passed' or 'failed'.

        Returns:
            A one-line descriptive string.
        """
        pct_missing = (missing_count / total_count) * 100 if total_count else 0
        verdict = "✓" if status == "passed" else "✗"
        return (
            f"{verdict} Column '{column}': {missing_count}/{total_count} missing "
            f"({pct_missing:.1f}%) — score {score:.3f} "
            f"({'≥' if status == 'passed' else '<'} threshold {threshold:.3f})."
        )

    def _build_result(
        self,
        rule: QualityRule,
        column: str,
        score: float,
        threshold: Threshold,
        failed_count: int,
        total_count: int,
        message: str,
        failed_row_indices: tuple[int, ...] = (),
    ) -> CheckResult:
        """Construct the CheckResult value object."""
        return CheckResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=self.rule_type,
            column=column,
            status=self._determine_status(score, threshold),
            score=score,
            threshold=threshold,
            failed_count=failed_count,
            total_count=total_count,
            severity=rule.severity,
            message=message,
            failed_row_indices=failed_row_indices,
        )
