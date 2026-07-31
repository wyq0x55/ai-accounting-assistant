"""Category classification pipeline (cost-ascending).

Order:
  1. Merchant mapping lookup (learned history)  -> cheapest, highest priority
  2. Built-in keyword rules                      -> free, deterministic
  3. LLM fallback                                -> only when 1 & 2 fail

Each stage returns a :class:`Classification` with a source tag so the caller
can decide whether the item needs manual review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Protocol

# Default seed categories (kept in sync with seeds.py).
DEFAULT_CATEGORIES = [
    "餐饮", "交通", "购物", "日用品", "医疗", "教育", "娱乐",
    "数码电子", "宠物", "人情往来", "通讯", "房租住房", "投资理财", "其他",
]

# Lightweight keyword rules -> category. Intentionally conservative.
_KEYWORD_RULES: dict[str, tuple[str, ...]] = {
    "餐饮": ("餐厅", "饭", "美食", "外卖", "星巴克", "瑞幸", "咖啡", "麦当劳",
             "肯德基", "奶茶", "食堂", "餐饮", "烧烤", "火锅"),
    "交通": ("地铁", "公交", "打车", "滴滴", "高铁", "火车", "机票", "加油",
             "停车", "出行", "12306", "共享单车"),
    "购物": ("京东", "淘宝", "天猫", "拼多多", "商城", "服饰", "苏宁"),
    "日用品": ("永辉", "超市", "便利店", "沃尔玛", "华润", "盒马", "家乐福"),
    "医疗": ("医院", "药", "诊所", "体检", "挂号", "药房", "医保"),
    "教育": ("学费", "培训", "课程", "书店", "图书", "学校", "考试"),
    "娱乐": ("电影", "游戏", "KTV", "演唱会", "健身", "旅游", "酒店", "景点"),
    "数码电子": ("苹果", "apple", "小米", "华为", "电脑", "手机", "数码", "耳机"),
    "宠物": ("宠物", "猫", "狗", "兽医", "宠", "喵", "汪"),
    "通讯": ("话费", "流量", "移动", "联通", "电信", "宽带", "充值"),
    "房租住房": ("房租", "物业", "水费", "电费", "燃气", "房贷", "租金"),
    "投资理财": ("基金", "股票", "理财", "证券", "保险", "定投"),
    "人情往来": ("红包", "礼金", "份子", "转账给", "还给"),
}


@dataclass
class Classification:
    category: str
    confidence: float
    source: str  # one of: mapping | rule | llm | fallback
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "reason": self.reason,
        }


class LLMClient(Protocol):
    def classify(
        self, merchant: Optional[str], raw_text: str, categories: list[str]
    ) -> Optional[Classification]:
        ...


MappingLookup = Callable[[str], Optional[str]]
"""Callable that returns a learned category for a normalized merchant, or None."""


def normalize_merchant(merchant: Optional[str]) -> str:
    """Normalize a merchant name for stable mapping keys."""
    if not merchant:
        return ""
    return "".join(merchant.split()).lower()


def _rule_match(merchant: Optional[str], raw_text: str) -> Optional[Classification]:
    haystack = f"{merchant or ''} {raw_text or ''}".lower()
    for category, keywords in _KEYWORD_RULES.items():
        for kw in keywords:
            if kw.lower() in haystack:
                return Classification(
                    category=category,
                    confidence=0.75,
                    source="rule",
                    reason=f"matched keyword '{kw}'",
                )
    return None


def classify(
    merchant: Optional[str],
    raw_text: str,
    *,
    mapping_lookup: Optional[MappingLookup] = None,
    llm_client: Optional[LLMClient] = None,
    categories: Optional[list[str]] = None,
) -> Classification:
    """Run the full classification pipeline and return a Classification."""
    categories = categories or DEFAULT_CATEGORIES
    key = normalize_merchant(merchant)

    # Stage 1: learned merchant mapping.
    if key and mapping_lookup is not None:
        learned = mapping_lookup(key)
        if learned:
            return Classification(
                category=learned,
                confidence=0.98,
                source="mapping",
                reason="learned from user history",
            )

    # Stage 2: keyword rules.
    rule_hit = _rule_match(merchant, raw_text)
    if rule_hit is not None:
        return rule_hit

    # Stage 3: LLM fallback (only when configured).
    if llm_client is not None:
        try:
            llm_result = llm_client.classify(merchant, raw_text, categories)
        except Exception:  # noqa: BLE001 - never crash the pipeline
            llm_result = None
        if llm_result is not None:
            if llm_result.category not in categories:
                llm_result.category = "其他"
            return llm_result

    # Nothing matched: mark as low-confidence "其他" for manual review.
    return Classification(
        category="其他",
        confidence=0.2,
        source="fallback",
        reason="no rule/mapping/LLM match",
    )
