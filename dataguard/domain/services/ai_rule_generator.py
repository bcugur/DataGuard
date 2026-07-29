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

# System prompt instructing Gemini to produce strict DataGuard YAML schema 1.0
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
"""


class AIRuleGeneratorService:
    """Generates DataGuard QualityRule YAML from natural language instructions."""

    @staticmethod
    def generate(prompt: str, api_key: str | None = None) -> tuple[str, str]:
        """Generate YAML rules from prompt.

        Args:
            prompt: Natural language description of validation rules in Turkish or English.
            api_key: Optional Google Gemini API key (Free Tier).

        Returns:
            Tuple of (yaml_content, source_used) where source_used is 'gemini' or 'smart_nlp'.
        """
        prompt_clean = prompt.strip()
        if not prompt_clean:
            raise ValueError("Lütfen açıklayıcı bir kural isteği girin.")

        # Try Gemini API if key is provided or present in environment
        if api_key:
            try:
                yaml_str = AIRuleGeneratorService._call_gemini_api(prompt_clean, api_key)
                if yaml_str and "version:" in yaml_str:
                    logger.info("Successfully generated YAML rules via Google Gemini API.")
                    return yaml_str, "gemini"
            except Exception as e:
                logger.warning("Gemini API call failed (%s). Falling back to Smart NLP Synthesizer.", e)

        # Fallback to Smart NLP Synthesizer
        yaml_str = AIRuleGeneratorService._synthesize_smart_nlp(prompt_clean)
        return yaml_str, "smart_nlp"

    @staticmethod
    def _call_gemini_api(prompt: str, api_key: str) -> str:
        """Call Google Gemini 1.5 Flash REST API (Free Tier)."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {"text": f"Kullanıcı İsteği: {prompt}"},
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
        # Clean markdown codeblocks if present
        clean_yaml = re.sub(r"^```(?:yaml)?\n", "", text_content, flags=re.MULTILINE)
        clean_yaml = re.sub(r"\n```$", "", clean_yaml, flags=re.MULTILINE).strip()
        return clean_yaml

    @staticmethod
    def _synthesize_smart_nlp(prompt: str) -> str:
        """Synthesize valid DataGuard YAML using Turkish NLP pattern matcher."""
        prompt_lower = prompt.lower()
        rules: list[dict[str, Any]] = []
        rule_idx = 1

        # Extract words/columns referenced in prompt
        # Common column names mentioned or general column patterns
        words = re.findall(r"\b[a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+\b", prompt)

        # 1. TCKN Check
        if any(k in prompt_lower for k in ("tc", "tckn", "kimlik")):
            col = AIRuleGeneratorService._find_col_name(words, ("tc", "tckn", "kimlik")) or "tc_kimlik"
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_tckn_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "tckn",
                "threshold": 1.0,
                "severity": "error"
            })
            rule_idx += 1

        # 2. VKN Check
        if any(k in prompt_lower for k in ("vkn", "vergi")):
            col = AIRuleGeneratorService._find_col_name(words, ("vkn", "vergi")) or "vergi_no"
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_vkn_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "vkn",
                "threshold": 1.0,
                "severity": "error"
            })
            rule_idx += 1

        # 3. IBAN Check
        if "iban" in prompt_lower:
            col = AIRuleGeneratorService._find_col_name(words, ("iban",)) or "iban_no"
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_iban_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "tr_iban",
                "threshold": 1.0,
                "severity": "error"
            })
            rule_idx += 1

        # 4. Telefon Check
        if any(k in prompt_lower for k in ("tel", "telefon", "phone", "gsm", "cep")):
            col = AIRuleGeneratorService._find_col_name(words, ("tel", "telefon", "phone", "gsm")) or "telefon"
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_telefon_format_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "phone_tr",
                "threshold": 1.0,
                "severity": "warning"
            })
            rule_idx += 1

        # 5. Email Check
        if any(k in prompt_lower for k in ("eposta", "e-posta", "email", "mail")):
            col = AIRuleGeneratorService._find_col_name(words, ("eposta", "email", "mail")) or "eposta"
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
            rule_idx += 1

        # 6. Uniqueness Check
        if any(k in prompt_lower for k in ("tekrarsız", "benzersiz", "unique", "çakışma", "çakışmasın", "id")):
            col = AIRuleGeneratorService._find_col_name(words, ("id", "kod", "key", "no")) or "musteri_id"
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_benzersizlik",
                "type": "uniqueness",
                "column": col,
                "threshold": 1.0,
                "severity": "error"
            })
            rule_idx += 1

        # 7. Completeness Check
        if any(k in prompt_lower for k in ("tam", "boş", "null", "eksik", "dolu", "zorunlu")):
            col = AIRuleGeneratorService._find_col_name(words, ("ad", "soyad", "isim", "musteri", "id")) or "ad_soyad"
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_tamlik",
                "type": "completeness",
                "column": col,
                "threshold": 0.90,
                "severity": "error"
            })
            rule_idx += 1

        # 8. Range (Age / Amount) Check
        range_match = re.search(r"(\d+)\s*(?:ile|-|veya)\s*(\d+)", prompt_lower)
        if range_match or any(k in prompt_lower for k in ("yaş", "aralık", "tutar", "fiyat", "miktar")):
            col = AIRuleGeneratorService._find_col_name(words, ("yaş", "yas", "tutar", "fiyat")) or "yas"
            min_v = int(range_match.group(1)) if range_match else 18
            max_v = int(range_match.group(2)) if range_match else 65
            rules.append({
                "id": f"rule_{rule_idx:03d}",
                "name": f"{col}_aralik_kontrolu",
                "type": "validity",
                "column": col,
                "validator": "range",
                "params": {"min_value": min_v, "max_value": max_v},
                "threshold": 0.90,
                "severity": "warning"
            })
            rule_idx += 1

        # Fallback default rules if no specific rules detected
        if not rules:
            rules = [
                {
                    "id": "rule_001",
                    "name": "musteri_id_benzersizlik",
                    "type": "uniqueness",
                    "column": "musteri_id",
                    "threshold": 1.0,
                    "severity": "error"
                },
                {
                    "id": "rule_002",
                    "name": "ad_soyad_tamlik",
                    "type": "completeness",
                    "column": "ad_soyad",
                    "threshold": 0.90,
                    "severity": "error"
                }
            ]

        doc = {"version": "1.0", "rules": rules}
        return yaml.dump(doc, allow_unicode=True, sort_keys=False)

    @staticmethod
    def _find_col_name(words: list[str], keywords: tuple[str, ...]) -> str | None:
        """Find candidate column name matching keywords from prompt words."""
        for w in words:
            w_lower = w.lower()
            if any(k in w_lower for k in keywords):
                return w
        return None
