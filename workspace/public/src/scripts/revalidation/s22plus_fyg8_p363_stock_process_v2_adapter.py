"""P363 sealed successor binding; no device authority."""
from s22plus_fyg8_p363_namespace import load
load(globals())

TOTAL_COMMANDS = 3
POLICY_PREIMAGE = OVERLAY_CONTRACT_ID + "|" + P363_RUN_ID_HEX + "|kernel-boot-uuid-v2|parent-id|ten-submitted-swaps|authenticated-download-control-once|durable-intent|acceptance-not-arrival|attended-exact-rollback"
POLICY_ID = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()[:32]
_return_contract = _contract
_return_audit = audit

def _contract():
    value = _return_contract()
    value.update(dispatch_only=False, display_response_required=True,
        native_return_control=True, control_mode='download', control_ack_scope='acceptance-only',
        framed_session_close_required=False, automatic_recovery_proved=False)
    return value

def audit():
    value = _return_audit()
    value.update(total_commands=3, contract=_contract())
    return value
