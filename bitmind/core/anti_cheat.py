import difflib
import os
from . import models

# Placeholder for AI scoring. Designed to be swapped for real OpenAI or other models.
# It reads OPENAI_API_KEY from environment variables but will not call any external API in the MVP.

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def ai_score_submission(content: str, task: models.Task) -> float:
    """
    Very small heuristic: if the task has an answer_key, compute similarity. Otherwise, return a neutral score.
    Returns value in [0.0, 1.0].
    """
    if task and task.answer_key:
        ratio = difflib.SequenceMatcher(None, content.strip().lower(), task.answer_key.strip().lower()).ratio()
        return float(round(ratio, 4))
    # No answer key available: return a soft default (0.5)
    return 0.5


def check_hidden_test(content: str, task: models.Task) -> bool | None:
    """
    If task.is_test_flag is True and we have an answer_key, perform an exact or similarity check.
    Returns True if passed, False if failed, None if not applicable.
    """
    if not task or not task.is_test_flag:
        return None
    if not task.answer_key:
        return None
    score = ai_score_submission(content, task)
    # pass threshold 0.8 for test
    return score >= 0.8


def fraud_risk_score(submission: models.Submission) -> float:
    """
    Heuristic fraud risk in [0.0, 1.0]. Higher means more suspicious.
    - Hidden test failure strongly increases risk
    - Very low reputation increases risk
    - Very short or identical content could increase risk
    """
    risk = 0.0
    task = submission.assignment and models.get_task(submission.assignment.task_id)
    if task and task.is_test_flag:
        ht = check_hidden_test(submission.content, task)
        if ht is False:
            risk += 0.6
    user = models.get_user(submission.user_id)
    if user:
        if user.reputation < 0.2:
            risk += 0.2
        if user.staked <= 0:
            risk += 0.1
    # short content penalty
    if len(submission.content.strip()) < 20:
        risk += 0.1
    # clamp
    return float(min(1.0, risk))
