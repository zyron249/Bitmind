from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..governance import proposals as gov_proposals, voting as gov_voting
from ..core import validators as core_validators, audit

router = APIRouter(prefix="/governance", tags=["governance"])

class CreateProposalRequest(BaseModel):
    title: str
    description: Optional[str] = None
    created_by: str
    voting_starts_at: Optional[str] = None  # ISO datetime
    voting_period_seconds: Optional[int] = 86400
    quorum_required: Optional[float] = 0.20

class ProposalResponse(BaseModel):
    proposal_id: str
    title: str
    description: Optional[str]
    created_by: str
    created_at: str
    status: str
    voting_starts_at: Optional[str]
    voting_ends_at: Optional[str]
    quorum_required: float

class VoteRequest(BaseModel):
    voter_validator_id: str
    proposal_id: str
    vote: str  # 'yes' or 'no'

@router.post("/proposals", status_code=201)
def create_proposal(req: CreateProposalRequest):
    # parse voting_starts_at if provided
    from datetime import datetime
    start = None
    if req.voting_starts_at:
        start = datetime.fromisoformat(req.voting_starts_at)
    p = gov_proposals.create_proposal(req.title, req.description or "", req.created_by, voting_starts_at=start, voting_period_seconds=req.voting_period_seconds or 86400, quorum_required=req.quorum_required or 0.20)
    return p.dict()

@router.get("/proposals")
def list_proposals():
    ps = gov_proposals.list_proposals()
    return [p.dict() for p in ps]

@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str):
    p = gov_proposals.get_proposal(proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return p.dict()

@router.post("/vote")
def cast_vote(req: VoteRequest):
    # check validator exists and active
    if not core_validators.is_authorized_validator(req.voter_validator_id):
        raise HTTPException(status_code=403, detail="Validator not authorized to vote")
    if req.vote not in ('yes', 'no'):
        raise HTTPException(status_code=400, detail="Invalid vote option")
    ok = gov_voting.cast_vote(req.voter_validator_id, req.proposal_id, req.vote)
    if not ok:
        raise HTTPException(status_code=400, detail="Vote failed (proposal inactive, outside voting period, or voter invalid)")
    return {"voted": True}

@router.post("/proposals/{proposal_id}/finalize")
def finalize_proposal(proposal_id: str):
    res = gov_proposals.finalize_proposal(proposal_id)
    if res.get('error'):
        raise HTTPException(status_code=400, detail=res['error'])
    return res
