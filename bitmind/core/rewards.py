from . import models, ledger

BASE_REWARD = 10.0  # base BMD per approved task


def compute_reward_for_submission(submission: models.Submission) -> float:
    user = models.get_user(submission.user_id)
    if not user:
        return 0.0
    # Simple formula: base * final_score * (1 + reputation)
    multiplier = 1.0 + user.reputation
    amount = BASE_REWARD * submission.final_score * multiplier
    return float(max(0.0, amount))


def distribute_reward_for_submission(submission_id: str):
    submission = models.InMemoryDB.submissions.get(submission_id)
    if not submission:
        return None
    if submission.final_score <= 0:
        return None
    amount = compute_reward_for_submission(submission)
    if amount <= 0:
        return None
    # credit user
    ledger.credit(submission.user_id, amount, reason=f"reward:submission:{submission.id}")
    return amount


def stake(user_id: str, amount: float):
    user = models.get_user(user_id)
    if not user:
        raise Exception("User not found")
    if amount <= 0:
        raise Exception("Stake amount must be positive")
    if user.balance < amount:
        raise Exception("Insufficient balance to stake")
    # Do not double-deduct balance here; ledger.add_entry will adjust balance.
    user.staked += amount
    models.InMemoryDB.users[user.id] = user
    # record stake as a negative ledger entry (reduces available balance)
    ledger.add_entry(user.id, -amount, reason="stake")
    return True


def slash(user_id: str, amount: float, reason: str = "slashing"):
    user = models.get_user(user_id)
    if not user:
        raise Exception("User not found")
    slashed = min(user.staked, amount)
    user.staked -= slashed
    models.InMemoryDB.users[user.id] = user
    # Record slashing event in ledger for audit purposes without modifying balance (stake already deducted)
    ledger.add_entry(user.id, 0.0, reason=reason)
    return slashed
