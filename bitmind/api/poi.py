from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

from ..core import models, anti_cheat, rewards, audit
from ..core import validators as core_validators
from ..consensus import slashing

router = APIRouter(prefix="/poi", tags=["proof_of_intelligence"])


class EvaluateRequest(BaseModel):
    user_id: str
    task_id: str
    submission_content: str
    reputation_score: Optional[float] = None
    fraud_risk: Optional[float] = None


class AwardRequest(BaseModel):
    submission_id: str
    approved_by_validator_id: str


class RejectRequest(BaseModel):
    submission_id: str
    validator_id: str
    reason: Optional[str] = None


class AppealRequest(BaseModel):
    submission_id: str
    user_id: str
    appeal_reason: str


def _ensure_runtime_stores():
    if not hasattr(models.InMemoryDB, "submission_fraud_scores"):
        models.InMemoryDB.submission_fraud_scores = {}


def _is_reputation_authorized_user(actor_id: str) -> bool:
    user = models.get_user(actor_id)
    return bool(user and user.reputation >= 0.8)


def _is_authorized_actor(actor_id: str) -> bool:
    validator = core_validators.get_validator(actor_id)
    if validator and validator.role in ("validator", "admin") and not validator.manually_deactivated:
        return True
    return _is_reputation_authorized_user(actor_id)


