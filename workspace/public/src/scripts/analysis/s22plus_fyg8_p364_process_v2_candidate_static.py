"""P364 diagnostic successor; source-bound H0 capability only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p364_namespace import load
load(globals())

SOURCE_FILES.update({'p364_progress_parser':REVALIDATION/'s22plus_fyg8_p364_progress.py',
    'p364_diagnostic_native':ROOT/'workspace/public/src/native-init/s22plus_native_return_diagnostics_v1.inc.c'})

if __name__=='__main__':raise SystemExit(main())
