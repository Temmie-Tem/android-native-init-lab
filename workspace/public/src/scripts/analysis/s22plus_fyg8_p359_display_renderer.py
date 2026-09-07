"""One cached ABGR8888 RGB/grid/edge frame over the sealed P358 renderer."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p358_display_renderer as predecessor

PREDECESSOR_SHA = '31b87bbc922b61e5f7f65a82dd085241745c8dff4012b34863d6c2f9d8e960fd'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P359 renderer predecessor changed')
    source = predecessor.render().decode()
    start = source.index('static void paint(struct buffer *b,unsigned frame) {')
    end = source.index('static int valid_id(', start)
    source = source[:start] + r'''static void paint(struct buffer *b,unsigned frame) {
    (void)frame;
    for(unsigned y=0;y<HEIGHT;y++) for(unsigned x=0;x<PITCH/4;x++) {
        uint32_t color=0xffffffff;
        if(x<WIDTH) {
            color=y<HEIGHT/2?(x<WIDTH/2?0xff0000ff:0xffff0000):0xff00ff00;
            if(x%120<4||y%120<4) color=0xff000000;
            if(x<8||x>=WIDTH-8||y<8||y>=HEIGHT-8) color=0xffffffff;
        }
        b->pixels[y*(PITCH/4)+x]=color;
    }
    __sync_synchronize();
}
''' + source[end:]
    changes = (
        ('/* Opaque ABGR8888 magenta; opaque white row padding. */',
         '/* Opaque RGB regions, 120-pixel black grid, 8-pixel white edge/padding. */'),
        ('requested=framebuffer-cached-abgr-magenta-v1 hardware-fill=off',
         'requested=framebuffer-cached-abgr-grid-v1 hardware-fill=off'),
    )
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('P359 renderer seam differs: ' + old)
        source = source.replace(old, new, 1)
    return source.encode()
