from ..core import models
from typing import List


def select_validators(min_reputation: float = 0.6) -> List[str]:
    # deterministically pick users with reputation >= min_reputation
    return [u.id for u in models.InMemoryDB.users.values() if u.reputation >= min_reputation]


def validators_approval(task_id: str, consensus_score: float, threshold: float = 0.6) -> bool:
    validators = select_validators()
    if not validators:
        # no validators -> default to approve
        return True
    # simple rule: each validator approves if consensus_score >= 0.5
    approvals = 0
    for v in validators:
        if consensus_score >= 0.5:
            approvals += 1
    ratio = approvals / len(validators)
    return ratio >= threshold
