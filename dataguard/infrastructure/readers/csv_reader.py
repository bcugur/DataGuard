"""CSVReader — IDataReader implementation for comma-separated files.

Uses pandas to read the file, then converts the DataFrame to a
domain Dataset object. pandas is never exposed beyond this module.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dataguard.domain.entities.dataset import Dataset
from dataguard.domain.ports.reader_port import IDataReader
from dataguard.shared.exceptions import DataReadError, FileNotFoundDataError
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

_SUPPORTED_EXTENSION = ".csv"


class CSVReader(IDataReader):
    """Reads CSV files and returns a Dataset domain object.

    Supports the ``IDataReader`` port. All pandas-specific logic
    is contained within this class; the domain never sees a DataFrame.

    Args:
        encoding: File encoding to use when reading. Defaults to 'utf-8'.
        separator: Column delimiter. Defaults to ','.
    """

    def __init__(self, encoding: str = "utf-8", separator: str = ",") -> None:
        self._encoding = encoding
        self._separator = separator

    def supports(self, source: Path) -> bool:
        """Return True for .csv files.

        Args:
            source: Path to the candidate file.

        Returns:
            bool: True if the file extension is ``.csv``.
        """
        return source.suffix.lower() == _SUPPORTED_EXTENSION

    def read(self, source: Path) -> Dataset:
        """Read a CSV file and convert it to a Dataset.

        Args:
            source: Path to the CSV file.

        Returns:
            Dataset: Immutable domain snapshot of the file contents.

        Raises:
            FileNotFoundDataError: If the file does not exist.
            DataReadError: If pandas fails to parse the file.
        """
        if not source.exists():
            raise FileNotFoundDataError(path=str(source))

        logger.debug("Reading CSV file '%s'.", source.name)

        try:
            raw_bytes = source.read_bytes()

            # Detect BOM first
            if raw_bytes.startswith(b"\xef\xbb\xbf"):
                candidate_encodings = ["utf-8-sig", "utf-8", "cp1254", "iso-8859-9"]
            else:
                # Prioritize Turkish Windows encoding (cp1254) for Excel files if 0xFD (ı) or 0xFE (ş) bytes exist
                has_turkish_ansi_bytes = any(b in raw_bytes for b in (0xFD, 0xFE, 0xD0, 0xDD, 0xDE, 0xF0))
                if has_turkish_ansi_bytes:
                    candidate_encodings = ["cp1254", "iso-8859-9", "utf-8-sig", "utf-8"]
                else:
                    candidate_encodings = ["utf-8-sig", "utf-8", "cp1254", "iso-8859-9"]

            best_df = None
            last_exc = None

            for enc in candidate_encodings:
                try:
                    df_candidate = pd.read_csv(
                        source,
                        encoding=enc,
                        sep=None,
                        engine="python",
                        keep_default_na=True,
                    )
                    best_df = df_candidate
                    break
                except Exception as e:
                    last_exc = e
                    continue

            if best_df is None:
                raise last_exc or Exception("CSV dosyasi desteklenen karakter kodlamalari ile okunamadi.")

            df = best_df
        except Exception as exc:
            raise DataReadError(
                message=f"Failed to parse CSV file '{source}': {exc}",
                context={"path": str(source), "reason": str(exc)},
            ) from exc

        return self._dataframe_to_dataset(df, source)

    @staticmethod
    def _dataframe_to_dataset(df: pd.DataFrame, source: Path) -> Dataset:
        """Convert a pandas DataFrame to a domain Dataset.

        Replaces pandas NA/NaN with Python None for domain compatibility.

        Args:
            df: The loaded DataFrame.
            source: Original source path (for Dataset metadata).

        Returns:
            Dataset: Immutable domain object.
        """
        columns = tuple(str(col) for col in df.columns)
        # Convert each column to a plain Python list; NaN → None
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
