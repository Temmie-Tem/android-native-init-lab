"""P364 diagnostic successor; source-bound H0 capability only."""
from s22plus_fyg8_p364_namespace import load
load(globals())

# Fixed authenticated diagnostic vocabulary, separate from CONTROL sequence 5.
FRAME_DIAGNOSTIC = 0x8b
DIAGNOSTIC_SEQUENCE_BASE = 0x100
DIAGNOSTIC_DOMAIN = b'S22PLUS-FYG8-P364-PROGRESS-v1'
ENTER, RETURN, CHILD_EXIT, CHILD_SIGNAL, TERMINAL = range(5)
STAGES = {1:'preparation',30:'nvmem-providers',31:'debugfs-mount',
    32:'reboot-registry-wait',33:'writer-binding',40:'pipe-create',
    41:'child-clock',42:'child-clone',43:'child-status',255:'terminal'}
for _i, (_name, *_rest) in enumerate(MODULES):
    for _j, _label in enumerate(('file-check','finit-module','file-close')):
        STAGES[10+3*_i+_j] = _name+':'+_label
_PREP_STAGES = tuple(range(10,22))+(30,31,32)+tuple(range(22,25))+(33,)
SUCCESS_EVENTS = ((1,ENTER),)+tuple((s,e) for s in _PREP_STAGES for e in (ENTER,RETURN))+((1,RETURN),)+tuple((s,e) for s in (40,41,42) for e in (ENTER,RETURN))
MAX_DIAGNOSTIC_FRAMES = len(SUCCESS_EVENTS)+2  # optional child status and terminal
DIAGNOSTIC_PAYLOAD_SIZE = 40
DIAGNOSTIC_WIRE_SIZE = 56
