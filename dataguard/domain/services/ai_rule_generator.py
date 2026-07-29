"""AIRuleGeneratorService domain service — Generates DataGuard YAML rules from natural language prompts.

Supports:
1. Google Gemini 1.5 Flash REST API (100% Free Tier).
2. Built-in Smart Turkish NLP Rule Synthesizer (Fallback, 100% offline & free).
"""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

import yaml

from dataguard.shared.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """Sen DataGuard Veri Kalitesi Platformu için kural üreten uzman bir yapay zekâ asistansısın.
Kullanıcının doğal dilde belirttiği veri doğrulama isteklerini incele ve SADECE geçerli DataGuard YAML kural dosyasını döndür.

DataGuard YAML Şeması (Versiyon 1.0):
```yaml
version: "1.0"
rules:
  - id: rule_001
    name: sütun_adı_tamlık
    type: completeness # completeness, uniqueness, veya validity
    column: sütun_adı
    threshold: 1.0 # 0.0 - 1.0 arası
    severity: error # error veya warning
  - id: rule_002
    name: sütun_adı_gecerlilik
    type: validity
    column: sütun_adı
    validator: tckn # tckn, vkn, tr_iban, phone_tr, enum, range, regex
    params: # validator tipine göre parametreler
      allowed_values: [Aktif, Pasif] # enum için
      min_value: 18 # range için
      max_value: 65
      pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$" # regex için
    threshold: 1.0
    severity: error
```

Kurallar:
1. Cevabında ekstra açıklama, selamlama veya markdown tırnakları (```yaml) BULUNMASIN. Sadece ham YAML metni döndür.
2. Desteklenen validator tipleri: 'tckn' (TC Kimlik), 'vkn' (Vergi No), 'tr_iban' (TR IBAN), 'phone_tr' (Telefon), 'enum', 'range', 'regex'.
3. Her kural için benzersiz bir id (rule_001, rule_002) ataması yap.
4. EĞER Mevcut Veri Sütunları verilmişse, kurallardaki 'column' alanında SADECE verilen sütun adlarını tam olarak kullan!
"""


