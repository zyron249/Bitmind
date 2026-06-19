from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..core import models, audit, validators as core_validators
from datetime import datetime

router = APIRouter(prefix="/poi", tags=["proof_of_intelligence"])

class AppealActionRequest(BaseModel):
    validator_id: str
    reason: Optional[str] = None

class BatchAppealActionRequest(BaseModel):
    validator_id: str
    appeal_ids: List[str]
    reason: Optional[str] = None

@router.get("/appeals/pending")
def list_pending_appeals():
    appeals = getattr(models.InMemoryDB, 'appeals', [])
    pending = [a for a in appeals if a.get('status') == 'pending']
    return pending

@router.post("/appeals/batch-approve")
def batch_approve_appeals(req: BatchAppealActionRequest):
    if not core_validators.is_authorized_validator(req.validator_id):
        raise HTTPException(status_code=403, detail="Validator not authorized")
    appeals = getattr(models.InMemoryDB, 'appeals', [])
    approved = []
    skipped = []
    failed = []
    for aid in req.appeal_ids:
        appeal = next((a for a in appeals if a.get('appeal_id') == aid), None)
        if not appeal:
            failed.append({"appeal_id": aid, "reason": "not_found"})
            continue
        if appeal.get('status') != 'pending':
            skipped.append(aid)
            continue
        # approve
        appeal['status'] = 'approved'
        appeal['resolved_by'] = req.validator_id
        appeal['resolved_at'] = datetime.utcnow().isoformat()
        sub_id = appeal.get('submission_id')
        sub = models.InMemoryDB.submissions.get(sub_id)
        if sub:
            sub.verdict = 'appeal_approved'
            models.InMemoryDB.submissions[sub.id] = sub
        audit.add_audit_event(event_type='appeal_approved', actor_id=req.validator_id, target_id=sub_id, reason=req.reason, metadata={'appeal_id': aid})
        approved.append(aid)
    return {"approved": approved, "skipped": skipped, "failed": failed}

@router.post("/appeals/batch-deny")
def batch_deny_appeals(req: BatchAppealActionRequest):
    if not core_validators.is_authorized_validator(req.validator_id):
        raise HTTPException(status_code=403, detail="Validator not authorized")
    appeals = getattr(models.InMemoryDB, 'appeals', [])
    denied = []
    skipped = []
    failed = []
    for aid in req.appeal_ids:
        appeal = next((a for a in appeals if a.get('appeal_id') == aid), None)
        if not appeal:
            failed.append({"appeal_id": aid, "reason": "not_found"})
            continue
        if appeal.get('status') != 'pending':
            skipped.append(aid)
            continue
        appeal['status'] = 'denied'
        appeal['resolved_by'] = req.validator_id
        appeal['resolved_at'] = datetime.utcnow().isoformat()
        appeal['denial_reason'] = req.reason
        # update submission if exists
        sub_id = appeal.get('submission_id')
        sub = models.InMemoryDB.submissions.get(sub_id)
        if sub:
            sub.verdict = 'appeal_denied'
            models.InMemoryDB.submissions[sub.id] = sub
        audit.add_audit_event(event_type='appeal_denied', actor_id=req.validator_id, target_id=sub_id, reason=req.reason, metadata={'appeal_id': aid})
        denied.append(aid)
    return {"denied": denied, "skipped": skipped, "failed": failed}
