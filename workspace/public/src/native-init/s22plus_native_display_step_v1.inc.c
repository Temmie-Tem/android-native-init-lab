/* Fixed eventfd request channel; one outstanding request, never a PID1 wait.
 * EFD_NONBLOCK is shared across fork/dup: neither process may clear it.
 * Queueing is not rendering. Only exact run/ordinal/pattern markers complete.
 */
static void pstep_handoff_tag(uint8_t *,const char *,const uint8_t *,uint32_t,const uint8_t *,size_t);
static long pstep_handoff_write(int,uint8_t,uint32_t,const uint8_t *,size_t,const struct timespec64 *);
static const char pstep_step_domain[]="S22PLUS-FYG8-PSTEP-DISPLAY-STEP-v1";
static const char pstep_step_ack_domain[]="S22PLUS-FYG8-PSTEP-DISPLAY-STEP-ACK-v1";

static int pstep_step_line(const char *line,size_t length,unsigned ordinal,int done) {
    char expected[128];size_t used=0;
    const char *prefix=done?"DISPLAY_STEP_DONE run=":"DISPLAY_STEP_STARTED run=";
    const char *middle=" ordinal=";const char *pattern=" pattern=";
    static const char hex[]="0123456789abcdef";
    if(ordinal<1U || ordinal>PSTEP_STEP_MAX)return 0;
    size_t n=cstr_len(prefix);memcpy(expected,prefix,n);used=n;
    for(unsigned i=0;i<16U;i++) {
        expected[used++]=hex[p328_run_id_bytes[i]>>4U];
        expected[used++]=hex[p328_run_id_bytes[i]&15U];
    }
    n=cstr_len(middle);memcpy(expected+used,middle,n);used+=n;
    expected[used++]=(char)('0'+ordinal);
    n=cstr_len(pattern);memcpy(expected+used,pattern,n);used+=n;
    expected[used++]=(char)('0'+ordinal);
    return length==used && p260_bytes_equal(line,expected,used);
}

static long pstep_step_output(struct pstep_control_state *state,const uint8_t *bytes,size_t size) {
    if(size>131072U-state->child_bytes)return -P260_EOVERFLOW;
    state->child_bytes+=(uint32_t)size;
    for(size_t i=0;i<size;i++) {
        if(bytes[i]=='\n') {
            if(!state->line_overflow) {
                for(unsigned ordinal=1;ordinal<=PSTEP_STEP_MAX;ordinal++) {
                    if(pstep_step_line(state->line,state->line_used,ordinal,0)) {
                        if(state->step_failed || !state->step_pending || state->step_requested!=ordinal || state->step_started+1U!=ordinal)
                            state->step_failed=1U;
                        else state->step_started=ordinal;
                    }
                    if(pstep_step_line(state->line,state->line_used,ordinal,1)) {
                        if(state->step_failed || !state->step_pending || state->step_started!=ordinal || state->step_completed+1U!=ordinal)
                            state->step_failed=1U;
                        else {state->step_completed=ordinal;state->step_pending=0U;}
                    }
                }
            }
            state->line_used=state->line_overflow=0U;
        } else if(state->line_used<sizeof(state->line))state->line[state->line_used++]=(char)bytes[i];
        else state->line_overflow=1U;
    }
    return 0;
}

static long pstep_step_sample(struct pstep_control_state *state,long pid,int *reaped,int *status,
    unsigned *code,struct timespec64 *now) {
    if(!*reaped) {
        long waited=sys_wait4(pid,status,WNOHANG);
        if(waited==pid)*reaped=1;
        else if(waited!=0)return waited<0?waited:-P260_EPROTO;
    }
    if(*reaped) {
        long rc=pstep_diag_child_status(*status);if(rc!=0)return rc;
        if(state->step_pending)state->step_failed=1U;
    }
    long rc=p241_clock_gettime(now);if(rc!=0)return rc;
    *code=state->step_completed|(state->step_started<<2U)|(state->step_pending?16U:0U)|
        (state->step_failed?32U:0U)|(!*reaped?64U:0U);
    return 0;
}

static long pstep_step_request(struct pstep_control_state *state,int fd,uint32_t sequence,
    const struct timespec64 *deadline,long pid,int *reaped,int *status) {
    unsigned code=0;struct timespec64 now={0};
    long rc=pstep_step_sample(state,pid,reaped,status,&code,&now);if(rc!=0)return rc;
    if(state->step_requested>=PSTEP_STEP_MAX || sequence!=11U+state->step_requested ||
        state->step_pending)return -P260_EPROTO;
    ++state->step_requested; /* Before response or sole write; never replay. */
    uint64_t ordinal=state->step_requested;
    unsigned queued=0U;
    if(*reaped || state->step_failed)state->step_failed=1U;
    else {
        state->step_pending=1U;
        long written=sys_write(state->step_fd,&ordinal,sizeof(ordinal));
        queued=written==(long)sizeof(ordinal);
        if(!queued)state->step_failed=1U;
    } /* Local IPC fault remains observable; CONTROL is available. */
    uint8_t ack[36]={1U,(uint8_t)ordinal,(uint8_t)queued,(uint8_t)state->step_failed};
    pstep_handoff_tag(ack+4U,pstep_step_ack_domain,state->active_nonce,sequence,ack,4U);
    return pstep_handoff_write(fd,0x90U,sequence,ack,sizeof(ack),deadline);
}

static long pstep_step_status(struct pstep_control_state *state,int fd,uint32_t sequence,
    const struct timespec64 *deadline,long pid,int *reaped,int *status) {
    if(state->status_count>=2U || sequence!=8U+state->status_count)return -P260_EPROTO;
    unsigned code=0;struct timespec64 now={0};
    long rc=pstep_step_sample(state,pid,reaped,status,&code,&now);if(rc!=0)return rc;
    uint32_t elapsed=0;
    if(!state->status_count)state->first_status_time=now;
    else {
        if(now.tv_sec<state->first_status_time.tv_sec || (now.tv_sec==state->first_status_time.tv_sec && now.tv_nsec<state->first_status_time.tv_nsec))return -P260_EPROTO;
        elapsed=p328_elapsed_ms(&state->first_status_time,&now);if(elapsed>60000U)return -P260_EPROTO;
    }
    ++state->status_count; /* Consume before response; partial response is terminal. */
    uint8_t payload[44]={2U,(uint8_t)state->status_count,(uint8_t)state->step_requested,
        (uint8_t)state->step_started,(uint8_t)state->step_completed,
        (uint8_t)((state->step_pending?1U:0U)|(state->step_failed?2U:0U)|(!*reaped?4U:8U)),
        (uint8_t)(*reaped?((unsigned)*status>>8U)&255U:0U),(uint8_t)(*reaped?((unsigned)*status&127U):0U)};
    p328_store_le32(payload+8U,elapsed);
    pstep_handoff_tag(payload+12U,pstep_status_response_domain,state->active_nonce,sequence,payload,12U);
    return pstep_handoff_write(fd,0x8fU,sequence,payload,sizeof(payload),deadline);
}

static long pstep_step_checkpoint(struct pstep_control_state *state,long pid,int *reaped,int *status) {
    unsigned code=0;struct timespec64 now={0};
    long rc=pstep_step_sample(state,pid,reaped,status,&code,&now);if(rc!=0)return rc;
    return pstep_diag_emit(44U,5U,(long)code);
}
