"""P371 fixed STATUS observations; H0 only until separately approved."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p371_namespace import load
load(globals())

SOURCE_FILES.update({'status_native':ROOT/'workspace/public/src/native-init/s22plus_native_status_v1.inc.c','status_handoff_host':ROOT/'workspace/public/src/scripts/revalidation/s22plus_fyg8_p371_planned_handoff.py'})

if __name__=="__main__":raise SystemExit(main())
