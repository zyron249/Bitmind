from bitmind.core import anti_cheat, models
from bitmind.core.models import InMemoryDB
import pytest

@pytest.fixture(autouse=True)
def reset_db():
    InMemoryDB.users = {}
    InMemoryDB.tasks = {}
    InMemoryDB.assignments = {}
    InMemoryDB.submissions = {}
    InMemoryDB.ledger_entries = []


def test_ai_scoring_and_hidden_test():
    task = models.create_task("What is 3+3?", "6", 1, True)
    # correct
    score = anti_cheat.ai_score_submission("6", task)
    assert score >= 0.9
    assert anti_cheat.check_hidden_test("6", task) is True
    # incorrect
    score2 = anti_cheat.ai_score_submission("seven", task)
    assert score2 < 0.8
    assert anti_cheat.check_hidden_test("seven", task) is False
