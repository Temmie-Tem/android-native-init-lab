"""P369 fixed display-wait experiment; no device authority."""
from s22plus_fyg8_p369_namespace import load
load(globals())

# Retain the pre-P368 validators, replacing the consumed exit-only criterion.
_wait_base_live=_live


def _live(observer,descriptor,key,writer,deadline,*,before_control):
    def delayed(request):
        # Independent of renderer progress; retained raw replay skips _live.
        left=deadline-time.monotonic()
        if left<=control.OBSERVATION_INTERVAL_SEC:raise TimeoutError('P369 observation interval exceeds deadline')
        time.sleep(control.OBSERVATION_INTERVAL_SEC)
        before_control(request)
    return _wait_base_live(observer,descriptor,key,writer,deadline,before_control=delayed)


def _require_wait_witness(row):
    expected=dict(submitted_swaps=3,exact_wait_marker=True,
        marker_age_at_least_two_seconds=True,child_unreaped_at_control=True)
    if (row['semantic']['display_submitted_swaps']!=0
            or row['semantic']['display_child_exited_before_ready'] is not False
            or row['native_progress']['child_status'] is not None
            or row['native_progress']['wait_checkpoint']!=expected):
        raise QualificationError('P369 exact userspace-wait witness missing')


def validate_session_result(shell,step):
    row=_exit_session(shell,step)
    _require_wait_witness(row)
    return row


def validate_qualification(value):
    result=_exit_qualification(value)
    _require_wait_witness(result['sessions'][0])
    return result
