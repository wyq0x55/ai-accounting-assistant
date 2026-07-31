from app.services.parser import (
    DIRECTION_EXPENSE,
    DIRECTION_INCOME,
    DIRECTION_TRANSFER,
    parse_text,
)


def test_parse_alipay_expense():
    p = parse_text("支付宝付款成功\n商户：永辉超市\n金额：126.58 元")
    assert p.amount == 126.58
    assert p.merchant == "永辉超市"
    assert p.pay_method == "支付宝"
    assert p.direction == DIRECTION_EXPENSE
    assert p.extract_confidence == 1.0


def test_parse_income_with_thousands():
    p = parse_text("微信收款 工资到账 12,345.00元")
    assert p.amount == 12345.0
    assert p.direction == DIRECTION_INCOME


def test_parse_transfer():
    p = parse_text("转账给张三 200元")
    assert p.direction == DIRECTION_TRANSFER


def test_parse_empty():
    p = parse_text("")
    assert p.amount is None
    assert "empty input" in p.notes
