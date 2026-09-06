"""Generated static renderer with exact source-derived mode and fake DRM only."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'workspace/public/src/scripts/analysis'),str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_fyg8_p354_display_renderer as renderer
import s22plus_fyg8_display_kms_contract_h0 as kms


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);out=Path(cls.tmp.name)
        headers=ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'
        source=(ROOT/'tests/s22plus_native_display_h0_harness.c').read_text()
        source=source.replace('#include "../workspace/public/src/native-init/s22plus_native_display_h0.c"','#include "renderer.c"')
        source=source.replace('static unsigned commits, tests, handles, flips, disables;', 'static unsigned commits, handles; static uint32_t *painted;')
        source=source.replace('static int pending;','').replace('static uint64_t event_token;','')
        source=source.replace('"type"};','"type", "zpos", "alpha", "fb_translation_mode", "noise_layer_v1", "DUPLICATE_NOISE"};')
        source=source.replace('return calloc(1,n);','painted=calloc(1,n);return painted;')
        a=source.index('int fake_munmap(');b=source.index('int fake_ioctl(',a)
        source=source[:a]+'''int fake_munmap(void *p,size_t n){(void)p;(void)n;assert(!"unexpected cleanup");return -1;}
int fake_close(int f){(void)f;assert(!"unexpected close");return -1;}
int fake_nanosleep(const struct timespec *d,struct timespec *r){
 assert(d->tv_sec==1&&!r&&commits==1&&handles==1);
 assert(painted[300*(PITCH/4)+100]==0x00e02020);
 assert(painted[300*(PITCH/4)+800]==0x000060e0);
 assert(painted[1200*(PITCH/4)+200]==0x0000b050);
 assert(painted[1400*(PITCH/4)+500]==0);
 for(unsigned y=0;y<HEIGHT;y++)for(unsigned x=0;x<PITCH/4;x++){
  uint32_t want=0xffffff;
  if(x<WIDTH&&y>=240&&y<780)want=x<540?0xe02020:0x0060e0;
  if(x>=150&&x<930&&y>=1100&&y<1800)want=0x00b050;
  if((x>=440&&x<640&&y>=1170&&y<1730)||(x>=270&&x<810&&y>=1350&&y<1550))want=0;
  assert(painted[y*(PITCH/4)+x]==want);
 }
 puts("H0_STATIC_HELD one_commit=1 one_buffer=1 cleanup=0");fflush(stdout);_Exit(0);
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
        source=source.replace('uint32_t ids[13],n=0;','uint32_t ids[19],n=0;')
        source=source.replace('assert(q->obj_id==30);ids[n++]=1;for(unsigned i=4;i<=13;i++)ids[n++]=i;', 'assert(q->obj_id==30||q->obj_id==31);ids[n++]=1;for(unsigned i=4;i<=16;i++)ids[n++]=i;')
        source=source.replace('v[i]=ids[i]==13?1:0;', 'v[i]=ids[i]==13?(q->obj_id==30?1:0):ids[i]==15?255:0;if(!strcmp(scenario,"bad-alpha")&&q->obj_id==30)for(unsigned i=0;i<n;i++)if(ids[i]==15)v[i]=0;')
        source=source.replace('q->prop_id<14','q->prop_id<19')
        source=source.replace('ids[n++]=2;ids[n++]=3;', 'ids[n++]=2;ids[n++]=3;if(strcmp(scenario,"absent-noise"))ids[n++]=17;if(!strcmp(scenario,"duplicate-noise"))ids[n++]=18;')
        source=source.replace('strcpy(q->name,pn[q->prop_id]);', 'strcpy(q->name,pn[q->prop_id]);if(q->prop_id==18)strcpy(q->name,"noise_layer_v1");')
        source=source.replace('q->count_props=n;', 'q->count_props=n;')
        source=source.replace('strcpy(q->name,pn[q->prop_id]);','strcpy(q->name,pn[q->prop_id]);if(!strcmp(scenario,"missing-property")&&q->prop_id==12)strcpy(q->name,"OTHER");')
        source=source.replace('q->offset=4096;', 'q->offset=!strcmp(scenario,"bad-map")?4097:4096;')
        a=source.index(' if(op==DRM_IOCTL_MODE_ATOMIC)');b=source.index(' assert(!"unexpected ioctl")',a)
        source=source[:a]+''' if(op==DRM_IOCTL_MODE_ATOMIC){struct drm_mode_atomic *q=arg;
 uint32_t *o=(void *)(uintptr_t)q->objs_ptr,*c=(void *)(uintptr_t)q->count_props_ptr,*p=(void *)(uintptr_t)q->props_ptr;
 uint64_t *v=(void *)(uintptr_t)q->prop_values_ptr;
 assert(commits==0&&handles==1&&q->flags==DRM_MODE_ATOMIC_ALLOW_MODESET&&q->user_data==0);
 assert(q->count_objs==(!strcmp(scenario,"success")?3U:4U));
 assert(o[0]==20&&o[1]==10&&o[2]==30&&c[0]==3&&c[1]==1&&c[2]==10);
 const uint32_t ids[]={2,3,17,1,4,1,5,6,7,8,9,10,11,12};assert(!memcmp(p,ids,sizeof(ids)));
 assert(v[0]==50&&v[1]==1&&v[2]==0&&v[3]==20&&v[4]==101&&v[5]==20&&v[6]==0&&v[7]==0&&v[8]==((uint64_t)WIDTH<<16)&&v[9]==((uint64_t)HEIGHT<<16)&&v[10]==0&&v[11]==0&&v[12]==WIDTH&&v[13]==HEIGHT);
 if(q->count_objs==4){assert(o[3]==31&&c[3]==2&&p[14]==4&&p[15]==1&&!v[14]&&!v[15]);}
 commits++;fprintf(stderr,"H0_ATOMIC_COUNT=%u\\n",commits);
 if(!strcmp(scenario,"commit-error")){errno=EIO;return -1;}return 0;}
'''+source[b:]
        source=source[:source.index('int main(int argc')]+'''int main(int argc,char **argv){assert(argc==2);scenario=argv[1];char *args[]={"renderer","--supervised-drm","c354f1e0a90b5e6d7c8a9b0c1d2e3f0b",NULL};return renderer_main(3,args);}
'''
        (out/'renderer.c').write_bytes(renderer.render());(out/'fixture.c').write_text(source);cls.binary=out/'fixture'
        result=subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-D_DEFAULT_SOURCE','-I',str(headers),'-I',str(ROOT/'workspace/public/src/native-init'),str(out/'fixture.c'),'-o',str(cls.binary)],capture_output=True)
        if result.returncode:raise AssertionError(result.stderr.decode())

    def run_case(self,name):
        return subprocess.run([self.binary,name],capture_output=True,timeout=3)

    def test_one_static_submission_and_inherited_plane_replacement(self):
        for name in ('success','inherited-zero-fb'):
            result=self.run_case(name);self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(b'H0_STATIC_HELD',result.stdout)
            self.assertEqual(result.stderr.count(b'H0_ATOMIC_COUNT='),1)
            self.assertNotIn(b'DISPLAY_FLIP',result.stdout+result.stderr)
            if name!='success':self.assertIn(b'plane=31 crtc=20 fb=0',result.stderr)

    def test_negative_inputs_stop_before_commit(self):
        for name in ('foreign-crtc','inherited-fb','duplicate-plane','bad-alpha','missing-property','bad-map','bad-mode','absent-noise','duplicate-noise'):
            result=self.run_case(name);self.assertEqual(result.returncode,1,(name,result.stderr))
            self.assertIn(b'DISPLAY_FAIL',result.stderr);self.assertNotIn(b'H0_ATOMIC_COUNT',result.stderr)

    def test_commit_error_has_no_retry_or_cleanup(self):
        result=self.run_case('commit-error');self.assertEqual(result.returncode,1,result.stderr)
        self.assertIn(b'stage=static-commit',result.stderr);self.assertEqual(result.stderr.count(b'H0_ATOMIC_COUNT='),1)


if __name__=='__main__':unittest.main()
