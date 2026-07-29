"""DataCleanser domain service — splits a Dataset into clean and quarantine Datasets.

Given a Dataset and a ValidationReport containing CheckResult objects (with
their failed_row_indices), DataCleanser separates:
  - clean_dataset: rows that passed ALL rules.
  - quarantine_dataset: rows that failed at least one rule, enriched with
    an 'İhlal Nedenleri' column detailing the violated rules and reasons.
"""

from __future__ import annotations

from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.entities.report import ValidationReport
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

REASON_COLUMN = "İhlal Nedenleri"


class DataCleanser:
    """Domain service for separating valid data from quarantined data."""

    @staticmethod
    def split(dataset: Dataset, report: ValidationReport) -> tuple[Dataset, Dataset]:
        """Split a dataset into (clean_dataset, quarantine_dataset).

        Args:
            dataset: Original input dataset.
            report: ValidationReport containing check results.

        Returns:
            Tuple of (clean_dataset, quarantine_dataset).
        """
        # Map 0-based row_index -> list of violation descriptions
        quarantine_reasons: dict[int, list[str]] = {}

        for result in report.results:
            # We quarantine rows from failing or error results that have recorded indices
            if result.failed_row_indices and (result.failed or result.severity == "error"):
                for row_idx in result.failed_row_indices:
                    if row_idx not in quarantine_reasons:
                        quarantine_reasons[row_idx] = []
                    reason_msg = DataCleanser._format_row_reason(result, dataset, row_idx)
                    quarantine_reasons[row_idx].append(reason_msg)

        quarantine_set = set(quarantine_reasons.keys())

        # Construct clean & quarantine data dicts
        clean_data: dict[str, list[object]] = {col: [] for col in dataset.columns}
        quarantine_data: dict[str, list[object]] = {col: [] for col in dataset.columns}
        quarantine_data[REASON_COLUMN] = []

        for row_idx in range(dataset.row_count):
            if row_idx in quarantine_set:
                for col in dataset.columns:
                    quarantine_data[col].append(dataset.data[col][row_idx])
                reasons_str = " | ".join(quarantine_reasons[row_idx])
                quarantine_data[REASON_COLUMN].append(reasons_str)
            else:
                for col in dataset.columns:
                    clean_data[col].append(dataset.data[col][row_idx])

        clean_row_count = len(next(iter(clean_data.values()), [])) if dataset.columns else 0
        quarantine_row_count = len(next(iter(quarantine_data.values()), [])) if dataset.columns else 0

        clean_ds = Dataset(
            source_path=f"{dataset.source_name}_clean",
            columns=dataset.columns,
            row_count=clean_row_count,
            data=clean_data,
        )

        quarantine_cols = dataset.columns + (REASON_COLUMN,)
        quarantine_ds = Dataset(
            source_path=f"{dataset.source_name}_quarantine",
            columns=quarantine_cols,
            row_count=quarantine_row_count,
            data=quarantine_data,
        )

        logger.info(
            "DataCleanser completed — total=%d clean=%d quarantine=%d",
            dataset.row_count,
            clean_row_count,
            quarantine_row_count,
        )

        return clean_ds, quarantine_ds

    @staticmethod
    def _format_row_reason(result: "CheckResult", dataset: Dataset, row_idx: int) -> str:  # noqa: F821
        """Compose a human-readable Turkish violation description for a single row."""
        col = result.column or "Genel"
        val = dataset.data[col][row_idx] if col in dataset.data and row_idx < len(dataset.data[col]) else None
        val_str = "boş" if val is None or str(val).strip() == "" else f"'{val}'"

        if result.rule_type == "completeness":
            return f"[{col}] Sütunu Eksik Veri ({val_str})"
        elif result.rule_type == "uniqueness":
            return f"[{col}] Sütununda Tekrarlayan Kayıt ({val_str})"
        elif result.rule_type == "validity":
            return f"[{col}] Sütununda Format/Değer Hatası ({val_str})"
        else:
            return f"[{col}] Kural İhlali: {result.rule_name}"
