from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid
from typing import Optional, List
from . import models

MIN_VALIDATOR_STAKE = 1000.0
UNSTAKE_COOLDOWN_SECONDS = 7 * 24 * 3600  # 7 days

class Validator(BaseModel):
    validator_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    role: str = "validator"  # validator or admin
    active: bool = False
    reputation_score: float = 0.0
    staked_amount: float = 0.0
    validator_score: float = 0.0
    successful_reviews: int = 0
    failed_reviews: int = 0
    slashes_count: int = 0
    unstake_cooldown_end: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


def _ensure_registry():
    if not hasattr(models.InMemoryDB, 'validators'):
        models.InMemoryDB.validators = {}


def create_validator(user_id: str, role: str = "validator", reputation_score: float = 0.0, staked_amount: float = 0.0) -> Validator:
    _ensure_registry()
    v = Validator(user_id=user_id, role=role, reputation_score=reputation_score, staked_amount=staked_amount)
    # active only if stake >= MIN_VALIDATOR_STAKE
    if v.staked_amount >= MIN_VALIDATOR_STAKE:
        v.active = True
    models.InMemoryDB.validators[v.validator_id] = v
    return v


def get_validator(validator_id: str) -> Optional[Validator]:
    _ensure_registry()
    return models.InMemoryDB.validators.get(validator_id)


def list_validators() -> List[Validator]:
    _ensure_registry()
    return list(models.InMemoryDB.validators.values())


def deactivate_validator(validator_id: str) -> bool:
    v = get_validator(validator_id)
    if not v:
        return False
    v.active = False
    models.InMemoryDB.validators[validator_id] = v
    return True


def is_authorized_validator(validator_id: str) -> bool:
    v = get_validator(validator_id)
    if not v:
        return False
    # authorized if active and role is validator or admin
    return v.active and v.role in ("validator", "admin")


def stake_validator(validator_id: str, amount: float) -> bool:
    """Stake BMD for a validator. Deducts from the user's balance via rewards.stake and updates validator stake."""
    v = get_validator(validator_id)
    if not v:
        return False
    # find user
    user = models.get_user(v.user_id)
    if not user:
        return False
    # Use rewards.stake to deduct user balance and user.staked
    from . import rewards as core_rewards
    try:
        core_rewards.stake(user.id, amount)
    except Exception:
        return False
    v.staked_amount += amount
    # activate if meets minimum
    if v.staked_amount >= MIN_VALIDATOR_STAKE:
        v.active = True
    models.InMemoryDB.validators[validator_id] = v
    return True


def initiate_unstake(validator_id: str) -> bool:
    v = get_validator(validator_id)
    if not v:
        return False
    # set cooldown end and deactivate
    v.unstake_cooldown_end = datetime.utcnow() + timedelta(seconds=UNSTAKE_COOLDOWN_SECONDS)
    v.active = False
    models.InMemoryDB.validators[validator_id] = v
    return True


def withdraw_stake(validator_id: str) -> Optional[float]:
    v = get_validator(validator_id)
    if not v:
        return None
    if not v.unstake_cooldown_end or datetime.utcnow() < v.unstake_cooldown_end:
        return None
    amount = v.staked_amount
    if amount <= 0:
        return 0.0
    # return funds to user
    from . import ledger
    ledger.add_entry(v.user_id, amount, reason=f"unstake:validator:{v.validator_id}")
    # subtract from user.staked if present
    user = models.get_user(v.user_id)
    if user:
        user.staked = max(0.0, user.staked - amount)
        models.InMemoryDB.users[user.id] = user
    v.staked_amount = 0.0
    v.unstake_cooldown_end = None
    models.InMemoryDB.validators[validator_id] = v
    return amount


def record_review_result(validator_id: str, success: bool):
    v = get_validator(validator_id)
    if not v:
        return False
    if success:
        v.successful_reviews += 1
    else:
        v.failed_reviews += 1
    # update validator_score: simple formula
    total = v.successful_reviews + v.failed_reviews
    if total > 0:
        v.validator_score = v.successful_reviews / total
    models.InMemoryDB.validators[validator_id] = v
    return True


def record_slash(validator_id: str):
    v = get_validator(validator_id)
    if not v:
        return False
    v.slashes_count += 1
    models.InMemoryDB.validators[validator_id] = v
    return True
