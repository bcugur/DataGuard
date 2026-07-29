"""Unit tests for UniquenessRule."""

from __future__ import annotations

import pytest

from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.rules.uniqueness import UniquenessRule


@pytest.fixture()
def rule() -> UniquenessRule:
    return UniquenessRule()


class TestUniquenessRulePassing:
    def test_all_unique_column_passes(
        self, rule: UniquenessRule, dataset_valid: Dataset
    ) -> None:
        quality_rule = QualityRule(
            id="r1", name="id_unique", rule_type="uniqueness", column="id", threshold=1.0
        )
        result = rule.check(quality_rule, dataset_valid, default_threshold=1.0)
        assert result.passed
        assert result.score == 1.0
        assert result.failed_count == 0

    def test_empty_dataset_vacuously_unique(self, rule: UniquenessRule) -> None:
        dataset = Dataset(
            source_path="test.csv", columns=("id",), row_count=0, data={"id": []}
        )
        quality_rule = QualityRule(
            id="r1", name="r", rule_type="uniqueness", column="id", threshold=1.0
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.passed
        assert result.score == 1.0


class TestUniquenessRuleFailing:
    def test_duplicate_values_fail(
        self, rule: UniquenessRule, dataset_with_duplicates: Dataset, uniqueness_rule: QualityRule
    ) -> None:
        # dataset_with_duplicates: user_id = [1, 2, 2, 3, 1] → 2 duplicates
        result = rule.check(uniqueness_rule, dataset_with_duplicates, default_threshold=1.0)
        assert result.failed
        assert result.failed_count == 2
        assert pytest.approx(result.score, abs=1e-3) == 0.60

    def test_all_duplicates_score_is_zero(self, rule: UniquenessRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("id",),
            row_count=3,
            data={"id": [1, 1, 1]},
        )
        quality_rule = QualityRule(
            id="r1", name="r", rule_type="uniqueness", column="id", threshold=1.0
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.failed
        assert result.failed_count == 2  # only first occurrence is unique
        assert pytest.approx(result.score, abs=1e-3) == pytest.approx(1 / 3)


class TestUniquenessRuleCompositeKey:
    def test_composite_key_uniqueness(self, rule: UniquenessRule) -> None:
        """Two columns together must be unique, even if each is not alone."""
        dataset = Dataset(
            source_path="test.csv",
            columns=("order_id", "line_no"),
            row_count=4,
            data={
                "order_id": [1, 1, 2, 2],
                "line_no": [1, 2, 1, 1],  # (2,1) appears twice
            },
        )
        quality_rule = QualityRule(
            id="r1",
            name="order_line_unique",
            rule_type="uniqueness",
            columns=("order_id", "line_no"),
            threshold=1.0,
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.failed
        assert result.failed_count == 1
