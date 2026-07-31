"""End-to-end API test: ingest -> review -> correct -> confirm -> stats."""

from __future__ import annotations


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_default_categories_seeded(client):
    r = client.get("/api/categories")
    names = [c["name"] for c in r.get_json()["items"]]
    assert "餐饮" in names and "其他" in names
    assert len(names) >= 14


def test_full_flow(client):
    # 1) ingest a raw message
    r = client.post("/api/ingest/text", json={"text": "支付宝付款成功 商户：永辉超市 金额：126.58 元"})
    assert r.status_code == 201
    tx = r.get_json()
    assert tx["amount"] == 126.58
    assert tx["state"] == "pending_review"

    tx_id = tx["id"]

    # 2) user corrects the category -> should trigger self-learning
    r = client.patch(f"/api/transactions/{tx_id}", json={"category": "日用品"})
    assert r.get_json()["category"] == "日用品"

    # mapping learned
    r = client.get("/api/mappings")
    keys = [m["category"] for m in r.get_json()["items"]]
    assert "日用品" in keys

    # 3) confirm (bridge disabled -> stays confirmed, unsynced)
    r = client.post(f"/api/transactions/{tx_id}/confirm")
    assert r.status_code == 200
    assert r.get_json()["state"] == "confirmed"

    # 4) a second identical merchant should now auto-classify via mapping
    r = client.post("/api/ingest/text", json={"text": "永辉超市 88.00元"})
    tx2 = r.get_json()
    assert tx2["category"] == "日用品"
    assert tx2["classify_source"] == "mapping"

    # 5) stats reflect the confirmed expense
    month = tx["date"][:7]
    r = client.get(f"/api/stats?month={month}")
    stats = r.get_json()
    assert stats["total_expense"] >= 126.58
    assert any(c["category"] == "日用品" for c in stats["category_breakdown"])

    # 6) monthly report renders (template mode, no LLM)
    r = client.get(f"/api/report/monthly?month={month}")
    body = r.get_json()
    assert body["source"] == "template"
    assert "支出" in body["summary"]