@router.post("/evaluate")
def evaluate(req: EvaluateRequest):
    user = models.get_user(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    task = models.get_task(req.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    assignment = models.Assignment(task_id=req.task_id, assignee_id=req.user_id)
    models.save_assignment(assignment)

    submission = models.Submission(
        assignment=assignment,
        user_id=req.user_id,
        content=req.submission_content,
    )

    submission.auto_score = anti_cheat.ai_score_submission(submission.content, task)

    ht_result = anti_cheat.check_hidden_test(submission.content, task)
    if ht_result is False:
        submission.final_score = 0.0
        submission.verdict = "hidden_test_failed"
        decision_reason = "hidden_test_failed"
    else:
        rep = req.reputation_score if req.reputation_score is not None else user.reputation
        submission.final_score = submission.auto_score * (0.5 + 0.5 * rep)
        submission.final_score = min(submission.final_score, 100.0)
        submission.verdict = "ok"
        decision_reason = "scored"

    models.save_submission(submission)

    _ensure_runtime_stores()
    fraud_score = float(req.fraud_risk) if req.fraud_risk is not None else anti_cheat.fraud_risk_score(submission)
    models.InMemoryDB.submission_fraud_scores[submission.id] = fraud_score

    reward_eligible = bool(submission.final_score > 0 and fraud_score < 0.8)

    audit.add_audit_event(
        event_type="evaluate",
        actor_id=req.user_id,
        target_id=submission.id,
        reason=decision_reason,
        metadata={"task_id": req.task_id, "fraud_score": fraud_score},
    )

    return {
        "submission_id": submission.id,
        "auto_score": submission.auto_score,
        "final_score": submission.final_score,
        "reward_eligible": reward_eligible,
        "fraud_score": fraud_score,
        "verdict": submission.verdict,
    }


@router.get("/status/{submission_id}")
def status(submission_id: str):
    submission = models.InMemoryDB.submissions.get(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    _ensure_runtime_stores()
    fraud_score = float(models.InMemoryDB.submission_fraud_scores.get(submission_id, anti_cheat.fraud_risk_score(submission)))

    return {
        "submission_id": submission.id,
        "auto_score": submission.auto_score,
        "final_score": submission.final_score,
        "reward_eligible": bool(submission.final_score > 0 and fraud_score < 0.8),
        "awarded": submission.awarded,
        "verdict": submission.verdict,
    }


@router.get("/evaluations")
def list_evaluations():
    _ensure_runtime_stores()
    out = []
    for submission in models.InMemoryDB.submissions.values():
        fraud_score = float(models.InMemoryDB.submission_fraud_scores.get(submission.id, anti_cheat.fraud_risk_score(submission)))
        out.append(
            {
                "submission_id": submission.id,
                "user_id": submission.user_id,
                "final_score": submission.final_score,
                "reward_eligible": bool(submission.final_score > 0 and fraud_score < 0.8),
                "awarded": submission.awarded,
                "verdict": submission.verdict,
            }
        )
    return out


@router.post("/award")
def award(req: AwardRequest):
    submission = models.InMemoryDB.submissions.get(req.submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    validator = core_validators.get_validator(req.approved_by_validator_id)
    if not _is_authorized_actor(req.approved_by_validator_id):
        if validator:
            slashing.slash_validator_for_event(req.approved_by_validator_id, "invalid_action")
        raise HTTPException(status_code=403, detail="Validator not authorized")

    if submission.awarded:
        if validator:
            slashing.slash_validator_for_event(req.approved_by_validator_id, "double_award")
        return {"awarded": False, "reason": "already_awarded", "submission_id": submission.id}

    _ensure_runtime_stores()
    fraud_score = float(models.InMemoryDB.submission_fraud_scores.get(submission.id, anti_cheat.fraud_risk_score(submission)))
    if submission.final_score <= 0 or fraud_score >= 0.8:
        if validator and fraud_score >= 0.8:
            slashing.slash_validator_for_event(req.approved_by_validator_id, "fraud_approval")
        return {"awarded": False, "reason": "not_eligible", "submission_id": submission.id}

    amount = rewards.distribute_reward_for_submission(submission.id)
    if not amount:
        return {"awarded": False, "reason": "not_eligible", "submission_id": submission.id}

    submission.awarded = True
    models.InMemoryDB.submissions[submission.id] = submission

    if validator:
        core_validators.record_review_result(req.approved_by_validator_id, True)

    audit.add_audit_event(
        event_type="award",
        actor_id=req.approved_by_validator_id,
        target_id=submission.id,
        metadata={"amount": amount},
    )

    return {"awarded": True, "submission_id": submission.id, "amount": amount}


@router.post("/reject")
def reject(req: RejectRequest):
    submission = models.InMemoryDB.submissions.get(req.submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    validator = core_validators.get_validator(req.validator_id)
    if not _is_authorized_actor(req.validator_id):
        if validator:
            slashing.slash_validator_for_event(req.validator_id, "invalid_action")
        raise HTTPException(status_code=403, detail="Validator not authorized")

    submission.verdict = "rejected"
    submission.rejection_reason = req.reason
    models.InMemoryDB.submissions[submission.id] = submission

    if not hasattr(models.InMemoryDB, "rejections"):
        models.InMemoryDB.rejections = []
    models.InMemoryDB.rejections.append(
        {
            "submission_id": submission.id,
            "validator_id": req.validator_id,
            "reason": req.reason,
            "created_at": datetime.utcnow().isoformat(),
        }
    )

    if validator:
        core_validators.record_review_result(req.validator_id, False)

    audit.add_audit_event(
        event_type="reject",
        actor_id=req.validator_id,
        target_id=submission.id,
        reason=req.reason,
    )

    return {"rejected": True, "submission_id": submission.id}


@router.post("/appeal")
def create_appeal(req: AppealRequest):
    submission = models.InMemoryDB.submissions.get(req.submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.user_id != req.user_id:
        raise HTTPException(status_code=403, detail="Only the submitter can appeal")

    if not hasattr(models.InMemoryDB, "appeals"):
        models.InMemoryDB.appeals = []

    appeal_id = str(uuid.uuid4())
    appeal = {
        "appeal_id": appeal_id,
        "submission_id": req.submission_id,
        "user_id": req.user_id,
        "appeal_reason": req.appeal_reason,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    models.InMemoryDB.appeals.append(appeal)

    submission.appealed = True
    models.InMemoryDB.submissions[submission.id] = submission

    audit.add_audit_event(
        event_type="appeal",
        actor_id=req.user_id,
        target_id=req.submission_id,
        reason=req.appeal_reason,
        metadata={"appeal_id": appeal_id},
    )

    return {"appeal_created": True, "appeal_id": appeal_id}


@router.get("/appeals")
def list_appeals():
    if not hasattr(models.InMemoryDB, "appeals"):
        models.InMemoryDB.appeals = []
    return models.InMemoryDB.appeals
