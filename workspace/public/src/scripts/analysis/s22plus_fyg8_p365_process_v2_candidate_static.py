"""P365 corrected ARM64 successor; no device authority."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p365_namespace import load
load(globals())

SOURCE_FILES.update({"p365_arm64_open_flags":ROOT/"workspace/public/src/native-init/s22plus_arm64_open_flags_v1.h"})

if __name__=="__main__":raise SystemExit(main())
