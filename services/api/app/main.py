from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from hashlib import sha256
from time import time
from uuid import uuid4

app = FastAPI(
    title="NeuraBit Prototype API",
    version="0.1.0"
)

TASKS = {}
SUBMISSIONS = {}
REPUTATION = {}
LEDGER = []


class TaskCreate(BaseModel):
    title: str
    prompt: str
    difficulty: int = Field(ge=1, le=10)
    gold_answer_hash: str | None = None


class SubmissionCreate(BaseModel):
    user_id: str
    answer: str
    stake: float = Field(default=0, ge=0)


class BlockReward(BaseModel):
    submission_id: str
    reward: float
    quality_score: float
    fraud_risk: float
    status: str


def hash_text(value: str) -> str:
    return sha256(
        value.strip().lower().encode()
    ).hexdigest()


def get_reputation(user_id: str) -> float:
    return REPUTATION.get(user_id, 0.5)


def quality_score(task: dict, answer: str) -> float:

    if len(answer.strip()) < 20:
        return 0.05

    if (
        task.get("gold_answer_hash")
        and hash_text(answer)
        == task["gold_answer_hash"]
    ):
        return 1.0

    return min(
        0.9,
        0.25 + len(answer.strip()) / 500
    )


def fraud_risk(
    user_id: str,
    answer: str,
    stake: float
) -> float:

    risk = 0.25

    if len(answer.strip()) < 20:
        risk += 0.5

    if stake <= 0:
        risk += 0.15

    if get_reputation(user_id) < 0.3:
        risk += 0.2

    return min(1.0, risk)


def calculate_reward(
    task: dict,
    q: float,
    risk: float,
    reputation: float
) -> float:

    if q < 0.6 or risk > 0.7:
        return 0.0

    base = task["difficulty"] * 2.5

    return round(
        base
        * q
        * (0.5 + reputation)
        * (1 - risk),
        6
    )


@app.get("/")
def root():
    return {
        "project": "NeuraBit",
        "status": "prototype"
    }


@app.post("/tasks")
def create_task(payload: TaskCreate):

    task_id = str(uuid4())

    TASKS[task_id] = (
        payload.model_dump()
        | {
            "task_id": task_id,
            "created_at": time()
        }
    )

    return TASKS[task_id]


@app.get("/tasks")
def list_tasks():
    return list(TASKS.values())


@app.post(
    "/tasks/{task_id}/submit",
    response_model=BlockReward
)
def submit(
    task_id: str,
    payload: SubmissionCreate
):

    task = TASKS.get(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    q = quality_score(
        task,
        payload.answer
    )

    risk = fraud_risk(
        payload.user_id,
        payload.answer,
        payload.stake
    )

    rep = get_reputation(
        payload.user_id
    )

    reward = calculate_reward(
        task,
        q,
        risk,
        rep
    )

    status = (
        "accepted"
        if reward > 0
        else "rejected_or_needs_review"
    )

    submission_id = str(uuid4())

    proof_hash = hash_text(
        f"{task_id}:{payload.user_id}:{payload.answer}:{time()}"
    )

    SUBMISSIONS[submission_id] = {
        "submission_id": submission_id,
        "task_id": task_id,
        "user_id": payload.user_id,
        "answer_hash": hash_text(
            payload.answer
        ),
        "quality_score": q,
        "fraud_risk": risk,
        "reward": reward,
        "status": status,
        "proof_hash": proof_hash
    }

    if reward > 0:

        REPUTATION[payload.user_id] = min(
            1.0,
            rep + 0.02
        )

        LEDGER.append({
            "type": "reward",
            "user_id": payload.user_id,
            "amount": reward,
            "proof_hash": proof_hash
        })

    else:

        REPUTATION[payload.user_id] = max(
            0.0,
            rep - 0.03
        )

    return BlockReward(
        submission_id=submission_id,
        reward=reward,
        quality_score=q,
        fraud_risk=risk,
        status=status
    )


@app.get("/ledger")
def ledger():
    return LEDGER


@app.get("/reputation/{user_id}")
def reputation(user_id: str):
    return {
        "user_id": user_id,
        "reputation": get_reputation(
            user_id
        )
    }
