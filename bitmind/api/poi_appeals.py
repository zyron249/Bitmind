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


def _resolve_single_appeal(appeal_id: str, validator_id: str, reason: Optional[str], approve: bool):
    appeals = getattr(models.InMemoryDB, 'appeals', [])
    appeal = next((a for a in appeals if a.get('appeal_id') == appeal_id), None)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if appeal.get('status') != 'pending':
        raise HTTPException(status_code=400, detail="Appeal already resolved")

    status = 'approved' if approve else 'denied'
    event_type = 'appeal_approved' if approve else 'appeal_denied'
    verdict = 'appeal_approved' if approve else 'appeal_denied'
    appeal['status'] = status
    appeal['resolved_by'] = validator_id
    appeal['resolved_at'] = datetime.utcnow().isoformat()
    if not approve:
        appeal['denial_reason'] = reason
    sub_id = appeal.get('submission_id')
    sub = models.InMemoryDB.submissions.get(sub_id)
    if sub:
        sub.verdict = verdict
        models.InMemoryDB.submissions[sub.id] = sub
    audit.add_audit_event(event_type=event_type, actor_id=validator_id, target_id=sub_id, reason=reason, metadata={'appeal_id': appeal_id})
    return {"appeal_id": appeal_id, "status": status}

@router.get("/appeals/pending")
def list_pending_appeals():
    appeals = getattr(models.InMemoryDB, 'appeals', [])
    pending = [a for a in appeals if a.get('status') == 'pending']
    return pending


@router.post("/appeal/{appeal_id}/approve")
def approve_appeal(appeal_id: str, req: AppealActionRequest):
    if not core_validators.is_authorized_validator(req.validator_id):
        raise HTTPException(status_code=403, detail="Validator not authorized")
    return _resolve_single_appeal(appeal_id, req.validator_id, req.reason, approve=True)


@router.post("/appeal/{appeal_id}/deny")
def deny_appeal(appeal_id: str, req: AppealActionRequest):
    if not core_validators.is_authorized_validator(req.validator_id):
        raise HTTPException(status_code=403, detail="Validator not authorized")
    return _resolve_single_appeal(appeal_id, req.validator_id, req.reason, approve=False)

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
