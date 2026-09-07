"""P363 offline promotion entry; connected preparation and F1 remain separate."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "revalidation"))
from s22plus_fyg8_p363_namespace import load
load(globals())

DEFAULT_PROMOTION = ROOT / 'workspace/private/outputs/s22plus_fyg8_p363/process-v2-promotion-20260908-01'

if __name__ == '__main__':
    raise SystemExit(main())
