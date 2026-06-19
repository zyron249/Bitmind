from bitmind.core import models, rewards
from bitmind.consensus import proof_of_intelligence

from bitmind.core.models import InMemoryDB
import pytest

@pytest.fixture(autouse=True)
def reset_db():
    InMemoryDB.users = {}
    InMemoryDB.tasks = {}
    InMemoryDB.assignments = {}
    InMemoryDB.submissions = {}
    InMemoryDB.ledger_entries = []


def test_proof_of_intelligence_flow():
    # create users
    u1 = models.create_user("alice")
    u2 = models.create_user("bob")
    u3 = models.create_user("carol")
    # make u1 a validator by boosting reputation
    u1.reputation = 0.9
    models.InMemoryDB.users[u1.id] = u1

    # create hidden test task
    task = models.create_task("What is 6+6?", "12", 1, True)

    # assign to 3 users
    a1 = models.Assignment(task_id=task.id, assignee_id=u1.id)
    a2 = models.Assignment(task_id=task.id, assignee_id=u2.id)
    a3 = models.Assignment(task_id=task.id, assignee_id=u3.id)
    models.save_assignment(a1)
    models.save_assignment(a2)
    models.save_assignment(a3)

    # stake for u3 to test slashing
    rewards.stake(u3.id, 10)

    # submissions: u1 correct, u2 correct, u3 wrong
    s1 = models.Submission(assignment=a1, user_id=u1.id, content="12")
    models.save_submission(s1)
    s2 = models.Submission(assignment=a2, user_id=u2.id, content="12")
    models.save_submission(s2)
    s3 = models.Submission(assignment=a3, user_id=u3.id, content="twelve")
    models.save_submission(s3)

    # process task
    result = proof_of_intelligence.process_task(task.id)

    # check consensus: two ok / three -> pass
    assert result["consensus"]["consensus_pass"] is True
    # approval should be True because u1 is validator and consensus_score likely >=0.5
    assert result["approval"] is True

    # outcomes: u1,u2 eligible, u3 not eligible
    outcomes = {o["submission_id"]: o for o in result["outcomes"]}
    o1 = outcomes[s1.id]
    o2 = outcomes[s2.id]
    o3 = outcomes[s3.id]
    assert o1["eligible"] is True
    assert o2["eligible"] is True
    assert o3["eligible"] is False

    # check reputation increased for winners
    u1_after = models.get_user(u1.id)
    u2_after = models.get_user(u2.id)
    assert u1_after.reputation >= 0.9
    assert u2_after.reputation > 0.5

    # check u3 stake was slashed by 50%
    u3_after = models.get_user(u3.id)
    assert u3_after.staked == pytest.approx(5.0)

    # ledger balances: winners should have >100
    ledger1 = rewards.compute_reward_for_submission(models.InMemoryDB.submissions[s1.id])
    assert ledger1 > 0

    bal1 = models.get_user(u1.id).balance
    bal2 = models.get_user(u2.id).balance
    assert bal1 >= 100.0
    assert bal2 >= 100.0
