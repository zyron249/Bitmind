from . import scoring
from ..core import models, anti_cheat, reputation, rewards
from .consensus import compute_consensus_for_task
from .validators import validators_approval


def evaluate_submission(submission_id: str):
    submission = models.InMemoryDB.submissions.get(submission_id)
    if not submission:
        return None
    task = models.get_task(submission.assignment.task_id)
    # AI score
    auto_score = scoring.ai_score(submission.content, task)
    submission.auto_score = auto_score
    # Hidden test check
    ht = anti_cheat.check_hidden_test(submission.content, task)
    if ht is False:
        submission.final_score = 0.0
        submission.verdict = "hidden_test_failed"
    else:
        # Reputation weighting
        user = models.get_user(submission.user_id)
        rep = user.reputation if user else 0.5
        # weight: final = auto_score * (0.5 + 0.5*rep)
        submission.final_score = auto_score * (0.5 + 0.5 * rep)
        submission.verdict = "ok"
    # Fraud risk
    fraud = anti_cheat.fraud_risk_score(submission)
    # persist
    models.InMemoryDB.submissions[submission.id] = submission
    return {"submission_id": submission.id, "auto_score": auto_score, "hidden_test": ht, "final_score": submission.final_score, "fraud": fraud}


def process_task(task_id: str, validator_threshold: float = 0.6):
    # Evaluate all submissions for task
    submissions = [s for s in models.InMemoryDB.submissions.values() if s.assignment.task_id == task_id]
    results = []
    for s in submissions:
        res = evaluate_submission(s.id)
        results.append(res)
    # Multi-review consensus
    consensus = compute_consensus_for_task(task_id)
    consensus_score = consensus["consensus_score"]
    consensus_pass = consensus["consensus_pass"]
    # Validators approval
    approval = validators_approval(task_id, consensus_score, threshold=validator_threshold)
    # Fraud analysis and reward eligibility
    outcome = []
    for s in submissions:
        fraud = anti_cheat.fraud_risk_score(s)
        eligible = False
        # Reward eligibility rules
        if consensus_pass and approval and s.final_score > 0 and fraud < 0.8:
            eligible = True
            rewards.distribute_reward_for_submission(s.id)
            reputation.update_reputation(s.user_id, s.final_score)
        else:
            # update reputation negatively on hidden test fail
            if s.verdict == "hidden_test_failed":
                reputation.update_reputation(s.user_id, 0.0)
        # Slashing for high fraud
        if fraud >= 0.7:
            user = models.get_user(s.user_id)
            if user and user.staked > 0:
                # slash 50% of staked
                rewards.slash(s.user_id, user.staked * 0.5, reason="fraud_slash")
        outcome.append({"submission_id": s.id, "eligible": eligible, "fraud": fraud, "final_score": s.final_score})
    return {"consensus": consensus, "approval": approval, "outcomes": outcome}
