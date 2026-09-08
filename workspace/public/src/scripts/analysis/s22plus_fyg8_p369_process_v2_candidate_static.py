"""P369 fixed display-wait experiment; no device authority."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p369_namespace import load
load(globals())

SOURCE_FILES.update({'wait_checkpoint':ROOT/'workspace/public/src/native-init/s22plus_native_wait_checkpoint_v1.inc.c'})

if __name__=="__main__":raise SystemExit(main())
