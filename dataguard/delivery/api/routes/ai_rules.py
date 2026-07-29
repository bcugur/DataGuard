"""AI Rules API route — generates YAML rule definitions from natural language prompts.

POST /api/ai/generate-rules
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from dataguard.domain.services.ai_rule_generator import AIRuleGeneratorService
from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/generate-rules", summary="Generate YAML rules from natural language prompt")
async def generate_rules(request: Request) -> JSONResponse:
    """Accept natural language instructions and return generated YAML rules."""
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        body = {}

    prompt = str(body.get("prompt", "")).strip()
    api_key = body.get("api_key") or None

    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="Lütfen geçerli bir kural cümlesi/prompt girin.",
        )

    try:
        yaml_content, source = AIRuleGeneratorService.generate(prompt, api_key=api_key)
        return JSONResponse(
            {
                "status": "success",
                "source": source,
                "yaml_content": yaml_content,
                "message": "YAML kural dosyası başarıyla üretildi.",
            }
        )
    except Exception as exc:
        logger.exception("AI rule generation failed.")
        raise HTTPException(status_code=500, detail=f"Kural üretilemedi: {exc}") from exc
