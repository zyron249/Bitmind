from bitmind.core import ledger, models
from bitmind.core.models import InMemoryDB
import pytest

@pytest.fixture(autouse=True)
def reset_db():
    InMemoryDB.users = {}
    InMemoryDB.tasks = {}
    InMemoryDB.assignments = {}
    InMemoryDB.submissions = {}
    InMemoryDB.ledger_entries = []


def test_ledger_credit_debit():
    u = models.create_user("ledgeruser")
    assert ledger.get_balance(u.id) == 100.0
    ledger.credit(u.id, 25, reason="test_credit")
    assert ledger.get_balance(u.id) == 125.0
    ledger.debit(u.id, 10, reason="test_debit")
    assert ledger.get_balance(u.id) == 115.0
    entries = ledger.get_ledger_for_user(u.id)
    assert len(entries) == 2
    reasons = [e.reason for e in entries]
    assert "test_credit" in reasons and "test_debit" in reasons
