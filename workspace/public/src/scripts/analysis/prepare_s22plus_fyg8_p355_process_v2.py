"""P355 offline promotion entry; connected preparation and F1 remain separate."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "revalidation"))
from s22plus_fyg8_p355_namespace import load
load(globals())

if __name__ == '__main__':
    raise SystemExit(main())
