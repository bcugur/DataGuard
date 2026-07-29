"""Unit tests for DataCleanser domain service."""

from dataguard.domain.entities.check_result import CheckResult
from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.report import ValidationReport
from dataguard.domain.services.cleanser import DataCleanser, REASON_COLUMN


def test_data_cleanser_splits_clean_and_quarantine_rows():
    dataset = Dataset(
        source_path="test.csv",
        columns=("id", "name", "age"),
        row_count=4,
        data={
            "id": [1, 2, 3, 4],
            "name": ["Ahmet", None, "Mehmet", "Can"],
            "age": [25, 30, -5, 40],
        },
    )

    report = ValidationReport(source_path="test.csv", rules_path="rules.yaml")

    # Rule 1: completeness failed on row 1 (name is None)
    result_c = CheckResult(
        rule_id="r1",
        rule_name="name_tamlik",
        rule_type="completeness",
        column="name",
        status="failed",
        score=0.75,
        threshold=1.0,
        failed_count=1,
        total_count=4,
        severity="error",
        message="1 null value found",
        failed_row_indices=(1,),
    )

    # Rule 2: range failed on row 2 (age is -5)
    result_r = CheckResult(
        rule_id="r2",
        rule_name="age_aralik",
        rule_type="validity",
        column="age",
        status="failed",
        score=0.75,
        threshold=1.0,
        failed_count=1,
        total_count=4,
        severity="warning",
        message="Out of range",
        failed_row_indices=(2,),
    )

    report.add_result(result_c)
    report.add_result(result_r)

    clean_ds, quarantine_ds = DataCleanser.split(dataset, report)

    # Clean rows: row 0 (id 1) and row 3 (id 4)
    assert clean_ds.row_count == 2
    assert clean_ds.data["id"] == [1, 4]
    assert clean_ds.data["name"] == ["Ahmet", "Can"]

    # Quarantine rows: row 1 (id 2) and row 2 (id 3)
    assert quarantine_ds.row_count == 2
    assert quarantine_ds.data["id"] == [2, 3]
    assert REASON_COLUMN in quarantine_ds.columns
    assert "name_tamlik" in str(quarantine_ds.data[REASON_COLUMN][0])
    assert "age_aralik" in str(quarantine_ds.data[REASON_COLUMN][1])
