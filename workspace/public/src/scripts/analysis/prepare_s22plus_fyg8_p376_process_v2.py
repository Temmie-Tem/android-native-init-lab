"""P376 boot HUD with the reviewed root console; fresh identity."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p376_namespace import load_template
load_template(globals())

if __name__=='__main__':raise SystemExit(main())
