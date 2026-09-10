"""v0.1.2-rc.4 output backpressure and bounded memory observations."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p381_namespace import load_predecessor
load_predecessor(globals())
import s22plus_memory_manifest_v1 as memory_manifest

_rc4_render=render
MEMORY_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_memory_snapshot_v1.inc.c'
GEM_MEMORY_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_hud_memory_v1.inc.c'


def render():
    source=_replace_once(_rc4_render(),b'v0.1.2-rc.3',b'v0.1.2-rc.4')
    source=_replace_once(source,b'struct buffer {',GEM_MEMORY_SOURCE.read_bytes()+b'\nstruct buffer {')
    source=_replace_once(source,b'call(DRM_IOCTL_MSM_GEM_NEW,&g,"cached-buffer"); b.handle=g.handle;',
        b'call(DRM_IOCTL_MSM_GEM_NEW,&g,"cached-buffer"); b.handle=g.handle;hud_mem_allocated();')
    source=_replace_once(source,b'call(DRM_IOCTL_GEM_CLOSE,&close,"hud-retire-gem");',
        b'call(DRM_IOCTL_GEM_CLOSE,&close,"hud-retire-gem");hud_mem_retired_one();')
    source=_replace_once(source,b'hud_flip_event(1,s.crtc);hud_record(&view);',
        b'hud_flip_event(1,s.crtc);hud_record(&view);hud_mem_record(view.sequence);')
    source=_replace_once(source,b'hud_retire(&b);b=fresh;',
        b'hud_retire(&b);b=fresh;hud_mem_record(view.sequence);')
    memory=memory_manifest.render()+b'\n#define MS_GEM_BUFFER_BYTES BYTES\n'+MEMORY_SOURCE.read_bytes()
    anchor=b'int main(int argc,char **argv) {'
    source=_replace_once(source,anchor,memory+b'\n'+anchor+
        b'\n    if(argc==3 && !strcmp(argv[1],"--memory-snapshot"))return memory_snapshot(argv[2]);')
    return source
