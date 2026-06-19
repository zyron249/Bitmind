from pydantic import BaseModel, Field
from datetime import datetime
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


def _ensure_store():
    if not hasattr(models.InMemoryDB, 'proposals'):
        models.InMemoryDB.proposals = {}


def create_proposal(title: str, description: str, created_by: str) -> Proposal:
    _ensure_store()
    p = Proposal(title=title, description=description, created_by=created_by)
    models.InMemoryDB.proposals[p.proposal_id] = p
    audit.add_audit_event(event_type='proposal_created', actor_id=created_by, target_id=p.proposal_id, reason=title)
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
    models.InMemoryDB.proposals[proposal_id] = p
    audit.add_audit_event(event_type='proposal_status_updated', actor_id=None, target_id=proposal_id, reason=status)
    return True
