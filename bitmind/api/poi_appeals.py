from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..core import models, audit, validators as core_validators
from ..consensus import slashing
from datetime import datetime
import uuid

router = APIRouter(prefix="/poi", tags=["proof_of_intelligence"])

class AppealActionRequest(BaseModel):
    validator_id: str
    reason: Optional[str] = None

@router.post("/appeal/{appeal_id}/approve")
def approve_appeal(appeal_id: str, req: AppealActionRequest):
    # authorization
    if not core_validators.is_authorized_validator(req.validator_id):
        raise HTTPException(status_code=403, detail="Validator not authorized")
    appeals = getattr(models.InMemoryDB, 'appeals', [])
    appeal = next((a for a in appeals if a.get('appeal_id') == appeal_id), None)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if appeal.get('status') != 'pending':
        raise HTTPException(status_code=400, detail="Appeal not pending")
    # approve
    appeal['status'] = 'approved'
    appeal['resolved_by'] = req.validator_id
    appeal['resolved_at'] = datetime.utcnow().isoformat()
    # update submission verdict
    sub_id = appeal.get('submission_id')
    sub = models.InMemoryDB.submissions.get(sub_id)
    if sub:
        sub.verdict = 'appeal_approved'
        models.InMemoryDB.submissions[sub.id] = sub
    # audit
    audit.add_audit_event(event_type='appeal_approved', actor_id=req.validator_id, target_id=sub_id, reason=req.reason, metadata={'appeal_id': appeal_id})
    # if approval on fraudulent approval? leave slashing to other flows
    return {"appeal_id": appeal_id, "status": "approved"}

@router.post("/appeal/{appeal_id}/deny")
def deny_appeal(appeal_id: str, req: AppealActionRequest):
    if not core_validators.is_authorized_validator(req.validator_id):
        raise HTTPException(status_code=403, detail="Validator not authorized")
    appeals = getattr(models.InMemoryDB, 'appeals', [])
    appeal = next((a for a in appeals if a.get('appeal_id') == appeal_id), None)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if appeal.get('status') != 'pending':
        raise HTTPException(status_code=400, detail="Appeal not pending")
    appeal['status'] = 'denied'
    appeal['resolved_by'] = req.validator_id
    appeal['resolved_at'] = datetime.utcnow().isoformat()
    appeal['denial_reason'] = req.reason
    # audit
    audit.add_audit_event(event_type='appeal_denied', actor_id=req.validator_id, target_id=appeal.get('submission_id'), reason=req.reason, metadata={'appeal_id': appeal_id})
    return {"appeal_id": appeal_id, "status": "denied"}
