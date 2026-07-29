"""Unit tests for ValidationReport aggregate."""

from __future__ import annotations

import pytest

from dataguard.domain.entities.report import ValidationReport


class TestValidationReportAggregates:
    def test_empty_report_has_zero_totals(self, empty_report: ValidationReport) -> None:
        assert empty_report.total_rules == 0
        assert empty_report.passed_rules == 0
        assert empty_report.failed_rules == 0

    def test_empty_report_overall_score_is_one(self, empty_report: ValidationReport) -> None:
        assert empty_report.overall_score == 1.0

    def test_empty_report_overall_status_is_passed(self, empty_report: ValidationReport) -> None:
        assert empty_report.overall_status == "passed"

    def test_add_passed_result_increments_passed(
        self, empty_report: ValidationReport, passed_check_result: object
    ) -> None:
        empty_report.add_result(passed_check_result)  # type: ignore[arg-type]
        assert empty_report.total_rules == 1
        assert empty_report.passed_rules == 1
        assert empty_report.failed_rules == 0

    def test_add_failed_error_result_changes_status_to_failed(
        self, empty_report: ValidationReport, failed_check_result: object
    ) -> None:
        empty_report.add_result(failed_check_result)  # type: ignore[arg-type]
        assert empty_report.overall_status == "failed"
        assert len(empty_report.blocking_failures) == 1

    def test_results_returns_copy(
        self, empty_report: ValidationReport, passed_check_result: object
    ) -> None:
        """Mutating the returned list must not affect the report."""
        empty_report.add_result(passed_check_result)  # type: ignore[arg-type]
        results_copy = empty_report.results
        results_copy.clear()
        assert empty_report.total_rules == 1  # original unchanged

    def test_overall_score_is_mean(
        self, empty_report: ValidationReport, passed_check_result: object, failed_check_result: object
    ) -> None:
        empty_report.add_result(passed_check_result)  # type: ignore[arg-type]  # score=1.0
        empty_report.add_result(failed_check_result)  # type: ignore[arg-type]  # score=0.8
        assert pytest.approx(empty_report.overall_score, abs=1e-4) == 0.90

    def test_to_dict_has_expected_keys(
        self, empty_report: ValidationReport, passed_check_result: object
    ) -> None:
        empty_report.add_result(passed_check_result)  # type: ignore[arg-type]
        d = empty_report.to_dict()
        assert "report_id" in d
        assert "summary" in d
        assert "results" in d
        summary = d["summary"]
        assert isinstance(summary, dict)
        assert "overall_status" in summary
        assert "overall_score" in summary
