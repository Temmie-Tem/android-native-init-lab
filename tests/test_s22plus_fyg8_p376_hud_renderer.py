"""Actual generated HUD renderer against deterministic target-shaped DRM.

Only syscalls/hardware are fixtures; paint/lifecycle/event parsing are production.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest
from tests import s22plus_display_step_h0_support as support
import s22plus_fyg8_p376_display_renderer as renderer
ROOT=Path(__file__).resolve().parents[1]


def fixture():
    source,headers=support.renderer_fixture()
    source=source.replace('#define main renderer_main','#define recv fake_recv\n#define clock_gettime fake_clock_gettime\n#define main renderer_main')
    source=source.replace('static unsigned commits, handles; static uint32_t *painted[2];',
        'static unsigned commits, handles,retired,unmapped,closed,flips,pending; static uint64_t event_token; static uint32_t *painted[8]; static uint64_t hashes[8];')
    source=source.replace('handles<=2','handles<=8').replace('q->handle<=2','q->handle<=8')
    a=source.index('int fake_munmap(');b=source.index('int fake_ioctl(',a)
    source=source[:a]+r'''
static uint64_t checksum(const uint32_t *p){uint64_t h=1;for(size_t i=0;i<BYTES/4;i++){assert(p[i]==0xff000000U||p[i]==0xffffffffU);h=(h^p[i])*1099511628211ULL;}return h;}
static void immutable(void){for(unsigned i=closed;i<commits;i++)assert(painted[i]&&checksum(painted[i])==hashes[i]);}
int fake_munmap(void *p,size_t n){assert(n==BYTES&&!pending&&retired==unmapped+1);if(!strcmp(scenario,"unmap-error")){errno=EIO;return -1;}assert(p==painted[unmapped]);free(p);painted[unmapped++]=NULL;return 0;}
int fake_close(int f){(void)f;assert(!"DRM descriptor closed before terminal");return -1;}
int fake_nanosleep(const struct timespec *d,struct timespec *r){assert(!r);if(!strcmp(scenario,"ipc-live")&&!d->tv_sec)return syscall(SYS_nanosleep,d,r);if(d->tv_sec==1){fprintf(stderr,"COUNTS commits=%u handles=%u retired=%u unmapped=%u closed=%u flips=%u\n",commits,handles,retired,unmapped,closed,flips);assert(handles-closed<=2);_Exit(1);}return 0;}
int fake_clock_gettime(clockid_t id,struct timespec *value){static uint64_t ticks;assert(id==CLOCK_MONOTONIC);if(!strcmp(scenario,"ipc-live"))return syscall(SYS_clock_gettime,id,value);ticks+=100;value->tv_sec=ticks/1000;value->tv_nsec=(ticks%1000)*1000000;return 0;}
ssize_t fake_recv(int f,void *out,size_t size,int flags){
 static unsigned seq,empty;assert(f==0&&size==40&&flags==(MSG_DONTWAIT|MSG_TRUNC));
 if(!strcmp(scenario,"ipc-live"))return syscall(SYS_recvfrom,f,out,size,flags,NULL,NULL);
 if(empty){empty=0;errno=EAGAIN;return -1;}
 if(commits==3){assert(handles==3&&closed==2&&retired==2&&unmapped==2&&flips==3&&!pending);immutable();puts("PASS three immutable frames max-two buffers and matched retirement");fflush(stdout);_Exit(0);}
 struct hud_snapshot value={.magic=0x31445548U,.sequence=++seq,.state=seq%2,.uptime_ms=1000ULL*seq};
 const unsigned char id[16]={0xc3,0x76,0xf1,0xe0,0xa9,0x0b,0x5e,0x6d,0x7c,0x8a,0x9b,0x0c,0x1d,0x2e,0x3f,0x0b};memcpy(value.run,id,16);
 if(!strcmp(scenario,"wrong-run"))value.run[0]^=1;
 if(!strcmp(scenario,"stale-sequence")&&commits)value.sequence--;
 if(!strcmp(scenario,"stale-parent")){errno=EAGAIN;return -1;}
 if(!strcmp(scenario,"oversized-packet"))return 41;
 if(!strcmp(scenario,"snapshot-eof"))return 0;
 memcpy(out,&value,40);empty=1;return 40;
}
ssize_t fake_read(int f,void *out,size_t n){
 assert(f==7&&n==sizeof(struct drm_event_vblank)&&pending);
 if(!strcmp(scenario,"event-timeout")){errno=EAGAIN;return -1;}
 struct drm_event_vblank e={.base={.type=DRM_EVENT_FLIP_COMPLETE,.length=sizeof(e)},.user_data=event_token,.crtc_id=20};
 if(!strcmp(scenario,"wrong-token"))e.user_data++;
 if(!strcmp(scenario,"duplicate-event")&&commits==2)e.user_data--;
 if(!strcmp(scenario,"wrong-crtc"))e.crtc_id++;
 if(!strcmp(scenario,"wrong-event-type"))e.base.type=DRM_EVENT_VBLANK;
 if(!strcmp(scenario,"bad-event-length"))e.base.length++;
 memcpy(out,&e,sizeof(e));pending=0;flips++;
 return !strcmp(scenario,"partial-event")?16:(ssize_t)sizeof(e);
}
''' + source[b:]
    source=source.replace('q->count_crtcs=1;q->count_connectors=',
        'if(q->count_encoders&&q->encoder_id_ptr){((uint32_t *)(uintptr_t)q->encoder_id_ptr)[0]=40;}q->count_encoders=1;q->count_crtcs=1;q->count_connectors=')
    a=source.index(' if(op==DRM_IOCTL_MODE_ATOMIC)');b=source.index(' assert(!"unexpected ioctl")',a)
    source=source[:a]+r'''
 if(op==DRM_IOCTL_MODE_ATOMIC){struct drm_mode_atomic *q=arg;
 uint32_t *o=(void *)(uintptr_t)q->objs_ptr,*c=(void *)(uintptr_t)q->count_props_ptr,*p=(void *)(uintptr_t)q->props_ptr;
 uint64_t *v=(void *)(uintptr_t)q->prop_values_ptr;
 immutable();assert(!pending&&handles==commits+1&&handles-closed<=2&&retired==closed&&unmapped==closed);
 assert(q->user_data==commits+1&&q->flags==((commits?0:DRM_MODE_ATOMIC_ALLOW_MODESET)|DRM_MODE_PAGE_FLIP_EVENT));
 if(!commits){assert(q->count_objs>=3&&o[0]==20&&o[1]==10&&o[2]==30&&c[0]==3&&c[1]==1&&c[2]==11);assert(v[2]==0&&v[4]==101&&v[14]==0);}
 else {assert(q->count_objs==1&&o[0]==30&&c[0]==1&&p[0]==4&&v[0]==101+commits);}
 /* First preparation/mapping happens here: CPU paint must already be complete. */
 uint32_t *pixels=painted[handles-1];assert(pixels);unsigned white=0;
 for(size_t i=0;i<BYTES/4;i++)white+=pixels[i]==0xffffffffU;
 assert(white>10000&&white<200000);assert(pixels[0]==0xff000000U);hashes[handles-1]=checksum(pixels);
 commits++;if(!strcmp(scenario,"commit-error")){errno=EIO;return -1;}
 event_token=q->user_data;pending=1;return 0;}
 if(op==DRM_IOCTL_MODE_RMFB){assert(!pending&&flips==commits&&commits==retired+2&&*(uint32_t*)arg==101+retired);immutable();if(!strcmp(scenario,"rmfb-error")){errno=EIO;return -1;}retired++;return 0;}
 if(op==DRM_IOCTL_GEM_CLOSE){struct drm_gem_close *q=arg;assert(!pending&&q->handle==closed+1&&unmapped==closed+1);if(!strcmp(scenario,"gem-close-error")){errno=EIO;return -1;}closed++;return 0;}
''' + source[b:]
    source=source.replace('q->handle=++handles;', 'assert(handles-closed<2&&retired==closed&&unmapped==closed);q->handle=++handles;')
    source=source[:source.index('int main(int argc')]+'''int main(int argc,char **argv){assert(argc==2);scenario=argv[1];
 if(!strcmp(scenario,"paint-bounds")){uint32_t *raw=malloc(BYTES+64);assert(raw);for(unsigned i=0;i<8;i++){raw[i]=0x12345678;raw[BYTES/4+8+i]=0xabcdef01;}struct buffer b={.pixels=raw+8};
 paint(&b,0xffffffffU);hud_text(&b,WIDTH-1,HEIGHT-1,"NNN");hud_text(&b,0xffffffffU,0xffffffffU,"OVERFLOW");
 for(unsigned i=0;i<8;i++){assert(raw[i]==0x12345678);assert(raw[BYTES/4+8+i]==0xabcdef01);}assert(b.pixels[(HEIGHT-1)*(PITCH/4)+WIDTH-1]==0xffffffffU);free(raw);puts("PASS clipped text and long uptime");return 0;}
 char *args[]={"renderer","--supervised-drm","c376f1e0a90b5e6d7c8a9b0c1d2e3f0b",NULL};return renderer_main(3,args);}\n'''
    return source,headers

class HudRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        folder=Path(cls.temp.name);source,headers=fixture()
        (folder/'renderer.c').write_bytes(renderer.render());(folder/'fixture.c').write_text(source)
        cls.binary=folder/'renderer'
        p=subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-D_DEFAULT_SOURCE','-I',str(headers),
            '-I',str(ROOT/'workspace/public/src/native-init'),str(folder/'fixture.c'),'-o',str(cls.binary)],capture_output=True)
        if p.returncode:raise AssertionError(p.stderr.decode())

    def run_case(self,name):return subprocess.run([self.binary,name],capture_output=True,timeout=6)

    def test_immutable_frames_retire_before_next_allocation(self):
        p=self.run_case('success');self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn(b'PASS three immutable frames',p.stdout);self.assertEqual(p.stderr.count(b'HUD_FRAME'),3)

    def test_event_uncertainty_never_retires_or_allocates_again(self):
        for case in ('wrong-token','wrong-crtc','wrong-event-type','bad-event-length','partial-event','event-timeout','commit-error'):
            with self.subTest(case=case):
                p=self.run_case(case);self.assertEqual(p.returncode,1,p.stderr)
                self.assertIn(b'commits=1 handles=1 retired=0 unmapped=0 closed=0',p.stderr)
                self.assertNotIn(b'HUD_FRAME',p.stderr)

    def test_stale_event_and_retirement_failures_stop_at_two_buffers(self):
        for case in ('duplicate-event','rmfb-error','unmap-error','gem-close-error'):
            with self.subTest(case=case):
                p=self.run_case(case);self.assertEqual(p.returncode,1,p.stderr)
                self.assertIn(b'commits=2 handles=2',p.stderr);self.assertIn(b'closed=0',p.stderr)

    def test_paint_long_uptime_and_clipping_keep_guards(self):
        p=self.run_case('paint-bounds');self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn(b'PASS clipped text',p.stdout)

    def test_bad_snapshot_never_commits(self):
        for case in ('wrong-run','oversized-packet','snapshot-eof','stale-parent'):
            with self.subTest(case=case):
                p=self.run_case(case);self.assertEqual(p.returncode,1,p.stderr)
                self.assertIn(b'commits=0 handles=0 retired=0',p.stderr)

    def test_stale_snapshot_has_no_new_allocation(self):
        p=self.run_case('stale-sequence');self.assertEqual(p.returncode,1,p.stderr)
        self.assertIn(b'commits=1 handles=1 retired=0',p.stderr)

if __name__=='__main__':unittest.main()
