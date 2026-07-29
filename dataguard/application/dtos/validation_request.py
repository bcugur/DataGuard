"""ValidationRequest DTO.

Carries the raw user input (CLI arguments) into the application layer.
Validated by pydantic so the use case receives clean, typed data.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, field_validator, model_validator


class ValidationRequest(BaseModel):
    """Immutable input DTO for the RunValidationUseCase.

    Created by the CLI delivery layer from parsed command-line arguments
    and passed directly to RunValidationUseCase.execute().

    Attributes:
        source_path: Path to the data file to validate (CSV or JSON).
        rules_path: Path to the YAML file containing rule definitions.
        report_dir: Directory where the JSON report will be saved.
            Defaults to ``Path('reports')``.
        verbose: If True, the notifier produces detailed per-row output.

    Raises:
        ValueError: If ``source_path`` or ``rules_path`` do not exist.
        ValueError: If ``source_path`` has an unsupported extension.
    """

    model_config = {"frozen": True}

    source_path: Path
    rules_path: Path
    report_dir: Path = Path("reports")
    verbose: bool = False

    @field_validator("source_path")
    @classmethod
    def source_must_exist(cls, value: Path) -> Path:
        """Ensure the data source file exists on disk."""
        if not value.exists():
            raise ValueError(f"Data source file not found: '{value}'")
        return value

    @field_validator("rules_path")
    @classmethod
    def rules_must_exist(cls, value: Path) -> Path:
        """Ensure the rules file exists on disk."""
        if not value.exists():
            raise ValueError(f"Rules file not found: '{value}'")
        return value

    @field_validator("source_path")
    @classmethod
    def source_extension_supported(cls, value: Path) -> Path:
        """Ensure the data source has a supported file extension."""
        from dataguard.shared.types import SUPPORTED_FILE_EXTENSIONS

        if value.suffix.lower() not in SUPPORTED_FILE_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension '{value.suffix}'. "
                f"Supported: {SUPPORTED_FILE_EXTENSIONS}"
            )
        return value

    @model_validator(mode="after")
    def report_dir_created(self) -> "ValidationRequest":
        """Create the report output directory if it does not exist."""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        return self
