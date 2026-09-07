/* P363 supervisor-owned fixed return control. No caller-supplied command.
 * Included in the freestanding runtime after its SHA/HMAC/frame primitives.
 * The host journal must consume its intent before sending any CONTROL byte.
 * Readiness reports stock insertion and observed swap count, never visibility
 * or recovery. An ACK proves acceptance only. Any returned syscall parks.
 */
#define P363_FRAME_CONTROL 6U
#define P363_FRAME_CONTROL_READY 0x89U
#define P363_FRAME_CONTROL_ACK 0x8aU
#define P363_CONTROL_SEQUENCE 5U
#define P363_CONTROL_PAYLOAD 36U
#define P363_MODE_DOWNLOAD 1U
#define P363_MODE_RESTART 2U
/* Ordinary restart exists for H0 qualification only; first live candidate is
 * immutable DOWNLOAD. Changing this value requires a fresh candidate/review. */
#define P363_LIVE_MODE P363_MODE_DOWNLOAD
static const char p363_control_domain[] = "S22PLUS-FYG8-P363-CONTROL-v1";
static const char p363_ready_domain[] = "S22PLUS-FYG8-P363-CONTROL-READY-v1";
static const char p363_ack_domain[] = "S22PLUS-FYG8-P363-CONTROL-ACK-v1";

struct p363_control_state {
    uint8_t header[P328_HEADER_SIZE], payload[P363_CONTROL_PAYLOAD];
    uint16_t header_used, payload_used;
    unsigned int consumed, ready, swaps, child_exited, line_used, line_overflow;
    uint32_t child_bytes;
    char line[512];
};

static void p363_control_tag(uint8_t *tag, const char *domain,
    const uint8_t *nonce, const uint8_t body[4]) {
    p328_hmac_message(tag, domain, cstr_len(domain), p328_run_id_bytes,
        nonce, P363_CONTROL_SEQUENCE, 1, body, 4U);
}

static long p363_write_status(int fd, uint8_t kind, const char *domain,
    const uint8_t *nonce, const uint8_t body[4], const struct timespec64 *deadline) {
    uint8_t wire[P328_HEADER_SIZE + P363_CONTROL_PAYLOAD] = {0};
    wire[0]=P328_MAGIC_0; wire[1]=P328_MAGIC_1;
    wire[2]=P328_MAGIC_2; wire[3]=P328_MAGIC_3;
    wire[4]=P328_FRAME_VERSION; wire[5]=kind;
    p328_store_le16(wire+6U, P363_CONTROL_PAYLOAD);
    p328_store_le32(wire+8U, P363_CONTROL_SEQUENCE);
    memcpy(wire+P328_HEADER_SIZE, body, 4U);
    p363_control_tag(wire+P328_HEADER_SIZE+4U, domain, nonce, body);
    p328_store_le32(wire+12U, p328_frame_crc(wire,
        wire+P328_HEADER_SIZE, P363_CONTROL_PAYLOAD));
    size_t used=0U;
    while (used<sizeof(wire)) {
        if (p282_deadline_expired(deadline)) return -ETIMEDOUT;
        long n=sys_write(fd,wire+used,sizeof(wire)-used);
        if (n == -EAGAIN || n == -P260_EINTR) {p282_poll_delay();continue;}
        if (n<=0 || (size_t)n>sizeof(wire)-used) return n<0?n:-EIO;
        used+=(size_t)n;
    }
    return 0;
}

static int p363_swap_line(const char *line, size_t length, unsigned int ordinal) {
    char expected[160]; size_t used=0U;
    static const char prefix[]="DISPLAY_SWAP_SUBMITTED run=";
    static const char middle[]=" swap=";
    static const char suffix[]=" ioctl_return=0 visible=UNPROVED";
    static const char hex[]="0123456789abcdef";
    memcpy(expected,prefix,sizeof(prefix)-1U);used=sizeof(prefix)-1U;
    for(unsigned int i=0U;i<16U;++i) {
        expected[used++]=hex[p328_run_id_bytes[i]>>4U];
        expected[used++]=hex[p328_run_id_bytes[i]&15U];
    }
    memcpy(expected+used,middle,sizeof(middle)-1U);used+=sizeof(middle)-1U;
    if(ordinal==10U) {expected[used++]='1';expected[used++]='0';}
    else if(ordinal>=1U && ordinal<=9U) expected[used++]=(char)('0'+ordinal);
    else return 0;
    memcpy(expected+used,suffix,sizeof(suffix)-1U);used+=sizeof(suffix)-1U;
    return length==used && p260_bytes_equal(line,expected,used);
}

static long p363_child_output(struct p363_control_state *state,
    const uint8_t *bytes,size_t size) {
    if(size>131072U-state->child_bytes) return -P260_EOVERFLOW;
    state->child_bytes+=(uint32_t)size;
    if(state->ready) return 0; /* Freeze the signed readiness milestone. */
    for(size_t i=0U;i<size;++i) {
        if(bytes[i]=='\n') {
            if(!state->line_overflow && state->swaps<10U &&
                p363_swap_line(state->line,state->line_used,state->swaps+1U))
                ++state->swaps;
            state->line_used=state->line_overflow=0U;
        } else if(state->line_used<sizeof(state->line))
            state->line[state->line_used++]=(char)bytes[i];
        else state->line_overflow=1U;
    }
    return 0;
}

