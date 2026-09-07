"""Ten bounded FB-only swaps of the sealed P360 retained frame pair."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p360_display_renderer as predecessor

PREDECESSOR_SHA = '46464e9a4bdc29cda8676766b3580f92aa9270654971925efda6dcb1d0911e5b'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P361 renderer predecessor changed')
    source = predecessor.render().decode()
    start = source.index('    struct timespec transition_delay={.tv_sec=5};')
    end = source.index('    /* Retain both unchanged buffers', start)
    source = source[:start] + r'''    uint32_t next_object=s.plane,next_count=1,next_property=property(&pp,"FB_ID",NULL);
    uint64_t next_value=0;
    struct drm_mode_atomic next={.count_objs=1,.objs_ptr=PTR(&next_object),
        .count_props_ptr=PTR(&next_count),.props_ptr=PTR(&next_property),
        .prop_values_ptr=PTR(&next_value)};
    for(unsigned swap=0;swap<10;swap++) {
        struct timespec transition_delay={.tv_sec=1};
        require(nanosleep(&transition_delay,NULL)==0,"transition-delay");
        next_value=(swap%2==0)?second.fb:b.fb;
        call(DRM_IOCTL_MODE_ATOMIC,&next,"repeat-frame-commit");
        fprintf(stderr,"DISPLAY_SWAP_SUBMITTED run=%s swap=%u ioctl_return=0 visible=UNPROVED\n",run_id,swap+1);fflush(stderr);
    }
''' + source[end:]
    old = 'requested=framebuffer-cached-abgr-two-frame-v1 hardware-fill=off'
    if source.count(old) != 1:
        raise ValueError('P361 renderer identity seam differs')
    return source.replace(old, 'requested=framebuffer-cached-abgr-ten-swaps-v1 hardware-fill=off', 1).encode()
