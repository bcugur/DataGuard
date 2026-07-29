"""Semantic type aliases and domain-wide constants.

This module defines type aliases and constants used across all layers.
Using NewType and TypeAlias improves readability and makes intent explicit.
No external dependencies — only stdlib typing constructs.
"""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

# ---------------------------------------------------------------------------
# Semantic type aliases
# Plain strings/floats with meaningful names for function signatures.
# ---------------------------------------------------------------------------

RuleId: TypeAlias = str
"""Unique identifier for a quality rule (e.g. 'rule_001')."""

RuleName: TypeAlias = str
"""Human-readable name for a quality rule (e.g. 'email_completeness')."""

ColumnName: TypeAlias = str
"""A single column name inside a dataset."""

Threshold: TypeAlias = float
"""Expected minimum quality score in the range [0.0, 1.0]."""

Score: TypeAlias = float
"""Achieved quality score in the range [0.0, 1.0]."""

SourcePath: TypeAlias = str
"""File-system path to a data source file (CSV, JSON, …)."""

RulesPath: TypeAlias = str
"""File-system path to a YAML rule definition file."""

# ---------------------------------------------------------------------------
# Literal union types — used as discriminated unions across the domain
# ---------------------------------------------------------------------------

RuleType: TypeAlias = Literal["completeness", "uniqueness", "validity"]
"""Supported quality rule categories in MVP."""

Severity: TypeAlias = Literal["error", "warning", "info"]
"""Impact level of a failing rule.

- error  : blocks overall validation (overall_status → 'failed')
- warning: noted but does not block
- info   : informational only
"""

CheckStatus: TypeAlias = Literal["passed", "failed", "skipped"]
"""Result status of a single rule execution."""

OverallStatus: TypeAlias = Literal["passed", "failed"]
"""Aggregate validation outcome for an entire report."""

ValidatorType: TypeAlias = Literal[
    "regex", "enum", "dtype", "range",
    "tckn", "tc_kimlik", "vkn", "vergi_no",
    "tr_iban", "iban", "phone_tr", "telefon"
]
"""Supported sub-validators for ValidityRule."""

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

MIN_THRESHOLD: Final[float] = 0.0
MAX_THRESHOLD: Final[float] = 1.0

MIN_SCORE: Final[float] = 0.0
MAX_SCORE: Final[float] = 1.0

SUPPORTED_FILE_EXTENSIONS: Final[tuple[str, ...]] = (".csv", ".json", ".xlsx", ".xls")
"""File extensions supported by the infrastructure readers in DataGuard."""

YAML_RULE_VERSION: Final[str] = "1.0"
"""Expected 'version' field value in a rule YAML file."""
