from app.services.classifier import classify, normalize_merchant


def test_mapping_takes_priority():
    learned = {normalize_merchant("永辉超市"): "日用品"}
    c = classify("永辉超市", "支付", mapping_lookup=lambda k: learned.get(k))
    assert c.source == "mapping"
    assert c.category == "日用品"
    assert c.confidence >= 0.95


def test_keyword_rule_match():
    c = classify("星巴克咖啡", "星巴克消费")
    assert c.source == "rule"
    assert c.category == "餐饮"


def test_fallback_when_no_match():
    c = classify("某不知名小店", "随便买了点")
    assert c.source == "fallback"
    assert c.category == "其他"
    assert c.confidence < 0.5


def test_llm_used_only_when_no_rule():
    class DummyLLM:
        called = False

        def classify(self, merchant, raw_text, categories):
            from app.services.classifier import Classification

            DummyLLM.called = True
            return Classification("数码电子", 0.8, "llm", "dummy")

    llm = DummyLLM()
    # Rule matches -> LLM must NOT be called.
    classify("星巴克", "咖啡", llm_client=llm)
    assert llm.called is False

    # No rule -> LLM is called.
    c = classify("XYZ神秘商户", "无关键词", llm_client=llm)
    assert llm.called is True
    assert c.source == "llm"