/* One finite read per call, with the original absolute child deadline. Partial
 * and flooded input cannot keep the supervisor inside the parser indefinitely. */
static long p363_try_control(struct p363_control_state *state,int fd,
    const uint8_t *nonce,const struct timespec64 *deadline) {
    if(state->consumed || p282_deadline_expired(deadline)) return -ETIMEDOUT;
    uint8_t *dest; size_t remaining;
    if(state->header_used<P328_HEADER_SIZE) {
        dest=state->header+state->header_used;
        remaining=P328_HEADER_SIZE-state->header_used;
    } else {
        dest=state->payload+state->payload_used;
        remaining=P363_CONTROL_PAYLOAD-state->payload_used;
    }
    long n=sys_read(fd,dest,remaining);
    if(n==-EAGAIN || n==-P260_EINTR) return 0;
    if(n<=0 || (size_t)n>remaining) return n<0?n:-EIO;
    if(!state->ready) return -P260_EPROTO;
    if(state->header_used<P328_HEADER_SIZE) {
        state->header_used+=(uint16_t)n;
        if(state->header_used<P328_HEADER_SIZE) return 0;
        const uint8_t *h=state->header;
        if(h[0]!=P328_MAGIC_0 || h[1]!=P328_MAGIC_1 || h[2]!=P328_MAGIC_2 ||
            h[3]!=P328_MAGIC_3 || h[4]!=P328_FRAME_VERSION ||
            h[5]!=P363_FRAME_CONTROL || p328_load_le16(h+6U)!=P363_CONTROL_PAYLOAD ||
            p328_load_le32(h+8U)!=P363_CONTROL_SEQUENCE) return -P260_EPROTO;
        return 0;
    }
    state->payload_used+=(uint16_t)n;
    if(state->payload_used<P363_CONTROL_PAYLOAD) return 0;
    const uint8_t *body=state->payload;
    uint8_t tag[P328_AUTH_TAG_SIZE];
    if(body[0]!=P363_LIVE_MODE || body[1] || body[2] || body[3] ||
        p328_load_le32(state->header+12U)!=p328_frame_crc(state->header,body,P363_CONTROL_PAYLOAD))
        return -P260_EPROTO;
    p363_control_tag(tag,p363_control_domain,nonce,body);
    if(!p328_constant_time_equal(body+4U,tag,sizeof(tag))) return -P260_EPROTO;
    state->consumed=1U; /* Before ACK and every privileged effect. Never reset. */
    const uint8_t accepted[4]={P363_LIVE_MODE,0U,(uint8_t)state->swaps,(uint8_t)state->child_exited};
    long rc=p363_write_status(fd,P363_FRAME_CONTROL_ACK,p363_ack_domain,
        nonce,accepted,deadline);
    /* If ACK cannot be completely written, do not call reboot. The host still
     * treats occurrence as unknown and must never repeat the request. */
    if(rc!=0) return rc;
    if(p282_deadline_expired(deadline)) return -ETIMEDOUT;
    /* The immutable mode maps to exactly one Linux reboot syscall. No fallback
     * on return, no argument from the renderer, and no arbitrary command text. */
    if(P363_LIVE_MODE==P363_MODE_DOWNLOAD)
        rc=syscall6(142,0xfee1deadUL,672274793UL,0xa1b2c3d4UL,
            (long)(uintptr_t)"download",0,0);
    else
        rc=syscall6(142,0xfee1deadUL,672274793UL,0x01234567UL,0,0,0);
    return rc<0?rc:-EIO;
}

/* BOOT-v2 wire bytes are SHA256 of exactly 36 lowercase canonical UUID ASCII
 * bytes from the kernel, without newline; session RNG remains independent. */
static long p363_kernel_boot_id(uint8_t digest[P335_BOOT_ID_SIZE]) {
    uint8_t uuid[38];size_t used=0U;
    long fd=sys_openat("/proc/sys/kernel/random/boot_id",O_RDONLY|O_CLOEXEC,0);
    if(fd<0) return fd;
    long rc=0;
    while(used<sizeof(uuid)) {
        long n=sys_read((int)fd,uuid+used,sizeof(uuid)-used);
        if(n<0) {rc=n;break;}
        if(n==0) break;
        if((size_t)n>sizeof(uuid)-used) {rc=-EIO;break;}
        used+=(size_t)n;
    }
    long closed=sys_close((int)fd);
    if(rc || closed) return rc?rc:closed;
    if(used!=37U || uuid[36]!='\n') return -P260_EPROTO;
    for(size_t i=0U;i<36U;++i) {
        if(i==8U||i==13U||i==18U||i==23U) {if(uuid[i]!='-')return -P260_EPROTO;}
        else if(!((uuid[i]>='0'&&uuid[i]<='9')||(uuid[i]>='a'&&uuid[i]<='f')))
            return -P260_EPROTO;
    }
    struct s22plus_max77705_runtime_sha256 context;
    s22plus_max77705_runtime_sha256_init(&context);
    s22plus_max77705_runtime_sha256_update(&context,uuid,36U);
    s22plus_max77705_runtime_sha256_final(&context,digest);
    return 0;
}
