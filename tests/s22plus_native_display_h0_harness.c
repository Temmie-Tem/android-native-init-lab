/* Host consumer harness: every device-facing syscall is replaced. */
#define main renderer_main
#define ioctl fake_ioctl
#define open fake_open
#define fstat fake_fstat
#define getppid fake_getppid
#define mmap fake_mmap
#define munmap fake_munmap
#define close fake_close
#define poll fake_poll
#define read fake_read
#define nanosleep fake_nanosleep
#include "../workspace/public/src/native-init/s22plus_native_display_h0.c"
#undef main
#include <stdarg.h>
#include <assert.h>
static const char *scenario;
static unsigned commits, tests, handles, flips, disables;
static int pending;
static uint64_t event_token;
static const char *pn[]={"", "CRTC_ID", "MODE_ID", "ACTIVE", "FB_ID", "SRC_X", "SRC_Y", "SRC_W", "SRC_H", "CRTC_X", "CRTC_Y", "CRTC_W", "CRTC_H", "type"};
int fake_open(const char *p,int flags,...) {assert(!strcmp(p,"/dev/dri/card0")&&(flags&O_NOFOLLOW));return 7;}
int fake_fstat(int f,struct stat *s) {assert(f==7);memset(s,0,sizeof(*s));s->st_mode=S_IFCHR;return 0;}
pid_t fake_getppid(void) {return 1;}
void *fake_mmap(void *a,size_t n,int prot,int flags,int f,off_t off) {assert(!a&&n==BYTES&&prot==(PROT_READ|PROT_WRITE)&&flags==MAP_SHARED&&f==7&&off==4096);return calloc(1,n);}
int fake_munmap(void *p,size_t n) {assert(n==BYTES&&disables==1);free(p);return 0;}
int fake_close(int f) {assert(f==7&&disables==1&&!pending);return 0;}
int fake_nanosleep(const struct timespec *d,struct timespec *r) {assert(d->tv_sec==1&&!r&&!pending);return 0;}
int fake_poll(struct pollfd *p,nfds_t n,int t) {assert(n==1&&p->fd==7&&t>0&&t<=3000&&pending);if(!strcmp(scenario,"timeout"))return 0;p->revents=POLLIN;return 1;}
ssize_t fake_read(int f,void *out,size_t n) {
 assert(f==7&&n>=sizeof(struct drm_event_vblank)&&pending);
 struct drm_event_vblank e={.base={.type=DRM_EVENT_FLIP_COMPLETE,.length=sizeof(e)},.user_data=event_token,.crtc_id=20};
 if(!strcmp(scenario,"wrong-token"))e.user_data++;
 if(!strcmp(scenario,"wrong-crtc"))e.crtc_id++;
 if(!strcmp(scenario,"bad-length"))e.base.length=4097;
 memcpy(out,&e,sizeof(e));pending=0;flips++;return sizeof(e);
}
int fake_ioctl(int f,unsigned long op,...) {
 assert(f==7);va_list ap;va_start(ap,op);void *arg=va_arg(ap,void *);va_end(ap);
 if(op==DRM_IOCTL_VERSION){struct drm_version *q=arg;memcpy(q->name,"msm",4);q->name_len=3;return 0;}
 if(op==DRM_IOCTL_SET_MASTER)return 0;
 if(op==DRM_IOCTL_SET_CLIENT_CAP){struct drm_set_client_cap *q=arg;assert(q->capability==DRM_CLIENT_CAP_ATOMIC&&q->value==1);return 0;}
 if(op==DRM_IOCTL_MODE_GETRESOURCES){struct drm_mode_card_res *q=arg;
  if(q->count_crtcs&&q->crtc_id_ptr)((uint32_t *)(uintptr_t)q->crtc_id_ptr)[0]=20;
  if(q->count_connectors&&q->connector_id_ptr)((uint32_t *)(uintptr_t)q->connector_id_ptr)[0]=10;
  q->count_crtcs=1;q->count_connectors=!strcmp(scenario,"resource-overflow")?129:1;return 0;}
 if(op==DRM_IOCTL_MODE_GETCONNECTOR){struct drm_mode_get_connector *q=arg;assert(q->connector_id==10);
  if(q->count_modes&&q->modes_ptr){struct drm_mode_modeinfo *m=(void *)(uintptr_t)q->modes_ptr;memset(m,0,sizeof(*m));m->hdisplay=WIDTH;m->vdisplay=HEIGHT;m->vrefresh=60;}
  if(q->count_encoders&&q->encoders_ptr)((uint32_t *)(uintptr_t)q->encoders_ptr)[0]=40;
  q->count_modes=1;q->count_encoders=1;q->connector_type=DRM_MODE_CONNECTOR_DSI;q->connection=1;return 0;}
 if(op==DRM_IOCTL_MODE_GETENCODER){struct drm_mode_get_encoder *q=arg;assert(q->encoder_id==40);q->possible_crtcs=1;return 0;}
 if(op==DRM_IOCTL_MODE_GETPLANERESOURCES){struct drm_mode_get_plane_res *q=arg;unsigned n=!strcmp(scenario,"competing-plane")?2:1;
  if(q->count_planes&&q->plane_id_ptr){assert(q->count_planes>=n);uint32_t *p=(void *)(uintptr_t)q->plane_id_ptr;p[0]=30;if(n==2)p[1]=31;}q->count_planes=n;return 0;}
 if(op==DRM_IOCTL_MODE_GETPLANE){struct drm_mode_get_plane *q=arg;assert(q->plane_id==30||q->plane_id==31);
  if(q->count_format_types&&q->format_type_ptr)((uint32_t *)(uintptr_t)q->format_type_ptr)[0]=DRM_FORMAT_XRGB8888;
  q->count_format_types=1;q->possible_crtcs=1;if(q->plane_id==31){q->crtc_id=20;q->fb_id=99;}return 0;}
 if(op==DRM_IOCTL_MODE_OBJ_GETPROPERTIES){struct drm_mode_obj_get_properties *q=arg;uint32_t ids[13],n=0;
  if(q->obj_id==10)ids[n++]=1;else if(q->obj_id==20){ids[n++]=2;ids[n++]=3;}
  else{assert(q->obj_id==30);ids[n++]=1;for(unsigned i=4;i<=13;i++)ids[n++]=i;}
  if(q->count_props&&q->props_ptr){assert(q->count_props>=n);uint64_t *v=(void *)(uintptr_t)q->prop_values_ptr;memcpy((void *)(uintptr_t)q->props_ptr,ids,n*4);for(unsigned i=0;i<n;i++)v[i]=ids[i]==13?1:0;}q->count_props=n;return 0;}
 if(op==DRM_IOCTL_MODE_GETPROPERTY){struct drm_mode_get_property *q=arg;assert(q->prop_id>0&&q->prop_id<14);strcpy(q->name,pn[q->prop_id]);return 0;}
 if(op==DRM_IOCTL_MSM_GEM_NEW){struct drm_msm_gem_new *q=arg;assert(q->size==BYTES&&q->flags==(MSM_BO_WC|MSM_BO_SCANOUT));q->handle=++handles;return 0;}
 if(op==DRM_IOCTL_MODE_MAP_DUMB){struct drm_mode_map_dumb *q=arg;assert(q->handle&&q->handle<=2);q->offset=4096;return 0;}
 if(op==DRM_IOCTL_MODE_ADDFB2){struct drm_mode_fb_cmd2 *q=arg;assert(q->width==WIDTH&&q->height==HEIGHT&&q->pitches[0]==PITCH&&q->pixel_format==DRM_FORMAT_XRGB8888);q->fb_id=q->handles[0]+100;return 0;}
 if(op==DRM_IOCTL_MODE_CREATEPROPBLOB){struct drm_mode_create_blob *q=arg;assert(q->length==sizeof(struct drm_mode_modeinfo));q->blob_id=50;return 0;}
 if(op==DRM_IOCTL_MODE_ATOMIC){struct drm_mode_atomic *q=arg;uint32_t *o=(void *)(uintptr_t)q->objs_ptr,*c=(void *)(uintptr_t)q->count_props_ptr,*p=(void *)(uintptr_t)q->props_ptr;uint64_t *v=(void *)(uintptr_t)q->prop_values_ptr;
  assert(!pending&&q->count_objs==3&&o[0]==10&&o[1]==20&&o[2]==30&&c[0]==1&&c[1]==2&&c[2]==10);
  const uint32_t want[]={1,2,3,4,1,5,6,7,8,9,10,11,12};assert(!memcmp(p,want,sizeof(want)));
  if(!v[2]){assert(commits==FRAMES&&flips==FRAMES&&q->flags==DRM_MODE_ATOMIC_ALLOW_MODESET&&!v[0]&&!v[1]&&!v[3]&&!v[4]);disables++;return 0;}
  assert(v[0]==20&&v[1]==50&&v[3]==101+commits%2&&v[4]==20&&v[7]==((uint64_t)WIDTH<<16)&&v[8]==((uint64_t)HEIGHT<<16)&&v[11]==WIDTH&&v[12]==HEIGHT);
  if(q->flags&DRM_MODE_ATOMIC_TEST_ONLY){assert(q->flags==(DRM_MODE_ATOMIC_TEST_ONLY|DRM_MODE_ATOMIC_ALLOW_MODESET)&&!q->user_data);tests++;if(!strcmp(scenario,"test-rejected")){errno=EINVAL;return -1;}return 0;}
  assert(tests==commits+1&&q->user_data==commits+1&&q->flags==(DRM_MODE_ATOMIC_ALLOW_MODESET|DRM_MODE_ATOMIC_NONBLOCK|DRM_MODE_PAGE_FLIP_EVENT));
  if(!strcmp(scenario,"commit-error")){errno=EIO;return -1;}event_token=q->user_data;pending=1;commits++;return 0;}
 if(op==DRM_IOCTL_MODE_RMFB||op==DRM_IOCTL_GEM_CLOSE||op==DRM_IOCTL_MODE_DESTROYPROPBLOB){assert(disables==1);return 0;}
 assert(!"unexpected ioctl");return -1;
}
int main(int argc,char **argv){assert(argc==2);scenario=argv[1];char *args[]={"renderer","--supervised-drm","0123456789abcdef0123456789abcdef",NULL};int rc=renderer_main(3,args);assert(!strcmp(scenario,"success")&&commits==FRAMES&&tests==FRAMES&&flips==FRAMES&&disables==1);return rc;}
