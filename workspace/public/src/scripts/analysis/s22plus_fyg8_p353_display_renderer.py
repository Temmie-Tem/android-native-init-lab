"""One static first frame; sealed P352 inputs, no consumed-source mutation."""
from pathlib import Path
import hashlib
import s22plus_fyg8_p352_display_renderer as predecessor

PREDECESSOR_SHA = '985279dfd296dab3a13d685f1d5487506bff771ac9bb2e486b275843390b729c'


def render():
    if hashlib.sha256(Path(predecessor.__file__).read_bytes()).hexdigest() != PREDECESSOR_SHA:
        raise ValueError('P353 renderer predecessor changed')
    source = predecessor.render().decode()
    source = source.replace('#define FRAMES 10U', '#define FRAMES 1U')
    source = source.replace('static int64_t now_ms(void)',
                            'static __attribute__((unused)) int64_t now_ms(void)')
    start = source.index('/* Refuse inherited competing scanout')
    end = source.index('struct buffer {', start)
    source = source[:start] + r'''
/* Snapshot before atomic duplicate callbacks can change inherited state. */
static uint32_t inherited_planes[LIMIT], inherited_count;
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
    struct drm_mode_get_plane_res q={.count_planes=LIMIT,.plane_id_ptr=PTR(planes)};
    call(DRM_IOCTL_MODE_GETPLANERESOURCES,&q,"initial-planes");
    require(q.count_planes && q.count_planes<=LIMIT,"initial-planes-bound");
    unsigned selected_seen=0;
    inherited_count=0;
    /* Emit the complete bounded snapshot before interpreting any attachment. */
    struct drm_mode_get_plane snapshot[LIMIT];
    memset(snapshot,0,sizeof(snapshot));
    for(uint32_t i=0;i<q.count_planes;i++) {
        require(planes[i]!=0,"initial-plane-id");
        for(uint32_t j=0;j<i;j++)require(planes[j]!=planes[i],"initial-plane-duplicate");
        snapshot[i].plane_id=planes[i];
        call(DRM_IOCTL_MODE_GETPLANE,&snapshot[i],"initial-plane");
        require(snapshot[i].plane_id==planes[i],"initial-plane-identity");
        fprintf(stderr,"DISPLAY_INITIAL plane=%u crtc=%u fb=%u possible=%u\n",
            snapshot[i].plane_id,snapshot[i].crtc_id,snapshot[i].fb_id,snapshot[i].possible_crtcs);
    }
    fflush(stderr);
    for(uint32_t i=0;i<q.count_planes;i++) {
        const struct drm_mode_get_plane *p=&snapshot[i];
        require(!p->fb_id,"inherited-framebuffer");
        require(!p->crtc_id || p->crtc_id==s.crtc,"competing-plane");
        if(p->plane_id==s.plane)selected_seen++;
        else if(p->crtc_id==s.crtc)inherited_planes[inherited_count++]=p->plane_id;
    }
    require(selected_seen==1,"initial-primary-absent");
}
''' + source[end:]
    start = source.index('#include "s22plus_native_display_visible_layout_h0.c"')
    end = source.index('static int valid_id(', start)
    source = source[:start] + r'''
/* Original fixed asymmetric pattern. White alone can be a vendor error fill. */
static void paint(struct buffer *b,unsigned frame) {
    (void)frame;
    for(unsigned y=0;y<HEIGHT;y++) for(unsigned x=0;x<PITCH/4;x++) {
        uint32_t color=0x00ffffff;
        if(x<WIDTH && y>=240 && y<780)color=x<WIDTH/2?0x00e02020:0x000060e0;
        if(x>=150 && x<930 && y>=1100 && y<1800)color=0x0000b050;
        if((x>=440 && x<640 && y>=1170 && y<1730) ||
           (x>=270 && x<810 && y>=1350 && y<1550))color=0x00000000;
        b->pixels[y*(PITCH/4)+x]=color;
    }
    __sync_synchronize();
}
''' + source[end:]
    start = source.index('    struct selection s=select_display();check_initial_state(s);')
    source = source[:start] + r'''
    struct selection s=select_display();check_initial_state(s);
    struct buffer b=allocate_buffer();paint(&b,0);
    struct drm_mode_create_blob blob={.data=PTR(&s.mode),.length=sizeof(s.mode)};
    call(DRM_IOCTL_MODE_CREATEPROPBLOB,&blob,"mode-blob");
    uint32_t objects[LIMIT+3],counts[LIMIT+3],ids[13+2*LIMIT];
    uint64_t values[13+2*LIMIT];
    struct props rp=get_props(s.crtc,DRM_MODE_OBJECT_CRTC),
        cp=get_props(s.connector,DRM_MODE_OBJECT_CONNECTOR),
        pp=get_props(s.plane,DRM_MODE_OBJECT_PLANE);
    uint64_t zpos=0,alpha=0,translation=0;
    property(&pp,"zpos",&zpos);property(&pp,"alpha",&alpha);
    property(&pp,"fb_translation_mode",&translation);
    require(zpos==0 && alpha==255 && translation==0,"primary-defaults");
    objects[0]=s.crtc;counts[0]=2;
    ids[0]=property(&rp,"MODE_ID",NULL);values[0]=blob.blob_id;
    ids[1]=property(&rp,"ACTIVE",NULL);values[1]=1;
    objects[1]=s.connector;counts[1]=1;
    ids[2]=property(&cp,"CRTC_ID",NULL);values[2]=s.crtc;
    objects[2]=s.plane;counts[2]=10;
    const char *names[10]={"FB_ID","CRTC_ID","SRC_X","SRC_Y","SRC_W","SRC_H","CRTC_X","CRTC_Y","CRTC_W","CRTC_H"};
    const uint64_t selected[10]={b.fb,s.crtc,0,0,(uint64_t)WIDTH<<16,(uint64_t)HEIGHT<<16,0,0,WIDTH,HEIGHT};
    for(unsigned i=0;i<10;i++){ids[3+i]=property(&pp,names[i],NULL);values[3+i]=selected[i];}
    for(uint32_t i=0;i<inherited_count;i++) {
        struct props p=get_props(inherited_planes[i],DRM_MODE_OBJECT_PLANE);
        objects[3+i]=inherited_planes[i];counts[3+i]=2;
        ids[13+2*i]=property(&p,"FB_ID",NULL);values[13+2*i]=0;
        ids[14+2*i]=property(&p,"CRTC_ID",NULL);values[14+2*i]=0;
    }
    struct drm_mode_atomic a={.flags=DRM_MODE_ATOMIC_ALLOW_MODESET,
        .count_objs=3+inherited_count,.objs_ptr=PTR(objects),.count_props_ptr=PTR(counts),
        .props_ptr=PTR(ids),.prop_values_ptr=PTR(values)};
    fprintf(stderr,"DISPLAY_SUBMIT run=%s crtc=%u primary=%u inherited=%u pattern=red-blue-green-black-cross-v1\n",
        run_id,s.crtc,s.plane,inherited_count);fflush(stderr);
    call(DRM_IOCTL_MODE_ATOMIC,&a,"static-commit");
    fprintf(stderr,"DISPLAY_SUBMITTED run=%s ioctl_return=0 visible=UNPROVED\n",run_id);fflush(stderr);
    /* Retain display resources in this child during the existing attended
     * window. No second modeset, cleanup, redraw, or USB-dependent action.
     * The existing parent deadline and physical Download own termination. */
    for(;;) {
        struct timespec delay={.tv_sec=1};
        (void)nanosleep(&delay,NULL);
    }
}
'''
    return source.encode()
