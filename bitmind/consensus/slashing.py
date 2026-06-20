from . import validators as consensus_validators
from ..core import validators as core_validators, rewards, audit

# slashing rules (percentages)
SLASH_FRAUD_APPROVAL = 0.10
SLASH_DOUBLE_AWARD = 0.05
SLASH_INVALID_ACTION = 0.02


def slash_validator_for_event(validator_id: str, event: str) -> float:
    v = core_validators.get_validator(validator_id)
    if not v:
        return 0.0
    percent = 0.0
    reason = ""
    if event == "fraud_approval":
        percent = SLASH_FRAUD_APPROVAL
        reason = "fraud_approval"
    elif event == "double_award":
        percent = SLASH_DOUBLE_AWARD
        reason = "double_award"
    elif event == "invalid_action":
        percent = SLASH_INVALID_ACTION
        reason = "invalid_action"
    else:
        return 0.0
    amount = v.staked_amount * percent
    if amount <= 0:
        return 0.0
    # apply slashing via rewards.slash on the underlying user
    slashed = rewards.slash(v.user_id, amount, reason=f"slash:{reason}")
    # update validator record
    v.staked_amount = max(0.0, v.staked_amount - slashed)
    core_validators.record_slash(validator_id)
    # update validator_score (penalize)
    v.validator_score = max(0.0, v.validator_score - percent)
    core_validators._ensure_registry()
    # removed unused variable core_validators_list
    core_validators.get_validator(validator_id)  # no-op to keep consistent
    # save back
    core_validators.get_validator(validator_id)
    # add audit event
    audit.add_audit_event(event_type="slash", actor_id=validator_id, target_id=v.user_id, reason=reason, metadata={"amount": slashed})
    return slashed
