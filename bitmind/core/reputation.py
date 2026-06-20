from . import models

ALPHA = 0.2
MIN_REPUTATION = 0.0
MAX_REPUTATION = 1.0


def update_reputation(user_id: str, final_score: float):
    current_user = models.get_user(user_id)
    if not current_user:
        return None

    clamped_score = max(0.0, min(1.0, float(final_score)))
    new_rep = ALPHA * clamped_score + (1 - ALPHA) * current_user.reputation
    new_rep = max(MIN_REPUTATION, min(MAX_REPUTATION, new_rep))

    user = current_user.model_copy(deep=True)
    # round to avoid floating point strict-equality issues in tests
    user.reputation = round(new_rep, 6)
    models.InMemoryDB.users[user.id] = user
    return user.reputation
