"""P363 sealed successor binding; no device authority."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "revalidation"))
from s22plus_fyg8_p363_namespace import load
load(globals())

DEFAULT_OUTPUT = ROOT / 'workspace/private/outputs/s22plus_fyg8_p363/process-v2-candidate-static-20260908-01.json'
SOURCE_FILES.update({
    'p363_native_return_intent': REVALIDATION / 's22plus_fyg8_p363_return_host.py',
    'p363_live_return_owner': REVALIDATION / 'device_action_f1_live_v2.py',
    'p363_typed_return_evidence': REVALIDATION / 'device_action_f1_evidence_v2.py',
})

if __name__ == '__main__':
    raise SystemExit(main())
