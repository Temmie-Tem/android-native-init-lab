"""P369 fixed display-wait experiment; no device authority."""
from s22plus_fyg8_p369_namespace import load
load(globals())

WAIT_CHECK=5
WAIT_CHECK_STAGE=44
WAIT_CHECK_PASS=3|16|32|64
OBSERVATION_INTERVAL_SEC=10
STAGES=dict(STAGES)|{WAIT_CHECK_STAGE:'wait-check-at-control'}
MAX_DIAGNOSTIC_FRAMES=len(SUCCESS_EVENTS)+3
