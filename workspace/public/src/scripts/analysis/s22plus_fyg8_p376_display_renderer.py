"""P376 boot HUD with the reviewed root console; fresh identity."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p376_namespace import load_template
load_template(globals())

ROOT=Path(__file__).resolve().parents[5]
HUD_RENDERER_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_hud_renderer_v1.inc.c'
_hud_base_render=render

def _replace_once(value,old,new):
    if value.count(old)!=1:raise ValueError('P376 renderer seam differs: '+repr(old[:80]))
    return value.replace(old,new,1)

def render():
    source=_hud_base_render()
    source=_replace_once(source,b'#include <sys/stat.h>',b'#include <sys/stat.h>\n#include <sys/socket.h>')
    # Failure parks with remaining resources intact. PID1 can still request
    # Download without waiting for a renderer exit or any DRM close operation.
    source=_replace_once(source,b'    _exit(1);',b'    for(;;){struct timespec d={.tv_sec=1};(void)nanosleep(&d,NULL);}')
    start=source.index(b'static void paint(');end=source.index(b'static int valid_id(',start)
    source=source[:start]+HUD_RENDERER_SOURCE.read_bytes()+b'\n'+source[end:]
    source=_replace_once(source,b'    struct buffer b=allocate_buffer(),second=allocate_buffer();\n    paint(&b,0);paint(&second,1);',
        b'    struct hud_snapshot view=hud_wait_snapshot();hud_console_state=view.state;\n    struct buffer b=allocate_buffer();paint(&b,(unsigned)(view.uptime_ms/1000U>0xffffffffU?0xffffffffU:view.uptime_ms/1000U));')
    source=_replace_once(source,b'.flags=DRM_MODE_ATOMIC_ALLOW_MODESET,',b'.flags=DRM_MODE_ATOMIC_ALLOW_MODESET|DRM_MODE_PAGE_FLIP_EVENT,.user_data=1,')
    source=_replace_once(source,b'    call(DRM_IOCTL_MODE_ATOMIC,&a,"static-commit");',b'    call(DRM_IOCTL_MODE_ATOMIC,&a,"static-commit");\n    hud_flip_event(1,s.crtc);hud_record(&view);')
    source=_replace_once(source,b'struct drm_mode_atomic next={.count_objs=1,',b'struct drm_mode_atomic next={.flags=DRM_MODE_PAGE_FLIP_EVENT,.count_objs=1,')
    source=_replace_once(source,b'struct selection s=select_display();check_initial_state(s);',b'struct selection s=select_display();check_initial_state(s);hud_single_encoder(s);')
    start=source.index(b'    for(unsigned swap=0;swap<10;swap++) {')
    source=source[:start]+b'''    for(uint64_t token=2;token<=601;token++) {
        view=hud_wait_snapshot();hud_console_state=view.state;
        struct buffer fresh=allocate_buffer();
        paint(&fresh,(unsigned)(view.uptime_ms/1000U>0xffffffffU?0xffffffffU:view.uptime_ms/1000U));
        next_value=fresh.fb;next.user_data=token;
        call(DRM_IOCTL_MODE_ATOMIC,&next,"hud-frame-commit");
        hud_flip_event(token,s.crtc);hud_record(&view);
        hud_retire(&b);b=fresh;
    }
    for(;;){struct timespec idle={.tv_sec=1};(void)nanosleep(&idle,NULL);}
}
'''
    return source
