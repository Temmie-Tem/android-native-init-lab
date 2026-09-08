"""P370 one planned pre-CONTROL handoff; H0 only until approved."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p370_namespace import load
load(globals())

if __name__=="__main__":raise SystemExit(main())
