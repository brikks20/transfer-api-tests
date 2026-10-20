from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app, reset_storage


# чистим данные перед каждым тестом, чтобы тесты не влияли друг на друга
@pytest.fixture(autouse=True)
def clean_storage():
    reset_storage()
    yield
    reset_storage()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def create_account(client):
    def _create(owner="Test User", balance="0"):
        r = client.post("/accounts", json={"owner": owner, "balance": balance})
        assert r.status_code == 201, r.text
        return r.json()

    return _create


@pytest.fixture
def sender(create_account):
    return create_account(owner="Sender", balance="2000000")


@pytest.fixture
def receiver(create_account):
    return create_account(owner="Receiver", balance="0")


# float для денег сравнивать нельзя, поэтому через Decimal
def as_money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))
