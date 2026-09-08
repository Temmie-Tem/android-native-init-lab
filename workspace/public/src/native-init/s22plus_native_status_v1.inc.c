/* P371 fixed observations. Sampling never consumes CONTROL or emits its checkpoint. */
static void p371_handoff_tag(uint8_t *,const char *,const uint8_t *,uint32_t,const uint8_t *,size_t);
static long p371_handoff_write(int,uint8_t,uint32_t,const uint8_t *,size_t,const struct timespec64 *);
static const char p371_status_request_domain[]="S22PLUS-FYG8-P371-STATUS-v1";
static const char p371_status_response_domain[]="S22PLUS-FYG8-P371-STATUS-REPLY-v1";

static long p371_sample_wait(struct p371_control_state *state,long pid,
    int *reaped,int *status,unsigned *code,struct timespec64 *now) {
    int alive=0;
    if(!*reaped) {
        long waited=sys_wait4(pid,status,WNOHANG);
        if(waited==0)alive=1;
        else if(waited==pid) {
            *reaped=1;
            long rc=p371_diag_child_status(*status);if(rc!=0)return rc;
        } else return waited<0?waited:-P260_EPROTO;
    }
    long rc=p241_clock_gettime(now);if(rc!=0)return rc;
    unsigned sampled=state->swaps;
    if(state->wait_marker==1U) {
        if(now->tv_sec<state->wait_started.tv_sec ||
            (now->tv_sec==state->wait_started.tv_sec && now->tv_nsec<state->wait_started.tv_nsec))
            return -P260_EPROTO;
        sampled|=16U;
        if(p328_elapsed_ms(&state->wait_started,now)>=2000U)sampled|=32U;
    }
    if(alive)sampled|=64U;
    *code=sampled;return 0;
}
static long p371_wait_checkpoint(struct p371_control_state *state,long pid,
    int *reaped,int *status) {
    unsigned code=0;struct timespec64 now={0};
    long rc=p371_sample_wait(state,pid,reaped,status,&code,&now);if(rc!=0)return rc;
    return p371_diag_emit(44U,5U,(long)code);
}
static long p371_status_reply(struct p371_control_state *state,int fd,
    uint32_t sequence,const struct timespec64 *deadline,long pid,int *reaped,int *status) {
    if(state->status_count>=2U || sequence!=8U+state->status_count)return -P260_EPROTO;
    unsigned code=0;struct timespec64 now={0};
    long rc=p371_sample_wait(state,pid,reaped,status,&code,&now);if(rc!=0)return rc;
    uint32_t elapsed=0;
    if(state->status_count==0U)state->first_status_time=now;
    else {
        if(now.tv_sec<state->first_status_time.tv_sec ||
            (now.tv_sec==state->first_status_time.tv_sec && now.tv_nsec<state->first_status_time.tv_nsec))
            return -P260_EPROTO;
        elapsed=p328_elapsed_ms(&state->first_status_time,&now);
        if(elapsed>60000U)return -P260_EPROTO;
    }
    state->status_count++; /* Consume before the response; never retry a partial write. */
    uint8_t payload[40]={1U,(uint8_t)state->status_count,(uint8_t)(code&15U),
        (uint8_t)((code>>4U)|(*reaped?8U:0U))};
    p328_store_le32(payload+4U,elapsed);
    p371_handoff_tag(payload+8U,p371_status_response_domain,state->active_nonce,sequence,payload,8U);
    return p371_handoff_write(fd,0x8fU,sequence,payload,sizeof(payload),deadline);
}
