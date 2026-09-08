"""P371 fixed STATUS observations; H0 only until separately approved."""
from s22plus_fyg8_p371_namespace import load
load(globals())

TOTAL_COMMANDS=6
POLICY_PREIMAGE=OVERLAY_CONTRACT_ID+'|'+P371_RUN_ID_HEX+'|one-child|two-authenticated-legs|two-fixed-status|control-10|original-deadline|exact-rollback'
POLICY_ID=hashlib.sha256(POLICY_PREIMAGE.encode('ascii')).hexdigest()[:32]
_status_contract=_contract
_status_acceptance=acceptance_fixture
_status_adapter_audit=audit

def _contract():
    value=_status_contract();value.update(control_sequence=10,status_sequences=[8,9],status_count=2)
    return value

def acceptance_fixture():
    value=_status_acceptance();value.update(total_commands=6,status_count=2)
    return value

def audit():
    value=_status_adapter_audit();value.update(total_commands=6,initial_reconnect_count=1,contract=_contract())
    return value
