"""P365 corrected ARM64 successor; no device authority."""
from s22plus_fyg8_p365_namespace import load
load(globals())

POLICY_PREIMAGE+='|arm64-directory-040000|arm64-nofollow-0100000'
POLICY_ID=hashlib.sha256(POLICY_PREIMAGE.encode('ascii')).hexdigest()[:32]
_flag_contract=_contract

def _contract():
    value=_flag_contract()
    value.update(target_open_flag_abi='linux-arm64',directory_open_flag=0o40000,
        module_nofollow_flag=0o100000)
    return value
