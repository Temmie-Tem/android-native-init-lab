"""P363 sealed successor binding; no device authority."""
from s22plus_fyg8_p363_namespace import load
load(globals())

import s22plus_fyg8_p363_return_spec as return_spec
PACKAGED_MODULE_NAMES = DISPLAY_MODULE_NAMES + tuple(n for n, _, _, _ in return_spec.MODULES)
_return_identity = validate_p363_identity

def validate_p363_identity():
    value = _return_identity()
    value.update(total_command_count=3, dispatch_only=False,
        native_return_control=True, control_mode='download',
        control_acceptance_is_recovery=False, automatic_recovery_proved=False)
    return value
