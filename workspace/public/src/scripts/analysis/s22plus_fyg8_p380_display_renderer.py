"""v0.1.2-rc.3 observed model binding and optional native memory snapshots."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p380_namespace import load_predecessor
load_predecessor(globals())

_model_render = render


def render():
    return _replace_once(_model_render(), b'v0.1.2-rc.2', b'v0.1.2-rc.3')
