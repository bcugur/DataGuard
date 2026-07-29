"""UniquenessRule — checks for duplicate values in one or more columns.

A column (or column combination) is considered "unique" if the fraction
of non-duplicate rows meets or exceeds the configured threshold.

Score formula:
    unique_count = number of rows whose column combination is distinct
    score = unique_count / total_count

Example YAML (single column):
    - id: rule_002
      name: user_id_unique
      type: uniqueness
      column: user_id
      threshold: 1.0
      severity: error

Example YAML (composite key):
    - id: rule_003
      name: order_line_unique
      type: uniqueness
      columns: [order_id, line_number]
      threshold: 1.0
      severity: error
"""

from __future__ import annotations

from dataguard.domain.entities.check_result import CheckResult
from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.rules.base import AbstractQualityRule
from dataguard.shared.types import Threshold


class UniquenessRule(AbstractQualityRule):
    """Validates that a column or column combination has no duplicate values.

    The rule supports both single-column and composite-key uniqueness checks.
    Rows that share identical values across all ``target_columns`` are counted
    as duplicates; only the first occurrence is counted as unique.

    Attributes:
        rule_type: Always ``'uniqueness'``.
    """

    rule_type: str = "uniqueness"

    def _execute(
        self,
        rule: QualityRule,
        dataset: Dataset,
        threshold: Threshold,
    ) -> CheckResult:
        """Count duplicate rows for the target column(s) and compute a score.

        Args:
            rule: The uniqueness rule definition. All target columns are
                guaranteed present in ``dataset`` by the base class.
            dataset: The dataset to evaluate.
            threshold: Resolved minimum uniqueness score.

        Returns:
            CheckResult with the uniqueness score and pass/fail verdict.
        """
        target_columns = rule.target_columns
        # Represent each row as a tuple of values across all target columns.
        rows: list[tuple[object, ...]] = [
            tuple(dataset.get_column_values(col)[i] for col in target_columns)
            for i in range(dataset.row_count)
        ]

        total_count = len(rows)

        if total_count == 0:
            return self._build_result(
                rule=rule,
                columns=target_columns,
                score=1.0,
                threshold=threshold,
                failed_count=0,
                total_count=0,
                message="Column has no rows — vacuously unique.",
            )

        seen: set[tuple[object, ...]] = set()
        duplicate_count = 0
        failed_row_indices_list: list[int] = []
        for i, row in enumerate(rows):
            if row in seen:
                duplicate_count += 1
                failed_row_indices_list.append(i)
            else:
                seen.add(row)

        failed_row_indices = tuple(failed_row_indices_list)
        unique_count = total_count - duplicate_count
        score = unique_count / total_count if total_count > 0 else 1.0

        status = self._determine_status(score, threshold)
        col_label = (
            target_columns[0] if len(target_columns) == 1
            else f"({', '.join(target_columns)})"
        )
        pct_dup = (duplicate_count / total_count) * 100
        verdict = "✓" if status == "passed" else "✗"
        message = (
            f"{verdict} Column '{col_label}': {duplicate_count}/{total_count} "
            f"duplicates ({pct_dup:.1f}%) — score {score:.3f} "
            f"({'≥' if status == 'passed' else '<'} threshold {threshold:.3f})."
        )

        return self._build_result(
            rule=rule,
            columns=target_columns,
            score=score,
            threshold=threshold,
            failed_count=duplicate_count,
            total_count=total_count,
            message=message,
            failed_row_indices=failed_row_indices,
        )

    # ── Private helper ─────────────────────────────────────────────────────

    @staticmethod
    def _build_result(
        rule: QualityRule,
        columns: tuple[str, ...],
        score: float,
        threshold: Threshold,
        failed_count: int,
        total_count: int,
        message: str,
        failed_row_indices: tuple[int, ...] = (),
    ) -> CheckResult:
        """Construct the CheckResult value object."""
        primary_column = columns[0] if len(columns) == 1 else None
        return CheckResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type="uniqueness",
            column=primary_column,
            status="passed" if score >= threshold else "failed",
            score=score,
            threshold=threshold,
            failed_count=failed_count,
            total_count=total_count,
            severity=rule.severity,
            message=message,
            failed_row_indices=failed_row_indices,
        )
