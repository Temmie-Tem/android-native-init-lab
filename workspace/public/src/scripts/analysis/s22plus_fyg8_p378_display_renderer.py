"""v0.1.2-rc.1 gauge telemetry HUD, prospective fresh candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p378_namespace import load_predecessor
load_predecessor(globals())

HUD_RENDERER_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_hud_renderer_v3.inc.c'
METRICS_SOURCE=ROOT/'workspace/public/src/native-init/s22plus_status_metrics_v2.inc.c'
