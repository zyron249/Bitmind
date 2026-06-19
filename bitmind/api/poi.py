from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..core import models, anti_cheat, rewards
from ..consensus import proof_of_intelligence, consensus, validators, scoring

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

    # consensus and validators
    cons = consensus.compute_consensus_for_task(req.task_id)
    approval = validators.validators_approval(req.task_id, cons["consensus_score"]) if req.validator_approvals is None else (req.validator_approvals > 0)

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
    task = models.get_task(submission.assignment.task_id)
    fraud = anti_cheat.fraud_risk_score(submission)
    cons = consensus.compute_consensus_for_task(submission.assignment.task_id)
    approval = validators.validators_approval(submission.assignment.task_id, cons["consensus_score"])
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
        cons = consensus.compute_consensus_for_task(s.assignment.task_id)
        approval = validators.validators_approval(s.assignment.task_id, cons["consensus_score"])
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
