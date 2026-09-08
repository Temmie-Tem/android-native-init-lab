"""P370 one planned pre-CONTROL handoff; H0 only until approved."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p370_namespace import load
load(globals())

SOURCE_FILES.update({'handoff_native':ROOT/'workspace/public/src/native-init/s22plus_native_handoff_v1.inc.c','handoff_host':ROOT/'workspace/public/src/scripts/revalidation/s22plus_native_planned_handoff_v1.py'})

if __name__=="__main__":raise SystemExit(main())
