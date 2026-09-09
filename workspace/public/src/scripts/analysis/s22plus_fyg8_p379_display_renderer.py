"""v0.1.2-rc.2 bounded gauge failure diagnostics; fresh candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p379_namespace import load_predecessor
load_predecessor(globals())

METRICS_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_status_metrics_v3.inc.c'
_diagnostic_render=render

def render():
    return _replace_once(_diagnostic_render(),b'v0.1.2-rc.1',b'v0.1.2-rc.2')
