/* Fixed P364 progress witnesses. No caller paths, device data or addresses.
 * An ENTER is fully sent before its operation. A failed write is sticky and
 * forecloses every later operation except existing local resource cleanup. */
#define P364_DIAG_FRAME 0x8bU
#define P364_DIAG_ENTER 0U
#define P364_DIAG_RETURN 1U
#define P364_DIAG_CHILD_EXIT 2U
#define P364_DIAG_CHILD_SIGNAL 3U
#define P364_DIAG_TERMINAL 4U
#define P364_DIAG_MAX_FRAMES 48U
static const char p364_diag_domain[]="S22PLUS-FYG8-P364-PROGRESS-v1";
struct p364_diagnostic_state {
    int fd, active, broken, terminal, child_reported;
    uint32_t ordinal;
    long first_error;
    uint8_t nonce[P328_NONCE_SIZE];
    struct timespec64 deadline;
};
static struct p364_diagnostic_state p364_diagnostic;

static long p364_diag_start(int fd,const uint8_t *nonce) {
    if(p364_diagnostic.active) return -P260_EPROTO;
    p364_diagnostic.active=1;p364_diagnostic.fd=fd;
    memcpy(p364_diagnostic.nonce,nonce,P328_NONCE_SIZE);
    long rc=p282_deadline_after(60LL,&p364_diagnostic.deadline);
    if(rc!=0) p364_diagnostic.broken=1;
    return rc;
}

static long p364_diag_emit(uint16_t stage,uint8_t event,long code) {
    struct p364_diagnostic_state *s=&p364_diagnostic;
    if(!s->active || s->broken || s->terminal || s->ordinal>=P364_DIAG_MAX_FRAMES)
        return -P260_EPROTO;
    if(code < -4095L || code > 255L) {s->broken=1;return -P260_EPROTO;}
    uint8_t wire[P328_HEADER_SIZE+40U]={P328_MAGIC_0,P328_MAGIC_1,P328_MAGIC_2,P328_MAGIC_3,P328_FRAME_VERSION,P364_DIAG_FRAME};
    uint32_t sequence=0x100U+s->ordinal;
    p328_store_le16(wire+6U,40U);p328_store_le32(wire+8U,sequence);
    p328_store_le16(wire+P328_HEADER_SIZE,stage);
    wire[P328_HEADER_SIZE+2U]=event;
    p328_store_le32(wire+P328_HEADER_SIZE+4U,(uint32_t)code);
    p328_hmac_message(wire+P328_HEADER_SIZE+8U,p364_diag_domain,
        sizeof(p364_diag_domain)-1U,p328_run_id_bytes,s->nonce,sequence,1,
        wire+P328_HEADER_SIZE,8U);
    p328_store_le32(wire+12U,p328_frame_crc(wire,wire+P328_HEADER_SIZE,40U));
    size_t used=0U;
    while(used<sizeof(wire)) {
        if(p282_deadline_expired(&s->deadline)) {s->broken=1;return -ETIMEDOUT;}
        long n=sys_write(s->fd,wire+used,sizeof(wire)-used);
        if(n==-EAGAIN || n==-P260_EINTR) {p282_poll_delay();continue;}
        if(n<=0 || (size_t)n>sizeof(wire)-used) {s->broken=1;return n<0?n:-EIO;}
        used+=(size_t)n;
    }
    ++s->ordinal;
    if(event==P364_DIAG_TERMINAL) s->terminal=1;
    return 0;
}
static long p364_diag_enter(uint16_t stage) {
    return p364_diag_emit(stage,P364_DIAG_ENTER,0);
}
static long p364_diag_result(uint16_t stage,long original) {
    if(original<0 && !p364_diagnostic.first_error) p364_diagnostic.first_error=original;
    long sent=p364_diag_emit(stage,P364_DIAG_RETURN,original);
    return original?original:sent;
}
static void p364_diag_finish(long original) {
    if(p364_diagnostic.first_error) original=p364_diagnostic.first_error;
    if(original==0) original=-P260_EPROTO;
    if(p364_diagnostic.active && !p364_diagnostic.broken && !p364_diagnostic.terminal)
        (void)p364_diag_emit(255U,P364_DIAG_TERMINAL,original);
}
static long p364_diag_child_status(int status) {
    if(p364_diagnostic.child_reported) return 0;
    p364_diagnostic.child_reported=1;
    unsigned int signal=(unsigned int)status&0x7fU;
    return p364_diag_emit(43U,signal?P364_DIAG_CHILD_SIGNAL:P364_DIAG_CHILD_EXIT,
        signal?(long)signal:(long)(((unsigned int)status>>8)&0xffU));
}

static long p364_insert_module(const struct p364_return_module *module) {
    size_t index=(size_t)(module-p364_return_modules);
    if(index>=sizeof(p364_return_modules)/sizeof(p364_return_modules[0])) return -P260_EPROTO;
    uint16_t stage=(uint16_t)(10U+3U*index);
    long rc=p364_diag_enter(stage);if(rc!=0)return rc;
    long fd=sys_openat(module->path,O_RDONLY|O_CLOEXEC|0400000,0);
    if(fd<0) return p364_diag_result(stage,fd);
    struct s22_p241_kernel_stat metadata={0};
    rc=syscall6(80,fd,(long)(uintptr_t)&metadata,0,0,0,0);
    if(rc==0 && (metadata.st_mode!=0100400U || metadata.st_uid || metadata.st_gid ||
        metadata.st_nlink!=1U || metadata.st_size!=(int64_t)module->size)) rc=-P260_EPROTO;
    struct s22plus_max77705_runtime_sha256 context;
    s22plus_max77705_runtime_sha256_init(&context);
    uint8_t bytes[4096],hash[32];uint64_t used=0U;
    while(rc==0) {
        long n=sys_read((int)fd,bytes,sizeof(bytes));
        if(n<0) {rc=n;break;}
        if(n==0) break;
        if((size_t)n>sizeof(bytes) || (uint64_t)n>module->size-used) {rc=-P260_EPROTO;break;}
        s22plus_max77705_runtime_sha256_update(&context,bytes,(size_t)n);used+=(uint64_t)n;
    }
    s22plus_max77705_runtime_sha256_final(&context,hash);
    if(rc==0 && (used!=module->size || !p328_constant_time_equal(hash,module->hash,32U))) rc=-P260_EPROTO;
    if(rc==0) rc=syscall6(62,fd,0,0,0,0,0);
    rc=p364_diag_result(stage,rc);
    if(rc==0) rc=p364_diag_enter(stage+1U);
    if(rc==0) rc=p364_diag_result(stage+1U,p241_finit_module((int)fd,module->params));
    if(rc!=0) {(void)sys_close((int)fd);return rc;}
    rc=p364_diag_enter(stage+2U);
    if(rc!=0) {(void)sys_close((int)fd);return rc;}
    return p364_diag_result(stage+2U,sys_close((int)fd));
}
