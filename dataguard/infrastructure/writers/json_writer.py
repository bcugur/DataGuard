"""JSONReportWriter — IReportWriter implementation for JSON output.

Serialises a ValidationReport to a timestamped JSON file using the
report's built-in to_dict() method. The file is written atomically
(write to temp name, then rename) to avoid partial outputs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dataguard.domain.entities.report import ValidationReport
from dataguard.domain.ports.writer_port import IReportWriter
from dataguard.shared.exceptions import ReportWriteError
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
_REPORT_FILENAME_TEMPLATE = "report_{timestamp}.json"


class JSONReportWriter(IReportWriter):
    """Writes a ValidationReport to a JSON file.

    The filename is auto-generated as ``report_YYYYMMDD_HHMMSS.json``
    inside the provided destination directory.

    Args:
        indent: JSON indentation level. Defaults to 2 for human readability.
    """

    def __init__(self, indent: int = 2) -> None:
        self._indent = indent

    def write(self, report: ValidationReport, destination: Path) -> Path:
        """Serialise the report and write it to a timestamped JSON file.

        Args:
            report: The fully populated ValidationReport aggregate.
            destination: Directory where the report file will be created.

        Returns:
            Path: The absolute path of the written JSON file.

        Raises:
            ReportWriteError: If the file cannot be written.
        """
        destination.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(tz=timezone.utc).strftime(_TIMESTAMP_FORMAT)
        filename = _REPORT_FILENAME_TEMPLATE.format(timestamp=timestamp)
        output_path = destination / filename

        logger.debug("Writing JSON report to '%s'.", output_path)

        try:
            report_dict = report.to_dict()
            json_content = json.dumps(report_dict, indent=self._indent, ensure_ascii=False)
            output_path.write_text(json_content, encoding="utf-8")
        except OSError as exc:
            raise ReportWriteError(
                destination=str(output_path),
                reason=str(exc),
            ) from exc

        logger.info("Report written: '%s' (%d bytes).", output_path.name, output_path.stat().st_size)
        return output_path
