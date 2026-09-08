/* P369: fixed wait evidence, separate from control availability.
 * A marker and an unreaped-child sample are not continuous liveness proof.
 */
static int p369_wait_line(const char *line,size_t length) {
    char expected[96];size_t used=0;
    static const char prefix[]="DISPLAY_WAIT_ENTERED run=";
    static const char suffix[]=" after_swaps=3";
    static const char hex[]="0123456789abcdef";
    memcpy(expected,prefix,sizeof(prefix)-1U);used=sizeof(prefix)-1U;
    for(unsigned i=0;i<16U;i++) {
        expected[used++]=hex[p328_run_id_bytes[i]>>4U];
        expected[used++]=hex[p328_run_id_bytes[i]&15U];
    }
    memcpy(expected+used,suffix,sizeof(suffix)-1U);used+=sizeof(suffix)-1U;
    return length==used && p260_bytes_equal(line,expected,used);
}

static long p369_note_wait(struct p369_control_state *state) {
    if(state->wait_marker || state->swaps!=3U) {
        state->wait_marker=2U; /* Duplicate/out-of-order marker cannot qualify. */
        return 0;
    }
    long rc=p241_clock_gettime(&state->wait_started);
    if(rc!=0)return rc;
    state->wait_marker=1U;
    return 0;
}

static long p369_wait_checkpoint(struct p369_control_state *state,long pid,
    int *reaped,int *status) {
    int alive=0;
    if(!*reaped) {
        long waited=sys_wait4(pid,status,WNOHANG);
        if(waited==0)alive=1;
        else if(waited==pid) {
            *reaped=1;
            long rc=p369_diag_child_status(*status);
            if(rc!=0)return rc;
        } else return waited<0?waited:-P260_EPROTO;
    }
    unsigned code=state->swaps; /* low four bits: observed submissions */
    if(state->wait_marker==1U) {
        struct timespec64 now={0};long rc=p241_clock_gettime(&now);
        if(rc!=0)return rc;
        if(now.tv_sec<state->wait_started.tv_sec ||
            (now.tv_sec==state->wait_started.tv_sec && now.tv_nsec<state->wait_started.tv_nsec))
            return -P260_EPROTO;
        code|=16U;
        if(p328_elapsed_ms(&state->wait_started,&now)>=2000U)code|=32U;
    }
    if(alive)code|=64U;
    return p369_diag_emit(44U,5U,(long)code);
}
