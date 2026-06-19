from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from typing import Optional, List
from . import models

class Validator(BaseModel):
    validator_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    role: str = "validator"  # validator or admin
    active: bool = True
    reputation_score: float = 0.0
    staked_amount: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


def create_validator(user_id: str, role: str = "validator", reputation_score: float = 0.0, staked_amount: float = 0.0) -> Validator:
    v = Validator(user_id=user_id, role=role, reputation_score=reputation_score, staked_amount=staked_amount)
    if not hasattr(models.InMemoryDB, 'validators'):
        models.InMemoryDB.validators = {}
    models.InMemoryDB.validators[v.validator_id] = v
    return v


def get_validator(validator_id: str) -> Optional[Validator]:
    if not hasattr(models.InMemoryDB, 'validators'):
        models.InMemoryDB.validators = {}
    return models.InMemoryDB.validators.get(validator_id)


def list_validators() -> List[Validator]:
    if not hasattr(models.InMemoryDB, 'validators'):
        models.InMemoryDB.validators = {}
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
