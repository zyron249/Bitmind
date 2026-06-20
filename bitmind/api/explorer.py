from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from ..core import models, audit
from ..core import validators as core_validators
from ..governance import proposals as gov_proposals, voting as gov_voting

router = APIRouter(prefix="/explorer", tags=["explorer"])

def paged_response(items: List[Any], limit: int, offset: int) -> Dict[str, Any]:
    total = len(items)
    sliced = items[offset: offset + limit]
    return {"items": sliced, "limit": limit, "offset": offset, "total": total}

def maybe_paged_response(items: List[Any], limit: Optional[int], offset: Optional[int], force_paged: bool = False):
    if force_paged or limit is not None or offset is not None:
        use_limit = 20 if limit is None else limit
        use_offset = 0 if offset is None else offset
        return paged_response(items, use_limit, use_offset)
    return items

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
def list_blocks(limit: Optional[int] = Query(None, ge=1), offset: Optional[int] = Query(None, ge=0)):
    blocks = getattr(models.InMemoryDB, 'blocks', [])
    return maybe_paged_response(blocks, limit, offset)

@router.get("/blocks/{block_index}")
def get_block(block_index: int):
    blocks = getattr(models.InMemoryDB, 'blocks', [])
    if block_index < 0 or block_index >= len(blocks):
        raise HTTPException(status_code=404, detail="Block not found")
    return blocks[block_index]

@router.get("/transactions")
def list_transactions(limit: Optional[int] = Query(None, ge=1), offset: Optional[int] = Query(None, ge=0), sender: Optional[str] = None, recipient: Optional[str] = None):
    blocks = getattr(models.InMemoryDB, 'blocks', [])
    txs = []
    for b in blocks:
        for tx in b.get('transactions', []):
            tx_copy = dict(tx)
            tx_copy['block_index'] = b.get('index')
            txs.append(tx_copy)
    # filters
    if sender:
        txs = [t for t in txs if t.get('from') == sender]
    if recipient:
        txs = [t for t in txs if t.get('to') == recipient]
    return maybe_paged_response(txs, limit, offset, force_paged=(sender is not None or recipient is not None))

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
def get_validators(limit: Optional[int] = Query(None, ge=1), offset: Optional[int] = Query(None, ge=0), active: Optional[bool] = None, role: Optional[str] = None):
    vals = core_validators.list_validators()
    if active is not None:
        vals = [v for v in vals if v.active == active]
    if role:
        vals = [v for v in vals if v.role == role]
    # ranking
    ranked = sorted(vals, key=lambda v: (v.validator_score, v.reputation_score, v.successful_reviews), reverse=True)
    ranked_dicts = [v.dict() for v in ranked]
    return maybe_paged_response(ranked_dicts, limit, offset, force_paged=(active is not None or role is not None))

@router.get("/governance")
def get_governance(limit: Optional[int] = Query(None, ge=1), offset: Optional[int] = Query(None, ge=0), status: Optional[str] = None):
    props = gov_proposals.list_proposals()
    if status:
        props = [p for p in props if p.status == status]
    out = []
    for p in props:
        tally = gov_voting.tally_votes_raw(p.proposal_id)
        out.append({
            "proposal": p.dict(),
            "yes_power": tally['yes_power'],
            "no_power": tally['no_power'],
            "cast_power": tally['cast_power'],
        })
    return maybe_paged_response(out, limit, offset, force_paged=(status is not None))

@router.get("/audit")
def get_audit(limit: Optional[int] = Query(None, ge=1), offset: Optional[int] = Query(None, ge=0), event_type: Optional[str] = None, actor_id: Optional[str] = None, target_id: Optional[str] = None):
    events = audit.list_audit_events()
    # filters
    if event_type:
        events = [e for e in events if e.event_type == event_type]
    if actor_id:
        events = [e for e in events if e.actor_id == actor_id]
    if target_id:
        events = [e for e in events if e.target_id == target_id]
    # sort by timestamp desc
    sorted_ev = sorted(events, key=lambda e: e.timestamp, reverse=True)
    ev_dicts = [e.dict() for e in sorted_ev]
    return maybe_paged_response(ev_dicts, limit, offset, force_paged=(event_type is not None or actor_id is not None or target_id is not None))