class AIRuleGeneratorService:
    """Generates DataGuard QualityRule YAML from natural language instructions."""

    @staticmethod
    def generate(
        prompt: str,
        dataset_columns: list[str] | None = None,
        api_key: str | None = None,
    ) -> tuple[str, str]:
        """Generate YAML rules from prompt and dataset column context."""
        prompt_clean = prompt.strip()
        if not prompt_clean:
            raise ValueError("Lütfen açıklayıcı bir kural isteği girin.")

        cols = [str(c).strip() for c in dataset_columns if str(c).strip()] if dataset_columns else []

        # Try Gemini API if key is provided
        if api_key:
            try:
                yaml_str = AIRuleGeneratorService._call_gemini_api(prompt_clean, cols, api_key)
                if yaml_str and "version:" in yaml_str:
                    logger.info("Successfully generated YAML rules via Google Gemini API.")
                    return yaml_str, "gemini"
            except Exception as e:
                logger.warning("Gemini API call failed (%s). Falling back to Smart NLP Synthesizer.", e)

        # Fallback to Smart NLP Synthesizer
        yaml_str = AIRuleGeneratorService._synthesize_smart_nlp(prompt_clean, cols)
        return yaml_str, "smart_nlp"

    @staticmethod
    def _call_gemini_api(prompt: str, cols: list[str], api_key: str) -> str:
        """Call Google Gemini 1.5 Flash REST API (Free Tier)."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        cols_text = f"\nMevcut Veri Sütunları: {cols}" if cols else ""
        user_text = f"Kullanıcı İsteği: {prompt}{cols_text}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {"text": user_text},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode("utf-8"))

        candidates = res_data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini API yanıt vermedi.")

        text_content = candidates[0]["content"]["parts"][0]["text"]
        clean_yaml = re.sub(r"^```(?:yaml)?\n", "", text_content, flags=re.MULTILINE)
        clean_yaml = re.sub(r"\n```$", "", clean_yaml, flags=re.MULTILINE).strip()
        return clean_yaml

    @staticmethod
    def _synthesize_smart_nlp(prompt: str, cols: list[str]) -> str:
        """Synthesize valid DataGuard YAML using Turkish NLP pattern matcher."""
        prompt_lower = prompt.lower()
        rules: list[dict[str, Any]] = []
        rule_idx = 1
        used_cols: set[str] = set()

        words = re.findall(r"\b[a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+\b", prompt)

        # Helper to pick best column from dataset_columns or prompt words
        def match_col(keywords: tuple[str, ...], default_name: str) -> str:
            # 1. Search dataset_columns first
            if cols:
                for c in cols:
                    c_lower = c.lower()
                    if any(k in c_lower for k in keywords):
                        return c
            # 2. Search prompt words
            for w in words:
                w_lower = w.lower()
                if any(k in w_lower for k in keywords):
                    return w
            return default_name

        # 1. TCKN Check
        if any(k in prompt_lower for k in ("tc", "tckn", "kimlik")):
            col = match_col(("tc", "tckn", "kimlik"), "tc_kimlik")
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_tckn_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "tckn",
                "threshold": 1.0,
                "severity": "error"
            })
            used_cols.add(col)
            rule_idx += 1

        # 2. VKN Check
        if any(k in prompt_lower for k in ("vkn", "vergi")):
            col = match_col(("vkn", "vergi"), "vergi_no")
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_vkn_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "vkn",
                "threshold": 1.0,
                "severity": "error"
            })
            used_cols.add(col)
            rule_idx += 1

        # 3. IBAN Check
        if "iban" in prompt_lower:
            col = match_col(("iban",), "iban_no")
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_iban_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "tr_iban",
                "threshold": 1.0,
                "severity": "error"
            })
            used_cols.add(col)
            rule_idx += 1

        # 4. Telefon Check
        if any(k in prompt_lower for k in ("tel", "telefon", "phone", "gsm", "cep")):
            col = match_col(("tel", "telefon", "phone", "gsm"), "telefon")
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_telefon_format_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "phone_tr",
                "threshold": 1.0,
                "severity": "warning"
            })
            used_cols.add(col)
            rule_idx += 1

        # 5. Email Check
        if any(k in prompt_lower for k in ("eposta", "e-posta", "email", "mail")):
            col = match_col(("eposta", "email", "mail"), "eposta")
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_eposta_format",
                "type": "validity",
                "column": col,
                "validator": "regex",
                "params": {"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
                "threshold": 0.90,
                "severity": "error"
            })
            used_cols.add(col)
            rule_idx += 1

        # 6. Uniqueness Check
        if any(k in prompt_lower for k in ("tekrarsız", "benzersiz", "unique", "çakışma", "çakışmasın", "id")):
            # If prompt mentions tckn/kimlik + benzersiz, target the TCKN column!
            if any(k in prompt_lower for k in ("tc", "tckn", "kimlik")):
                col = match_col(("tc", "tckn", "kimlik"), "tc_kimlik")
            else:
                col = match_col(("id", "kod", "key", "no"), "musteri_id")
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_benzersizlik",
                "type": "uniqueness",
                "column": col,
                "threshold": 1.0,
                "severity": "error"
            })
            used_cols.add(col)
            rule_idx += 1

        # 7. Completeness Check
        if any(k in prompt_lower for k in ("tam", "boş", "null", "eksik", "dolu", "zorunlu")):
            col = match_col(("ad", "soyad", "isim", "musteri", "id"), "ad_soyad")
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_tamlik",
                "type": "completeness",
                "column": col,
                "threshold": 0.90,
                "severity": "error"
            })
            used_cols.add(col)
            rule_idx += 1

        # 8. Range (Age / Amount / Salary) Check
        range_match = re.search(r"(\d+)\s*(?:ile|-|veya|'den|den|'dan|dan)?\s*(?:küçük|büyük|arası|kadar|fazla)?", prompt_lower)
        if any(k in prompt_lower for k in ("yaş", "yas", "tutar", "fiyat", "miktar", "maaş", "maas")):
            col = match_col(("yaş", "yas", "tutar", "fiyat", "maaş", "maas"), "yas")
            
            # Detect range boundaries
            numbers = [int(n) for n in re.findall(r"\b\d+\b", prompt)]
            min_v = numbers[0] if numbers else 18
            max_v = numbers[1] if len(numbers) > 1 else 99

            params: dict[str, Any] = {}
            if "küçük olmasın" in prompt_lower or "büyük" in prompt_lower or "en az" in prompt_lower:
                params["min_value"] = min_v
            elif "büyük olmasın" in prompt_lower or "küçük" in prompt_lower or "en çok" in prompt_lower:
                params["max_value"] = min_v
            else:
                params["min_value"] = min_v
                params["max_value"] = max_v

            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_aralik_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "range",
                "params": params,
                "threshold": 0.90,
                "severity": "warning"
            })
            used_cols.add(col)
            rule_idx += 1

        # Fallback default rules if no specific rules detected
        if not rules:
            fallback_col1 = cols[0] if cols else "musteri_id"
            fallback_col2 = cols[1] if len(cols) > 1 else "ad_soyad"
            rules = [
                {
                    "id": "rule_001",
                    "name": f"{fallback_col1}_benzersizlik",
                    "type": "uniqueness",
                    "column": fallback_col1,
                    "threshold": 1.0,
                    "severity": "error"
                },
                {
                    "id": "rule_002",
                    "name": f"{fallback_col2}_tamlik",
                    "type": "completeness",
                    "column": fallback_col2,
                    "threshold": 0.90,
                    "severity": "error"
                }
            ]

        doc = {"version": "1.0", "rules": rules}
        return yaml.dump(doc, allow_unicode=True, sort_keys=False)
