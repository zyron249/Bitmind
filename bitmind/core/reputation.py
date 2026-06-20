from . import models

# Simple reputation update functions

ALPHA = 0.3  # how strongly a single task updates reputation
MIN_REPUTATION = 0.0
MAX_REPUTATION = 1.0


def update_reputation(user_id: str, final_score: float):
    user = models.get_user(user_id)
    if not user:
        return None
    user = user.model_copy(deep=True)  # deep copy to avoid mutating the original object before changes are committed
    new_rep = ALPHA * final_score + (1 - ALPHA) * user.reputation
    # clamp
    new_rep = max(MIN_REPUTATION, min(MAX_REPUTATION, new_rep))
    user.reputation = new_rep
    models.InMemoryDB.users[user.id] = user
    return user.reputation
