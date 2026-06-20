from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..core import validators as core_validators, models, audit

router = APIRouter(prefix="/validators", tags=["validators"])

class CreateValidatorRequest(BaseModel):
    user_id: str
    role: Optional[str] = "validator"
    reputation_score: Optional[float] = 0.0
    staked_amount: Optional[float] = 0.0

class StakeRequest(BaseModel):
    validator_id: str
    amount: float

class UnstakeRequest(BaseModel):
    validator_id: str

class WithdrawRequest(BaseModel):
    validator_id: str

@router.post("", status_code=201)
def create_validator(req: CreateValidatorRequest):
    user = models.get_user(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    v = core_validators.create_validator(user_id=req.user_id, role=req.role, reputation_score=req.reputation_score, staked_amount=req.staked_amount)
    # audit
    audit.add_audit_event(event_type='validator_created', actor_id=req.user_id, target_id=v.validator_id)
    return v.dict()

@router.get("")
def list_validators():
    vals = core_validators.list_validators()
    return [v.dict() for v in vals]

@router.get("/ranking")
def ranking():
    vals = core_validators.list_validators()
    # sort by validator_score desc, reputation desc, successful_reviews desc
    sorted_vals = sorted(vals, key=lambda v: (v.validator_score, v.reputation_score, v.successful_reviews), reverse=True)
    return [v.dict() for v in sorted_vals]

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
    audit.add_audit_event(event_type='validator_deactivated', actor_id=validator_id, target_id=validator_id)
    return {"deactivated": True, "validator_id": validator_id}

@router.post("/stake")
def stake(req: StakeRequest):
    v = core_validators.get_validator(req.validator_id)
    if not v:
        raise HTTPException(status_code=404, detail="Validator not found")
    ok = core_validators.stake_validator(req.validator_id, req.amount)
    if not ok:
        raise HTTPException(status_code=400, detail="Stake failed (insufficient balance or error)")
    audit.add_audit_event(event_type='stake', actor_id=v.user_id, target_id=v.validator_id, reason=f"amount={req.amount}")
    return {"staked": True, "validator_id": req.validator_id, "amount": req.amount}

@router.post("/unstake")
def unstake(req: UnstakeRequest):
    v = core_validators.get_validator(req.validator_id)
    if not v:
        raise HTTPException(status_code=404, detail="Validator not found")
    ok = core_validators.initiate_unstake(req.validator_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Unstake initiation failed")
    audit.add_audit_event(event_type='unstake_initiated', actor_id=v.user_id, target_id=v.validator_id)
    return {"unstake_initiated": True, "validator_id": req.validator_id, "unstake_cooldown_end": core_validators.get_validator(req.validator_id).unstake_cooldown_end}

@router.post("/withdraw")
def withdraw(req: WithdrawRequest):
    v = core_validators.get_validator(req.validator_id)
    if not v:
        raise HTTPException(status_code=404, detail="Validator not found")
    amount = core_validators.withdraw_stake(req.validator_id)
    if amount is None:
        raise HTTPException(status_code=400, detail="Cannot withdraw yet or no stake")
    audit.add_audit_event(event_type='withdraw', actor_id=v.user_id, target_id=v.validator_id, reason=f"amount={amount}")
    return {"withdrawn": True, "validator_id": req.validator_id, "amount": amount}
