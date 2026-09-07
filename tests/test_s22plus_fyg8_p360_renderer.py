"""Generated static renderer with exact source-derived mode and fake DRM only."""
from pathlib import Path
import json
import resource
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'workspace/public/src/scripts/analysis'),str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_fyg8_p360_display_renderer as renderer
import s22plus_fyg8_display_kms_contract_h0 as kms


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);out=Path(cls.tmp.name)
        headers=ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'
        source=(ROOT/'tests/s22plus_native_display_h0_harness.c').read_text()
        source=source.replace('DRM_FORMAT_XRGB8888','DRM_FORMAT_ABGR8888')
        source=source.replace('MSM_BO_WC|MSM_BO_SCANOUT','MSM_BO_CACHED|MSM_BO_SCANOUT')
        source=source.replace('#include "../workspace/public/src/native-init/s22plus_native_display_h0.c"','#include "renderer.c"')
        source=source.replace('static unsigned commits, tests, handles, flips, disables;', 'static unsigned commits, handles; static uint32_t *painted[2];')
        source=source.replace('static int pending;','').replace('static uint64_t event_token;','')
        source=source.replace('"type"};','"type", "zpos", "alpha", "fb_translation_mode", "noise_layer_v1", "DUPLICATE_NOISE", "color_fill", "DUPLICATE_FILL"};')
        source=source.replace('return calloc(1,n);','assert(handles>=1&&handles<=2);painted[handles-1]=calloc(1,n);return painted[handles-1];')
        a=source.index('int fake_munmap(');b=source.index('int fake_ioctl(',a)
        source=source[:a]+'''int fake_munmap(void *p,size_t n){(void)p;(void)n;assert(!"unexpected cleanup");return -1;}
int fake_close(int f){(void)f;assert(!"unexpected close");return -1;}
int fake_nanosleep(const struct timespec *d,struct timespec *r){
 assert(!r&&handles==2);
 if(d->tv_sec==5){assert(commits==1);if(!strcmp(scenario,"sleep-error")){errno=EINTR;return -1;}return 0;}
 assert(d->tv_sec==1&&commits==2);
 for(unsigned frame=0;frame<2;frame++){
 for(unsigned y=0;y<HEIGHT;y++)for(unsigned x=0;x<PITCH/4;x++){
  uint32_t want=0xffffffff;
  if(x>=8&&x<WIDTH-8&&y>=8&&y<HEIGHT-8){
   want=frame?(y<1170?(x<540?0xff00ff00:0xff0000ff):0xffff0000):(y<1170?(x<540?0xff0000ff:0xffff0000):0xff00ff00);
   for(unsigned grid=0;grid<WIDTH;grid+=120)if(x>=grid&&x<grid+4)want=0xff000000;
   for(unsigned grid=0;grid<HEIGHT;grid+=120)if(y>=grid&&y<grid+4)want=0xff000000;
  }
  if(frame&&x>=260&&x<820&&y>=740&&y<1600){
   want=0xff000000;
   const char *glyph[]={"1111","0001","1111","1000","1111"};
   int row=y<900?0:y<1110?1:y<1230?2:y<1440?3:4;
   if(x>=300&&x<780&&y>=780&&y<1560&&glyph[row][(x-300)/120]=='1')want=0xffffffff;
  }
  assert(painted[frame][y*(PITCH/4)+x]==want);
 }
 }
 puts("H0_STATIC_HELD two_commits=1 two_buffers=1 cleanup=0");fflush(stdout);_Exit(0);
}
''' + source[b:]
        source=source.replace('memcpy(q->name,"msm",4);q->name_len=3;', 'memcpy(q->name,"msm_drm",8);q->name_len=7;')
        a=source.index('  if(q->count_modes&&q->modes_ptr)');b=source.index('  if(q->count_encoders',a)
        mode='{'+','.join('.'+k+'='+json.dumps(v) for k,v in kms.SELECTED.items())+'}'
        source=source[:a]+'''  if(q->count_modes&&q->modes_ptr){struct drm_mode_modeinfo mode='''+mode+''';if(!strcmp(scenario,"bad-mode"))mode.clock++;memcpy((void *)(uintptr_t)q->modes_ptr,&mode,sizeof(mode));}
'''+source[b:]
        source=source.replace('unsigned n=!strcmp(scenario,"competing-plane")?2:1;','unsigned n=strcmp(scenario,"success")?2:1;')
        source=source.replace('p[0]=30;if(n==2)p[1]=31;', 'p[0]=30;if(n==2)p[1]=!strcmp(scenario,"duplicate-plane")?30:31;')
        source=source.replace('q->crtc_id=20;q->fb_id=99;', 'q->crtc_id=!strcmp(scenario,"foreign-crtc")?21:20;q->fb_id=!strcmp(scenario,"inherited-fb")?99:0;')
        source=source.replace('uint32_t ids[13],n=0;','uint32_t ids[21],n=0;')
        source=source.replace('assert(q->obj_id==30);ids[n++]=1;for(unsigned i=4;i<=13;i++)ids[n++]=i;', 'assert(q->obj_id==30||q->obj_id==31);ids[n++]=1;for(unsigned i=4;i<=16;i++)ids[n++]=i;if(q->obj_id==30){if(strcmp(scenario,"absent-fill"))ids[n++]=19;if(!strcmp(scenario,"duplicate-fill"))ids[n++]=20;}')
        source=source.replace('v[i]=ids[i]==13?1:0;', 'v[i]=ids[i]==13?(q->obj_id==30?1:0):ids[i]==15?255:0;if(!strcmp(scenario,"bad-alpha")&&q->obj_id==30)for(unsigned i=0;i<n;i++)if(ids[i]==15)v[i]=0;')
        source=source.replace('q->prop_id<14','q->prop_id<21')
        source=source.replace('ids[n++]=2;ids[n++]=3;', 'ids[n++]=2;ids[n++]=3;if(strcmp(scenario,"absent-noise"))ids[n++]=17;if(!strcmp(scenario,"duplicate-noise"))ids[n++]=18;')
        source=source.replace('strcpy(q->name,pn[q->prop_id]);', 'strcpy(q->name,pn[q->prop_id]);if(q->prop_id==18)strcpy(q->name,"noise_layer_v1");if(q->prop_id==20)strcpy(q->name,"color_fill");')
        source=source.replace('q->count_props=n;', 'q->count_props=n;')
        source=source.replace('strcpy(q->name,pn[q->prop_id]);','strcpy(q->name,pn[q->prop_id]);if(!strcmp(scenario,"missing-property")&&q->prop_id==12)strcpy(q->name,"OTHER");')
        source=source.replace('q->offset=4096;', 'q->offset=!strcmp(scenario,"bad-map")?4097:4096;')
        source=source.replace('[0]=DRM_FORMAT_ABGR8888;', '[0]=!strcmp(scenario,"unsupported-abgr")?DRM_FORMAT_XRGB8888:DRM_FORMAT_ABGR8888;')
        a=source.index(' if(op==DRM_IOCTL_MODE_ATOMIC)');b=source.index(' assert(!"unexpected ioctl")',a)
        source=source[:a]+''' if(op==DRM_IOCTL_MODE_ATOMIC){struct drm_mode_atomic *q=arg;
 uint32_t *o=(void *)(uintptr_t)q->objs_ptr,*c=(void *)(uintptr_t)q->count_props_ptr,*p=(void *)(uintptr_t)q->props_ptr;
 uint64_t *v=(void *)(uintptr_t)q->prop_values_ptr;
 assert(handles==2);
 if(commits==1){assert(q->flags==0&&q->user_data==0&&q->count_objs==1&&o[0]==30&&c[0]==1&&p[0]==4&&v[0]==102);
 commits++;fprintf(stderr,"H0_ATOMIC_COUNT=%u\\n",commits);
 if(!strcmp(scenario,"second-error")){errno=EIO;return -1;}return 0;}
 assert(commits==0&&q->flags==DRM_MODE_ATOMIC_ALLOW_MODESET&&q->user_data==0);
 assert(q->count_objs==(!strcmp(scenario,"success")?3U:4U));
 assert(o[0]==20&&o[1]==10&&o[2]==30&&c[0]==3&&c[1]==1&&c[2]==11);
 const uint32_t ids[]={2,3,17,1,4,1,5,6,7,8,9,10,11,12,19};assert(!memcmp(p,ids,sizeof(ids)));
 assert(v[0]==50&&v[1]==1&&v[2]==0&&v[3]==20&&v[4]==101&&v[5]==20&&v[6]==0&&v[7]==0&&v[8]==((uint64_t)WIDTH<<16)&&v[9]==((uint64_t)HEIGHT<<16)&&v[10]==0&&v[11]==0&&v[12]==WIDTH&&v[13]==HEIGHT&&v[14]==0);
 if(q->count_objs==4){assert(o[3]==31&&c[3]==2&&p[15]==4&&p[16]==1&&!v[15]&&!v[16]);}
 commits++;fprintf(stderr,"H0_ATOMIC_COUNT=%u\\n",commits);
 if(!strcmp(scenario,"commit-error")){errno=EIO;return -1;}return 0;}
'''+source[b:]
        source=source[:source.index('int main(int argc')]+'''int main(int argc,char **argv){assert(argc==2);scenario=argv[1];char *args[]={"renderer","--supervised-drm","c360f1e0a90b5e6d7c8a9b0c1d2e3f0a",NULL};return renderer_main(3,args);}
'''
        oracle_start=source.index(' for(unsigned frame=0;frame<2;frame++){')
        oracle_end=source.index(' puts("H0_STATIC_HELD',oracle_start)
        oracle=source[oracle_start:oracle_end]
        source=source[:oracle_start]+' verify_paints();\n'+source[oracle_end:]
        source=source.replace('int fake_nanosleep(', 'static void verify_paints(void){'+oracle+'}\nint fake_nanosleep(',1)
        source=source.replace(' assert(commits==0&&q->flags', ' verify_paints();\n assert(commits==0&&q->flags')
        source=source.replace('q->handle=++handles;', 'if(handles==1&&!strcmp(scenario,"second-new-error")){errno=ENOMEM;return -1;}q->handle=++handles;')
        source=source.replace('painted[handles-1]=calloc(1,n);', 'if(handles==2&&!strcmp(scenario,"second-map-error")){errno=ENOMEM;return MAP_FAILED;}painted[handles-1]=calloc(1,n);')
        source=source.replace('q->fb_id=q->handles[0]+100;', 'if(q->handles[0]==2&&!strcmp(scenario,"second-fb-error")){errno=ENOMEM;return -1;}q->fb_id=q->handles[0]+100;')
        (out/'renderer.c').write_bytes(renderer.render());(out/'fixture.c').write_text(source);cls.binary=out/'fixture'
        result=subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-D_DEFAULT_SOURCE','-I',str(headers),'-I',str(ROOT/'workspace/public/src/native-init'),str(out/'fixture.c'),'-o',str(cls.binary)],capture_output=True)
        if result.returncode:raise AssertionError(result.stderr.decode())

    def run_case(self,name):
        def limits():
            resource.setrlimit(resource.RLIMIT_AS,(64*1024*1024,64*1024*1024))
            resource.setrlimit(resource.RLIMIT_CPU,(15,15))
        return subprocess.run([self.binary,name],capture_output=True,timeout=3,preexec_fn=limits)

    def test_two_retained_frames_and_inherited_plane_replacement(self):
        for name in ('success','inherited-zero-fb'):
            result=self.run_case(name);self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(b'H0_STATIC_HELD',result.stdout)
            self.assertEqual(result.stderr.count(b'H0_ATOMIC_COUNT='),2)
            self.assertNotIn(b'DISPLAY_FLIP',result.stdout+result.stderr)
            if name!='success':self.assertIn(b'plane=31 crtc=20 fb=0',result.stderr)

    def test_negative_inputs_stop_before_commit(self):
        for name in ('foreign-crtc','inherited-fb','duplicate-plane','bad-alpha','missing-property','bad-map','bad-mode','absent-noise','duplicate-noise','absent-fill','duplicate-fill','unsupported-abgr','second-new-error','second-map-error','second-fb-error'):
            result=self.run_case(name);self.assertEqual(result.returncode,1,(name,result.stderr))
            self.assertIn(b'DISPLAY_FAIL',result.stderr);self.assertNotIn(b'H0_ATOMIC_COUNT',result.stderr)

    def test_commit_error_has_no_retry_or_cleanup(self):
        result=self.run_case('commit-error');self.assertEqual(result.returncode,1,result.stderr)
        self.assertIn(b'stage=static-commit',result.stderr);self.assertEqual(result.stderr.count(b'H0_ATOMIC_COUNT='),1)


    def test_second_error_has_no_retry(self):
        result=self.run_case('second-error');self.assertEqual(result.returncode,1,result.stderr)
        self.assertIn(b'stage=second-frame-commit',result.stderr);self.assertEqual(result.stderr.count(b'H0_ATOMIC_COUNT='),2)

    def test_interrupted_delay_has_no_second_commit(self):
        result=self.run_case('sleep-error');self.assertEqual(result.returncode,1,result.stderr)
        self.assertIn(b'stage=transition-delay',result.stderr);self.assertEqual(result.stderr.count(b'H0_ATOMIC_COUNT='),1)

if __name__=='__main__':unittest.main()
