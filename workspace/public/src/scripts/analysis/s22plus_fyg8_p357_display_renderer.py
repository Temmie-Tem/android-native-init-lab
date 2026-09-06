"""Opaque ABGR8888 framebuffer magenta over the sealed P356 renderer."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p356_display_renderer as predecessor

PREDECESSOR_SHA = '91e1301c8397e590d7d46a10376d1526c9754b0ced6065cf50154de178cc0103'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P357 renderer predecessor changed')
    source = predecessor.render().decode()
    # Qualify support and register the framebuffer with the same FourCC.
    if source.count('DRM_FORMAT_XRGB8888') != 2:
        raise ValueError('P357 format selection/registration seam differs')
    source = source.replace('DRM_FORMAT_XRGB8888', 'DRM_FORMAT_ABGR8888')
    changes = (
        ('x<WIDTH?0x00ff00ff:0x00ffffff', 'x<WIDTH?0xffff00ff:0xffffffff'),
        ('/* Visible magenta; keep original white row padding as a diagnostic. */',
         '/* Opaque ABGR8888 magenta; opaque white row padding. */'),
        ('requested=framebuffer-magenta-v1 hardware-fill=off',
         'requested=framebuffer-abgr-magenta-v1 hardware-fill=off'),
    )
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('P357 renderer seam differs: ' + old)
        source = source.replace(old, new, 1)
    return source.encode()
