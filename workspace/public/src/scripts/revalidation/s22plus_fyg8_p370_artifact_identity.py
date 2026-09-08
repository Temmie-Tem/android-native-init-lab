"""P370 one planned pre-CONTROL handoff; H0 only until approved."""
from s22plus_fyg8_p370_namespace import load
load(globals())

_handoff_identity=validate_p370_identity

def validate_p370_identity():
    value=_handoff_identity()
    value.update(initial_session_count=2,same_fd_session_count=1,total_session_count=2,
        initial_reconnect_count=1,total_command_count=4,planned_handoff=True,
        child_relaunched=False,control_sequence=8)
    return value
