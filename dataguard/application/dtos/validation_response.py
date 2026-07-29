"""ValidationResponse DTO.

Carries the validation outcome from the application layer back to the
delivery (CLI) layer. Decouples the CLI from ValidationReport internals.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dataguard.shared.types import OverallStatus


class CheckResultSummary(BaseModel):
    """Lightweight summary of a single rule result for the response DTO.

    Attributes:
        rule_id: Identifier of the executed rule.
        rule_name: Human-readable rule name.
        rule_type: Category (completeness, uniqueness, validity).
        column: Target column, or None for multi-column rules.
        status: passed | failed | skipped.
        score: Achieved quality score (0.0–1.0).
        threshold: Required minimum score.
        failed_count: Number of rows that failed this rule.
        total_count: Total rows evaluated.
        severity: error | warning | info.
        message: Human-readable explanation.
    """

    model_config = ConfigDict(frozen=True)

    rule_id: str
    rule_name: str
    rule_type: str
    column: str | None
    status: str
    score: float
    threshold: float
    failed_count: int
    total_count: int
    severity: str
    message: str


class ValidationResponse(BaseModel):
    """Output DTO returned by RunValidationUseCase.execute().

    The CLI layer uses this DTO to render output and set the process
    exit code. It never touches the ValidationReport aggregate directly.

    Attributes:
        report_id: UUID of the validation run.
        source_name: Filename of the validated data source.
        overall_status: 'passed' or 'failed'.
        overall_score: Mean quality score across all rules.
        total_rules: Number of rules executed.
        passed_rules: Number of rules that passed.
        failed_rules: Number of rules that failed.
        skipped_rules: Number of rules that were skipped.
        results: Per-rule result summaries.
        report_path: Path to the written JSON report file.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str
    source_name: str
    overall_status: OverallStatus
    overall_score: float
    total_rules: int
    passed_rules: int
    failed_rules: int
    skipped_rules: int
    results: list[CheckResultSummary]
    report_path: Path

    @property
    def succeeded(self) -> bool:
        """Return True if the overall validation passed."""
        return self.overall_status == "passed"
