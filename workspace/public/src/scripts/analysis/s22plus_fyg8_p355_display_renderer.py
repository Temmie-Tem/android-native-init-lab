"""P354 transaction with one selected-plane hardware magenta fill property."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p354_display_renderer as predecessor

PREDECESSOR_SHA = '9b198b14d5d8a498be977b9853388d7f94458698acfbe8501482583eabccb5f0'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P355 renderer predecessor changed')
    source = predecessor.render().decode()
    changes = (
        ('ids[14+2*LIMIT]', 'ids[15+2*LIMIT]'),
        ('values[14+2*LIMIT]', 'values[15+2*LIMIT]'),
        ('objects[2]=s.plane;counts[2]=10;', 'objects[2]=s.plane;counts[2]=11;'),
        ('    for(uint32_t i=0;i<inherited_count;i++) {',
         '    /* Keep the painted FB as a distinct non-fill diagnostic outcome. */\n'
         '    ids[14]=property(&pp,"color_fill",NULL);values[14]=0x80ff00ffULL;\n'
         '    for(uint32_t i=0;i<inherited_count;i++) {'),
        ('ids[15+2*i]=property(&p,"CRTC_ID",NULL);values[15+2*i]=0;',
         'ids[16+2*i]=property(&p,"CRTC_ID",NULL);values[16+2*i]=0;'),
        ('ids[14+2*i]=property(&p,"FB_ID",NULL);values[14+2*i]=0;',
         'ids[15+2*i]=property(&p,"FB_ID",NULL);values[15+2*i]=0;'),
        ('pattern=red-blue-green-black-cross-v1',
         'requested=hardware-magenta-v1 framebuffer=red-blue-green-black-cross-v1'),
    )
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('P355 renderer seam differs: ' + old)
        source = source.replace(old, new, 1)
    return source.encode()
