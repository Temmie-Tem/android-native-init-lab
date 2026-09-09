"""v0.1.1-rc.1 system-status HUD, fresh candidate identity."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p377_namespace import load_predecessor
load_predecessor(globals())

SOURCE_FILES.update({
    'p377_hud_renderer_native':ROOT/'workspace/public/src/native-init/s22plus_hud_renderer_v2.inc.c',
    'p377_metrics_native':ROOT/'workspace/public/src/native-init/s22plus_status_metrics_v1.inc.c',
    'p377_status_hud_contract':ROOT/'docs/operations/S22PLUS_FYG8_STATUS_HUD_V1.md',
})

if __name__=='__main__':raise SystemExit(main())
