"""v0.1.2-rc.3 observed model binding and optional native memory snapshots."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p380_namespace import load_predecessor
load_predecessor(globals())

SOURCE_FILES.update({
    'p380_model_memory_contract':ROOT/'docs/operations/S22PLUS_FYG8_GAUGE_MODEL_MEMORY_V1.md',
    'p380_model_provider_build':ROOT/'workspace/public/src/scripts/analysis/s22plus_fyg8_telemetry_provider_h0_v3.py',
})
DEFAULT_OUTPUT=ROOT/'workspace/private/outputs/s22plus_fyg8_p380/process-v2-candidate-static-20260910-01.json'

if __name__=="__main__":raise SystemExit(main())
