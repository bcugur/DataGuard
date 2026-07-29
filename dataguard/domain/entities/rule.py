"""QualityRule entity.

Represents the definition of a single data quality rule as configured by
the user (e.g. in a YAML file). This is a pure value object — it carries
no behaviour; execution logic lives in domain/rules/.

Design
------
- Immutable (frozen=True): rule definitions are configuration; they don't
  change during a validation run.
- ``params`` is an open dict to support rule-type-specific parameters
  (e.g. regex pattern for ValidityRule, allowed_values for enum checks)
  without polluting the base entity with type-specific fields.
- ``threshold`` defaults to None so that the application layer can
  substitute the global default from settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dataguard.shared.types import (
    ColumnName,
    RuleId,
    RuleName,
    RuleType,
    Severity,
    Threshold,
    ValidatorType,
)


@dataclass(frozen=True)
class QualityRule:
    """Immutable definition of a data quality rule.

    A QualityRule describes *what* to check. The *how* is delegated to
    a concrete AbstractQualityRule subclass in domain/rules/.

    Attributes:
        id: Unique identifier for the rule (e.g. 'rule_001').
        name: Human-readable name (e.g. 'email_completeness').
        rule_type: Category of the rule — drives which checker is selected.
        column: Primary column the rule targets. None for multi-column rules.
        columns: For rules that operate on multiple columns simultaneously.
        threshold: Minimum acceptable quality score in [0.0, 1.0].
            None means "use the application default".
        severity: Impact level when the rule fails.
        validator_type: Sub-type for ValidityRule (regex, enum, dtype, range).
            Ignored for other rule types.
        params: Rule-type-specific parameters (e.g. {'pattern': r'^\\d+$'}).

    Raises:
        ValueError: If neither ``column`` nor ``columns`` is provided.
        ValueError: If ``threshold`` is outside [0.0, 1.0].
    """

    id: RuleId
    name: RuleName
    rule_type: RuleType
    severity: Severity = "error"
    column: ColumnName | None = None
    columns: tuple[ColumnName, ...] = field(default_factory=tuple)
    threshold: Threshold | None = None
    validator_type: ValidatorType | None = None
    params: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Enforce entity invariants."""
        if self.column is None and not self.columns:
            raise ValueError(
                f"Rule '{self.id}' must specify either 'column' or 'columns'."
            )
        if self.threshold is not None and not (0.0 <= self.threshold <= 1.0):
            raise ValueError(
                f"Rule '{self.id}': threshold must be in [0.0, 1.0], "
                f"got {self.threshold}."
            )

    # ── Convenience properties ─────────────────────────────────────────────

    @property
    def target_columns(self) -> tuple[ColumnName, ...]:
        """Return all columns this rule targets (normalised to a tuple).

        If ``column`` is set, it is wrapped in a single-element tuple.
        If ``columns`` is set, it is returned directly.
        """
        if self.column is not None:
            return (self.column,)
        return self.columns

    @property
    def is_blocking(self) -> bool:
        """Return True if a failure of this rule blocks overall validation.

        Only rules with severity='error' are considered blocking.
        """
        return self.severity == "error"

    def effective_threshold(self, default: Threshold) -> Threshold:
        """Return the rule's threshold, falling back to the provided default.

        Args:
            default: Application-level default threshold from settings.

        Returns:
            The rule's own threshold, or ``default`` if none is set.
        """
        return self.threshold if self.threshold is not None else default

    def __repr__(self) -> str:
        return (
            f"QualityRule(id='{self.id}', type='{self.rule_type}', "
            f"column={self.column!r}, severity='{self.severity}')"
        )
