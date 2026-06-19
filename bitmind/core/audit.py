from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from typing import Optional, List
from . import models

class AuditEvent(BaseModel):
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    actor_id: Optional[str] = None
    target_id: Optional[str] = None
    reason: Optional[str] = None
    metadata: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


def _ensure_store():
    if not hasattr(models.InMemoryDB, 'audit_events'):
        models.InMemoryDB.audit_events = {}


def add_audit_event(event_type: str, actor_id: Optional[str] = None, target_id: Optional[str] = None, reason: Optional[str] = None, metadata: Optional[dict] = None) -> AuditEvent:
    _ensure_store()
    ev = AuditEvent(event_type=event_type, actor_id=actor_id, target_id=target_id, reason=reason, metadata=metadata)
    models.InMemoryDB.audit_events[ev.audit_id] = ev
    return ev


def list_audit_events() -> List[AuditEvent]:
    _ensure_store()
    return list(models.InMemoryDB.audit_events.values())


def get_audit_event(audit_id: str) -> Optional[AuditEvent]:
    _ensure_store()
    return models.InMemoryDB.audit_events.get(audit_id)
