from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid
from typing import Optional, List
from ..core import models, audit

class Proposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"  # active, passed, rejected
    voting_starts_at: datetime | None = None
    voting_ends_at: datetime | None = None
    executed_at: datetime | None = None
    quorum_required: float = 0.20
    # Set slightly above 2/3 to prevent premature finalization when a simple majority exists but not all votes are cast.
    early_majority_threshold: float = 0.67


def _ensure_store():
    if not hasattr(models.InMemoryDB, 'proposals'):
        models.InMemoryDB.proposals = {}


def create_proposal(title: str, description: str, created_by: str, voting_starts_at: datetime | None = None, voting_period_seconds: int = 86400, quorum_required: float = 0.20) -> Proposal:
    _ensure_store()
    now = datetime.utcnow()
    if voting_starts_at is None:
        voting_starts_at = now
    voting_ends_at = voting_starts_at + timedelta(seconds=voting_period_seconds)
    p = Proposal(title=title, description=description, created_by=created_by, voting_starts_at=voting_starts_at, voting_ends_at=voting_ends_at, quorum_required=quorum_required)
    models.InMemoryDB.proposals[p.proposal_id] = p
    audit.add_audit_event(event_type='proposal_created', actor_id=created_by, target_id=p.proposal_id, reason=title, metadata={"voting_starts_at": p.voting_starts_at.isoformat(), "voting_ends_at": p.voting_ends_at.isoformat()})
    return p


def get_proposal(proposal_id: str) -> Optional[Proposal]:
    _ensure_store()
    return models.InMemoryDB.proposals.get(proposal_id)


def list_proposals() -> List[Proposal]:
    _ensure_store()
    return list(models.InMemoryDB.proposals.values())


def set_proposal_status(proposal_id: str, status: str) -> bool:
    _ensure_store()
    p = models.InMemoryDB.proposals.get(proposal_id)
    if not p:
        return False
    p.status = status
    if status == 'passed' or status == 'rejected':
        p.executed_at = datetime.utcnow()
    models.InMemoryDB.proposals[proposal_id] = p
    audit.add_audit_event(event_type='proposal_status_updated', actor_id=None, target_id=proposal_id, reason=status)
    return True


def finalize_proposal(proposal_id: str) -> dict:
    _ensure_store()
    p = models.InMemoryDB.proposals.get(proposal_id)
    if not p:
        return {"error": "not_found"}
    now = datetime.utcnow()
    if p.voting_ends_at and now < p.voting_ends_at:
        return {"error": "voting_not_ended"}
    # tally votes via governance.voting.tally_and_update but we need quorum check
    from . import voting
    tally = voting.tally_votes_raw(proposal_id)
    total_active = voting.total_active_stake()
    yes = tally["yes_power"]
    no = tally["no_power"]
    cast = tally["cast_power"]
    quorum = 0.0
    if total_active > 0:
        quorum = cast / total_active
    if quorum < p.quorum_required:
        set_proposal_status(proposal_id, 'rejected')
        audit.add_audit_event(event_type='proposal_finalized', actor_id=None, target_id=proposal_id, reason='quorum_failed', metadata={"quorum": quorum, "required": p.quorum_required})
        return {"status": "rejected", "reason": "quorum_not_met", "quorum": quorum}
    # quorum met
    if yes > no:
        set_proposal_status(proposal_id, 'passed')
        audit.add_audit_event(event_type='proposal_finalized', actor_id=None, target_id=proposal_id, reason='passed', metadata={"yes": yes, "no": no, "quorum": quorum})
        return {"status": "passed", "yes": yes, "no": no, "quorum": quorum}
    else:
        set_proposal_status(proposal_id, 'rejected')
        audit.add_audit_event(event_type='proposal_finalized', actor_id=None, target_id=proposal_id, reason='rejected', metadata={"yes": yes, "no": no, "quorum": quorum})
        return {"status": "rejected", "yes": yes, "no": no, "quorum": quorum}
