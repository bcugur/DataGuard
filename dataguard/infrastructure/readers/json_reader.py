"""JSONReader — IDataReader implementation for JSON files.

Supports both JSON arrays (list of records) and JSON objects
(column-oriented dict). Uses pandas for consistent NaN handling
and type inference.

Supported formats:
    - Array of records: [{"col": val, ...}, ...]
    - Column-oriented:  {"col": [val, ...], ...}
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.ports.reader_port import IDataReader
from dataguard.shared.exceptions import DataReadError, FileNotFoundDataError
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

_SUPPORTED_EXTENSION = ".json"


class JSONReader(IDataReader):
    """Reads JSON files and returns a Dataset domain object.

    Args:
        orient: pandas ``orient`` parameter for ``read_json``.
            Use ``'records'`` for array-of-records format (default),
            or ``'columns'`` for column-oriented dicts.
    """

    def __init__(self, orient: str = "records") -> None:
        self._orient = orient

    def supports(self, source: Path) -> bool:
        """Return True for .json files.

        Args:
            source: Path to the candidate file.

        Returns:
            bool: True if the file extension is ``.json``.
        """
        return source.suffix.lower() == _SUPPORTED_EXTENSION

    def read(self, source: Path) -> Dataset:
        """Read a JSON file and convert it to a Dataset.

        Args:
            source: Path to the JSON file.

        Returns:
            Dataset: Immutable domain snapshot.

        Raises:
            FileNotFoundDataError: If the file does not exist.
            DataReadError: If pandas fails to parse the file.
        """
        if not source.exists():
            raise FileNotFoundDataError(path=str(source))

        logger.debug("Reading JSON file '%s' (orient=%s).", source.name, self._orient)

        try:
            df = pd.read_json(source, orient=self._orient)
        except Exception as exc:
            raise DataReadError(
                message=f"Failed to parse JSON file '{source}': {exc}",
                context={
                    "path": str(source),
                    "orient": self._orient,
                    "reason": str(exc),
                },
            ) from exc

        return self._dataframe_to_dataset(df, source)

    @staticmethod
    def _dataframe_to_dataset(df: pd.DataFrame, source: Path) -> Dataset:
        """Convert a pandas DataFrame to a domain Dataset.

        Args:
            df: The loaded DataFrame.
            source: Original source path (for Dataset metadata).

        Returns:
            Dataset: Immutable domain object with None instead of NaN.
        """
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
