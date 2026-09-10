"""v0.1.2-rc.5 qualification with compact host observation journal."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p382_namespace import load_predecessor
load_predecessor(globals())

_rc5_render=render

def render():
    return _replace_once(_rc5_render(),b"v0.1.2-rc.4",b"v0.1.2-rc.5")
