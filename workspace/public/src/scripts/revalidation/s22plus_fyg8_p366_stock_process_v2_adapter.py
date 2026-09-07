"""P366 exact native departure successor; no device authority."""
from s22plus_fyg8_p366_namespace import load
load(globals())

POLICY_PREIMAGE+='|exact-native-usb-departure-before-strict-odin|same-30sec-window'
POLICY_ID=hashlib.sha256(POLICY_PREIMAGE.encode('ascii')).hexdigest()[:32]
_departure_contract=_contract

def _contract():
    value=_departure_contract()
    value.update(native_usb_departure_before_odin=True,software_window_renewed=False,
        odin_inventory_errors_tolerated=False)
    return value
