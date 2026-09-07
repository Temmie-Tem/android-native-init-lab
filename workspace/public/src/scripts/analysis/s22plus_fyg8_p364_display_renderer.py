"""P364 diagnostic successor; source-bound H0 capability only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p364_namespace import load
load(globals())
