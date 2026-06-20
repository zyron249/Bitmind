from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# In-memory DB singleton
class InMemoryDB:
    users: dict = {}
    tasks: dict = {}
    assignments: dict = {}
    submissions: dict = {}
    ledger_entries: list = []
    appeals: list = []
    rejections: list = []

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    reputation: float = 0.5
    balance: float = 10000.0  # start with enough simulated BMD for testing
    staked: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    answer_key: Optional[str] = None
    difficulty: int = 1
    is_test_flag: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Assignment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    assignee_id: str
    status: str = "assigned"
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None

class Submission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assignment: Assignment
    user_id: str
    content: str
    auto_score: float = 0.0
    human_score: Optional[float] = None
    final_score: float = 0.0
    verdict: Optional[str] = None
    awarded: bool = False
    rejection_reason: Optional[str] = None
    appealed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LedgerEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Convenience functions
def create_user(username: str) -> User:
    user = User(username=username)
    InMemoryDB.users[user.id] = user
    return user

def get_user(user_id: str) -> Optional[User]:
    return InMemoryDB.users.get(user_id)

def create_task(prompt: str, answer_key: Optional[str], difficulty: int, is_test: bool) -> Task:
    task = Task(prompt=prompt, answer_key=answer_key, difficulty=difficulty, is_test_flag=is_test)
    InMemoryDB.tasks[task.id] = task
    return task

def get_task(task_id: str) -> Optional[Task]:
    return InMemoryDB.tasks.get(task_id)

def save_assignment(assignment: Assignment) -> Assignment:
    InMemoryDB.assignments[assignment.id] = assignment
    return assignment

def get_assignment(assignment_id: str) -> Optional[Assignment]:
    return InMemoryDB.assignments.get(assignment_id)

def save_submission(submission: Submission) -> Submission:
    InMemoryDB.submissions[submission.id] = submission
    # update assignment
    assignment = submission.assignment
    assignment.status = "submitted"
    assignment.submitted_at = submission.created_at
    InMemoryDB.assignments[assignment.id] = assignment
    return submission

def get_submissions_for_task(task_id: str) -> List[Submission]:
    return [s for s in InMemoryDB.submissions.values() if s.assignment.task_id == task_id]

def add_ledger_entry(entry: LedgerEntry) -> LedgerEntry:
    InMemoryDB.ledger_entries.append(entry)
    return entry

def get_ledger_for_user(user_id: str) -> List[LedgerEntry]:
    return [e for e in InMemoryDB.ledger_entries if e.user_id == user_id]
