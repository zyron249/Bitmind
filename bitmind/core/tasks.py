from typing import List
from . import models

# Task management

def create_task(prompt: str, answer_key: str | None, difficulty: int = 1, is_test: bool = False) -> models.Task:
    return models.create_task(prompt, answer_key, difficulty, is_test)


def assign_task_to_users(task_id: str, assignee_ids: List[str]):
    created = []
    for uid in assignee_ids:
        assignment = models.Assignment(task_id=task_id, assignee_id=uid)
        models.save_assignment(assignment)
        created.append(assignment)
    return created


def submit_assignment(assignment_id: str, content: str):
    assignment = models.get_assignment(assignment_id)
    submission = models.Submission(assignment=assignment, user_id=assignment.assignee_id, content=content)
    models.save_submission(submission)
    return submission


def try_resolve_task_consensus(task_id: str):
    # Placeholder: when all assignments submitted, compute average final_score
    # For MVP, find assignments for task and if all assignments are submitted, average their final_score.
    assignments = [a for a in models.InMemoryDB.assignments.values() if a.task_id == task_id]
    if not assignments:
        return None
    if any(a.status != "submitted" for a in assignments):
        return None
    submissions = [models.InMemoryDB.submissions[k] for k in models.InMemoryDB.submissions if models.InMemoryDB.submissions[k].assignment.task_id == task_id]
    if not submissions:
        return None
    avg = sum(s.final_score for s in submissions) / len(submissions)
    # For demo, set each submission human_score/final_score to avg
    for s in submissions:
        s.human_score = avg
        s.final_score = avg
        models.InMemoryDB.submissions[s.id] = s
    return avg
