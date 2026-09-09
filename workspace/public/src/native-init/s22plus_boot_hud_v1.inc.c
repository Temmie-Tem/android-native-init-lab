/* PID1 HUD ownership is separate from the command process group.
 * One bounded nonblocking diagnostic read and one disposable snapshot per tick.
 * Never wait for renderer/DRM cleanup; no restart and no parent DRM operations.
 */
#define HUD1_LIMIT 131072U
/* Exact target ARM64 fcntl UAPI, including its O_NOFOLLOW override. */
#define HUD1_LOG_FLAGS (00000001|00000100|00000200|0100000|02000000)
struct hud1_state {
    long pid;
    int input,output,log,reaped,status,signalled,failed,wait_unknown;
    uint32_t sequence,bytes;
    uint64_t last;
};
static void hud1_close(int *fd) {if(*fd>=0)(void)sys_close(*fd);*fd=-1;}
static void hud1_log(struct hud1_state *h,const void *p,unsigned n) {
    if(h->log<0)return;
    if(n>HUD1_LIMIT-h->bytes || sys_write(h->log,p,n)!=(long)n) {
        h->failed=1;hud1_close(&h->log);return;
    }
    h->bytes+=n;
}
static void hud1_number(struct hud1_state *h,const char *prefix,unsigned long n) {
    char line[96],digits[24];unsigned used=0,count=0;
    while(prefix[used]){line[used]=prefix[used];++used;}
    do {digits[count++]=(char)('0'+n%10);n/=10;}while(n && count<sizeof(digits));
    while(count){line[used++]=digits[--count];}
    line[used++]='\n';hud1_log(h,line,used);
}
static void hud1_stop(struct hud1_state *h) {
    hud1_close(&h->input);
    if(h->pid>0 && !h->reaped && !h->wait_unknown && !h->signalled) {
        h->signalled=1;long rc=syscall6(129,h->pid,9,0,0,0,0);
        hud1_number(h,rc<0?"HUD_SIGNAL_ERROR ":"HUD_SIGNAL_ATTEMPT ",rc<0?(unsigned long)-rc:(unsigned long)h->pid);
    }
}
static void hud1_start(struct hud1_state *h) {
    int pair[2]={-1,-1},out[2]={-1,-1};
    h->input=h->output=h->log=-1;
    long rc=sys_openat("/s22-root-work/hud.log",HUD1_LOG_FLAGS,0400);
    if(rc<0){h->failed=1;return;}h->log=(int)rc;
    /* ARM64 socketpair(199), AF_UNIX=1, SOCK_SEQPACKET=5.
     * SOCK_NONBLOCK/O_NONBLOCK and SOCK_CLOEXEC/O_CLOEXEC share UAPI values. */
    rc=syscall6(199,1,5|O_NONBLOCK|O_CLOEXEC,0,(long)(uintptr_t)pair,0,0);
    if(rc<0)goto fail;
    rc=sys_pipe2(out,O_NONBLOCK|O_CLOEXEC);if(rc<0)goto fail;
    if(pair[0]<=2 || pair[1]<=2 || out[0]<=2 || out[1]<=2){rc=-P260_EPROTO;goto fail;}
    long pid=sys_clone();if(pid<0){rc=pid;goto fail;}
    if(!pid) {
        if(p328_setsid()<0)sys_exit(126);
        if(p328_dup_to(pair[1],0)!=0 || p328_dup_to(out[1],1)!=1 || p328_dup_to(out[1],2)!=2)sys_exit(126);
        /* Keep diagnostic writes nonblocking. No child can backpressure PID1. */
        if(syscall6(436,3,0xffffffffU,0,0,0,0)<0)sys_exit(126);
        char *argv[]={"/s22-display","--supervised-drm",(char *)rc1_run_id_ascii,NULL};
        char *env[]={"PATH=/bin","HOME=/","TERM=dumb",NULL};
        (void)sys_execve("/s22-display",argv,env);sys_exit(126);
    }
    h->pid=pid;h->input=pair[0];h->output=out[0];
    (void)sys_close(pair[1]);(void)sys_close(out[1]);
    hud1_number(h,"HUD_START ",(unsigned long)pid);return;
fail:
    for(unsigned i=0;i<2;i++){if(pair[i]>=0)(void)sys_close(pair[i]);if(out[i]>=0)(void)sys_close(out[i]);}
    h->failed=1;hud1_number(h,"HUD_START_ERROR ",(unsigned long)-rc);
}
static void hud1_tick(struct hud1_state *h,uint64_t now,unsigned console_state) {
    if(h->pid<=0)return;
    if(h->output>=0) {
        uint8_t bytes[512];long n=sys_read(h->output,bytes,sizeof(bytes));
        if(n>0)hud1_log(h,bytes,(unsigned)n);
        else if(n==0)hud1_close(&h->output);
        else if(n!=-EAGAIN && n!=-P260_EINTR){h->failed=1;hud1_close(&h->output);}
    }
    if(!h->reaped && !h->wait_unknown) {
        long n=sys_wait4(h->pid,&h->status,WNOHANG);
        if(n==h->pid){h->reaped=1;hud1_number(h,"HUD_EXIT ",(unsigned)h->status);hud1_close(&h->input);}
        else if(n!=0){h->failed=1;h->wait_unknown=1;hud1_number(h,"HUD_WAIT_ERROR ",(unsigned long)(n<0?-n:n));}
    }
    if(h->failed){hud1_stop(h);return;}
    if(h->input<0 || h->reaped || h->signalled)return;
    if(h->sequence && now-h->last<1000U)return;
    h->last=now;++h->sequence;
    uint8_t snapshot[40]={0};
    p328_store_le32(snapshot,0x31445548U);p328_store_le32(snapshot+4,h->sequence);
    p328_store_le32(snapshot+8,console_state);
    for(unsigned i=0;i<8;i++)snapshot[16+i]=(uint8_t)(now>>(8U*i));
    memcpy(snapshot+24,p328_run_id_bytes,16);
    /* ARM64 sendto(206), MSG_NOSIGNAL=0x4000. EAGAIN drops this snapshot.
     * Do not change SIGPIPE disposition inherited by command children. */
    long n=syscall6(206,h->input,(long)(uintptr_t)snapshot,sizeof(snapshot),0x4000,0,0);
    if(n!=(long)sizeof(snapshot) && n!=-EAGAIN && n!=-P260_EINTR){h->failed=1;hud1_number(h,"HUD_INPUT_ERROR ",(unsigned long)(n<0?-n:n));hud1_stop(h);}
}
