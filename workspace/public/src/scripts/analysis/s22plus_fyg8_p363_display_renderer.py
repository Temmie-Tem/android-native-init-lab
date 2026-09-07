"""P363 retains the exact P361 ten-swap renderer; control belongs to PID1."""
import s22plus_fyg8_p361_display_renderer as predecessor
from pathlib import Path
import hashlib
PREDECESSOR_SHA = '706ea91f0fccbe8db50bcb80356d251a970fe6bcd74a5efa0e91151cf2cbf678'
def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P363 renderer predecessor changed')
    return predecessor.render()
