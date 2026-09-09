/* Text-only immutable frame: exact 1080x2340 ABGR scanout, CPU paint once.
 * Every new GEM is painted before its first scanout preparation/DMA mapping.
 */
static const uint8_t hud_glyphs[37][7]={
 {14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},
 {30,1,1,14,1,1,30},{2,6,10,18,31,2,2},{31,16,16,30,1,1,30},
 {14,16,16,30,17,17,14},{31,1,2,4,8,8,8},{14,17,17,14,17,17,14},
 {14,17,17,15,1,1,14},
 {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{14,17,16,16,16,17,14},
 {30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},
 {14,17,16,23,17,17,15},{17,17,17,31,17,17,17},{14,4,4,4,4,4,14},
 {7,2,2,2,2,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},
 {17,27,21,21,17,17,17},{17,25,21,19,17,17,17},{14,17,17,17,17,17,14},
 {30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},
 {15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},
 {17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},
 {17,17,10,4,4,4,4},{31,1,2,4,8,16,31},{0,4,4,0,4,4,0}
};
static unsigned hud_console_state;
static void hud_text(struct buffer *b,unsigned x,unsigned y,const char *text) {
    const unsigned scale=8;
    for(unsigned i=0;text[i] && i<24;i++) {
        unsigned c=(unsigned char)text[i],index=37;
        if(c>='0'&&c<='9')index=c-'0';else if(c>='A'&&c<='Z')index=10+c-'A';else if(c==':')index=36;
        if(index==37)continue;
        for(unsigned row=0;row<7;row++)for(unsigned column=0;column<5;column++)
            if(hud_glyphs[index][row]&(1U<<(4-column)))
                for(unsigned dy=0;dy<scale;dy++)for(unsigned dx=0;dx<scale;dx++) {
                    uint64_t px=(uint64_t)x+(uint64_t)i*6*scale+column*scale+dx;
                    uint64_t py=(uint64_t)y+row*scale+dy;
                    if(px<WIDTH && py<HEIGHT)b->pixels[py*(PITCH/4)+px]=0xffffffffU;
                }
    }
}
static void paint(struct buffer *b,unsigned seconds) {
    for(size_t i=0;i<BYTES/4;i++)b->pixels[i]=0xff000000U;
    hud_text(b,64,100,"NATIVE INIT");hud_text(b,64,220,"PID1: RUNNING");
    char uptime[32];
    if(seconds>999999U)snprintf(uptime,sizeof(uptime),"UPTIME: OVER 999999 S");
    else snprintf(uptime,sizeof(uptime),"UPTIME: %06u S",seconds);
    hud_text(b,64,340,uptime);
    hud_text(b,64,460,hud_console_state==0?"CONSOLE: READY":hud_console_state==1?"CONSOLE: BUSY":"CONSOLE: BLOCKED");
    hud_text(b,64,620,"STATUS AT LAST UPDATE");
    __sync_synchronize();
}
struct hud_snapshot {uint32_t magic,sequence,state,reserved;uint64_t uptime_ms;uint8_t run[16];};
_Static_assert(sizeof(struct hud_snapshot)==40,"snapshot wire size");
static uint32_t hud_last_sequence;
static uint64_t hud_last_uptime;
static int hud_snapshot_read(struct hud_snapshot *value) {
    /* recv(MSG_TRUNC) detects oversized SOCK_SEQPACKET messages. Drain a finite
     * batch so a slow renderer paints the newest snapshot, never a history. */
    int found=0;
    for(unsigned i=0;i<32;i++) {
        struct hud_snapshot next={0};ssize_t n=recv(STDIN_FILENO,&next,sizeof(next),MSG_DONTWAIT|MSG_TRUNC);
        if(n<0 && (errno==EAGAIN || errno==EINTR))break;
        require(n==(ssize_t)sizeof(next),"hud-snapshot-size-or-eof");
        require(next.magic==0x31445548U && next.reserved==0 && next.state<=2 &&
            next.sequence>hud_last_sequence && (!hud_last_sequence || next.uptime_ms>=hud_last_uptime),"hud-snapshot-order");
        char hex[33];for(unsigned j=0;j<16;j++)snprintf(hex+2*j,3,"%02x",next.run[j]);
        require(!strcmp(hex,run_id),"hud-snapshot-run");
        hud_last_sequence=next.sequence;hud_last_uptime=next.uptime_ms;*value=next;found=1;
        /* If the finite drain bound is exhausted, fail instead of painting
         * stale backlog or taking unbounded work. Parent sends at most 1/sec. */
        require(i<31,"hud-snapshot-backlog");
    }
    return found;
}
static struct hud_snapshot hud_wait_snapshot(void) {
    struct hud_snapshot value={0};int64_t start=now_ms();
    for(;;) {
        if(hud_snapshot_read(&value))return value;
        require(now_ms()-start<5000,"hud-parent-stale");
        struct timespec idle={.tv_nsec=10000000};
        if(nanosleep(&idle,NULL)<0 && errno!=EINTR)fail("hud-snapshot-wait");
    }
}
static void hud_flip_event(uint64_t token,uint32_t crtc) {
    int64_t start=now_ms();
    for(;;) {
        struct drm_event_vblank event={0};ssize_t n=read(fd,&event,sizeof(event));
        if(n==(ssize_t)sizeof(event)) {
            require(event.base.type==DRM_EVENT_FLIP_COMPLETE && event.base.length==sizeof(event) &&
                event.user_data==token && event.crtc_id==crtc,"hud-flip-event-binding");
            return;
        }
        require(n<0 && (errno==EAGAIN || errno==EINTR),"hud-flip-event-size");
        require(now_ms()-start<3000,"hud-flip-event-timeout");
        struct pollfd wait={.fd=fd,.events=POLLIN};int rc=poll(&wait,1,20);
        if(rc<0 && errno!=EINTR)fail("hud-flip-poll");
        if(rc>0)require(!(wait.revents&(POLLERR|POLLHUP|POLLNVAL)),"hud-flip-endpoint");
    }
}
static void hud_retire(struct buffer *old) {
    call(DRM_IOCTL_MODE_RMFB,&old->fb,"hud-retire-fb");
    if(munmap(old->pixels,BYTES))fail("hud-retire-map");
    struct drm_gem_close close={.handle=old->handle};call(DRM_IOCTL_GEM_CLOSE,&close,"hud-retire-gem");
}
static void hud_record(const struct hud_snapshot *value) {
    fprintf(stderr,"HUD_FRAME run=%s seq=%u uptime_ms=%" PRIu64 " state=%u event=matched visible=UNPROVED\n",
        run_id,value->sequence,value->uptime_ms,value->state);fflush(stderr);
}

static void hud_single_encoder(struct selection selected) {
    uint32_t encoder=0;struct drm_mode_get_connector conn={.connector_id=selected.connector};
    call(DRM_IOCTL_MODE_GETCONNECTOR,&conn,"hud-encoder-count");
    require(conn.count_encoders==1,"hud-one-connector-encoder");
    conn.count_modes=conn.count_props=0;conn.encoders_ptr=PTR(&encoder);
    call(DRM_IOCTL_MODE_GETCONNECTOR,&conn,"hud-encoder");
    require(conn.count_encoders==1 && encoder,"hud-selected-encoder");
    uint32_t ids[LIMIT];struct drm_mode_card_res resources={0};
    call(DRM_IOCTL_MODE_GETRESOURCES,&resources,"hud-all-encoder-count");
    require(resources.count_encoders>0 && resources.count_encoders<=LIMIT,"hud-encoder-bound");
    uint32_t count=resources.count_encoders;
    resources.count_crtcs=resources.count_connectors=resources.count_fbs=0;resources.encoder_id_ptr=PTR(ids);
    call(DRM_IOCTL_MODE_GETRESOURCES,&resources,"hud-all-encoders");
    require(resources.count_encoders==count,"hud-encoders-changed");
    unsigned found=0;
    for(unsigned i=0;i<count;i++) {
        struct drm_mode_get_encoder value={.encoder_id=ids[i]};
        call(DRM_IOCTL_MODE_GETENCODER,&value,"hud-encoder-binding");
        if(ids[i]==encoder){found++;require(!value.crtc_id || value.crtc_id==selected.crtc,"hud-selected-crtc");}
        else require(!value.crtc_id,"hud-foreign-encoder-active");
    }
    require(found==1,"hud-selected-encoder-unique");
}
