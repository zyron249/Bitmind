from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..core import models, anti_cheat, rewards, ledger, validators as core_validators
from ..consensus import proof_of_intelligence, consensus as consensus_module, validators as consensus_validators, scoring, slashing as slashing_rules
import uuid
from datetime import datetime

router = APIRouter(prefix="/poi", tags=["proof_of_intelligence"])

class EvaluateRequest(BaseModel):
    user_id: str
    task_id: str
    submission_content: str
    ai_score: Optional[float] = None
    hidden_test_passed: Optional[bool] = None
    reviewer_scores: Optional[List[float]] = None
    reputation_score: Optional[float] = None
    fraud_risk: Optional[float] = None
    validator_approvals: Optional[int] = None

class EvaluateResponse(BaseModel):
    submission_id: str
    final_score: float
    reward_eligible: bool
    reward_amount: float
    decision_reason: str

class AwardRequest(BaseModel):
    submission_id: str
    approved_by_validator_id: str

class AwardResponse(BaseModel):
    awarded: bool
    amount: float
    ledger_entry_id: Optional[str]
    reason: str

class RejectRequest(BaseModel):
    submission_id: str
    validator_id: str
    reason: str

class AppealRequest(BaseModel):
    submission_id: str
    user_id: str
    appeal_reason: str

@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_contribution(req: EvaluateRequest):
    # validate user and task
    user = models.get_user(req.user_id)
    task = models.get_task(req.task_id)
    if not user or not task:
        raise HTTPException(status_code=404, detail="User or Task not found")
    # create an assignment and submission
    assignment = models.Assignment(task_id=req.task_id, assignee_id=req.user_id)
    models.save_assignment(assignment)
    submission = models.Submission(assignment=assignment, user_id=req.user_id, content=req.submission_content)
    models.save_submission(submission)

    # AI score: use provided ai_score or compute
    if req.ai_score is not None:
        submission.auto_score = req.ai_score
    else:
        submission.auto_score = scoring.ai_score(submission.content, task)

    # Hidden test: respect provided flag if given, otherwise compute
    if req.hidden_test_passed is not None:
        ht = req.hidden_test_passed
    else:
        ht = anti_cheat.check_hidden_test(submission.content, task)

    if ht is False:
        submission.final_score = 0.0
        submission.verdict = "hidden_test_failed"
        decision_reason = "hidden_test_failed"
    else:
        # apply reputation weighting
        rep = req.reputation_score if req.reputation_score is not None else user.reputation
        submission.final_score = submission.auto_score * (0.5 + 0.5 * rep)
        submission.verdict = "ok"
        decision_reason = "scored"

    # fraud risk
    fraud = req.fraud_risk if req.fraud_risk is not None else anti_cheat.fraud_risk_score(submission)
    submission.fraud_risk = fraud

    # consensus and validators
    cons = consensus_module.compute_consensus_for_task(req.task_id)
    approval = consensus_validators.validators_approval(req.task_id, cons["consensus_score"]) if req.validator_approvals is None else (req.validator_approvals > 0)

    # reward eligibility (note: do not distribute here)
    eligible = False
    if cons["consensus_pass"] and approval and submission.final_score > 0 and fraud < 0.8:
        eligible = True
        decision_reason = "approved"
    else:
        if submission.verdict == "hidden_test_failed":
            decision_reason = "hidden_test_failed"
        elif not cons["consensus_pass"]:
            decision_reason = "consensus_failed"
        elif not approval:
            decision_reason = "validators_rejected"
        elif fraud >= 0.8:
            decision_reason = "high_fraud_risk"

    reward_amount = 0.0
    if eligible:
        reward_amount = rewards.compute_reward_for_submission(submission)

    # persist updated submission
    models.InMemoryDB.submissions[submission.id] = submission

    return EvaluateResponse(
        submission_id=submission.id,
        final_score=submission.final_score,
        reward_eligible=eligible,
        reward_amount=reward_amount,
        decision_reason=decision_reason,
    )

