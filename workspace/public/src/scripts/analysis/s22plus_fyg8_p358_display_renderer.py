"""Cached ABGR8888 magenta over the sealed P357 renderer; H0 only."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p357_display_renderer as predecessor

PREDECESSOR_SHA = 'd662c4adbc15d2584f0b2ccef7b221adda5fbea8c7c2b78af15545c454ff6cd7'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P358 renderer predecessor changed')
    source = predecessor.render().decode()
    changes = (
        ('MSM_BO_SCANOUT|MSM_BO_WC', 'MSM_BO_SCANOUT|MSM_BO_CACHED'),
        ('"wc-buffer"', '"cached-buffer"'),
        ('CPU WC buffers', 'CPU cached buffers'),
        ('requested=framebuffer-abgr-magenta-v1 hardware-fill=off',
         'requested=framebuffer-cached-abgr-magenta-v1 hardware-fill=off'),
    )
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('P358 renderer seam differs: ' + old)
        source = source.replace(old, new, 1)
    return source.encode()
