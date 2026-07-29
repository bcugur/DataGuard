"""Preview API route — returns column info from an uploaded data file.

GET /api/preview is used by the frontend to discover column names and
infer types after the user uploads a data file, before running validation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from dataguard.infrastructure.readers.csv_reader import CSVReader
from dataguard.infrastructure.readers.json_reader import JSONReader
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["preview"])

# Keyword fragments that suggest a column is an identifier.
_ID_KEYWORDS = ("id", "key", "uuid", "kod", "code", "no", "num", "ref", "pk")


def _infer_column_kind(col: str, values: list[object]) -> str:
    """Guess a human-readable column kind from name and sample values."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "Bilinmiyor"

    sample = non_null[0]
    if isinstance(sample, bool):
        return "Mantıksal"
    if isinstance(sample, (int, float)):
        return "Sayı"
    if isinstance(sample, str):
        lower = str(sample).lower()
        if any(sep in lower for sep in ("-", "/", ":")) and len(lower) >= 8:
            return "Tarih"
        return "Metin"
    return "Bilinmiyor"


def _is_id_column(col: str) -> bool:
    """Return True if the column name looks like an identifier."""
    col_lower = col.lower()
    return any(kw in col_lower for kw in _ID_KEYWORDS)


@router.post("/preview", summary="Preview columns from an uploaded data file")
async def preview(request: Request) -> JSONResponse:
    """Read the uploaded file and return column metadata."""
    form = await request.form()
    data_file = form.get("data_file")

    if not data_file or not hasattr(data_file, "filename") or not data_file.filename:
        raise HTTPException(status_code=400, detail="Lutfen gecerli bir veri dosyasi yukleyin.")

    data_suffix = Path(data_file.filename).suffix.lower()

    if data_suffix not in (".csv", ".json"):
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen format '{data_suffix}'. Kabul edilen: .csv, .json",
        )

    tmp_path: Path | None = None
    try:
        data_bytes = await data_file.read()
        if not data_bytes:
            raise HTTPException(status_code=400, detail="Dosya bos.")

        with tempfile.NamedTemporaryFile(suffix=data_suffix, delete=False) as tmp:
            tmp.write(data_bytes)
            tmp_path = Path(tmp.name)

        reader = CSVReader() if data_suffix == ".csv" else JSONReader()
        dataset = reader.read(tmp_path)

        columns = []
        for col in dataset.columns:
            values = (dataset.data.get(col) or [])[:10]
            kind = _infer_column_kind(col, values)
            columns.append(
                {
                    "name": col,
                    "kind": kind,
                    "is_id_like": _is_id_column(col),
                    "null_count": sum(1 for v in dataset.data.get(col, []) if v is None),
                    "sample": [str(v) for v in values[:5] if v is not None],
                }
            )

        return JSONResponse(
            {
                "filename": data_file.filename,
                "row_count": dataset.row_count,
                "column_count": dataset.column_count,
                "columns": columns,
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Preview hatasi.")
        raise HTTPException(status_code=500, detail=f"Dosya okunamadi: {exc}") from exc
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