@router.get("/status/{submission_id}")
def get_poi_status(submission_id: str):
    submission = models.InMemoryDB.submissions.get(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    # removed unused 'task' variable
    fraud = anti_cheat.fraud_risk_score(submission)
    cons = consensus_module.compute_consensus_for_task(submission.assignment.task_id)
    approval = consensus_validators.validators_approval(submission.assignment.task_id, cons["consensus_score"])
    eligible = cons["consensus_pass"] and approval and submission.final_score > 0 and fraud < 0.8
    return {
        "submission_id": submission.id,
        "final_score": submission.final_score,
        "verdict": submission.verdict,
        "fraud_risk": fraud,
        "consensus": cons,
        "validator_approval": approval,
        "reward_eligible": eligible,
    }

@router.get("/evaluations")
def list_poi_evaluations():
    out = []
    for s in models.InMemoryDB.submissions.values():
        fraud = anti_cheat.fraud_risk_score(s)
        cons = consensus_module.compute_consensus_for_task(s.assignment.task_id)
        approval = consensus_validators.validators_approval(s.assignment.task_id, cons["consensus_score"])
        eligible = cons["consensus_pass"] and approval and s.final_score > 0 and fraud < 0.8
        out.append({
            "submission_id": s.id,
            "user_id": s.user_id,
            "task_id": s.assignment.task_id,
            "final_score": s.final_score,
            "verdict": s.verdict,
            "fraud_risk": fraud,
            "reward_eligible": eligible,
        })
    return out

@router.post("/award", response_model=AwardResponse)
def award_submission(req: AwardRequest):
    sub = models.InMemoryDB.submissions.get(req.submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    # authorization check: approved_by_validator_id must be an active validator
    if not core_validators.is_authorized_validator(req.approved_by_validator_id):
        slashing_rules.slash_validator_for_event(req.approved_by_validator_id, "invalid_action")
        raise HTTPException(status_code=403, detail="Validator not authorized")
    if sub.awarded:
        slashing_rules.slash_validator_for_event(req.approved_by_validator_id, "double_award")
        return AwardResponse(awarded=False, amount=0.0, ledger_entry_id=None, reason="already_awarded")
    # check eligibility
    fraud = sub.fraud_risk if sub.fraud_risk is not None else anti_cheat.fraud_risk_score(sub)
    cons = consensus_module.compute_consensus_for_task(sub.assignment.task_id)
    eligible = cons["consensus_pass"] and sub.verdict == "ok" and sub.final_score > 0 and fraud < 0.8
    if not eligible:
        if fraud >= 0.8:
            slashing_rules.slash_validator_for_event(req.approved_by_validator_id, "fraud_approval")
        else:
            slashing_rules.slash_validator_for_event(req.approved_by_validator_id, "invalid_action")
        return AwardResponse(awarded=False, amount=0.0, ledger_entry_id=None, reason="not_eligible")
    # award
    amount = rewards.compute_reward_for_submission(sub)
    entry = ledger.add_entry(sub.user_id, amount, reason=f"award:submission:{sub.id}:approved_by:{req.approved_by_validator_id}")
    sub.awarded = True
    models.InMemoryDB.submissions[sub.id] = sub
    return AwardResponse(awarded=True, amount=amount, ledger_entry_id=entry.id, reason="awarded")

@router.post("/reject")
def reject_submission(req: RejectRequest):
    sub = models.InMemoryDB.submissions.get(req.submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    # authorization check
    if not core_validators.is_authorized_validator(req.validator_id):
        raise HTTPException(status_code=403, detail="Validator not authorized")
    sub.verdict = "rejected"
    sub.rejection_reason = req.reason
    models.InMemoryDB.submissions[sub.id] = sub
    if not hasattr(models.InMemoryDB, 'rejections'):
        models.InMemoryDB.rejections = []
    models.InMemoryDB.rejections.append({"submission_id": sub.id, "validator_id": req.validator_id, "reason": req.reason})
    return {"rejected": True, "submission_id": sub.id, "reason": req.reason}

@router.post("/appeal")
def appeal_submission(req: AppealRequest):
    sub = models.InMemoryDB.submissions.get(req.submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if sub.user_id != req.user_id:
        raise HTTPException(status_code=403, detail="User not owner of submission")
    appeal = {"appeal_id": str(uuid.uuid4()), "submission_id": sub.id, "user_id": req.user_id, "appeal_reason": req.appeal_reason, "status": "pending", "created_at": datetime.utcnow().isoformat()}
    if not hasattr(models.InMemoryDB, 'appeals'):
        models.InMemoryDB.appeals = []
    models.InMemoryDB.appeals.append(appeal)
    sub.appealed = True
    models.InMemoryDB.submissions[sub.id] = sub
    return {"appeal_created": True, "appeal_id": appeal["appeal_id"]}

@router.get("/appeals")
def list_appeals():
    if not hasattr(models.InMemoryDB, 'appeals'):
        models.InMemoryDB.appeals = []
    return models.InMemoryDB.appeals
