from fastapi import APIRouter, HTTPException
from ..core import audit

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("")
def list_audit():
    events = audit.list_audit_events()
    return [e.dict() for e in events]

@router.get("/{audit_id}")
def get_audit(audit_id: str):
    ev = audit.get_audit_event(audit_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return ev.dict()
