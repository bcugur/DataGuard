"""FileRuleRepository — IRuleRepository implementation using YAML files.

Loads QualityRule definitions from a YAML file that follows the DataGuard
rule schema (version 1.0). Validates each rule entry before constructing
the domain object to give clear, actionable error messages on misconfiguration.

Expected YAML structure:
    version: "1.0"
    rules:
      - id: rule_001
        name: email_completeness
        type: completeness
        column: email
        threshold: 0.95
        severity: error

      - id: rule_002
        name: status_validity
        type: validity
        column: status
        validator: enum
        params:
          allowed_values: [active, inactive, pending]
        severity: warning
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.ports.repository_port import IRuleRepository
from dataguard.shared.exceptions import (
    InvalidRuleSchemaError,
    RuleLoadError,
    UnknownRuleTypeError,
)
from dataguard.shared.logging import get_logger
from dataguard.shared.types import SUPPORTED_FILE_EXTENSIONS, YAML_RULE_VERSION

logger = get_logger(__name__)

# Required fields every rule entry must have.
_REQUIRED_FIELDS = {"id", "name", "type"}

# Valid severity values.
_VALID_SEVERITIES = {"error", "warning", "info"}

# Valid rule types in MVP.
_VALID_RULE_TYPES = {"completeness", "uniqueness", "validity"}


class FileRuleRepository(IRuleRepository):
    """Loads QualityRule objects from a YAML file on disk.

    Implements ``IRuleRepository``. Performs schema validation on each
    rule entry and converts raw YAML dicts into QualityRule domain objects.
    """

    def load(self, path: Path) -> list[QualityRule]:
        """Parse the YAML file and return a list of QualityRule objects.

        Args:
            path: Path to the YAML rule definition file.

        Returns:
            list[QualityRule]: Ordered list of validated rule objects.

        Raises:
            RuleLoadError: If the file cannot be read or is not valid YAML.
            InvalidRuleSchemaError: If a rule entry is missing required fields.
            UnknownRuleTypeError: If a rule specifies an unsupported type.
        """
        if not path.exists():
            raise RuleLoadError(
                message=f"Rules file not found: '{path}'",
                context={"path": str(path)},
            )

        logger.debug("Loading rules from '%s'.", path.name)

        try:
            with path.open(encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise RuleLoadError(
                message=f"Failed to parse YAML rules file '{path}': {exc}",
                context={"path": str(path), "reason": str(exc)},
            ) from exc

        if not isinstance(raw, dict):
            raise RuleLoadError(
                message=f"Rules file '{path}' must be a YAML mapping at the top level.",
                context={"path": str(path)},
            )

        self._validate_version(raw, path)

        raw_rules: list[dict[str, Any]] = raw.get("rules", [])
        if not raw_rules:
            logger.warning("Rules file '%s' contains no rules.", path.name)
            return []

        rules: list[QualityRule] = []
        for entry in raw_rules:
            rule = self._parse_rule(entry)
            rules.append(rule)

        logger.info("Loaded %d rule(s) from '%s'.", len(rules), path.name)
        return rules

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _validate_version(raw: dict[str, Any], path: Path) -> None:
        """Warn if the file version does not match the expected schema version.

        Args:
            raw: Parsed top-level YAML dict.
            path: Source path (for error context).
        """
        file_version = str(raw.get("version", ""))
        if file_version and file_version != YAML_RULE_VERSION:
            logger.warning(
                "Rules file '%s' declares version '%s'; expected '%s'. "
                "Proceeding, but some fields may be ignored.",
                path.name,
                file_version,
                YAML_RULE_VERSION,
            )

    @staticmethod
    def _parse_rule(entry: dict[str, Any]) -> QualityRule:
        """Convert a raw YAML dict to a QualityRule domain object.

        Args:
            entry: One rule entry from the YAML ``rules`` list.

        Returns:
            QualityRule: Validated, immutable rule object.

        Raises:
            InvalidRuleSchemaError: If required fields are missing.
            UnknownRuleTypeError: If the rule type is not supported.
        """
        rule_id = str(entry.get("id", "<unknown>"))

        # Validate required fields.
        missing = [f for f in _REQUIRED_FIELDS if f not in entry]
        if missing:
            raise InvalidRuleSchemaError(rule_id=rule_id, missing_fields=missing)

        rule_type = str(entry["type"]).lower()
        if rule_type not in _VALID_RULE_TYPES:
            raise UnknownRuleTypeError(
                rule_type=rule_type,
                supported=tuple(_VALID_RULE_TYPES),
            )

        severity = str(entry.get("severity", "error")).lower()
        if severity not in _VALID_SEVERITIES:
            logger.warning(
                "Rule '%s' has unknown severity '%s'; defaulting to 'error'.",
                rule_id,
                severity,
            )
            severity = "error"

        # Normalise column(s).
        column: str | None = entry.get("column")
        columns_raw = entry.get("columns", [])
        columns: tuple[str, ...] = tuple(str(c) for c in columns_raw)

        # Threshold.
        raw_threshold = entry.get("threshold")
        threshold: float | None = float(raw_threshold) if raw_threshold is not None else None

        # Validity-specific fields.
        validator_type = entry.get("validator") or entry.get("validator_type")
        params: dict[str, Any] = entry.get("params", {}) or {}

        return QualityRule(
            id=rule_id,
            name=str(entry["name"]),
            rule_type=rule_type,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            column=column,
            columns=columns,
            threshold=threshold,
            validator_type=validator_type,  # type: ignore[arg-type]
            params=params,
        )
