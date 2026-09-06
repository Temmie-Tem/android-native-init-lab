#!/usr/bin/env python3
"""P350 H0 A/B packaging using the existing P319 compiler and boot packager.

Inputs are immutable P344 source/boot plus the reduced display module graph.
The 73-module USB plan is byte-identical. No device CLI is invoked.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[5]
sys.path[:0]=[str(Path(__file__).parent),str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_fyg8_p319_stock_candidate_build as packager
import s22plus_fyg8_p350_artifact_identity as artifact
import s22plus_fyg8_p350_research_shell_runtime as runtime
import s22plus_boot_verify as boot_verify

BASE=ROOT/'workspace/private/outputs/s22plus_fyg8_p344/stock-candidate-build-v1-20260905-01'
BASE_RESULT={'size':105068,'sha256':'d299eeb15d216040bd26294e760f71bfd4d9ac7e40d95d2aaefb6a476a20e6cd'}
DISPLAY=ROOT/'workspace/private/outputs/s22-display-build-h0'
HEADERS=ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'
NATIVE=ROOT/'workspace/public/src/native-init'
DEFAULT_OUTPUT_ROOT=ROOT/'workspace/private/outputs/s22plus_fyg8_p350/stock-candidate-build-v1-20260906-02'
SCHEMA='s22plus-fyg8-p350-stock-candidate-build-v1'
VERDICT='PASS_P350_STOCK_CANDIDATE_BUILD_H0_DISPLAY'
MODULE_NAMES=artifact.DISPLAY_MODULE_NAMES
RENDERER_FLAGS=('-static','-O2','-Wall','-Wextra','-Werror','-Wl,--build-id=none','-DP350_DISPLAY_VARIANT')

class AuditError(ValueError):pass

def identity(b):return {'size':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode()
def stable(p,expected=None):
    p=Path(p)
    st=p.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:raise AuditError('nonregular input: '+str(p))
    b=p.read_bytes()
    if expected is not None and identity(b)!=expected:raise AuditError('input identity differs: '+str(p))
    return b

def write(p,b,mode=0o400):
    p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
    p.chmod(mode)

def source_files():
    result={}
    for module in list(sys.modules.values()):
        p=getattr(module,'__file__',None)
        if p:
            p=Path(p).resolve()
            if p.is_file() and p.is_relative_to(ROOT/'workspace/public/src'):
                result[str(p.relative_to(ROOT))]=p
    for p in (Path(__file__),NATIVE/'s22plus_native_display_h0.c',NATIVE/'s22plus_native_display_load.inc.c'):
        result[str(p.relative_to(ROOT))]=p
    return result

def module_plan(a):
    stable(DISPLAY/'union-modules-final/msm_drm.ko', {'size':10534768,'sha256':'f4e5e9f5cf737f6e128e3bd904f3cadcb961552aa8a2ade86d2b94e01b2239e4'})
    added=set(a['additional_to_usb_plan']);seen=set();active=set();order=[]
    def visit(n):
        if n in active:raise AuditError('cyclic display dependency')
        if n in seen:return
        active.add(n)
        for d in a['graph'][n]:visit(d)
        active.remove(n);seen.add(n)
        if n in added:order.append(n)
    visit('msm_drm.ko')
    if tuple(order)!=MODULE_NAMES or set(order)!=added:raise AuditError('display addition set/order differs')
    if len(a['graph'])!=82 or any(v['unresolved'] for v in a['results'].values()):raise AuditError('combined graph is not resolved')
    for n,v in a['results'].items():stable(DISPLAY/'union-modules-final'/n,{'size':v['size'],'sha256':v['sha256']})
    lines=['#define P350_DISPLAY_MODULE_COUNT 9U',
        'struct p350_display_module { const char *path; unsigned long long size; int display; };',
        'static const struct p350_display_module p350_display_modules[] = {']
    lines += ['    {"/s22-display-modules/%s", %dULL, %d},'%(n,a['results'][n]['size'],n=='msm_drm.ko') for n in order]
    return ('\n'.join(lines+['};'])+'\n').encode()

def entries(boot):
    parsed=boot_verify.parse_boot_v4(boot)
    ramdisk=boot_verify.decompress_lz4_stream_python(parsed.ramdisk,maximum=128<<20)
    rows=boot_verify.parse_newc(ramdisk)
    if len({e.name for e in rows})!=len(rows):raise AuditError('duplicate ramdisk entry')
    return parsed,{e.name:e for e in rows}

def entry_identity(e):
    return dict(mode=e.mode,uid=e.uid,gid=e.gid,nlink=e.nlink,mtime=e.mtime,**identity(e.data))

def check_ramdisk(boot,base_boot,image,init,renderer,modules):
    parsed,rows=entries(boot);_,old=entries(base_boot)
    extras={'s22-display','s22-display-modules'}|{'s22-display-modules/'+n for n in MODULE_NAMES}
    if set(rows)!=set(old)|extras or set(old)&extras:raise AuditError('ramdisk inventory differs')
    if parsed.kernel!=image or rows['init'].data!=init:raise AuditError('Image/init differs')
    for n,e in old.items():
        if n=='init':
            if any(getattr(e,k)!=getattr(rows[n],k) for k in ('mode','uid','gid','nlink')):raise AuditError('init metadata changed')
        elif entry_identity(e)!=entry_identity(rows[n]):raise AuditError('inherited entry changed: '+n)
    expected={'s22-display':(renderer,0o100750),'s22-display-modules':(b'',0o040500)}
    expected.update({'s22-display-modules/'+n:(b,0o100400) for n,b in modules.items()})
    for n,(b,mode) in expected.items():
        e=rows[n]
        if e.data!=b or (e.mode,e.uid,e.gid,e.nlink)!=(mode,0,0,1):raise AuditError('display entry differs: '+n)
    if len(boot)!=len(base_boot) or parsed.header['header_version']!=4:raise AuditError('boot container layout differs')
    return {n:entry_identity(e) for n,e in sorted(rows.items())}

def run(argv,cwd,log):
    environment=os.environ.copy()
    for key in packager.COMPILER_ENVIRONMENT_KEYS:environment.pop(key,None)
    environment.update(LANG='C',LC_ALL='C',SOURCE_DATE_EPOCH='0')
    p=subprocess.run([str(x) for x in argv],cwd=cwd,env=environment,stdin=subprocess.DEVNULL,capture_output=True,timeout=180)
    write(log,p.stdout+p.stderr)
    if p.returncode:raise AuditError('host tool failed; retained '+str(log))
    return p.stdout

def build_package(out,label,base_boot,image,init,renderer,modules,tools):
    work=out/('pack-'+label);work.mkdir(mode=0o700)
    write(work/'base.img',base_boot)
    run([tools['magiskboot'],'unpack','-h',work/'base.img'],work,work/'unpack.log')
    (work/'kernel').write_bytes(image)
    files={'init':(init,0o750),'s22-display':(renderer,0o750)}
    files.update({'s22-display-modules/'+n:(b,0o400) for n,b in modules.items()})
    commands=['mkdir 500 s22-display-modules']
    for index,(name,(b,mode)) in enumerate(files.items()):
        p=work/f'asset-{index}';write(p,b)
        commands.append(f'add {mode:o} {name} {p}')
    run([tools['magiskboot'],'cpio',work/'ramdisk.cpio',*commands],work,work/'cpio.log')
    run([tools['magiskboot'],'repack',work/'base.img',work/'boot.img'],work,work/'repack.log')
    boot=stable(work/'boot.img');inventory=check_ramdisk(boot,base_boot,image,init,renderer,modules)
    dest=out/('candidate-'+label);dest.mkdir(mode=0o700)
    write(dest/'boot.img',boot)
    run([tools['lz4'],'--content-size','-B6','-f','-q',dest/'boot.img',dest/'boot.img.lz4'],work,work/'lz4.log')
    (dest/'boot.img.lz4').chmod(0o400)
    (dest/'odin4').mkdir(mode=0o700)
    ap_structure=packager._write_deterministic_boot_ap(stable(dest/'boot.img.lz4'),dest/'odin4/AP.tar.md5')
    (dest/'odin4/AP.tar.md5').chmod(0o400)
    child=entries(base_boot)[1]['s22-e1-child'].data
    artifact.inspect_ap(dest/'odin4/AP.tar.md5',expected_image=image,expected_init=init,expected_child=child)
    return dict(boot_img=identity(boot),boot_img_lz4=identity(stable(dest/'boot.img.lz4')),
        ap_tar_md5=identity(stable(dest/'odin4/AP.tar.md5')),inventory=inventory,ap_structure=ap_structure)

def build_result(output_root=DEFAULT_OUTPUT_ROOT,*,audit_only=False):
    out=Path(output_root).absolute()
    if audit_only:return audit_existing(out)
    if out.exists() or out.is_symlink():raise AuditError('output exists')
    base=json.loads(stable(BASE/'result.json',BASE_RESULT))
    graph=json.loads(stable(DISPLAY/'union-audit-final.json'))
    plan=module_plan(graph)
    sources={name:identity(stable(p)) for name,p in source_files().items()}
    out.mkdir(parents=True,mode=0o700)
    write(out/'source-inputs.json',canonical(sources))
    print('SOURCE_KEYS',json.dumps(sorted(sources)))
    before=stable(BASE/'stock-sources'/packager.RUNTIME_INCLUDE_NAME,base['source_closure'][packager.RUNTIME_INCLUDE_NAME])
    key=runtime.predecessor._materialized_key(before)
    transformed=runtime.transform_runtime_include(before,key)
    original=stable(BASE/'inputs/fixed-Image',artifact.P344_IMAGE_IDENTITY)
    image,image_receipt=artifact.transform_image(original)
    for name,expected in base['source_closure'].items():
        b=stable(BASE/'stock-sources'/name,expected)
        write(out/'stock-sources'/name,transformed if name==packager.RUNTIME_INCLUDE_NAME else b)
    write(out/'inputs/child-source.c',stable(BASE/'inputs/child-source.c',base['inputs']['child-source.c']))
    write(out/'inputs/fixed-Image',image)
    write(out/'inputs/s22plus_native_display_plan.h',plan)
    packager.RUN_ID=artifact.P350_RUN_ID;packager._bind_tools();tools=packager._tools()
    ua=packager._compile_userspace(out/'stock-sources',out/'userspace-a',label='p350-a')
    ub=packager._compile_userspace(out/'stock-sources',out/'userspace-b',label='p350-b')
    if ua!=ub:raise AuditError('userspace A/B differs')
    compiler=[tools['gcc'],*RENDERER_FLAGS,'-I',out/'inputs','-I',HEADERS,NATIVE/'s22plus_native_display_h0.c']
    deps=run([tools['gcc'],'-M','-DP350_DISPLAY_VARIANT','-I',out/'inputs','-I',HEADERS,NATIVE/'s22plus_native_display_h0.c'],out,out/'renderer-dependencies.log').decode().replace('\\\n',' ')
    header_paths=shlex.split(deps.split(':',1)[1])
    toolchain={str(Path(n).absolute()):identity(Path(n).read_bytes()) for n in header_paths}
    for name in ('libc.a','libgcc.a','libgcc_eh.a','crt1.o','crti.o','crtbeginT.o','crtend.o','crtn.o'):
        p=Path(subprocess.check_output([str(tools['gcc']),'-print-file-name='+name],text=True).strip())
        if not p.is_absolute() or not p.is_file():raise AuditError('static runtime input absent: '+name)
        toolchain[str(p)]=identity(p.read_bytes())
    for label in ('a','b'):
        run([*compiler,'-o',out/f'renderer-{label}'],out,out/f'renderer-{label}.log')
        (out/f'renderer-{label}').chmod(0o400)
    renderer=stable(out/'renderer-a')
    if renderer!=stable(out/'renderer-b'):raise AuditError('renderer A/B differs')
    elf=subprocess.check_output([str(tools['file']),'-b',str(out/'renderer-a')],text=True)
    headers=subprocess.check_output([str(tools['readelf']),'-W','-l',str(out/'renderer-a')],text=True)
    if 'ARM aarch64' not in elf or 'statically linked' not in elf or 'INTERP' in headers:raise AuditError('renderer ELF differs')
    modules={n:stable(DISPLAY/'union-modules-final'/n,{'size':graph['results'][n]['size'],'sha256':graph['results'][n]['sha256']}) for n in MODULE_NAMES}
    for n,b in modules.items():write(out/'module-bytes'/n,b)
    init=stable(out/'userspace-a/init',ua['init'])
    base_boot=stable(BASE/'candidate-a/boot.img',base['phase2']['candidate']['a']['boot_img'])
    a=build_package(out,'a',base_boot,image,init,renderer,modules,tools)
    b=build_package(out,'b',base_boot,image,init,renderer,modules,tools)
    if a!=b:raise AuditError('boot/AP A/B differs')
    result=dict(schema=SCHEMA,verdict=VERDICT,run_id_hex=artifact.P350_RUN_ID_HEX,target=runtime.TARGET,
        source_inputs=sources,toolchain_inputs=toolchain,tools=packager.TOOL_IDENTITIES,
        source_closure={p.name:identity(stable(p)) for p in (out/'stock-sources').iterdir()},
        image=identity(image),image_transform=image_receipt,init=ua['init'],child=ua['child'],renderer=identity(renderer),
        module_bytes={n:identity(v) for n,v in modules.items()},module_plan=identity(plan),
        candidate={'a':a,'b':b},usb_plan_unchanged=True,byte_identical=True,
        scope=dict(tier='H0',device_contact=False,candidate_transfers=0,rollback_transfers=0,live_authorized=False))
    for p,v in toolchain.items():
        if identity(Path(p).read_bytes())!=v:raise AuditError('compiler input changed')
    if {n:identity(stable(p)) for n,p in source_files().items()}!=sources:raise AuditError('source input changed during build')
    write(out/'result.json',canonical(result))
    return audit_existing(out)

def validate_ap_boot_join(ap_payload, expected_boot, expected_frame):
    frame,_=artifact._INNER._parse_ap(ap_payload,'P350 final AP join')
    if identity(frame)!=expected_frame:raise AuditError('AP boot member differs')
    decoded=boot_verify.decompress_lz4_frame_python(frame,expected_size=len(expected_boot))
    if decoded!=expected_boot:raise AuditError('transmitted AP boot differs from audited boot')
    return True

def audit_existing(output_root=DEFAULT_OUTPUT_ROOT):
    out=Path(output_root).absolute();r=json.loads(stable(out/'result.json'))
    if r.get('schema')!=SCHEMA or r.get('verdict')!=VERDICT or r.get('run_id_hex')!=artifact.P350_RUN_ID_HEX:raise AuditError('build result identity differs')
    for n,v in r['source_inputs'].items():stable(ROOT/n,v)
    for n,v in r['toolchain_inputs'].items():
        if identity(Path(n).read_bytes())!=v:raise AuditError('toolchain input differs')
    for n,v in r['source_closure'].items():stable(out/'stock-sources'/n,v)
    image=stable(out/'inputs/fixed-Image',r['image']);artifact.validate_image(image)
    init=stable(out/'userspace-a/init',r['init']);stable(out/'userspace-b/init',r['init'])
    renderer=stable(out/'renderer-a',r['renderer']);stable(out/'renderer-b',r['renderer'])
    modules={n:stable(out/'module-bytes'/n,v) for n,v in r['module_bytes'].items()}
    if set(modules)!=set(MODULE_NAMES):raise AuditError('module set differs')
    base=json.loads(stable(BASE/'result.json',BASE_RESULT));base_boot=stable(BASE/'candidate-a/boot.img',base['phase2']['candidate']['a']['boot_img'])
    for label in ('a','b'):
        c=r['candidate'][label];p=out/('candidate-'+label)
        boot=stable(p/'boot.img',c['boot_img']);stable(p/'boot.img.lz4',c['boot_img_lz4'])
        validate_ap_boot_join(stable(p/'odin4/AP.tar.md5',c['ap_tar_md5']),boot,c['boot_img_lz4'])
        artifact.inspect_ap(p/'odin4/AP.tar.md5',expected_image=image,expected_init=init,expected_child=stable(out/('userspace-'+label)/'s22-e1-child',r['child']),expected_ap=c['ap_tar_md5'])
        if check_ramdisk(boot,base_boot,image,init,renderer,modules)!=c['inventory']:raise AuditError('inventory differs')
    if r['candidate']['a']!=r['candidate']['b']:raise AuditError('stored A/B differs')
    return r

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=DEFAULT_OUTPUT_ROOT);parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    result=build_result(args.out,audit_only=args.audit_only)
    print(json.dumps({'verdict':result['verdict'],'ap':result['candidate']['a']['ap_tar_md5']},sort_keys=True))
