/* P370: one acknowledged pre-CONTROL handoff. Never restart the child or budget. */
static long p370_kernel_boot_id(uint8_t output[32]);
static const char p370_detach_domain[]="S22PLUS-FYG8-P370-DETACH-v1";
static const char p370_detach_ack_domain[]="S22PLUS-FYG8-P370-DETACH-ACK-v1";
static const char p370_resume_open_domain[]="S22PLUS-FYG8-P370-RESUME-OPEN-v1";
static const char p370_resume_challenge_domain[]="S22PLUS-FYG8-P370-RESUME-CHALLENGE-v1";
static const char p370_resume_auth_domain[]="S22PLUS-FYG8-P370-RESUME-AUTH-v1";
static const char p370_resume_ack_domain[]="S22PLUS-FYG8-P370-RESUME-ACK-v1";

static void p370_handoff_tag(uint8_t *tag,const char *domain,const uint8_t *nonce,
    uint32_t sequence,const uint8_t *body,size_t size) {
    p328_hmac_message(tag,domain,cstr_len(domain),p328_run_id_bytes,nonce,
        sequence,1,body,size);
}
static long p370_handoff_write(int fd,uint8_t kind,uint32_t sequence,
    const uint8_t *payload,size_t size,const struct timespec64 *deadline) {
    if(size>100U)return -P260_EOVERFLOW;
    uint8_t wire[P328_HEADER_SIZE+100U]={0};
    wire[0]=P328_MAGIC_0;wire[1]=P328_MAGIC_1;wire[2]=P328_MAGIC_2;wire[3]=P328_MAGIC_3;
    wire[4]=P328_FRAME_VERSION;wire[5]=kind;p328_store_le16(wire+6U,(uint16_t)size);
    p328_store_le32(wire+8U,sequence);memcpy(wire+P328_HEADER_SIZE,payload,size);
    p328_store_le32(wire+12U,p328_frame_crc(wire,wire+P328_HEADER_SIZE,(uint16_t)size));
    size_t used=0;
    while(used<P328_HEADER_SIZE+size) {
        if(p282_deadline_expired(deadline))return -ETIMEDOUT;
        long n=sys_write(fd,wire+used,P328_HEADER_SIZE+size-used);
        if(n==-EAGAIN || n==-P260_EINTR){p282_poll_delay();continue;}
        if(n<=0 || (size_t)n>P328_HEADER_SIZE+size-used)return n<0?n:-EIO;
        used+=(size_t)n;
    }
    return 0;
}
static long p370_handoff_status(int fd,uint8_t kind,uint32_t sequence,
    const char *domain,const uint8_t *nonce,const uint8_t body[4],
    const struct timespec64 *deadline) {
    uint8_t payload[36];memcpy(payload,body,4U);
    p370_handoff_tag(payload+4U,domain,nonce,sequence,body,4U);
    return p370_handoff_write(fd,kind,sequence,payload,sizeof(payload),deadline);
}
static void p370_reset_request(struct p370_control_state *state) {
    state->header_used=state->payload_used=0U;
    memset(state->header,0,sizeof(state->header));memset(state->payload,0,sizeof(state->payload));
}
static long p370_try_control(struct p370_control_state *state,int fd,
    const uint8_t *initial_nonce,const struct timespec64 *deadline,long pid,int *reaped,int *status) {
    (void)initial_nonce;
    if(state->consumed || p282_deadline_expired(deadline))return -ETIMEDOUT;
    if(!state->ready || state->retained_pid!=pid || pid<=0)return -P260_EPROTO;
    if(state->handoff_phase==1U && !p282_deadline_expired(&state->quiet_until))return 0;
    unsigned phase=state->handoff_phase;
    if(phase>3U)return -P260_EPROTO;
    uint8_t expected_kind=phase==0U?7U:phase==1U?8U:phase==2U?9U:P370_FRAME_CONTROL;
    uint32_t expected_sequence=5U+phase;
    uint8_t *dest;size_t remaining;
    if(state->header_used<P328_HEADER_SIZE) {
        dest=state->header+state->header_used;remaining=P328_HEADER_SIZE-state->header_used;
    } else {dest=state->payload+state->payload_used;remaining=36U-state->payload_used;}
    long n=sys_read(fd,dest,remaining);
    if(n==-EAGAIN || n==-P260_EINTR)return 0;
    /* Even during handoff EOF/EIO/ENODEV/EPIPE are terminal, never retried. */
    if(n<=0 || (size_t)n>remaining)return n<0?n:-EIO;
    if(state->header_used<P328_HEADER_SIZE) {
        state->header_used+=(uint16_t)n;if(state->header_used<P328_HEADER_SIZE)return 0;
        const uint8_t *h=state->header;
        if(h[0]!=P328_MAGIC_0 || h[1]!=P328_MAGIC_1 || h[2]!=P328_MAGIC_2 || h[3]!=P328_MAGIC_3 ||
            h[4]!=P328_FRAME_VERSION || h[5]!=expected_kind || p328_load_le16(h+6U)!=36U ||
            p328_load_le32(h+8U)!=expected_sequence)return -P260_EPROTO;
        return 0;
    }
    state->payload_used+=(uint16_t)n;if(state->payload_used<36U)return 0;
    const uint8_t *body=state->payload;uint8_t tag[32];
    if(body[0]!=1U || body[1] || body[2] || body[3] ||
        p328_load_le32(state->header+12U)!=p328_frame_crc(state->header,body,36U))return -P260_EPROTO;
    const char *domain=phase==0U?p370_detach_domain:phase==1U?p370_resume_open_domain:
        phase==2U?p370_resume_auth_domain:p370_control_domain;
    const uint8_t *nonce=phase==2U?state->resume_nonce:state->active_nonce;
    p370_handoff_tag(tag,domain,nonce,expected_sequence,body,4U);
    if(!p328_constant_time_equal(body+4U,tag,32U))return -P260_EPROTO;
    if(phase==0U) {
        if(state->handoff_used)return -P260_EPROTO;
        state->handoff_used=1U;state->handoff_phase=1U; /* Before ACK, never reset. */
        const uint8_t ack[4]={1U,(uint8_t)state->handoff_used,
            (uint8_t)(state->retained_pid==pid && pid>0),(uint8_t)state->consumed};
        long rc=p370_handoff_status(fd,0x8cU,5U,p370_detach_ack_domain,state->active_nonce,ack,deadline);
        if(rc!=0)return rc;
        rc=p241_clock_gettime(&state->quiet_until);if(rc!=0)return rc;
        state->quiet_until.tv_sec+=2LL;
        p370_reset_request(state);return 0;
    }
    if(phase==1U) {
        if(state->handoff_used!=1U)return -P260_EPROTO;
        long rc=p328_getrandom_nonce(state->resume_nonce);if(rc!=0)return rc;
        if(p328_constant_time_equal(state->resume_nonce,state->active_nonce,32U))return -P260_EPROTO;
        rc=p370_kernel_boot_id(state->resume_boot);if(rc!=0)return rc;
        uint8_t challenge[100];memcpy(challenge,state->resume_nonce,32U);
        memcpy(challenge+32U,state->resume_boot,32U);
        challenge[64]=1U;challenge[65]=(uint8_t)state->handoff_used;
        challenge[66]=(uint8_t)(state->retained_pid==pid && pid>0);challenge[67]=(uint8_t)state->consumed;
        p370_handoff_tag(challenge+68U,p370_resume_challenge_domain,state->active_nonce,6U,challenge,68U);
        state->handoff_phase=2U;p370_reset_request(state);
        return p370_handoff_write(fd,0x8dU,6U,challenge,sizeof(challenge),deadline);
    }
    if(phase==2U) {
        memcpy(state->active_nonce,state->resume_nonce,32U);
        memcpy(p370_diagnostic.nonce,state->active_nonce,32U);
        state->handoff_phase=3U;p370_reset_request(state);
        const uint8_t ack[4]={1U,(uint8_t)state->handoff_used,
            (uint8_t)(state->retained_pid==pid && pid>0),(uint8_t)state->consumed};
        return p370_handoff_status(fd,0x8eU,7U,p370_resume_ack_domain,state->active_nonce,ack,deadline);
    }
    state->consumed=1U;
    long sampled=p370_wait_checkpoint(state,pid,reaped,status);if(sampled!=0)return sampled;
    p370_diagnostic.terminal=1;
    const uint8_t accepted[4]={P370_LIVE_MODE,0U,0U,0U};
    long rc=p370_write_status(fd,P370_FRAME_CONTROL_ACK,p370_ack_domain,state->active_nonce,accepted,deadline);
    if(rc!=0)return rc;
    if(p282_deadline_expired(deadline))return -ETIMEDOUT;
    rc=syscall6(142,0xfee1deadUL,672274793UL,0xa1b2c3d4UL,(long)(uintptr_t)"download",0,0);
    return rc<0?rc:-EIO;
}
