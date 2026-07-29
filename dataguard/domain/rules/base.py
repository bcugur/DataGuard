"""AbstractQualityRule — base class for all quality rule implementations.

Concrete rule classes (CompletenessRule, UniquenessRule, ValidityRule)
inherit from AbstractQualityRule and implement the ``_execute()`` hook.
The public ``check()`` method provides the uniform contract consumed by
the application layer.

Design
------
- Template Method Pattern: check() handles pre/post concerns (logging,
  skipping missing columns, wrapping exceptions) while _execute() contains
  the pure rule logic.
- Each subclass is responsible for one rule type only (SRP).
- Rules never mutate the Dataset — they only read from it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from dataguard.domain.entities.check_result import CheckResult
from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.rule import QualityRule
from dataguard.shared.exceptions import ValidationExecutionError
from dataguard.shared.logging import get_logger
from dataguard.shared.types import CheckStatus, RuleType, Threshold

logger = get_logger(__name__)


class AbstractQualityRule(ABC):
    """Template base class for quality rule executors.

    Each concrete subclass corresponds to one ``RuleType`` value and knows
    how to evaluate that type of rule against a Dataset.

    Subclasses must implement:
        - ``rule_type`` class attribute (declares which type it handles)
        - ``_execute()`` method (contains the actual check logic)

    The public ``check()`` method orchestrates:
        1. Column existence validation (skip if missing)
        2. Delegation to ``_execute()``
        3. Exception wrapping to ``ValidationExecutionError``
        4. Debug logging
    """

    #: Subclasses declare which RuleType they handle.
    rule_type: RuleType

    def check(self, rule: QualityRule, dataset: Dataset, default_threshold: Threshold) -> CheckResult:
        """Execute the quality rule against the dataset.

        This is the public entry point called by the application layer.
        It applies the Template Method pattern: common concerns are handled
        here; rule-specific logic is in ``_execute()``.

        Args:
            rule: The rule definition to execute.
            dataset: The loaded dataset to validate.
            default_threshold: Fallback threshold if the rule has none.

        Returns:
            CheckResult: The outcome of executing this rule.

        Raises:
            ValidationExecutionError: If an unexpected error occurs during
                rule execution (wraps the original exception).
        """
        threshold = rule.effective_threshold(default_threshold)

        # Skip the rule if the target column doesn't exist in the dataset.
        for column in rule.target_columns:
            if not dataset.has_column(column):
                logger.warning(
                    "Skipping rule '%s': column '%s' not found in dataset '%s'.",
                    rule.name,
                    column,
                    dataset.source_name,
                )
                return self._make_skipped_result(rule, threshold, column)

        try:
            result = self._execute(rule, dataset, threshold)
        except ValidationExecutionError:
            raise  # already wrapped — re-raise as-is
        except Exception as exc:
            raise ValidationExecutionError(
                rule_id=rule.id,
                reason=str(exc),
            ) from exc

        logger.debug(
            "Rule '%s' → status=%s score=%.3f threshold=%.3f",
            rule.name,
            result.status,
            result.score,
            result.threshold,
        )
        return result

    @abstractmethod
    def _execute(
        self,
        rule: QualityRule,
        dataset: Dataset,
        threshold: Threshold,
    ) -> CheckResult:
        """Perform the rule-specific validation logic.

        Subclasses implement this method. All preconditions (column existence,
        threshold resolution) are guaranteed by ``check()`` before this is called.

        Args:
            rule: The rule definition.
            dataset: The validated dataset (columns are guaranteed present).
            threshold: The resolved threshold (never None).

        Returns:
            CheckResult: The result of the check.
        """

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _determine_status(score: float, threshold: Threshold) -> CheckStatus:
        """Return 'passed' if score >= threshold, else 'failed'.

        Args:
            score: Achieved quality score.
            threshold: Required minimum score.

        Returns:
            CheckStatus literal.
        """
        return "passed" if score >= threshold else "failed"

    @staticmethod
    def _make_skipped_result(
        rule: QualityRule,
        threshold: Threshold,
        missing_column: str,
    ) -> CheckResult:
        """Build a CheckResult with status='skipped' for a missing column.

        Args:
            rule: The rule that was skipped.
            threshold: The resolved threshold for this rule.
            missing_column: The column that was not found.

        Returns:
            CheckResult with score=0.0, failed_count=0, total_count=0.
        """
        return CheckResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            column=missing_column,
            status="skipped",
            score=0.0,
            threshold=threshold,
            failed_count=0,
            total_count=0,
            severity=rule.severity,
            message=f"Column '{missing_column}' not found in dataset — rule skipped.",
        )
