"""Fixed display-step variant; shared implementation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_display_step_v1_namespace import load
load(globals())

if __name__=="__main__":raise SystemExit(main())
