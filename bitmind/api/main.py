from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uuid
from bitmind.api import poi
from bitmind.api import validators as validators_api
from bitmind.api import audit as audit_api
from bitmind.core import tasks, models, anti_cheat, reputation, rewards, ledger

app = FastAPI(title="BitMind MVP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(poi.router)
app.include_router(validators_api.router)
app.include_router(audit_api.router)

# Request/response models
class CreateUserRequest(BaseModel):
    username: str

class CreateTaskRequest(BaseModel):
    prompt: str
    answer_key: str | None = None
    difficulty: int = 1
    is_test: bool = False

class AssignTaskRequest(BaseModel):
    assignees: List[str]

class SubmitRequest(BaseModel):
    content: str

class StakeRequest(BaseModel):
    amount: float

# Simple admin endpoints
@app.post("/users")
def create_user(req: CreateUserRequest):
    user = models.create_user(req.username)
    return user.dict()

@app.get("/users/{user_id}")
def get_user(user_id: str):
    user = models.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.dict()

@app.post("/tasks")
def create_task(req: CreateTaskRequest):
    task = tasks.create_task(req.prompt, req.answer_key, req.difficulty, req.is_test)
    return task.dict()

@app.post("/tasks/{task_id}/assign")
def assign_task(task_id: str, req: AssignTaskRequest):
    task = models.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    assignments = tasks.assign_task_to_users(task_id, req.assignees)
    return {"assignments": [a.dict() for a in assignments]}

@app.post("/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: str, req: SubmitRequest):
    assignment = models.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.status != "assigned":
        raise HTTPException(status_code=400, detail="Assignment not in assigned state")
    submission = tasks.submit_assignment(assignment_id, req.content)

    # Auto-score via AI placeholder
    auto_score = anti_cheat.ai_score_submission(submission.content, models.get_task(submission.assignment.task_id))
    submission.auto_score = auto_score

    # Hidden test check
    task = models.get_task(submission.assignment.task_id)
    ht_result = anti_cheat.check_hidden_test(submission.content, task)

    # Fraud risk
    fraud_score = anti_cheat.fraud_risk_score(submission)

    # Finalize provisional score (placeholder: combine auto_score and hidden test)
    final_score = submission.auto_score
    if ht_result is False:
        final_score = 0.0
        submission.verdict = "hidden_test_failed"
    else:
        submission.verdict = "ok"

    submission.final_score = final_score

    # Save submission
    models.save_submission(submission)

    # If all assignments for task submitted, run consensus placeholder
    tasks.try_resolve_task_consensus(submission.assignment.task_id)

    # Update reputation
    reputation.update_reputation(submission.user_id, submission.final_score)

    # Distribute rewards (simulated)
    rewards.distribute_reward_for_submission(submission.id)

    return {
        "submission": submission.dict(),
        "hidden_test_passed": ht_result,
        "fraud_score": fraud_score,
    }

@app.post("/users/{user_id}/stake")
def stake(user_id: str, req: StakeRequest):
    user = models.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        rewards.stake(user_id, req.amount)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"user": models.get_user(user_id).dict()}

@app.get("/ledger/{user_id}")
def get_ledger(user_id: str):
    entries = ledger.get_ledger_for_user(user_id)
    return {"entries": [e.dict() for e in entries], "balance": ledger.get_balance(user_id)}
