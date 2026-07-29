"""Shared pytest fixtures and configuration.

All fixtures defined here are available to every test module without
explicit imports (pytest auto-discovery via conftest.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dataguard.domain.entities.check_result import CheckResult
from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.entities.report import ValidationReport


# ---------------------------------------------------------------------------
# Dataset fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def dataset_valid() -> Dataset:
    """A clean dataset with no quality issues."""
    return Dataset(
        source_path="tests/fixtures/sample_valid.csv",
        columns=("id", "email", "status", "age"),
        row_count=5,
        data={
            "id": [1, 2, 3, 4, 5],
            "email": [
                "alice@example.com",
                "bob@example.com",
                "carol@example.com",
                "dave@example.com",
                "eve@example.com",
            ],
            "status": ["active", "inactive", "active", "pending", "active"],
            "age": [25, 34, 29, 41, 22],
        },
    )


@pytest.fixture()
def dataset_with_nulls() -> Dataset:
    """A dataset with NULL / empty values in the email column."""
    return Dataset(
        source_path="tests/fixtures/sample_invalid.csv",
        columns=("id", "email", "status"),
        row_count=5,
        data={
            "id": [1, 2, 3, 4, 5],
            "email": ["alice@example.com", None, "  ", None, "eve@example.com"],
            "status": ["active", "inactive", "active", "pending", "active"],
        },
    )


@pytest.fixture()
def dataset_with_duplicates() -> Dataset:
    """A dataset with duplicate user_id values."""
    return Dataset(
        source_path="tests/fixtures/sample_invalid.csv",
        columns=("user_id", "name"),
        row_count=5,
        data={
            "user_id": [1, 2, 2, 3, 1],  # 1 and 2 are duplicated
            "name": ["Alice", "Bob", "Bob2", "Carol", "Alice2"],
        },
    )


@pytest.fixture()
def dataset_with_invalid_status() -> Dataset:
    """A dataset with invalid enum values in the status column."""
    return Dataset(
        source_path="tests/fixtures/sample_invalid.csv",
        columns=("id", "status"),
        row_count=5,
        data={
            "id": [1, 2, 3, 4, 5],
            "status": ["active", "inactive", "UNKNOWN", "pending", "deleted"],
        },
    )


# ---------------------------------------------------------------------------
# Rule fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def completeness_rule() -> QualityRule:
    """A completeness rule checking the email column (threshold=0.8)."""
    return QualityRule(
        id="rule_001",
        name="email_completeness",
        rule_type="completeness",
        column="email",
        threshold=0.8,
        severity="error",
    )


@pytest.fixture()
def uniqueness_rule() -> QualityRule:
    """A uniqueness rule checking the user_id column (threshold=1.0)."""
    return QualityRule(
        id="rule_002",
        name="user_id_unique",
        rule_type="uniqueness",
        column="user_id",
        threshold=1.0,
        severity="error",
    )


@pytest.fixture()
def validity_enum_rule() -> QualityRule:
    """A validity rule checking status against an allowed set."""
    return QualityRule(
        id="rule_003",
        name="status_validity",
        rule_type="validity",
        column="status",
        threshold=1.0,
        severity="warning",
        validator_type="enum",
        params={"allowed_values": ["active", "inactive", "pending"]},
    )


# ---------------------------------------------------------------------------
# Report fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def empty_report() -> ValidationReport:
    """A ValidationReport with no results yet."""
    return ValidationReport(
        source_path="tests/fixtures/sample_valid.csv",
        rules_path="tests/fixtures/sample_rules.yaml",
    )


@pytest.fixture()
def passed_check_result() -> CheckResult:
    """A CheckResult representing a passing rule."""
    return CheckResult(
        rule_id="rule_001",
        rule_name="email_completeness",
        rule_type="completeness",
        column="email",
        status="passed",
        score=1.0,
        threshold=0.95,
        failed_count=0,
        total_count=100,
        severity="error",
        message="✓ All values present.",
    )


@pytest.fixture()
def failed_check_result() -> CheckResult:
    """A CheckResult representing a failing error-severity rule."""
    return CheckResult(
        rule_id="rule_002",
        rule_name="user_id_unique",
        rule_type="uniqueness",
        column="user_id",
        status="failed",
        score=0.8,
        threshold=1.0,
        failed_count=2,
        total_count=10,
        severity="error",
        message="✗ 2 duplicates found.",
    )
