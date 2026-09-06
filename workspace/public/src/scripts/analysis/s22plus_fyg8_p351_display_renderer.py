"""Construct the P351 renderer from the unchanged reviewed P350 DRM core."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[5]
NATIVE=ROOT/'workspace/public/src/native-init'
BASE=NATIVE/'s22plus_native_display_h0.c'
BASE_SHA='0aef36334a305287f98e11470a2a64b44d8e1bd4126adaafd0b9a4ed8e0846d7'

def render():
    raw=BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA:raise ValueError('P350 renderer template drift')
    s=raw.decode()
    s=s.replace('static void fail(const char *stage) {','#ifdef P350_DISPLAY_VARIANT\nstatic void p351_failure_diagnostic(void);\n#endif\nstatic void fail(const char *stage) {',1)
    s=s.replace('    _exit(1);','#ifdef P350_DISPLAY_VARIANT\n    p351_failure_diagnostic();\n#endif\n    _exit(1);',1)
    a=s.index('/* Tiny original 3x5 hex font');b=s.index('static void wait_flip(',a)
    s=s[:a]+'''#include "s22plus_native_display_visible_layout_h0.c"
static void paint(struct buffer *b,unsigned frame) {
    require(s22plus_display_paint_visible(b->pixels,BYTES/4,PITCH/4,run_id,frame)==0,"visible-layout");
    __sync_synchronize();
}
'''+s[b:]
    s=s.replace('#include "s22plus_native_display_load.inc.c"','#include "s22plus_native_display_ready_v2.inc.c"',1)
    s=s.replace('    p350_prepare_driver();','    p351_prepare_driver();',1)
    return s.encode()
