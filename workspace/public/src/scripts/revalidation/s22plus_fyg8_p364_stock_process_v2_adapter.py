"""P364 diagnostic successor; source-bound H0 capability only."""
from s22plus_fyg8_p364_namespace import load
load(globals())

POLICY_PREIMAGE+='|authenticated-stage-errno-before-park|partial-progress-not-full-proof'
POLICY_ID=hashlib.sha256(POLICY_PREIMAGE.encode('ascii')).hexdigest()[:32]
_progress_base_contract=_contract

def _contract():
    value=_progress_base_contract()
    value.update(authenticated_progress=True,preparation_failure_reported=True,
        diagnostic_only_fields='fixed-stage-event-errno',partial_progress_is_qualification=False)
    return value
