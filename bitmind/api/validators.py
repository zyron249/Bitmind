from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..core import validators as core_validators, models

router = APIRouter(prefix="/validators", tags=["validators"])

class CreateValidatorRequest(BaseModel):
    user_id: str
    role: Optional[str] = "validator"
    reputation_score: Optional[float] = 0.0
    staked_amount: Optional[float] = 0.0

@router.post("", status_code=201)
def create_validator(req: CreateValidatorRequest):
    user = models.get_user(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    v = core_validators.create_validator(user_id=req.user_id, role=req.role, reputation_score=req.reputation_score, staked_amount=req.staked_amount)
    return v.dict()

@router.get("")
def list_validators():
    vals = core_validators.list_validators()
    return [v.dict() for v in vals]

@router.get("/{validator_id}")
def get_validator(validator_id: str):
    v = core_validators.get_validator(validator_id)
    if not v:
        raise HTTPException(status_code=404, detail="Validator not found")
    return v.dict()

@router.post("/{validator_id}/deactivate")
def deactivate(validator_id: str):
    ok = core_validators.deactivate_validator(validator_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Validator not found")
    return {"deactivated": True, "validator_id": validator_id}
