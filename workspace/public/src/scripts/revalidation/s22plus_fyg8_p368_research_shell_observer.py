"""P368 fixed child-exit experiment; H0 only until separately approved."""
from s22plus_fyg8_p368_namespace import load
load(globals())

# Fault qualification is checked after CONTROL, never a new recovery gate.
_exit_session=validate_session_result
_exit_qualification=validate_qualification

def _require_exit_witness(row):
    semantic=row['semantic']
    if (semantic['display_submitted_swaps']!=3
            or semantic['display_child_exited_before_ready'] is not True
            or row['native_progress']['child_status']!={'event':control.CHILD_EXIT,'code':7}):
        raise QualificationError('P368 exact three-submission exit-7 witness missing')

def validate_session_result(shell,step):
    row=_exit_session(shell,step)
    _require_exit_witness(row)
    return row

def validate_qualification(value):
    result=_exit_qualification(value)
    _require_exit_witness(result['sessions'][0])
    return result
