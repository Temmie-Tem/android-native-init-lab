"""Memory-buffer magenta with hardware fill explicitly disabled."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p355_display_renderer as predecessor

PREDECESSOR_SHA = '487feb0cf9592ccc2cf43b4cf0d132ae32ca72b0b79866eab7fbd5b329ae9867'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P356 renderer predecessor changed')
    source = predecessor.render().decode()
    start = source.index('static void paint(struct buffer *b,unsigned frame) {')
    end = source.index('static int valid_id(', start)
    source = source[:start] + r'''static void paint(struct buffer *b,unsigned frame) {
    (void)frame;
    for(unsigned y=0;y<HEIGHT;y++) for(unsigned x=0;x<PITCH/4;x++)
        b->pixels[y*(PITCH/4)+x]=x<WIDTH?0x00ff00ff:0x00ffffff;
    __sync_synchronize();
}
''' + source[end:]
    changes = (
        ('/* Original fixed asymmetric pattern. White alone can be a vendor error fill. */',
         '/* Visible magenta; keep original white row padding as a diagnostic. */'),
        ('/* Keep the painted FB as a distinct non-fill diagnostic outcome. */',
         '/* Explicit zero selects normal framebuffer sourcing. */'),
        ('values[14]=0x80ff00ffULL;', 'values[14]=0;'),
        ('requested=hardware-magenta-v1 framebuffer=red-blue-green-black-cross-v1',
         'requested=framebuffer-magenta-v1 hardware-fill=off'),
    )
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('P356 renderer seam differs: ' + old)
        source = source.replace(old, new, 1)
    return source.encode()
