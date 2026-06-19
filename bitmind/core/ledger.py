from . import models


def add_entry(user_id: str, amount: float, reason: str = "") -> models.LedgerEntry:
    entry = models.LedgerEntry(user_id=user_id, amount=amount, reason=reason)
    models.add_ledger_entry(entry)
    # update user balance
    user = models.get_user(user_id)
    if user:
        user.balance += amount
        models.InMemoryDB.users[user.id] = user
    return entry


def credit(user_id: str, amount: float, reason: str = "credit") -> models.LedgerEntry:
    return add_entry(user_id, amount, reason)


def debit(user_id: str, amount: float, reason: str = "debit") -> models.LedgerEntry:
    return add_entry(user_id, -abs(amount), reason)


def get_ledger_for_user(user_id: str):
    return models.get_ledger_for_user(user_id)


def get_balance(user_id: str):
    user = models.get_user(user_id)
    return user.balance if user else 0.0
