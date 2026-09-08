"""P368 fixed child-exit experiment; H0 only until separately approved."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p368_namespace import load
load(globals())

_original_render=render

def render():
    source=_original_render()
    anchor=b'fflush(stderr);\n    }'
    if source.count(anchor)!=1:raise ValueError('P368 third-submission seam differs')
    return source.replace(anchor,b'fflush(stderr);\n        if(swap==2U)_exit(7); /* Fixed early termination; no cleanup retry. */\n    }',1)

if __name__=="__main__":raise SystemExit(main())
