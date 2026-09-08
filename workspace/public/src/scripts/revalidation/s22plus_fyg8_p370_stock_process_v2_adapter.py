"""P370 one planned pre-CONTROL handoff; H0 only until approved."""
from s22plus_fyg8_p370_namespace import load
load(globals())

INITIAL_SESSION_COUNT=2
SAME_FD_SESSION_COUNT=1
INITIAL_RECONNECT_COUNT=1
TOTAL_COMMANDS=4
POLICY_PREIMAGE=OVERLAY_CONTRACT_ID+'|'+P370_RUN_ID_HEX+'|one-child|two-authenticated-legs|one-planned-handoff|fresh-nonce-control-8|original-deadline|exact-rollback'
POLICY_ID=hashlib.sha256(POLICY_PREIMAGE.encode('ascii')).hexdigest()[:32]
_handoff_contract=_contract
_handoff_acceptance=acceptance_fixture
_handoff_audit=audit

def _contract():
    value=_handoff_contract()
    value.update(initial_session_count=2,same_fd_session_count=1,initial_reconnect_count=1,
        planned_handoff=True,control_sequence=8,child_relaunched=False)
    return value

def acceptance_fixture():
    value=_handoff_acceptance()
    value.update(initial_session_count=2,same_fd_session_count=1,initial_reconnect_count=1)
    return value

def audit():
    value=_handoff_audit()
    value.update(initial_session_count=2,total_commands=4,contract=_contract())
    return value
