from bitmind.core import reputation, models
from bitmind.core.models import InMemoryDB
import pytest

@pytest.fixture(autouse=True)
def reset_db():
    InMemoryDB.users = {}
    InMemoryDB.tasks = {}
    InMemoryDB.assignments = {}
    InMemoryDB.submissions = {}
    InMemoryDB.ledger_entries = []


def test_reputation_update():
    u = models.create_user("repuser")
    assert u.reputation == 0.5
    # good final score
    reputation.update_reputation(u.id, 1.0)
    u2 = models.get_user(u.id)
    assert u2.reputation > 0.5
    # bad final score
    reputation.update_reputation(u.id, 0.0)
    u3 = models.get_user(u.id)
    assert u3.reputation < u2.reputation
