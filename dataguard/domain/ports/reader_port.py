"""IDataReader port — abstract contract for reading data sources.

Any infrastructure adapter that reads a file (CSV, JSON, Parquet, …)
must implement this interface. The domain and application layers depend
only on IDataReader, never on a concrete adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from dataguard.domain.entities.dataset import Dataset


class IDataReader(ABC):
    """Abstract base class for data source readers.

    Infrastructure adapters (CSVReader, JSONReader, …) inherit from this
    class and implement ``read()``. The application layer receives an
    IDataReader via dependency injection and remains decoupled from the
    concrete file format.
    """

    @abstractmethod
    def read(self, source: Path) -> Dataset:
        """Read a data source and return a Dataset domain object.

        Args:
            source: Absolute or relative path to the data file.

        Returns:
            Dataset: An immutable snapshot of the loaded data.

        Raises:
            FileNotFoundDataError: If ``source`` does not exist.
            UnsupportedFormatError: If the file extension is not supported.
            DataReadError: For any other read-level failure.
        """

    @abstractmethod
    def supports(self, source: Path) -> bool:
        """Return True if this reader can handle the given file.

        Used by a ReaderFactory to select the correct adapter at runtime
        without the application needing to know which reader handles which
        extension.

        Args:
            source: Path to the candidate data file.

        Returns:
            bool: True if this reader accepts the file format.
        """
