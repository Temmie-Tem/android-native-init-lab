"""Shared renderer extension: fixed nonblocking eventfd requests, no auto swaps."""
_step_previous_render=render

def render():
    source=_step_previous_render()
    start=source.find(b'    for(unsigned swap=0;swap<10;swap++) {')
    end=source.find(b'    /* Retain both unchanged buffers',start)
    if start<0 or end<start:raise ValueError('step renderer loop seam differs')
    loop=b'''    require((fcntl(STDIN_FILENO,F_GETFL)&O_NONBLOCK)!=0,"step-input-nonblocking");
    for(unsigned ordinal=1;ordinal<=STEP_MAX;ordinal++) {
        uint64_t request=0;
        for(;;) {
            ssize_t count=read(STDIN_FILENO,&request,sizeof(request));
            if(count==(ssize_t)sizeof(request))break;
            require(count<0 && (errno==EAGAIN || errno==EINTR),"step-input-exact-read");
            struct timespec idle={.tv_nsec=10000000};
            require(nanosleep(&idle,NULL)==0,"step-input-wait");
        }
        require(request==ordinal,"step-input-ordinal");
        fprintf(stderr,"DISPLAY_STEP_STARTED run=%s ordinal=%u pattern=%u\\n",run_id,ordinal,ordinal);fflush(stderr);
        if(STEP_EXIT)_exit(7); /* Declared failure after receipt, before submission. */
        next_value=ordinal==1U?second.fb:b.fb;
        call(DRM_IOCTL_MODE_ATOMIC,&next,"requested-frame-commit");
        fprintf(stderr,"DISPLAY_STEP_DONE run=%s ordinal=%u pattern=%u\\n",run_id,ordinal,ordinal);fflush(stderr);
    }
'''.replace(b'STEP_MAX',str(_STEP_MAX).encode()).replace(b'STEP_EXIT',b'1' if _STEP_EXIT else b'0')
    return source[:start]+loop+source[end:]
