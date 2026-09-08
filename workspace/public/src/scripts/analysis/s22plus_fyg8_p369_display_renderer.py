"""P369 fixed display-wait experiment; no device authority."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"revalidation"))
from s22plus_fyg8_p369_namespace import load
load(globals())

_wait_previous_render=render

def render():
    source=_wait_previous_render()
    old=b'if(swap==2U)_exit(7); /* Fixed early termination; no cleanup retry. */'
    new=b'if(swap==2U) {\n            fprintf(stderr,"DISPLAY_WAIT_ENTERED run=%s after_swaps=3\\n",run_id);\n            fflush(stderr);\n            for(;;) {struct timespec idle={.tv_sec=1};(void)nanosleep(&idle,NULL);}\n        }'
    if source.count(old)!=1:raise ValueError('P369 fixed-wait seam differs')
    return source.replace(old,new,1)

if __name__=="__main__":raise SystemExit(main())
