"""Application configuration via environment variables.

Uses pydantic-settings to read values from environment variables or a .env
file. The DATAGUARD_ prefix namespaces all settings to avoid collisions.

Usage
-----
    from dataguard.shared.config import get_settings

    settings = get_settings()
    print(settings.log_level)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from dataguard.shared.types import MAX_THRESHOLD, MIN_THRESHOLD


class DataGuardSettings(BaseSettings):
    """Typed, validated application settings.

    All fields are read from environment variables prefixed with DATAGUARD_.
    Falls back to .env file if the variable is not set in the shell.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DATAGUARD_",
        case_sensitive=False,
        extra="ignore",  # silently ignore unknown env vars
    )

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Logging verbosity level (DEBUG | INFO | WARNING | ERROR | CRITICAL).",
    )

    # ── Output ────────────────────────────────────────────────────────────
    report_output_dir: Path = Field(
        default=Path("reports"),
        description="Directory where generated JSON reports are saved.",
    )

    # ── Validation defaults ────────────────────────────────────────────────
    default_threshold: float = Field(
        default=0.95,
        ge=MIN_THRESHOLD,
        le=MAX_THRESHOLD,
        description="Default minimum quality threshold for rules that do not specify one.",
    )

    # ── Validators ────────────────────────────────────────────────────────

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Ensure log_level is one of the standard Python logging levels."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(
                f"Invalid log level '{value}'. Allowed values: {sorted(allowed)}"
            )
        return upper

    @field_validator("report_output_dir")
    @classmethod
    def ensure_report_dir_exists(cls, value: Path) -> Path:
        """Create the report output directory if it does not already exist."""
        value.mkdir(parents=True, exist_ok=True)
        return value


@lru_cache(maxsize=1)
def get_settings() -> DataGuardSettings:
    """Return the application settings singleton.

    The result is cached so that environment variables and .env files
    are read only once per process lifetime. Call get_settings.cache_clear()
    in tests to reset between test cases.

    Returns:
        DataGuardSettings: Validated, immutable settings object.
    """
    return DataGuardSettings()
