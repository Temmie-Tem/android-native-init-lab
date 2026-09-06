/* H0 fixed DRM renderer. No live lane or generic display utility.
 * Exact FYG8 vendor UAPI; CPU WC buffers, no GPU submission or input fences.
 * A supervisor must own the overall deadline and physical recovery. Neither
 * poll deadlines nor process signals can recover a wedged kernel modeset.
 */
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#ifndef __user
#define __user /* UAPI sparse annotation, erased by headers_install. */
#endif
#include <drm.h>
#include <drm_mode.h>
#include <drm_fourcc.h>
#include <msm_drm.h>

#define LIMIT 128
#define WIDTH 1080U
#define HEIGHT 2340U
#define PITCH (4U * ((WIDTH + 31U) & ~31U))
#define BYTES ((size_t)PITCH * HEIGHT)
#define FRAMES 10U
#define PTR(x) ((__u64)(uintptr_t)(x))
static int fd = -1;
static const char *run_id;
static void fail(const char *stage) {
    fprintf(stderr, "DISPLAY_FAIL stage=%s errno=%d\n", stage, errno);
    /* No follow-up modeset after uncertainty. Closing may itself block in the
     * kernel: the external supervisor must retain recovery ownership. */
    _exit(1);
}
static void require(int ok, const char *stage) {
    if (!ok) { errno = EPROTO; fail(stage); }
}
static void call(unsigned long op, void *arg, const char *stage) {
    if (ioctl(fd, op, arg) < 0) fail(stage); /* Never replay a possible effect. */
}
static int64_t now_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) fail("clock");
    return (int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
struct props { uint32_t id[LIMIT]; uint64_t value[LIMIT]; uint32_t n; };
static struct props get_props(uint32_t obj, uint32_t type) {
    struct props p = {0};
    struct drm_mode_obj_get_properties q = {.obj_id=obj, .obj_type=type};
    call(DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &q, "properties-count");
    require(q.count_props && q.count_props <= LIMIT, "properties-bound");
    p.n = q.count_props; q.props_ptr=PTR(p.id); q.prop_values_ptr=PTR(p.value);
    call(DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &q, "properties");
    require(q.count_props == p.n, "properties-changed");
    return p;
}
static uint32_t property(struct props *p, const char *name, uint64_t *value) {
    uint32_t found=0;
    for (uint32_t i=0; i<p->n; ++i) {
        struct drm_mode_get_property q={.prop_id=p->id[i]};
        call(DRM_IOCTL_MODE_GETPROPERTY, &q, "property-name");
        require(memchr(q.name, 0, sizeof(q.name)) != NULL, "property-name-bound");
        if (!strcmp(q.name,name)) {
            require(!found, "duplicate-property"); found=q.prop_id;
            if (value) *value=p->value[i];
        }
    }
    require(found != 0, "missing-property"); return found;
}
struct selection { uint32_t connector, crtc, plane; struct drm_mode_modeinfo mode; };
static struct selection select_display(void) {
    struct selection s={0};
    uint32_t crtcs[LIMIT], connectors[LIMIT];
    struct drm_mode_card_res r={0};
    call(DRM_IOCTL_MODE_GETRESOURCES,&r,"resources-count");
    require(r.count_crtcs && r.count_crtcs<=32 && r.count_connectors && r.count_connectors<=LIMIT,"resources-bound");
    uint32_t nc=r.count_connectors, nr=r.count_crtcs;
    r.crtc_id_ptr=PTR(crtcs); r.connector_id_ptr=PTR(connectors);
    /* Only retrieve arrays used here; omitted arrays have capacity zero. */
    r.count_fbs=0; r.count_encoders=0;
    call(DRM_IOCTL_MODE_GETRESOURCES,&r,"resources");
    require(r.count_crtcs==nr && r.count_connectors==nc,"resources-changed");
    uint32_t possible=0;
    for(uint32_t i=0;i<nc;i++) {
        struct drm_mode_get_connector c={.connector_id=connectors[i]};
        struct drm_mode_modeinfo modes[LIMIT]; uint32_t encoders[LIMIT];
        call(DRM_IOCTL_MODE_GETCONNECTOR,&c,"connector-count");
        if(c.connector_type!=DRM_MODE_CONNECTOR_DSI || c.connection!=1) continue;
        require(!s.connector,"multiple-dsi");
        require(c.count_modes && c.count_modes<=LIMIT && c.count_encoders && c.count_encoders<=LIMIT,"connector-bound");
        uint32_t nm=c.count_modes, ne=c.count_encoders;
        c.modes_ptr=PTR(modes); c.encoders_ptr=PTR(encoders); c.count_props=0;
        call(DRM_IOCTL_MODE_GETCONNECTOR,&c,"connector");
        require(c.count_modes==nm && c.count_encoders==ne && c.connection==1 && c.connector_type==DRM_MODE_CONNECTOR_DSI,"connector-changed");
        /* A unique lowest-refresh progressive 1080x2340 mode bounds initial
         * bandwidth. Duplicate/equal refresh modes require explicit design. */
        uint32_t hz=UINT32_MAX, matches=0;
        for(uint32_t j=0;j<nm;j++) {
            if(modes[j].hdisplay!=WIDTH || modes[j].vdisplay!=HEIGHT ||
               (modes[j].flags & (DRM_MODE_FLAG_INTERLACE|DRM_MODE_FLAG_DBLSCAN)) ||
               modes[j].vrefresh<30 || modes[j].vrefresh>60) continue;
            if(modes[j].vrefresh<hz) {hz=modes[j].vrefresh;s.mode=modes[j];matches=1;}
            else if(modes[j].vrefresh==hz) matches++;
        }
        require(matches==1,"mode-selection"); s.connector=c.connector_id;
        for(uint32_t j=0;j<ne;j++) {
            struct drm_mode_get_encoder e={.encoder_id=encoders[j]};
            call(DRM_IOCTL_MODE_GETENCODER,&e,"encoder"); possible|=e.possible_crtcs;
        }
    }
    require(s.connector && possible,"no-dsi");
    struct drm_mode_get_plane_res pr={0}; uint32_t planes[LIMIT];
    call(DRM_IOCTL_MODE_GETPLANERESOURCES,&pr,"planes-count");
    require(pr.count_planes && pr.count_planes<=LIMIT,"planes-bound");
    uint32_t np=pr.count_planes; pr.plane_id_ptr=PTR(planes);
    call(DRM_IOCTL_MODE_GETPLANERESOURCES,&pr,"planes");
    require(pr.count_planes==np,"planes-changed");
    /* Deterministic first compatible primary plane / CRTC pair. TEST_ONLY
     * must accept this exact state; no fallback attempts after a commit. */
    for(uint32_t i=0;i<np && !s.plane;i++) {
        struct drm_mode_get_plane p={.plane_id=planes[i]}; uint32_t formats[LIMIT];
        call(DRM_IOCTL_MODE_GETPLANE,&p,"plane-count");
        require(p.count_format_types<=LIMIT,"formats-bound");
        uint32_t nf=p.count_format_types; p.format_type_ptr=PTR(formats);
        call(DRM_IOCTL_MODE_GETPLANE,&p,"plane");
        require(p.count_format_types==nf,"formats-changed");
        int supported=0; for(uint32_t j=0;j<nf;j++) supported|=(formats[j]==DRM_FORMAT_XRGB8888);
        if(!supported) continue;
        struct props pp=get_props(p.plane_id,DRM_MODE_OBJECT_PLANE); uint64_t type=0;
        property(&pp,"type",&type); if(type!=1 /* stable UAPI primary-plane enum */) continue;
        for(uint32_t j=0;j<nr;j++) if((possible&p.possible_crtcs)&(1U<<j)) {
            s.plane=p.plane_id;s.crtc=crtcs[j];break;
        }
    }
    require(s.plane && s.crtc,"no-primary"); return s;
}
/* Refuse inherited competing scanout rather than disabling unknown objects. */
static void check_initial_state(struct selection s) {
    uint32_t crtcs[LIMIT], connectors[LIMIT], planes[LIMIT];
    struct drm_mode_card_res r={.count_crtcs=LIMIT,.count_connectors=LIMIT,
        .crtc_id_ptr=PTR(crtcs),.connector_id_ptr=PTR(connectors)};
    call(DRM_IOCTL_MODE_GETRESOURCES,&r,"initial-resources");
    require(r.count_crtcs<=LIMIT && r.count_connectors<=LIMIT,"initial-resources-bound");
    for(uint32_t i=0;i<r.count_crtcs;i++) if(crtcs[i]!=s.crtc) {
        struct props p=get_props(crtcs[i],DRM_MODE_OBJECT_CRTC);uint64_t active=0;
        property(&p,"ACTIVE",&active);require(!active,"competing-crtc");
    }
    for(uint32_t i=0;i<r.count_connectors;i++) {
        struct props p=get_props(connectors[i],DRM_MODE_OBJECT_CONNECTOR);uint64_t crtc=0;
        property(&p,"CRTC_ID",&crtc);
        require(!crtc || (connectors[i]==s.connector && crtc==s.crtc),"competing-connector");
    }
    struct drm_mode_get_plane_res rplane={.count_planes=LIMIT,.plane_id_ptr=PTR(planes)};
    call(DRM_IOCTL_MODE_GETPLANERESOURCES,&rplane,"initial-planes");
    require(rplane.count_planes<=LIMIT,"initial-planes-bound");
    for(uint32_t i=0;i<rplane.count_planes;i++) {
        struct drm_mode_get_plane p={.plane_id=planes[i]};
        call(DRM_IOCTL_MODE_GETPLANE,&p,"initial-plane");
        require((!p.crtc_id && !p.fb_id) || (p.plane_id==s.plane && p.crtc_id==s.crtc),"competing-plane");
    }
}
struct buffer { uint32_t handle, fb; uint32_t *pixels; };
static struct buffer allocate_buffer(void) {
    struct buffer b={0};
    struct drm_msm_gem_new g={.size=BYTES,.flags=MSM_BO_SCANOUT|MSM_BO_WC};
    call(DRM_IOCTL_MSM_GEM_NEW,&g,"wc-buffer"); b.handle=g.handle;
    struct drm_mode_map_dumb m={.handle=b.handle};
    call(DRM_IOCTL_MODE_MAP_DUMB,&m,"map-offset");
    require(m.offset<=INT64_MAX && !(m.offset&4095),"map-offset-bound");
    b.pixels=mmap(NULL,BYTES,PROT_READ|PROT_WRITE,MAP_SHARED,fd,(off_t)m.offset);
    if(b.pixels==MAP_FAILED) fail("mmap");
    struct drm_mode_fb_cmd2 f={.width=WIDTH,.height=HEIGHT,.pixel_format=DRM_FORMAT_XRGB8888};
    f.handles[0]=b.handle;f.pitches[0]=PITCH;
    call(DRM_IOCTL_MODE_ADDFB2,&f,"framebuffer");b.fb=f.fb_id;return b;
}
/* Tiny original 3x5 hex font, sufficient for exact 128-bit run ID and counter. */
static const uint16_t glyph[16]={0x7b6f,0x2492,0x73e7,0x73cf,0x5bc9,0x79cf,0x79ef,0x7249,0x7bef,0x7bcf,0x7bed,0x6bae,0x7927,0x6b6e,0x79e7,0x79e4};
static unsigned hexval(char c) {return c<='9'?(unsigned)(c-'0'):(unsigned)(c-'a'+10);}
static void digit(uint32_t *p,unsigned x,unsigned y,unsigned v) {
    const unsigned scale=12;
    for(unsigned row=0;row<5;row++) for(unsigned col=0;col<3;col++)
        if(glyph[v] & (1U<<(14-row*3-col)))
            for(unsigned dy=0;dy<scale;dy++) for(unsigned dx=0;dx<scale;dx++)
                p[(y+row*scale+dy)*(PITCH/4)+x+col*scale+dx]=0x00ffffff;
}
static void paint(struct buffer *b,unsigned frame) {
    for(size_t i=0;i<BYTES/4;i++) b->pixels[i]=0x00102030;
    for(unsigned i=0;i<32;i++) digit(b->pixels,60+(i%16)*60,240+(i/16)*96,hexval(run_id[i]));
    digit(b->pixels,60,500,(frame>>4)&15);digit(b->pixels,120,500,frame&15);
    /* Moving block makes different completed frames visually distinguishable. */
    for(unsigned y=700;y<850;y++) for(unsigned x=60+frame*80;x<120+frame*80;x++) b->pixels[y*(PITCH/4)+x]=0x0000ff80;
    __sync_synchronize(); /* Order writes to WC mapping before ioctl submission. */
}
static void wait_flip(uint64_t token,uint32_t crtc) {
    int64_t deadline=now_ms()+3000;
    for(;;) {
        int64_t remaining=deadline-now_ms(); require(remaining>0,"flip-timeout");
        struct pollfd p={.fd=fd,.events=POLLIN};
        int n=poll(&p,1,(int)remaining); if(n<0 && errno==EINTR) continue;
        require(n>0 && p.revents==POLLIN,"flip-poll");
        unsigned char bytes[4096]; ssize_t len=read(fd,bytes,sizeof(bytes));
        if(len<0 && (errno==EINTR || errno==EAGAIN)) continue;
        require(len>0,"flip-read");
        size_t offset=0; int found=0;
        while(offset<(size_t)len) {
            struct drm_event h; require((size_t)len-offset>=sizeof(h),"event-header");
            memcpy(&h,bytes+offset,sizeof(h));
            require(h.length>=sizeof(h) && h.length<=(size_t)len-offset,"event-length");
            require(h.type==DRM_EVENT_FLIP_COMPLETE && h.length==sizeof(struct drm_event_vblank),"event-type");
            struct drm_event_vblank e;memcpy(&e,bytes+offset,sizeof(e));
            require(!found && e.user_data==token && e.crtc_id==crtc,"event-binding");
            found=1;offset+=h.length;
        }
        if(found) return;
    }
}
static int valid_id(const char *s) {
    if(strlen(s)!=32) return 0;
    for(unsigned i=0;i<32;i++) if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f'))) return 0;
    return 1;
}
#ifdef P350_DISPLAY_VARIANT
#include "s22plus_native_display_load.inc.c"
#endif

int main(int argc,char **argv) {
    require(argc==3 && (!strcmp(argv[1],"--h0-paint") || !strcmp(argv[1],"--supervised-drm")) && valid_id(argv[2]),"arguments");
    run_id=argv[2];
    if(!strcmp(argv[1],"--h0-paint")) {
        struct buffer b={.pixels=calloc(1,BYTES)};require(b.pixels!=NULL,"paint-allocation");
        for(unsigned i=0;i<FRAMES;i++) paint(&b,i);
        require(fwrite(b.pixels,1,BYTES,stdout)==BYTES,"paint-output");free(b.pixels);return 0;
    }
    require(getppid()==1,"supervisor-pid");
#ifdef P350_DISPLAY_VARIANT
    p350_prepare_driver();
#endif
    fd=open("/dev/dri/card0",O_RDWR|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);if(fd<0)fail("open-card0");
    struct stat st; if(fstat(fd,&st))fail("card-stat");require(S_ISCHR(st.st_mode),"card-type");
#ifdef P350_DISPLAY_VARIANT
    require(st.st_rdev==makedev(226,0) && st.st_uid==0 && (st.st_mode&0777)==0600,"opened-drm-node-binding");
#endif
    char name[32]={0};struct drm_version v={.name_len=sizeof(name)-1,.name=name};
    call(DRM_IOCTL_VERSION,&v,"driver-version");require(v.name_len<sizeof(name)&&!strcmp(name,"msm"),"driver-name");
    call(DRM_IOCTL_SET_MASTER,NULL,"master");
#ifdef P350_DISPLAY_VARIANT
    p350_drop_privileges();
#endif
    struct drm_set_client_cap cap={.capability=DRM_CLIENT_CAP_ATOMIC,.value=1};
    call(DRM_IOCTL_SET_CLIENT_CAP,&cap,"atomic-cap");
    struct selection s=select_display();check_initial_state(s);struct buffer b[2]={allocate_buffer(),allocate_buffer()};
    struct drm_mode_create_blob blob={.data=PTR(&s.mode),.length=sizeof(s.mode)};
    call(DRM_IOCTL_MODE_CREATEPROPBLOB,&blob,"mode-blob");
    uint32_t objects[3]={s.connector,s.crtc,s.plane},counts[3]={1,2,10},ids[13];
    uint64_t values[13]={s.crtc,blob.blob_id,1,0,s.crtc,0,0,(uint64_t)WIDTH<<16,(uint64_t)HEIGHT<<16,0,0,WIDTH,HEIGHT};
    struct props cp=get_props(s.connector,DRM_MODE_OBJECT_CONNECTOR),rp=get_props(s.crtc,DRM_MODE_OBJECT_CRTC),pp=get_props(s.plane,DRM_MODE_OBJECT_PLANE);
    ids[0]=property(&cp,"CRTC_ID",NULL);ids[1]=property(&rp,"MODE_ID",NULL);ids[2]=property(&rp,"ACTIVE",NULL);
    const char *names[10]={"FB_ID","CRTC_ID","SRC_X","SRC_Y","SRC_W","SRC_H","CRTC_X","CRTC_Y","CRTC_W","CRTC_H"};
    for(unsigned i=0;i<10;i++) ids[i+3]=property(&pp,names[i],NULL);
    struct drm_mode_atomic a={.count_objs=3,.objs_ptr=PTR(objects),.count_props_ptr=PTR(counts),.props_ptr=PTR(ids),.prop_values_ptr=PTR(values)};
    for(unsigned frame=0;frame<FRAMES;frame++) {
        /* Reuse only the buffer retired by the previous matching flip event. */
        paint(&b[frame%2],frame); values[3]=b[frame%2].fb;
        a.flags=DRM_MODE_ATOMIC_TEST_ONLY|DRM_MODE_ATOMIC_ALLOW_MODESET;a.user_data=0;
        call(DRM_IOCTL_MODE_ATOMIC,&a,"test-only");
        a.flags=DRM_MODE_ATOMIC_ALLOW_MODESET|DRM_MODE_ATOMIC_NONBLOCK|DRM_MODE_PAGE_FLIP_EVENT;a.user_data=frame+1;
        call(DRM_IOCTL_MODE_ATOMIC,&a,"commit");wait_flip(frame+1,s.crtc);
        printf("DISPLAY_FLIP run=%s counter=%u crtc=%u completed=1\n",run_id,frame,s.crtc);fflush(stdout);
        struct timespec delay={.tv_sec=1};if(nanosleep(&delay,NULL))fail("frame-delay");
    }
    /* Explicit completed disable before normal resource teardown. */
    values[0]=0;values[1]=0;values[2]=0;values[3]=0;values[4]=0;
    a.flags=DRM_MODE_ATOMIC_ALLOW_MODESET;a.user_data=0;
    call(DRM_IOCTL_MODE_ATOMIC,&a,"disable-blocking");
    for(unsigned i=0;i<2;i++) {
        call(DRM_IOCTL_MODE_RMFB,&b[i].fb,"remove-fb");
        if(munmap(b[i].pixels,BYTES))fail("unmap");
        struct drm_gem_close g={.handle=b[i].handle};call(DRM_IOCTL_GEM_CLOSE,&g,"close-gem");
    }
    struct drm_mode_destroy_blob d={.blob_id=blob.blob_id};call(DRM_IOCTL_MODE_DESTROYPROPBLOB,&d,"destroy-blob");
    if(close(fd))fail("close-drm");
    printf("DISPLAY_DONE run=%s completed_frames=%u disabled=1\n",run_id,FRAMES);return 0;
}
