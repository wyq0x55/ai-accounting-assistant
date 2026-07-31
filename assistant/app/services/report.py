"""Statistics and AI monthly report generation.

Statistics are computed locally from the assistant database so they work
offline. The natural-language monthly report uses the LLM when available and
falls back to a deterministic template otherwise.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Optional

from .llm import OpenAICompatibleClient


def _month_key(date_str: str) -> str:
    # date_str is ISO "YYYY-MM-DD".
    return date_str[:7] if date_str else "unknown"


def compute_stats(transactions: Iterable[dict], month: Optional[str] = None) -> dict:
    """Aggregate confirmed/archived expense transactions.

    Each transaction dict must contain: amount, category, direction, date.
    """
    by_category: dict[str, float] = defaultdict(float)
    by_merchant: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    total_expense = 0.0
    total_income = 0.0
    count = 0

    for tx in transactions:
        date = tx.get("date") or ""
        if month and _month_key(date) != month:
            continue
        amount = float(tx.get("amount") or 0)
        direction = tx.get("direction", "expense")
        by_month[_month_key(date)] += amount if direction == "expense" else 0
        if direction == "expense":
            total_expense += amount
            by_category[tx.get("category") or "其他"] += amount
            merchant = tx.get("merchant") or tx.get("payee") or "未知商户"
            by_merchant[merchant] += amount
            count += 1
        elif direction == "income":
            total_income += amount

    category_breakdown = [
        {
            "category": c,
            "amount": round(v, 2),
            "percent": round(v / total_expense * 100, 1) if total_expense else 0,
        }
        for c, v in sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)
    ]
    top_merchants = [
        {"merchant": m, "amount": round(v, 2)}
        for m, v in sorted(by_merchant.items(), key=lambda kv: kv[1], reverse=True)[:10]
    ]
    trend = [
        {"month": m, "expense": round(v, 2)}
        for m, v in sorted(by_month.items())
    ]

    return {
        "month": month,
        "total_expense": round(total_expense, 2),
        "total_income": round(total_income, 2),
        "transaction_count": count,
        "category_breakdown": category_breakdown,
        "top_merchants": top_merchants,
        "trend": trend,
    }


def _template_report(stats: dict, prev_stats: Optional[dict]) -> str:
    lines = []
    total = stats["total_expense"]
    lines.append(f"本月共记录 {stats['transaction_count']} 笔支出，合计 {total:.2f} 元。")
    if prev_stats and prev_stats.get("total_expense"):
        prev = prev_stats["total_expense"]
        if prev:
            delta = (total - prev) / prev * 100
            trend_word = "增长" if delta >= 0 else "下降"
            lines.append(f"较上月{trend_word} {abs(delta):.1f}%。")
    if stats["category_breakdown"]:
        top = stats["category_breakdown"][0]
        lines.append(
            f"占比最高的分类是「{top['category']}」，为 {top['amount']:.2f} 元"
            f"（{top['percent']:.1f}%）。"
        )
    if stats["top_merchants"]:
        m = stats["top_merchants"][0]
        lines.append(f"消费最多的商户是「{m['merchant']}」，合计 {m['amount']:.2f} 元。")
    return " ".join(lines)


def generate_monthly_report(
    stats: dict,
    prev_stats: Optional[dict] = None,
    llm_client: Optional[OpenAICompatibleClient] = None,
) -> dict:
    """Return {'summary': str, 'source': 'llm'|'template', 'stats': stats}."""
    template = _template_report(stats, prev_stats)
    summary = template
    source = "template"

    if llm_client is not None and llm_client.enabled:
        prompt = (
            "根据以下本月记账统计数据，写一段 3-5 句的中文月度消费分析，"
            "指出主要支出结构、异常或值得关注的点，并给出一条务实建议。\n\n"
            f"本月统计: {stats}\n上月统计: {prev_stats}"
        )
        llm_summary = llm_client.summarize(prompt)
        if llm_summary:
            summary = llm_summary
            source = "llm"

    return {"summary": summary, "source": source, "stats": stats}
