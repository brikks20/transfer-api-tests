import pytest

from tests.conftest import as_money


def test_create_account(client):
    r = client.post("/accounts", json={"owner": "Azat", "balance": "500.50"})

    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "owner", "balance"}
    assert body["owner"] == "Azat"
    assert as_money(body["balance"]) == as_money("500.50")


def test_balance_default_zero(client):
    r = client.post("/accounts", json={"owner": "Azat"})

    assert r.status_code == 201
    assert as_money(r.json()["balance"]) == 0


def test_ids_are_unique(create_account):
    ids = {create_account()["id"] for _ in range(5)}
    assert len(ids) == 5


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"owner": ""},
        {"owner": "A" * 101},
        {"owner": "Azat", "balance": "-1"},
        {"owner": "Azat", "balance": "10.555"},
        {"owner": "Azat", "balance": "abc"},
    ],
    ids=["empty_body", "empty_owner", "long_owner", "negative_balance", "3_decimals", "not_number"],
)
def test_create_account_invalid(client, payload):
    r = client.post("/accounts", json=payload)
    assert r.status_code == 422


def test_get_account(client, create_account):
    acc = create_account(owner="Azat", balance="100")

    r = client.get(f"/accounts/{acc['id']}")

    assert r.status_code == 200
    assert r.json() == acc


def test_get_account_not_found(client):
    r = client.get("/accounts/does-not-exist")

    assert r.status_code == 404
    assert r.json()["detail"] == "Account not found"
