from typing import Optional, List
from ..core import models
from ..core import validators as core_validators
from ..core import audit
from . import proposals


def _ensure_store():
    if not hasattr(models.InMemoryDB, 'votes'):
        models.InMemoryDB.votes = {}

class Vote:
    def __init__(self, voter_id: str, proposal_id: str, vote: str, voting_power: float):
        self.voter_id = voter_id
        self.proposal_id = proposal_id
        self.vote = vote  # 'yes' or 'no'
        self.voting_power = voting_power


def cast_vote(voter_validator_id: str, proposal_id: str, vote: str) -> bool:
    """voter_validator_id is validator.validator_id"""
    _ensure_store()
    # check validator
    v = core_validators.get_validator(voter_validator_id)
    if not v or not core_validators.is_authorized_validator(voter_validator_id):
        return False
    # ensure proposal exists and active
    p = proposals.get_proposal(proposal_id)
    if not p or p.status != 'active':
        return False
    # voting power = validator.staked_amount
    voting_power = v.staked_amount
    key = f"{proposal_id}:{voter_validator_id}"
    models.InMemoryDB.votes[key] = Vote(voter_id=voter_validator_id, proposal_id=proposal_id, vote=vote, voting_power=voting_power)
    audit.add_audit_event(event_type='proposal_vote', actor_id=voter_validator_id, target_id=proposal_id, reason=vote, metadata={'voting_power': voting_power})
    # After casting vote, attempt tally and update status if threshold met
    tally_and_update(proposal_id)
    return True


def tally_and_update(proposal_id: str) -> dict:
    _ensure_store()
    # collect votes for proposal
    votes = [v for k, v in models.InMemoryDB.votes.items() if v.proposal_id == proposal_id]
    if not votes:
        return {'yes_power': 0.0, 'no_power': 0.0, 'total_active_stake': total_active_stake(), 'passed': False}
    yes_power = sum(v.voting_power for v in votes if v.vote == 'yes')
    no_power = sum(v.voting_power for v in votes if v.vote == 'no')
    total_active = total_active_stake()
    passed = False
    # proposal passes if yes_power > 50% of total_active stake
    if total_active > 0 and (yes_power / total_active) > 0.5:
        proposals.set_proposal_status(proposal_id, 'passed')
        passed = True
    elif total_active > 0 and (no_power / total_active) >= 0.5:
        proposals.set_proposal_status(proposal_id, 'rejected')
    return {'yes_power': yes_power, 'no_power': no_power, 'total_active_stake': total_active, 'passed': passed}


def total_active_stake() -> float:
    vals = core_validators.list_validators()
    return sum(v.staked_amount for v in vals if v.active)


def list_votes_for_proposal(proposal_id: str) -> List[Vote]:
    _ensure_store()
    return [v for k, v in models.InMemoryDB.votes.items() if v.proposal_id == proposal_id]
