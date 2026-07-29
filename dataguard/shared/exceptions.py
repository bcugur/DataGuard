"""DataGuard exception hierarchy.

All custom exceptions inherit from DataGuardError so that callers can catch
the entire family with a single except clause, or catch specific subtypes
for fine-grained error handling.

Hierarchy
---------
DataGuardError
├── ConfigurationError
├── DataReadError
│   ├── FileNotFoundDataError
│   └── UnsupportedFormatError
├── RuleLoadError
│   ├── InvalidRuleSchemaError
│   └── UnknownRuleTypeError
├── ValidationExecutionError
└── ReportWriteError
"""

from __future__ import annotations


class DataGuardError(Exception):
    """Base class for all DataGuard exceptions.

    Args:
        message: Human-readable description of the error.
        context: Optional dict with diagnostic key-value pairs.
    """

    def __init__(self, message: str, context: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, object] = context or {}

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} [{ctx_str}]"
        return self.message


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class ConfigurationError(DataGuardError):
    """Raised when the application configuration is invalid or incomplete.

    Example triggers:
    - Missing required environment variable.
    - Threshold value outside [0.0, 1.0].
    """


# ---------------------------------------------------------------------------
# Data reading errors
# ---------------------------------------------------------------------------


class DataReadError(DataGuardError):
    """Raised when a data source cannot be read or parsed."""


class FileNotFoundDataError(DataReadError):
    """Raised when the specified data file does not exist on disk.

    Args:
        path: The file-system path that was not found.
    """

    def __init__(self, path: str) -> None:
        super().__init__(
            message=f"Data file not found: '{path}'",
            context={"path": path},
        )


class UnsupportedFormatError(DataReadError):
    """Raised when the data file has an extension DataGuard cannot read.

    Args:
        extension: The file extension that is not supported (e.g. '.xlsx').
        supported: Tuple of extensions that ARE supported.
    """

    def __init__(self, extension: str, supported: tuple[str, ...]) -> None:
        super().__init__(
            message=(
                f"Unsupported file format '{extension}'. "
                f"Supported formats: {', '.join(supported)}"
            ),
            context={"extension": extension, "supported": list(supported)},
        )


# ---------------------------------------------------------------------------
# Rule loading errors
# ---------------------------------------------------------------------------


class RuleLoadError(DataGuardError):
    """Raised when rule definitions cannot be loaded or parsed."""


class InvalidRuleSchemaError(RuleLoadError):
    """Raised when a rule definition is missing required fields.

    Args:
        rule_id: The rule identifier, if available.
        missing_fields: List of required fields that are absent.
    """

    def __init__(self, rule_id: str, missing_fields: list[str]) -> None:
        super().__init__(
            message=(
                f"Rule '{rule_id}' has invalid schema. "
                f"Missing required fields: {missing_fields}"
            ),
            context={"rule_id": rule_id, "missing_fields": missing_fields},
        )


class UnknownRuleTypeError(RuleLoadError):
    """Raised when a rule definition specifies an unknown rule type.

    Args:
        rule_type: The unrecognized rule type string.
        supported: Tuple of supported rule type strings.
    """

    def __init__(self, rule_type: str, supported: tuple[str, ...]) -> None:
        super().__init__(
            message=(
                f"Unknown rule type '{rule_type}'. "
                f"Supported types: {', '.join(supported)}"
            ),
            context={"rule_type": rule_type, "supported": list(supported)},
        )


# ---------------------------------------------------------------------------
# Validation execution errors
# ---------------------------------------------------------------------------


class ValidationExecutionError(DataGuardError):
    """Raised when an unexpected error occurs while executing a rule.

    Args:
        rule_id: Identifier of the rule that failed to execute.
        reason: Technical description of the failure.
    """

    def __init__(self, rule_id: str, reason: str) -> None:
        super().__init__(
            message=f"Rule '{rule_id}' failed to execute: {reason}",
            context={"rule_id": rule_id, "reason": reason},
        )


# ---------------------------------------------------------------------------
# Report writing errors
# ---------------------------------------------------------------------------


class ReportWriteError(DataGuardError):
    """Raised when a validation report cannot be written to disk.

    Args:
        destination: The file path that could not be written.
        reason: Technical description of the failure.
    """

    def __init__(self, destination: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to write report to '{destination}': {reason}",
            context={"destination": destination, "reason": reason},
        )
