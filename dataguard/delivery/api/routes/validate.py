"""Validation API route.

POST /api/validate
  - Accepts two file uploads: data_file + rules_file
  - Runs the validation pipeline
  - Returns the full ValidationReport as JSON
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from dataguard.domain.entities.report import ValidationReport
from dataguard.domain.entities.rule import QualityRule
from dataguard.domain.ports.notifier_port import INotifier
from dataguard.domain.rules.completeness import CompletenessRule
from dataguard.domain.rules.uniqueness import UniquenessRule
from dataguard.domain.rules.validity import ValidityRule
from dataguard.infrastructure.readers.csv_reader import CSVReader
from dataguard.infrastructure.readers.json_reader import JSONReader
from dataguard.infrastructure.repositories.file_rule_repo import FileRuleRepository
from dataguard.infrastructure.writers.json_writer import JSONReportWriter
from dataguard.shared.config import get_settings
from dataguard.shared.exceptions import DataGuardError
from dataguard.shared.logging import get_logger
from dataguard.shared.types import SUPPORTED_FILE_EXTENSIONS

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["validation"])

# Rule executor registry
_RULE_REGISTRY = {
    "completeness": CompletenessRule(),
    "uniqueness": UniquenessRule(),
    "validity": ValidityRule(),
}

# Column name fragments that suggest an identifier column.
_ID_KEYWORDS = ("id", "key", "uuid", "kod", "code", "no", "num", "ref", "pk")


def _auto_generate_rules(dataset: "Dataset") -> list[QualityRule]:  # noqa: F821
    """Generate sensible default rules when no rules file is provided."""
    rules: list[QualityRule] = []
    for i, col in enumerate(dataset.columns):
        rules.append(
            QualityRule(
                id=f"auto_{i + 1:03d}_c",
                name=f"{col}_tamlık",
                rule_type="completeness",
                column=col,
                threshold=0.80,
                severity="warning",
            )
        )
        col_lower = col.lower()
        if any(kw in col_lower for kw in _ID_KEYWORDS):
            rules.append(
                QualityRule(
                    id=f"auto_{i + 1:03d}_u",
                    name=f"{col}_tekrarsızlık",
                    rule_type="uniqueness",
                    column=col,
                    threshold=1.0,
                    severity="error",
                )
            )
    return rules


def _rules_from_json(raw: list[dict[str, Any]]) -> list[QualityRule]:
    """Build QualityRule objects from a JSON array sent by the frontend."""
    rules: list[QualityRule] = []
    type_names = {"completeness": "tamlık", "uniqueness": "tekrarsızlık", "validity": "geçerlilik"}
    for i, item in enumerate(raw):
        col = str(item.get("column", ""))
        rule_type = str(item.get("type", "completeness"))
        tr_type = type_names.get(rule_type, rule_type)
        rules.append(
            QualityRule(
                id=item.get("id", f"ui_{i + 1:03d}"),
                name=item.get("name", f"{col}_{tr_type}"),
                rule_type=rule_type,  # type: ignore[arg-type]
                column=col or None,
                threshold=float(item.get("threshold", 0.80)),
                severity=item.get("severity", "warning"),  # type: ignore[arg-type]
                validator_type=item.get("validator"),  # type: ignore[arg-type]
                params=item.get("params", {}),
            )
        )
    return rules


class _NullNotifier(INotifier):
    """No-op notifier for the web API (terminal output is suppressed)."""

    def notify(self, report: ValidationReport) -> None:  # noqa: D102
        pass


@router.post("/validate", summary="Run a data quality validation")
async def validate(request: Request) -> JSONResponse:
    """Validate a data file against quality rules via multipart form data."""
    form = await request.form()
    data_file = form.get("data_file")
    rules_file = form.get("rules_file")
    rules_json = form.get("rules_json")

    if not data_file or not hasattr(data_file, "filename") or not data_file.filename:
        raise HTTPException(status_code=400, detail="Lutfen gecerli bir veri dosyasi (CSV veya JSON) yukleyin.")

    data_filename = data_file.filename
    has_rules_file = bool(rules_file and hasattr(rules_file, "filename") and rules_file.filename)
    rules_filename = rules_file.filename if has_rules_file else "otomatik"

    data_suffix = Path(data_filename).suffix.lower()
    if data_suffix not in SUPPORTED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen format '{data_suffix}'. Kabul edilen: {', '.join(SUPPORTED_FILE_EXTENSIONS)}",
        )

    logger.info(
        "API dogrulama istegi — veri='%s' kurallar='%s'",
        data_filename,
        rules_filename,
    )

    # ── Write uploads to temp files ────────────────────────────────────────
    tmp_data_path: Path | None = None
    tmp_rules_path: Path | None = None

    try:
        data_bytes = await data_file.read()
        rules_bytes = await rules_file.read() if has_rules_file else None

        if not data_bytes:
            raise HTTPException(status_code=400, detail="Veri dosyasi bos.")

        with tempfile.NamedTemporaryFile(
            suffix=data_suffix, delete=False
        ) as tmp_d:
            tmp_d.write(data_bytes)
            tmp_data_path = Path(tmp_d.name)

        if rules_bytes:
            with tempfile.NamedTemporaryFile(
                suffix=".yaml", delete=False
            ) as tmp_r:
                tmp_r.write(rules_bytes)
                tmp_rules_path = Path(tmp_r.name)

        # ── Select reader ──────────────────────────────────────────────────
        reader = CSVReader() if data_suffix == ".csv" else JSONReader()

        # ── Load rules + dataset ───────────────────────────────────────────
        rule_repo = FileRuleRepository()
        dataset = reader.read(tmp_data_path)

        # Determine rule source (priority: yaml > json > auto)
        if tmp_rules_path:
            rules = rule_repo.load(tmp_rules_path)
            rules_source = f"YAML: {rules_filename}"
        elif rules_json:
            try:
                raw_list = json.loads(rules_json)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"Gecersiz rules_json: {exc}") from exc
            rules = _rules_from_json(raw_list)
            rules_source = "UI (secilen kurallar)"
        else:
            rules = _auto_generate_rules(dataset)
            rules_source = "Otomatik (varsayilan kurallar)"

        logger.info("Kural kaynagi: %s — %d kural", rules_source, len(rules))

        # ── Build report ───────────────────────────────────────────────────
        report = ValidationReport(
            source_path=data_filename,
            rules_path=rules_source,
        )

        settings = get_settings()
        for rule in rules:
            executor = _RULE_REGISTRY.get(rule.rule_type)
            if executor is None:
                logger.warning("Unknown rule type '%s' — skipping.", rule.rule_type)
                continue
            result = executor.check(rule, dataset, settings.default_threshold)
            report.add_result(result)

        # ── Persist JSON report ────────────────────────────────────────────
        writer = JSONReportWriter()
        report_path = writer.write(report, Path("reports"))
        logger.info("Report saved: '%s'", report_path.name)

        # ── Return enriched dict ───────────────────────────────────────────
        response_data: dict[str, Any] = report.to_dict()
        response_data["meta"] = {
            "report_file": report_path.name,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "columns": list(dataset.columns),
        }
        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except DataGuardError as exc:
        logger.warning("DataGuardError during API validation: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during API validation.")
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc
    finally:
        if tmp_data_path and tmp_data_path.exists():
            tmp_data_path.unlink()
        if tmp_rules_path and tmp_rules_path.exists():
            tmp_rules_path.unlink()
