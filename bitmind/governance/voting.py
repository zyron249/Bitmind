from typing import Optional, List
from ..core import models
from ..core import validators as core_validators
from ..core import audit
from . import proposals
from datetime import datetime


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
    # check voting period
    now = datetime.utcnow()
    if p.voting_starts_at and now < p.voting_starts_at:
        return False
    if p.voting_ends_at and now > p.voting_ends_at:
        return False
    # voting power = validator.staked_amount
    voting_power = v.staked_amount
    key = f"{proposal_id}:{voter_validator_id}"
    models.InMemoryDB.votes[key] = Vote(voter_id=voter_validator_id, proposal_id=proposal_id, vote=vote, voting_power=voting_power)
    audit.add_audit_event(event_type='proposal_vote', actor_id=voter_validator_id, target_id=proposal_id, reason=vote, metadata={'voting_power': voting_power})
    # After casting vote, attempt early finalize if early majority reached and quorum met
    tally = tally_votes_raw(proposal_id)
    total_active = total_active_stake()
    cast_power = tally['cast_power']
    quorum = (cast_power / total_active) if total_active > 0 else 0.0
    yes_power = tally['yes_power']
    no_power = tally['no_power']
    # early finalize condition
    if total_active > 0 and quorum >= p.quorum_required:
        # if yes or no majority exceed early_majority_threshold of total_active, finalize early
        if (yes_power / total_active) >= p.early_majority_threshold:
            proposals.set_proposal_status(proposal_id, 'passed')
        elif (no_power / total_active) >= p.early_majority_threshold:
            proposals.set_proposal_status(proposal_id, 'rejected')
        elif cast_power >= total_active:
            proposals.set_proposal_status(proposal_id, 'passed' if yes_power > no_power else 'rejected')
    return True


def tally_votes_raw(proposal_id: str) -> dict:
    _ensure_store()
    votes = [v for k, v in models.InMemoryDB.votes.items() if v.proposal_id == proposal_id]
    yes_power = sum(v.voting_power for v in votes if v.vote == 'yes')
    no_power = sum(v.voting_power for v in votes if v.vote == 'no')
    cast = yes_power + no_power
    return {'yes_power': yes_power, 'no_power': no_power, 'cast_power': cast}


def total_active_stake() -> float:
    vals = core_validators.list_validators()
    return sum(v.staked_amount for v in vals if v.active)


def list_votes_for_proposal(proposal_id: str) -> List[Vote]:
    _ensure_store()
    return [v for k, v in models.InMemoryDB.votes.items() if v.proposal_id == proposal_id]
