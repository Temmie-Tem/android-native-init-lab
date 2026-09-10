"""v0.1.2-rc.5 qualification with compact host observation journal."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p382_namespace import load_predecessor
load_predecessor(globals())

SOURCE_FILES["p382_rc5_contract"]=ROOT/"docs/operations/S22PLUS_FYG8_JOURNAL_CLOSE_RC5_V1.md"
DEFAULT_OUTPUT=ROOT/"workspace/private/outputs/s22plus_fyg8_p382/process-v2-candidate-static-20260910-01.json"

if __name__=="__main__":raise SystemExit(main())
