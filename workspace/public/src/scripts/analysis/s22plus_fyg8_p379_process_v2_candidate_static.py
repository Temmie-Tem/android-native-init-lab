"""v0.1.2-rc.2 bounded gauge failure diagnostics; fresh candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p379_namespace import load_predecessor
load_predecessor(globals())

SOURCE_FILES.update({
    'p379_diagnostic_contract':ROOT/'docs/operations/S22PLUS_FYG8_GAUGE_DIAGNOSTICS_V1.md',
    'p379_diagnostic_provider_build':ROOT/'workspace/public/src/scripts/analysis/s22plus_fyg8_telemetry_provider_h0_v2.py',
})

DEFAULT_OUTPUT=ROOT/'workspace/private/outputs/s22plus_fyg8_p379/process-v2-candidate-static-20260910-02.json'

if __name__=='__main__':raise SystemExit(main())
