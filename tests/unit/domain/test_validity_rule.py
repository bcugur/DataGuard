"""Unit tests for ValidityRule."""

from __future__ import annotations

import pytest

from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.rules.validity import ValidityRule


@pytest.fixture()
def rule() -> ValidityRule:
    return ValidityRule()


class TestValidityRuleEnum:
    def test_all_valid_enum_passes(
        self, rule: ValidityRule, dataset_valid: Dataset, validity_enum_rule: QualityRule
    ) -> None:
        result = rule.check(validity_enum_rule, dataset_valid, default_threshold=1.0)
        assert result.passed
        assert result.score == 1.0

    def test_invalid_enum_value_fails(
        self, rule: ValidityRule, dataset_with_invalid_status: Dataset
    ) -> None:
        quality_rule = QualityRule(
            id="r1",
            name="status_validity",
            rule_type="validity",
            column="status",
            threshold=1.0,
            validator_type="enum",
            params={"allowed_values": ["active", "inactive", "pending"]},
        )
        result = rule.check(quality_rule, dataset_with_invalid_status, default_threshold=1.0)
        assert result.failed
        assert result.failed_count == 2  # 'UNKNOWN' and 'deleted'


class TestValidityRuleRegex:
    def test_valid_email_regex_passes(self, rule: ValidityRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("email",),
            row_count=3,
            data={"email": ["a@b.com", "user@domain.org", "test@x.io"]},
        )
        quality_rule = QualityRule(
            id="r1",
            name="email_regex",
            rule_type="validity",
            column="email",
            threshold=1.0,
            validator_type="regex",
            params={"pattern": r"^[\w.+-]+@[\w-]+\.[\w.]+$"},
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.passed

    def test_invalid_email_regex_fails(self, rule: ValidityRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("email",),
            row_count=3,
            data={"email": ["valid@test.com", "not-an-email", None]},
        )
        quality_rule = QualityRule(
            id="r1",
            name="email_regex",
            rule_type="validity",
            column="email",
            threshold=1.0,
            validator_type="regex",
            params={"pattern": r"^[\w.+-]+@[\w-]+\.[\w.]+$"},
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.failed
        assert result.failed_count == 2


class TestValidityRuleRange:
    def test_values_in_range_pass(self, rule: ValidityRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("age",),
            row_count=3,
            data={"age": [18, 35, 99]},
        )
        quality_rule = QualityRule(
            id="r1",
            name="age_range",
            rule_type="validity",
            column="age",
            threshold=1.0,
            validator_type="range",
            params={"min_value": 0, "max_value": 150},
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.passed

    def test_out_of_range_fails(self, rule: ValidityRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("age",),
            row_count=3,
            data={"age": [25, -5, 200]},  # -5 and 200 out of range
        )
        quality_rule = QualityRule(
            id="r1",
            name="age_range",
            rule_type="validity",
            column="age",
            threshold=1.0,
            validator_type="range",
            params={"min_value": 0, "max_value": 150},
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.failed
        assert result.failed_count == 2


class TestValidityRuleDtype:
    def test_valid_int_dtype_passes(self, rule: ValidityRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("count",),
            row_count=3,
            data={"count": ["1", "2", "3"]},
        )
        quality_rule = QualityRule(
            id="r1",
            name="count_dtype",
            rule_type="validity",
            column="count",
            threshold=1.0,
            validator_type="dtype",
            params={"expected_type": "int"},
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.passed

    def test_invalid_dtype_fails(self, rule: ValidityRule) -> None:
        dataset = Dataset(
            source_path="test.csv",
            columns=("count",),
            row_count=3,
            data={"count": ["1", "abc", None]},
        )
        quality_rule = QualityRule(
            id="r1",
            name="count_dtype",
            rule_type="validity",
            column="count",
            threshold=1.0,
            validator_type="dtype",
            params={"expected_type": "int"},
        )
        result = rule.check(quality_rule, dataset, default_threshold=1.0)
        assert result.failed
        assert result.failed_count == 2
