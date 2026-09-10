"""v0.1.2-rc.4 output backpressure and bounded memory observations."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p381_namespace import load_predecessor
load_predecessor(globals())

SOURCE_FILES.update({
    'p381_output_backpressure':ROOT/'workspace/public/src/native-init/s22plus_root_console_output_v2.inc.c',
    'p381_memory_snapshot':ROOT/'workspace/public/src/native-init/s22plus_memory_snapshot_v1.inc.c',
    'p381_hud_memory':ROOT/'workspace/public/src/native-init/s22plus_hud_memory_v1.inc.c',
    'p381_memory_manifest':ROOT/'workspace/public/src/scripts/analysis/s22plus_memory_manifest_v1.py',
    'p381_memory_decoder':ROOT/'workspace/public/src/scripts/revalidation/s22plus_memory_snapshot_v1.py',
    'p381_rc4_contract':ROOT/'docs/operations/S22PLUS_FYG8_OUTPUT_MEMORY_RC4_V1.md',
})
DEFAULT_OUTPUT=ROOT/'workspace/private/outputs/s22plus_fyg8_p381/process-v2-candidate-static-20260910-01.json'

if __name__=="__main__":raise SystemExit(main())
