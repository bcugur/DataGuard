"""ExcelReader — IDataReader implementation for Excel files (.xlsx, .xls).

Uses pandas with openpyxl to read Excel files, then converts the DataFrame
to a domain Dataset object.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.ports.reader_port import IDataReader
from dataguard.shared.exceptions import DataReadError, FileNotFoundDataError
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

_SUPPORTED_EXTENSIONS = (".xlsx", ".xls")


class ExcelReader(IDataReader):
    """Reads Excel files (.xlsx, .xls) and returns a Dataset domain object.

    Args:
        sheet_name: Name or 0-indexed index of the sheet to read. Defaults to 0.
    """

    def __init__(self, sheet_name: str | int = 0) -> None:
        self._sheet_name = sheet_name

    def supports(self, source: Path) -> bool:
        """Return True for .xlsx and .xls files."""
        return source.suffix.lower() in _SUPPORTED_EXTENSIONS

    def read(self, source: Path) -> Dataset:
        """Read an Excel file and convert it to a Dataset."""
        if not source.exists():
            raise FileNotFoundDataError(path=str(source))

        logger.debug("Reading Excel file '%s' (sheet=%s).", source.name, self._sheet_name)

        try:
            df = pd.read_excel(source, sheet_name=self._sheet_name, engine="openpyxl")
        except Exception as exc:
            raise DataReadError(
                message=f"Failed to parse Excel file '{source}': {exc}",
                context={"path": str(source), "reason": str(exc)},
            ) from exc

        return self._dataframe_to_dataset(df, source)

    @staticmethod
    def _dataframe_to_dataset(df: pd.DataFrame, source: Path) -> Dataset:
        """Convert pandas DataFrame to domain Dataset (NaN -> None)."""
        columns = tuple(str(col) for col in df.columns)
        data: dict[str, list[object]] = {
            col: [None if pd.isna(v) else v for v in df[col].tolist()]
            for col in columns
        }
        return Dataset(
            source_path=str(source),
            columns=columns,
            row_count=len(df),
            data=data,
        )
