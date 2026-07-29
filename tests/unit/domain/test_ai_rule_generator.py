"""Unit tests for AIRuleGeneratorService domain service."""

from dataguard.domain.services.ai_rule_generator import AIRuleGeneratorService


def test_ai_rule_generator_smart_nlp_synthesis():
    prompt = "Müşteri ID benzersiz ve tam olsun, tc_kimlik geçerli olsun, yaş 18 ile 65 arasında olsun"
    yaml_content, source = AIRuleGeneratorService.generate(prompt)

    assert source == "smart_nlp"
    assert "version: \"1.0\"" in yaml_content or "version: '1.0'" in yaml_content
    assert "tckn" in yaml_content
    assert "uniqueness" in yaml_content
    assert "completeness" in yaml_content
    assert "range" in yaml_content
    assert "min_value: 18" in yaml_content
    assert "max_value: 65" in yaml_content


def test_ai_rule_generator_empty_prompt_raises_error():
    try:
        AIRuleGeneratorService.generate("   ")
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "Lütfen açıklayıcı" in str(exc)
