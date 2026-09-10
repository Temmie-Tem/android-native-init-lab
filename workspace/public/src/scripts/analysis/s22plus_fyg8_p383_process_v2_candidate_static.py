"""v0.2.0-rc.1 native baseline first roundtrip qualification."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p383_namespace import load_predecessor
load_predecessor(globals())

SOURCE_FILES["p383_roundtrip_contract"]=ROOT/"docs/operations/S22PLUS_NATIVE_ROUNDTRIP_FIRST_QUALIFICATION_V1.md"
SOURCE_FILES["p383_native_health"]=ROOT/"workspace/public/src/scripts/revalidation/s22plus_native_baseline_health_v1.py"
SOURCE_FILES["p383_roundtrip_owner"]=ROOT/"workspace/public/src/scripts/revalidation/s22plus_native_roundtrip_owner_v1.py"
DEFAULT_OUTPUT=ROOT/"workspace/private/outputs/s22plus_fyg8_p383/process-v2-candidate-static-20260910-01.json"

if __name__=="__main__":raise SystemExit(main())
