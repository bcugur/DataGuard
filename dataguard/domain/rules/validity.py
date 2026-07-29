"""ValidityRule — checks column values against configurable validators.

Supports four validator sub-types:
    - ``regex``  : values must match a regular expression pattern
    - ``enum``   : values must be members of an allowed set
    - ``dtype``  : values must be castable to a given Python type
    - ``range``  : numeric values must fall within [min_value, max_value]

Score formula:
    score = valid_count / total_count

Example YAML (enum):
    - id: rule_004
      name: status_validity
      type: validity
      column: status
      validator: enum
      params:
        allowed_values: [active, inactive, pending]
      threshold: 1.0
      severity: warning

Example YAML (regex):
    - id: rule_005
      name: email_format
      type: validity
      column: email
      validator: regex
      params:
        pattern: '^[\\w.+-]+@[\\w-]+\\.[\\w.]+$'
      threshold: 0.98
      severity: error

Example YAML (range):
    - id: rule_006
      name: age_range
      type: validity
      column: age
      validator: range
      params:
        min_value: 0
        max_value: 150
      threshold: 1.0
      severity: error
"""

from __future__ import annotations

import re
from typing import Any

from dataguard.domain.entities.check_result import CheckResult
from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.rules.base import AbstractQualityRule
from dataguard.shared.exceptions import InvalidRuleSchemaError
from dataguard.shared.types import Threshold

# Mapping from dtype validator param string to Python type.
_DTYPE_MAP: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
}


class ValidityRule(AbstractQualityRule):
    """Validates column values against a configurable validator.

    Delegates to one of four private validator methods based on
    ``rule.validator_type``. Each validator returns a set of
    row indices that failed the check.

    Attributes:
        rule_type: Always ``'validity'``.
    """

    rule_type: str = "validity"

    def _execute(
        self,
        rule: QualityRule,
        dataset: Dataset,
        threshold: Threshold,
    ) -> CheckResult:
        """Dispatch to the appropriate validator and compute a score.

        Args:
            rule: The validity rule definition. ``rule.validator_type``
                selects the sub-validator. ``rule.params`` supplies its
                configuration.
            dataset: The dataset to evaluate.
            threshold: Resolved minimum validity score.

        Returns:
            CheckResult with the validity score and pass/fail verdict.

        Raises:
            InvalidRuleSchemaError: If ``validator_type`` is missing or unknown.
        """
        if rule.validator_type is None:
            raise InvalidRuleSchemaError(
                rule_id=rule.id,
                missing_fields=["validator_type"],
            )

        column: str = rule.column  # type: ignore[assignment]
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
                message="Column has no rows — vacuously valid.",
            )

        failed_indices = self._validate(rule, values)
        failed_count = len(failed_indices)
        valid_count = total_count - failed_count
        score = valid_count / total_count

        status = self._determine_status(score, threshold)
        pct_invalid = (failed_count / total_count) * 100
        verdict = "✓" if status == "passed" else "✗"
        message = (
            f"{verdict} Column '{column}' [{rule.validator_type}]: "
            f"{failed_count}/{total_count} invalid ({pct_invalid:.1f}%) "
            f"— score {score:.3f} "
            f"({'≥' if status == 'passed' else '<'} threshold {threshold:.3f})."
        )

        return self._build_result(
            rule=rule,
            column=column,
            score=score,
            threshold=threshold,
            failed_count=failed_count,
            total_count=total_count,
            message=message,
        )

    # ── Dispatcher ─────────────────────────────────────────────────────────

    def _validate(self, rule: QualityRule, values: list[object]) -> set[int]:
        """Route to the correct sub-validator and return failing row indices.

        Args:
            rule: Rule definition carrying validator_type and params.
            values: List of raw column values.

        Returns:
            Set of integer indices into ``values`` that failed validation.

        Raises:
            InvalidRuleSchemaError: If the validator_type is unsupported.
        """
        validators = {
            "regex": self._validate_regex,
            "enum": self._validate_enum,
            "dtype": self._validate_dtype,
            "range": self._validate_range,
        }
        validator_fn = validators.get(rule.validator_type or "")
        if validator_fn is None:
            raise InvalidRuleSchemaError(
                rule_id=rule.id,
                missing_fields=[f"validator_type='{rule.validator_type}' (unsupported)"],
            )
        return validator_fn(values, rule.params)

    # ── Sub-validators ─────────────────────────────────────────────────────

    @staticmethod
    def _validate_regex(values: list[object], params: dict[str, Any]) -> set[int]:
        """Validate that string values match a regular expression.

        Args:
            values: Column values to check.
            params: Must contain ``'pattern'`` key with a valid regex string.

        Returns:
            Set of indices where the value does not match the pattern.
            None values are counted as failures.
        """
        pattern = re.compile(str(params.get("pattern", "")))
        failed: set[int] = set()
        for i, value in enumerate(values):
            if value is None or not pattern.fullmatch(str(value)):
                failed.add(i)
        return failed

    @staticmethod
    def _validate_enum(values: list[object], params: dict[str, Any]) -> set[int]:
        """Validate that values belong to an allowed set.

        Args:
            values: Column values to check.
            params: Must contain ``'allowed_values'`` key with a list.

        Returns:
            Set of indices where the value is not in the allowed set.
            None values are counted as failures.
        """
        allowed: set[object] = set(params.get("allowed_values", []))
        return {i for i, v in enumerate(values) if v not in allowed}

    @staticmethod
    def _validate_dtype(values: list[object], params: dict[str, Any]) -> set[int]:
        """Validate that values can be cast to the expected Python type.

        Args:
            values: Column values to check.
            params: Must contain ``'expected_type'`` key
                (one of 'int', 'float', 'str', 'bool').

        Returns:
            Set of indices where the value is not of the expected type.
            None values are counted as failures.
        """
        type_name = str(params.get("expected_type", "str"))
        expected_type = _DTYPE_MAP.get(type_name, str)
        failed: set[int] = set()
        for i, value in enumerate(values):
            if value is None:
                failed.add(i)
                continue
            try:
                expected_type(value)  # type: ignore[call-arg]
            except (ValueError, TypeError):
                failed.add(i)
        return failed

    @staticmethod
    def _validate_range(values: list[object], params: dict[str, Any]) -> set[int]:
        """Validate that numeric values fall within [min_value, max_value].

        Args:
            values: Column values to check.
            params: May contain ``'min_value'`` and/or ``'max_value'`` keys.
                Bounds are inclusive.

        Returns:
            Set of indices where the value is outside the range.
            None values and non-numeric values are counted as failures.
        """
        min_val: float | None = (
            float(params["min_value"]) if "min_value" in params else None
        )
        max_val: float | None = (
            float(params["max_value"]) if "max_value" in params else None
        )
        failed: set[int] = set()
        for i, value in enumerate(values):
            if value is None:
                failed.add(i)
                continue
            try:
                numeric = float(value)  # type: ignore[arg-type]
            except (ValueError, TypeError):
                failed.add(i)
                continue
            if min_val is not None and numeric < min_val:
                failed.add(i)
            elif max_val is not None and numeric > max_val:
                failed.add(i)
        return failed

    # ── Result builder ─────────────────────────────────────────────────────

    def _build_result(
        self,
        rule: QualityRule,
        column: str,
        score: float,
        threshold: Threshold,
        failed_count: int,
        total_count: int,
        message: str,
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
        )
