"""v0.1.2-rc.1 gauge telemetry HUD, prospective fresh candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p378_namespace import load_predecessor
load_predecessor(globals())

SOURCE_FILES.update({
    'p378_gauge_contract':ROOT/'docs/operations/S22PLUS_FYG8_GAUGE_HUD_V1.md',
    'p378_gauge_provider_build':ROOT/'workspace/public/src/scripts/analysis/s22plus_fyg8_telemetry_provider_h0.py',
})

if __name__=='__main__':raise SystemExit(main())
