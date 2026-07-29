"""Unit tests for CompletenessRule."""

from __future__ import annotations

import pytest

from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.rules.completeness import CompletenessRule


@pytest.fixture()
def rule() -> CompletenessRule:
    return CompletenessRule()


class TestCompletenessRulePassing:
    """Tests where the rule should pass."""

    def test_fully_complete_column_passes(
        self, rule: CompletenessRule, dataset_valid: Dataset, completeness_rule: QualityRule
    ) -> None:
        result = rule.check(completeness_rule, dataset_valid, default_threshold=0.95)
        assert result.passed
        assert result.score == 1.0
        assert result.failed_count == 0

    def test_score_above_threshold_passes(self, rule: CompletenessRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("email",),
            row_count=10,
            data={"email": ["a@b.com"] * 9 + [None]},  # 90% complete
        )
        quality_rule = QualityRule(
            id="r1", name="r", rule_type="completeness", column="email", threshold=0.80
        )
        result = rule.check(quality_rule, dataset, default_threshold=0.95)
        assert result.passed
        assert pytest.approx(result.score, abs=1e-3) == 0.90

    def test_empty_dataset_is_vacuously_complete(self, rule: CompletenessRule) -> None:
        dataset = Dataset(
            source_path="test.csv", columns=("email",), row_count=0, data={"email": []}
        )
        quality_rule = QualityRule(
            id="r1", name="r", rule_type="completeness", column="email", threshold=0.95
        )
        result = rule.check(quality_rule, dataset, default_threshold=0.95)
        assert result.passed
        assert result.score == 1.0


class TestCompletenessRuleFailing:
    """Tests where the rule should fail."""

    def test_column_with_nulls_fails(
        self,
        rule: CompletenessRule,
        dataset_with_nulls: Dataset,
        completeness_rule: QualityRule,
    ) -> None:
        # dataset_with_nulls has 2 Nones and 1 whitespace in 'email' (3/5 missing)
        quality_rule = QualityRule(
            id="r1",
            name="email_completeness",
            rule_type="completeness",
            column="email",
            threshold=0.95,
            severity="error",
        )
        result = rule.check(quality_rule, dataset_with_nulls, default_threshold=0.95)
        assert result.failed
        assert result.failed_count == 3  # None, None, whitespace-only
        assert pytest.approx(result.score, abs=1e-3) == 0.40

    def test_whitespace_only_counted_as_missing(self, rule: CompletenessRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("name",),
            row_count=3,
            data={"name": ["Alice", "   ", ""]},
        )
        quality_rule = QualityRule(
            id="r1", name="r", rule_type="completeness", column="name", threshold=1.0
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.failed
        assert result.failed_count == 2


class TestCompletenessRuleSkipping:
    """Tests for the skip behaviour when column is absent."""

    def test_missing_column_produces_skipped_result(
        self, rule: CompletenessRule, dataset_valid: Dataset
    ) -> None:
        quality_rule = QualityRule(
            id="r1",
            name="nonexistent_col_rule",
            rule_type="completeness",
            column="nonexistent_column",
            threshold=0.95,
        )
        result = rule.check(quality_rule, dataset_valid, default_threshold=0.95)
        assert result.status == "skipped"
        assert "not found" in result.message.lower()


class TestCompletenessRuleMetadata:
    """Tests for CheckResult metadata correctness."""

    def test_result_carries_correct_rule_metadata(
        self, rule: CompletenessRule, dataset_valid: Dataset, completeness_rule: QualityRule
    ) -> None:
        result = rule.check(completeness_rule, dataset_valid, default_threshold=0.95)
        assert result.rule_id == completeness_rule.id
        assert result.rule_name == completeness_rule.name
        assert result.rule_type == "completeness"
        assert result.severity == completeness_rule.severity

    def test_threshold_from_rule_takes_priority(self, rule: CompletenessRule, dataset_valid: Dataset) -> None:
        quality_rule = QualityRule(
            id="r1", name="r", rule_type="completeness", column="email", threshold=0.50
        )
        result = rule.check(quality_rule, dataset_valid, default_threshold=0.99)
        # Rule threshold (0.50) should be used, not the default (0.99)
        assert result.threshold == 0.50
