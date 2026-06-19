from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from ..core import models, audit
from ..core import validators as core_validators
from ..governance import proposals as gov_proposals, voting as gov_voting

router = APIRouter(prefix="/explorer", tags=["explorer"])

@router.get("/summary")
def summary():
    blocks = getattr(models.InMemoryDB, 'blocks', [])
    total_blocks = len(blocks)
    # transactions
    txs = []
    for b in blocks:
        txs.extend(b.get('transactions', []))
    total_transactions = len(txs)
    # validators
    validators = core_validators.list_validators()
    total_validators = len(validators)
    # proposals
    proposals = gov_proposals.list_proposals()
    total_proposals = len(proposals)
    # audits
    audits = audit.list_audit_events()
    total_audit_events = len(audits)
    # PoI evaluations (submissions)
    submissions = getattr(models.InMemoryDB, 'submissions', {})
    total_poi_evaluations = len(submissions)
    return {
        "total_blocks": total_blocks,
        "total_transactions": total_transactions,
        "total_validators": total_validators,
        "total_proposals": total_proposals,
        "total_audit_events": total_audit_events,
        "total_poi_evaluations": total_poi_evaluations,
    }

@router.get("/blocks")
def list_blocks():
    blocks = getattr(models.InMemoryDB, 'blocks', [])
    return blocks

@router.get("/blocks/{block_index}")
def get_block(block_index: int):
    blocks = getattr(models.InMemoryDB, 'blocks', [])
    if block_index < 0 or block_index >= len(blocks):
        raise HTTPException(status_code=404, detail="Block not found")
    return blocks[block_index]

@router.get("/transactions")
def list_transactions():
    blocks = getattr(models.InMemoryDB, 'blocks', [])
    txs = []
    for b in blocks:
        for tx in b.get('transactions', []):
            tx_copy = dict(tx)
            tx_copy['block_index'] = b.get('index')
            txs.append(tx_copy)
    return txs

@router.get("/transactions/{txid}")
def get_transaction(txid: str):
    blocks = getattr(models.InMemoryDB, 'blocks', [])
    for b in blocks:
        for tx in b.get('transactions', []):
            if tx.get('txid') == txid:
                tx_copy = dict(tx)
                tx_copy['block_index'] = b.get('index')
                return tx_copy
    raise HTTPException(status_code=404, detail="Transaction not found")

@router.get("/validators")
def get_validators():
    vals = core_validators.list_validators()
    # include ranking info
    ranked = sorted(vals, key=lambda v: (v.validator_score, v.reputation_score, v.successful_reviews), reverse=True)
    return [v.dict() for v in ranked]

@router.get("/governance")
def get_governance():
    props = gov_proposals.list_proposals()
    out = []
    for p in props:
        tally = gov_voting.tally_votes_raw(p.proposal_id)
        out.append({
            "proposal": p.dict(),
            "yes_power": tally['yes_power'],
            "no_power": tally['no_power'],
            "cast_power": tally['cast_power'],
        })
    return out

@router.get("/audit")
def get_audit():
    events = audit.list_audit_events()
    # return recent (sorted by timestamp desc)
    sorted_ev = sorted(events, key=lambda e: e.timestamp, reverse=True)
    return [e.dict() for e in sorted_ev]
