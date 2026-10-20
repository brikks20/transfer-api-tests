# Сервис переводов, который тестируем
# Правила: до 10000 без комиссии, больше 10000 - комиссия 1%
# сумма от 1 до 1 000 000, себе переводить нельзя

from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

COMMISSION_FREE_LIMIT = Decimal("10000.00")
COMMISSION_RATE = Decimal("0.01")
MIN_AMOUNT = Decimal("1.00")
MAX_AMOUNT = Decimal("1000000.00")

app = FastAPI(title="Transfer API")

# храним все в памяти, базы нет
accounts = {}
transfers = {}


def reset_storage():
    accounts.clear()
    transfers.clear()


def money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_commission(amount):
    if amount <= COMMISSION_FREE_LIMIT:
        return Decimal("0.00")
    return money(amount * COMMISSION_RATE)


class AccountCreate(BaseModel):
    owner: str = Field(min_length=1, max_length=100)
    balance: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)


class TransferCreate(BaseModel):
    from_account: str
    to_account: str
    amount: Decimal = Field(decimal_places=2)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate):
    account_id = str(uuid4())
    account = {"id": account_id, "owner": payload.owner, "balance": money(payload.balance)}
    accounts[account_id] = account
    return account


@app.get("/accounts/{account_id}")
def get_account(account_id: str):
    if account_id not in accounts:
        raise HTTPException(404, "Account not found")
    return accounts[account_id]


@app.post("/transfers", status_code=status.HTTP_201_CREATED)
def create_transfer(payload: TransferCreate):
    amount = money(payload.amount)

    if amount < MIN_AMOUNT or amount > MAX_AMOUNT:
        raise HTTPException(422, f"Amount must be between {MIN_AMOUNT} and {MAX_AMOUNT}")
    if payload.from_account == payload.to_account:
        raise HTTPException(400, "Cannot transfer to the same account")

    sender = accounts.get(payload.from_account)
    receiver = accounts.get(payload.to_account)
    if sender is None or receiver is None:
        raise HTTPException(404, "Account not found")

    commission = calculate_commission(amount)
    total = amount + commission
    if sender["balance"] < total:
        raise HTTPException(409, "Insufficient funds")

    sender["balance"] = money(sender["balance"] - total)
    receiver["balance"] = money(receiver["balance"] + amount)

    transfer = {
        "id": str(uuid4()),
        "from_account": sender["id"],
        "to_account": receiver["id"],
        "amount": amount,
        "commission": commission,
        "total_debited": money(total),
        "status": "completed",
    }
    transfers[transfer["id"]] = transfer
    return transfer


@app.get("/transfers/{transfer_id}")
def get_transfer(transfer_id: str):
    if transfer_id not in transfers:
        raise HTTPException(404, "Transfer not found")
    return transfers[transfer_id]
