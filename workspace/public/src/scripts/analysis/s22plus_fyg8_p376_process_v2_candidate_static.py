"""P376 boot HUD with the reviewed root console; fresh identity."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p376_namespace import load_template
load_template(globals())

SOURCE_FILES.update({
    'p376_hud_native':runtime.HUD_SOURCE,
    'p376_hud_renderer_native':ROOT/'workspace/public/src/native-init/s22plus_hud_renderer_v1.inc.c',
    'p376_hud_renderer':Path(__file__).with_name('s22plus_fyg8_p376_display_renderer.py'),
    'p376_namespace':REVALIDATION/'s22plus_fyg8_p376_namespace.py',
    'p376_hud_contract':ROOT/'docs/operations/S22PLUS_FYG8_BOOT_HUD_V1.md',
})

if __name__=='__main__':raise SystemExit(main())
