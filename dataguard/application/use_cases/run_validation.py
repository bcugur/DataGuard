"""RunValidationUseCase — core orchestration logic.

This use case is the heart of DataGuard. It coordinates all domain objects
and infrastructure ports to execute a full validation run:

    1. Load quality rules from the repository
    2. Read the data source into a Dataset
    3. Select the appropriate rule executor for each rule
    4. Execute each rule and collect CheckResults
    5. Build the ValidationReport aggregate
    6. Write the report to disk
    7. Notify the user
    8. Return a ValidationResponse DTO to the caller

Design decisions
----------------
- All dependencies are injected via __init__ (Dependency Inversion).
- The use case has no knowledge of file formats, YAML parsing, or
  terminal rendering — those are infrastructure concerns.
- A RuleRegistry dict maps rule_type strings to AbstractQualityRule
  instances, making it easy to add new rule types without modifying
  this class (Open/Closed Principle).
"""

from __future__ import annotations

from pathlib import Path

from dataguard.application.dtos.validation_request import ValidationRequest
from dataguard.application.dtos.validation_response import (
    CheckResultSummary,
    ValidationResponse,
)
from dataguard.domain.entities.check_result import CheckResult
from dataguard.domain.entities.report import ValidationReport
from dataguard.domain.ports.notifier_port import INotifier
from dataguard.domain.ports.reader_port import IDataReader
from dataguard.domain.ports.repository_port import IRuleRepository
from dataguard.domain.ports.writer_port import IReportWriter
from dataguard.domain.rules.base import AbstractQualityRule
from dataguard.domain.rules.completeness import CompletenessRule
from dataguard.domain.rules.uniqueness import UniquenessRule
from dataguard.domain.rules.validity import ValidityRule
from dataguard.shared.config import get_settings
from dataguard.shared.exceptions import UnknownRuleTypeError
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Rule registry — maps rule_type string → executor instance
# To add a new rule type: implement AbstractQualityRule and add it here.
# ---------------------------------------------------------------------------
_RULE_REGISTRY: dict[str, AbstractQualityRule] = {
    "completeness": CompletenessRule(),
    "uniqueness": UniquenessRule(),
    "validity": ValidityRule(),
}


class RunValidationUseCase:
    """Orchestrate a full data quality validation run.

    This is the single use case in the MVP. It accepts a ValidationRequest
    (from the CLI), delegates to infrastructure ports for I/O, applies
    domain rules, and returns a ValidationResponse.

    Args:
        reader: Adapter that reads the source data file into a Dataset.
        rule_repository: Adapter that loads QualityRule definitions.
        report_writer: Adapter that serialises the ValidationReport.
        notifier: Adapter that communicates the result to the user.
    """

    def __init__(
        self,
        reader: IDataReader,
        rule_repository: IRuleRepository,
        report_writer: IReportWriter,
        notifier: INotifier,
    ) -> None:
        self._reader = reader
        self._rule_repository = rule_repository
        self._report_writer = report_writer
        self._notifier = notifier
        self._settings = get_settings()

    def execute(self, request: ValidationRequest) -> ValidationResponse:
        """Run the validation pipeline end-to-end.

        Args:
            request: Validated input DTO carrying source and rules paths.

        Returns:
            ValidationResponse: Summary DTO for the CLI to render and act on.

        Raises:
            DataReadError: If the data source cannot be read.
            RuleLoadError: If the rules file cannot be parsed.
            ValidationExecutionError: If a rule fails unexpectedly.
            ReportWriteError: If the report cannot be saved.
        """
        logger.info(
            "Starting validation — source='%s' rules='%s'",
            request.source_path.name,
            request.rules_path.name,
        )

        # ── Step 1: Load rules ─────────────────────────────────────────────
        rules = self._rule_repository.load(request.rules_path)
        logger.info("Loaded %d rule(s) from '%s'.", len(rules), request.rules_path.name)

        # ── Step 2: Read data ──────────────────────────────────────────────
        dataset = self._reader.read(request.source_path)
        logger.info(
            "Dataset loaded — rows=%d columns=%d source='%s'.",
            dataset.row_count,
            dataset.column_count,
            dataset.source_name,
        )

        # ── Step 3: Initialise report aggregate ───────────────────────────
        report = ValidationReport(
            source_path=str(request.source_path),
            rules_path=str(request.rules_path),
        )

        # ── Step 4: Execute each rule ──────────────────────────────────────
        default_threshold = self._settings.default_threshold

        for rule in rules:
            executor = _RULE_REGISTRY.get(rule.rule_type)
            if executor is None:
                raise UnknownRuleTypeError(
                    rule_type=rule.rule_type,
                    supported=tuple(_RULE_REGISTRY.keys()),
                )

            result: CheckResult = executor.check(rule, dataset, default_threshold)
            report.add_result(result)
            logger.debug(
                "Rule '%s' → %s (score=%.3f)",
                rule.name,
                result.status.upper(),
                result.score,
            )

        logger.info(
            "Validation complete — status=%s score=%.3f passed=%d failed=%d",
            report.overall_status.upper(),
            report.overall_score,
            report.passed_rules,
            report.failed_rules,
        )

        # ── Step 5: Write report ───────────────────────────────────────────
        report_path = self._report_writer.write(report, request.report_dir)
        logger.info("Report saved to '%s'.", report_path)

        # ── Step 6: Notify ─────────────────────────────────────────────────
        self._notifier.notify(report)

        # ── Step 7: Build and return response DTO ─────────────────────────
        return self._build_response(report, report_path)

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _build_response(
        report: ValidationReport,
        report_path: Path,
    ) -> ValidationResponse:
        """Convert the domain aggregate to a response DTO.

        Args:
            report: The fully populated ValidationReport.
            report_path: Path where the JSON report was written.

        Returns:
            ValidationResponse DTO for the CLI layer.
        """
        result_summaries = [
            CheckResultSummary(
                rule_id=r.rule_id,
                rule_name=r.rule_name,
                rule_type=r.rule_type,
                column=r.column,
                status=r.status,
                score=r.score,
                threshold=r.threshold,
                failed_count=r.failed_count,
                total_count=r.total_count,
                severity=r.severity,
                message=r.message,
            )
            for r in report.results
        ]

        return ValidationResponse(
            report_id=report.report_id,
            source_name=report.source_name,
            overall_status=report.overall_status,
            overall_score=report.overall_score,
            total_rules=report.total_rules,
            passed_rules=report.passed_rules,
            failed_rules=report.failed_rules,
            skipped_rules=report.skipped_rules,
            results=result_summaries,
            report_path=report_path,
        )
