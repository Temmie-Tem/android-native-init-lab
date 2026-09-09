"""v0.1.1-rc.1 system-status HUD, fresh candidate identity."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p377_namespace import load_predecessor
load_predecessor(globals())

HUD_RENDERER_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_hud_renderer_v2.inc.c'
METRICS_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_status_metrics_v1.inc.c'
_status_base_render=render

def render():
    source=_status_base_render()
    anchor=b'/* Text-only immutable frame:'
    source=_replace_once(source,anchor,METRICS_SOURCE.read_bytes()+b'\n'+anchor)
    anchor=b'int main(int argc,char **argv) {'
    source=_replace_once(source,anchor,anchor+b'\n    if(argc==3 && !strcmp(argv[1],"--collect-status"))return status_collect(argv[2]);')
    return source
