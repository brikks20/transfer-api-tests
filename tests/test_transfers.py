import pytest

from tests.conftest import as_money


def transfer(client, frm, to, amount):
    return client.post(
        "/transfers",
        json={"from_account": frm["id"], "to_account": to["id"], "amount": amount},
    )


# граничные значения для комиссии, порог 10000
@pytest.mark.parametrize(
    "amount, commission",
    [
        ("1.00", "0.00"),
        ("9999.99", "0.00"),
        ("10000.00", "0.00"),  # на пороге комиссии еще нет
        ("10000.01", "100.00"),
        ("10001.00", "100.01"),
        ("50000.00", "500.00"),
        ("1000000.00", "10000.00"),
    ],
)
def test_commission(client, sender, receiver, amount, commission):
    r = transfer(client, sender, receiver, amount)

    assert r.status_code == 201, r.text
    body = r.json()
    assert as_money(body["commission"]) == as_money(commission)
    assert as_money(body["total_debited"]) == as_money(amount) + as_money(commission)


def test_transfer_response(client, sender, receiver):
    r = transfer(client, sender, receiver, "100.00")

    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "from_account", "to_account", "amount",
                         "commission", "total_debited", "status"}
    assert body["status"] == "completed"
    assert body["from_account"] == sender["id"]
    assert body["to_account"] == receiver["id"]


def test_balances_after_transfer(client, create_account):
    s = create_account(balance="20000.00")
    rcv = create_account(balance="500.00")

    r = transfer(client, s, rcv, "15000.00")
    assert r.status_code == 201

    # отправитель платит 15000 + 150 комиссии, получатель получает 15000
    assert as_money(client.get(f"/accounts/{s['id']}").json()["balance"]) == as_money("4850.00")
    assert as_money(client.get(f"/accounts/{rcv['id']}").json()["balance"]) == as_money("15500.00")


def test_get_transfer(client, sender, receiver):
    created = transfer(client, sender, receiver, "100.00").json()

    r = client.get(f"/transfers/{created['id']}")

    assert r.status_code == 200
    assert r.json() == created


def test_exact_balance_is_enough(client, create_account):
    # 20000 + 1% = 20200, на счете ровно столько
    s = create_account(balance="20200.00")
    rcv = create_account()

    r = transfer(client, s, rcv, "20000.00")

    assert r.status_code == 201
    assert as_money(client.get(f"/accounts/{s['id']}").json()["balance"]) == 0


@pytest.mark.parametrize("amount", ["0.99", "0", "-100", "1000000.01"])
def test_amount_out_of_range(client, sender, receiver, amount):
    r = transfer(client, sender, receiver, amount)
    assert r.status_code == 422


def test_amount_not_number(client, sender, receiver):
    r = transfer(client, sender, receiver, "сто рублей")
    assert r.status_code == 422


def test_transfer_to_myself(client, sender):
    r = transfer(client, sender, sender, "100.00")

    assert r.status_code == 400
    assert r.json()["detail"] == "Cannot transfer to the same account"


def test_unknown_sender(client, receiver):
    r = transfer(client, {"id": "unknown"}, receiver, "100.00")
    assert r.status_code == 404


def test_unknown_receiver(client, sender):
    r = transfer(client, sender, {"id": "unknown"}, "100.00")
    assert r.status_code == 404


def test_insufficient_funds(client, create_account):
    # нужно 20200, на счете на копейку меньше
    s = create_account(balance="20199.99")
    rcv = create_account(balance="0")

    r = transfer(client, s, rcv, "20000.00")

    assert r.status_code == 409
    assert r.json()["detail"] == "Insufficient funds"
    # деньги не должны списаться
    assert as_money(client.get(f"/accounts/{s['id']}").json()["balance"]) == as_money("20199.99")
    assert as_money(client.get(f"/accounts/{rcv['id']}").json()["balance"]) == 0


def test_get_transfer_not_found(client):
    r = client.get("/transfers/does-not-exist")
    assert r.status_code == 404


@pytest.mark.parametrize("field", ["from_account", "to_account", "amount"])
def test_missing_field(client, sender, receiver, field):
    payload = {"from_account": sender["id"], "to_account": receiver["id"], "amount": "100"}
    del payload[field]

    r = client.post("/transfers", json=payload)
    assert r.status_code == 422
