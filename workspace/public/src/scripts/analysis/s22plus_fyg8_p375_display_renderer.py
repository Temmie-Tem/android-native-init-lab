"""P375 sealed packaging asset; unreachable from the root-console path."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'revalidation'))
from s22plus_fyg8_p375_namespace import load
load(globals())
