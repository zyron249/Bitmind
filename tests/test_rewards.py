import pytest
from bitmind.core import rewards, models, ledger
from bitmind.core.models import InMemoryDB

@pytest.fixture(autouse=True)
def reset_db():
    InMemoryDB.users = {}
    InMemoryDB.tasks = {}
    InMemoryDB.assignments = {}
    InMemoryDB.submissions = {}
    InMemoryDB.ledger_entries = []


def test_stake_and_slash():
    # create user
    user = models.create_user("staker")
    assert user.balance == 100.0

    # stake
    rewards.stake(user.id, 20)
    u = models.get_user(user.id)
    assert u.staked == 20
    assert u.balance == 80.0

    # slash some
    slashed = rewards.slash(user.id, 10, reason="fraud")
    assert slashed == 10
    u2 = models.get_user(user.id)
    assert u2.staked == 10

    # ledger entries reflect stake and slashing
    entries = ledger.get_ledger_for_user(user.id)
    reasons = [e.reason for e in entries]
    assert "stake" in reasons
    assert "fraud" in reasons
