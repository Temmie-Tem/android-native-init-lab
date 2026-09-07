"""Two retained cached frames, one bounded blocking FB-only transition."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p359_display_renderer as predecessor

PREDECESSOR_SHA = '6377b26ec719f3aa849134991e89930741dc4c0a1ec662c10b877d74ca78f816'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P360 renderer predecessor changed')
    source = predecessor.render().decode()
    changes = (
        ('#define FRAMES 1U', '#define FRAMES 2U'),
        ('    (void)frame;\n', ''),
        ('color=y<HEIGHT/2?(x<WIDTH/2?0xff0000ff:0xffff0000):0xff00ff00;',
         'color=frame?(y<HEIGHT/2?(x<WIDTH/2?0xff00ff00:0xff0000ff):0xffff0000):\n'
         '                (y<HEIGHT/2?(x<WIDTH/2?0xff0000ff:0xffff0000):0xff00ff00);'),
        ('        b->pixels[y*(PITCH/4)+x]=color;',
         '        /* Large white 2 with a black rectangular backing, second frame only. */\n'
         '        if(frame && x>=260 && x<820 && y>=740 && y<1600) {\n'
         '            color=0xff000000;\n'
         '            if((x>=300&&x<780&&((y>=780&&y<900)||(y>=1110&&y<1230)||(y>=1440&&y<1560))) ||\n'
         '               (x>=660&&x<780&&y>=900&&y<1110) ||\n'
         '               (x>=300&&x<420&&y>=1230&&y<1440)) color=0xffffffff;\n'
         '        }\n'
         '        b->pixels[y*(PITCH/4)+x]=color;'),
        ('for(unsigned i=0;i<FRAMES;i++) paint(&b,i);\n        require(fwrite(b.pixels,1,BYTES,stdout)==BYTES,"paint-output");',
         'for(unsigned i=0;i<FRAMES;i++) {paint(&b,i);\n'
         '            require(fwrite(b.pixels,1,BYTES,stdout)==BYTES,"paint-output");}'),
        ('struct buffer b=allocate_buffer();paint(&b,0);',
         'struct buffer b=allocate_buffer(),second=allocate_buffer();\n'
         '    paint(&b,0);paint(&second,1);'),
        ('    /* Retain display resources in this child during the existing attended\n'
         '     * window. No second modeset, cleanup, redraw, or USB-dependent action.\n'
         '     * The existing parent deadline and physical Download own termination. */',
         '    struct timespec transition_delay={.tv_sec=5};\n'
         '    require(nanosleep(&transition_delay,NULL)==0,"transition-delay");\n'
         '    uint32_t next_object=s.plane,next_count=1,next_property=property(&pp,"FB_ID",NULL);\n'
         '    uint64_t next_value=second.fb;\n'
         '    struct drm_mode_atomic next={.count_objs=1,.objs_ptr=PTR(&next_object),\n'
         '        .count_props_ptr=PTR(&next_count),.props_ptr=PTR(&next_property),\n'
         '        .prop_values_ptr=PTR(&next_value)};\n'
         '    call(DRM_IOCTL_MODE_ATOMIC,&next,"second-frame-commit");\n'
         '    fprintf(stderr,"DISPLAY_SECOND_SUBMITTED run=%s ioctl_return=0 visible=UNPROVED\\n",run_id);fflush(stderr);\n'
         '    /* Retain both unchanged buffers, FBs and mode blob until the existing\n'
         '     * parent deadline or physical Download. No retry or cleanup. */'),
        ('requested=framebuffer-cached-abgr-grid-v1 hardware-fill=off',
         'requested=framebuffer-cached-abgr-two-frame-v1 hardware-fill=off'),
    )
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('P360 renderer seam differs: ' + old)
        source = source.replace(old, new, 1)
    return source.encode()
