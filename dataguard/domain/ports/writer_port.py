"""IReportWriter port — abstract contract for writing validation reports.

Any adapter that serialises a ValidationReport (JSON file, HTML file,
database row, …) must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from dataguard.domain.entities.report import ValidationReport


class IReportWriter(ABC):
    """Abstract base class for report serialisers.

    Infrastructure adapters (JSONReportWriter, HTMLReportWriter, …) inherit
    from this class and implement ``write()``.
    """

    @abstractmethod
    def write(self, report: ValidationReport, destination: Path) -> Path:
        """Serialise the validation report to the given destination.

        Args:
            report: The fully populated ValidationReport aggregate.
            destination: Directory or file path where the report is saved.
                Implementations may append a timestamped filename if a
                directory is provided.

        Returns:
            Path: The actual file path where the report was written.
                Callers use this to display the location to the user.

        Raises:
            ReportWriteError: If the report cannot be written.
        """
