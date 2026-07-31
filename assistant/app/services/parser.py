"""Rule-based parser: extract structured fields from raw consumption text.

This is stage 1 of the parsing pipeline. It relies only on the Python
standard library so it can run offline and be unit-tested in isolation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Direction of a transaction from the user's point of view.
DIRECTION_EXPENSE = "expense"
DIRECTION_INCOME = "income"
DIRECTION_TRANSFER = "transfer"

# Keyword tables kept intentionally small and explicit.
_INCOME_KEYWORDS = ("收入", "到账", "工资", "退款", "收款", "红包收入", "利息")
_TRANSFER_KEYWORDS = ("转账", "还款", "转入", "转出", "提现")

_PAY_METHODS = {
    "支付宝": ("支付宝", "alipay"),
    "微信": ("微信", "wechat", "weixin"),
    "云闪付": ("云闪付", "unionpay"),
    "信用卡": ("信用卡", "credit"),
    "储蓄卡": ("储蓄卡", "借记卡", "debit"),
    "现金": ("现金", "cash"),
    "银行卡": ("银行卡", "银联"),
}

# Merchant markers that usually precede a merchant name.
_MERCHANT_LABELS = ("商户", "商家", "收款方", "对方", "店铺", "门店", "merchant")

# Amount markers.
_AMOUNT_LABELS = ("金额", "支付", "付款", "消费", "amount", "合计", "实付")

# Match a currency amount such as 126.58, ￥126.58, 1,234.00, 126.58 元.
_AMOUNT_RE = re.compile(
    r"(?:￥|¥|\$|RMB|CNY)?\s*"
    r"(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
    r"\s*(?:元|块|yuan|RMB|CNY)?",
    re.IGNORECASE,
)


@dataclass
class ParsedTransaction:
    """Result of the rule-based parsing stage."""

    amount: Optional[float] = None
    merchant: Optional[str] = None
    direction: str = DIRECTION_EXPENSE
    pay_method: Optional[str] = None
    raw_text: str = ""
    # Confidence that the *extraction* (not classification) succeeded.
    extract_confidence: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "merchant": self.merchant,
            "direction": self.direction,
            "pay_method": self.pay_method,
            "raw_text": self.raw_text,
            "extract_confidence": round(self.extract_confidence, 3),
            "notes": self.notes,
        }


def _detect_direction(text: str) -> str:
    if any(k in text for k in _TRANSFER_KEYWORDS):
        return DIRECTION_TRANSFER
    if any(k in text for k in _INCOME_KEYWORDS):
        return DIRECTION_INCOME
    return DIRECTION_EXPENSE


def _detect_pay_method(text: str) -> Optional[str]:
    lowered = text.lower()
    for name, aliases in _PAY_METHODS.items():
        if any(alias.lower() in lowered for alias in aliases):
            return name
    return None


def _extract_amount(text: str) -> Optional[float]:
    """Prefer amounts that appear right after an amount label."""
    for label in _AMOUNT_LABELS:
        idx = text.find(label)
        if idx == -1:
            continue
        window = text[idx : idx + 40]
        m = _AMOUNT_RE.search(window[len(label):])
        if m:
            return _to_float(m.group("num"))
    # Fallback: pick the largest numeric token that looks like money.
    candidates = [
        _to_float(m.group("num"))
        for m in _AMOUNT_RE.finditer(text)
        if m.group("num")
    ]
    candidates = [c for c in candidates if c is not None and c > 0]
    if candidates:
        # A money amount usually has decimals or is the largest value.
        with_decimals = [c for c in candidates if c != int(c)]
        return with_decimals[0] if with_decimals else max(candidates)
    return None


def _extract_merchant(text: str) -> Optional[str]:
    for label in _MERCHANT_LABELS:
        # Match "商户：永辉超市" or "商户 永辉超市".
        pattern = re.compile(
            rf"{label}\s*[:：]?\s*(?P<name>[^\n，,。；;]+)", re.IGNORECASE
        )
        m = pattern.search(text)
        if m:
            name = m.group("name").strip()
            # Trim trailing amount fragments if present.
            name = re.split(r"\s{2,}|金额|付款|支付", name)[0].strip()
            if name:
                return name
    return None


def _to_float(num: str) -> Optional[float]:
    try:
        return float(num.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def parse_text(text: str) -> ParsedTransaction:
    """Parse a raw consumption message into a ParsedTransaction.

    The returned ``extract_confidence`` reflects how many key fields were
    recovered; downstream code decides whether an LLM fallback is needed.
    """
    text = (text or "").strip()
    result = ParsedTransaction(raw_text=text)
    if not text:
        result.notes.append("empty input")
        return result

    result.amount = _extract_amount(text)
    result.merchant = _extract_merchant(text)
    result.direction = _detect_direction(text)
    result.pay_method = _detect_pay_method(text)

    score = 0.0
    if result.amount is not None:
        score += 0.6
    else:
        result.notes.append("amount not found")
    if result.merchant:
        score += 0.3
    else:
        result.notes.append("merchant not found")
    if result.pay_method:
        score += 0.1
    result.extract_confidence = score
    return result
