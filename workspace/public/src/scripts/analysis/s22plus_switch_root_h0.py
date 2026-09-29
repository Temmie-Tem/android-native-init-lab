"""Build separately pinned ARM64 PID1 preparation and post-switch witness."""
import argparse
import hashlib
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_native_root_inspect_h0 as inspection
import s22plus_native_staged_preflight_profile_v1 as staged
import s22plus_switch_root_source_v1 as source
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify

NATIVE=inspection.NATIVE
BUSYBOX_SHA256='7d93682be37cf6ed46699f6fff546b80bf133cf8ec342c2d04bc23387f78bc34'


def busybox():
    artifact,_,_=inspection.profile.prior_inputs()
    result=pin(Path(artifact['rootfs']['path']).parent/'busybox')
    require(result['size']==1975064 and result['sha256']==BUSYBOX_SHA256,'selected BusyBox 1.37 differs')
    return result


def array(name,data):return 'static const uint8_t '+name+'[]={'+','.join(map(str,data))+'};\n'


def payload_header(witness):
    return (f'static const uint64_t sw_witness_size={witness["size"]}ULL;\n'+
        array('sw_witness_sha256',bytes.fromhex(witness['sha256']))).encode()


def seal(run,key):
    require(len(bytes.fromhex(run))==16 and len(key)==32,'switch identity differs')
    bb=busybox()
    return (array('sw_run',bytes.fromhex(run))+array('sw_key',key)+
        f'static const uint64_t sw_busybox_size={bb["size"]}ULL;\n'+
        array('sw_busybox_sha256',bytes.fromhex(bb['sha256']))).encode()


def source_files(virt=False):
    paths=set(inspection.source_files(staged=True))|set(source.source_files())|set(inspection.fs_build.SOURCE_FILES)|{
        Path(__file__),Path(inspection.archive.__file__),Path(inspection.fs_build.predecessor.__file__),
        Path(inspection.fs_build.predecessor.gpt.__file__)}
    if virt:paths.add(ROOT/'workspace/public/src/debian/s22plus_v1/device/virt-binding.inc.c')
    return sorted(paths)


def build(out,run,key,*,virt=False,fault=0,checker_fault=0,debian=None):
    require(type(fault) is int and fault in (0,1,2,3) and type(checker_fault) is int and
        checker_fault in range(10) and (not fault and not checker_fault or virt),'fault requires virtual discovery')
    out=private_path(ROOT,out,exists=False);require(not out.exists(),'fresh switch build required')
    if debian is not None:
        import s22plus_debian_handoff_h0 as extension
        extension.validate_options(debian,virt)
    paths=source_files(virt) if debian is None else extension.source_files(virt)
    receipts=[pin(p,maximum=4*1024*1024) for p in paths]
    out.mkdir(mode=0o700,parents=True)
    for row in receipts:
        copy=out/'source-snapshot'/str(Path(row['path']).relative_to(ROOT))
        copy.parent.mkdir(mode=0o700,parents=True,exist_ok=True);copy.write_bytes(verify(row,maximum=4*1024*1024).read_bytes());copy.chmod(0o400)
    table,count,boot=inspection.table_bytes()
    (out/'table.bin').write_bytes(table)
    (out/'s22plus_native_ext4_seal_v1.h').write_bytes(inspection.fs_build.seal(inspection.profile.filesystem.BINDING,run,initialize=False))
    (out/'s22plus_native_root_inspect_seal_v1.h').write_bytes(inspection.header(table,count,boot))
    (out/'s22plus_native_userspace_probe_seal_v1.h').write_bytes(inspection.userspace_header())
    (out/'s22plus_native_staged_preflight_seal_v1.h').write_bytes(staged.header())
    (out/'s22plus_switch_root_seal_v1.h').write_bytes(seal(run,key))
    compiler=shutil.which('aarch64-linux-gnu-gcc');require(compiler is not None,'ARM64 compiler missing')
    compiler_pin=inspection.fs_build.compiler_identity(compiler)
    flags=['-std=c11','-static','-Os','-fno-ident','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable','-I',out,'-I',NATIVE]
    if virt:flags+=['-DS22_ROOT_INSPECT_VIRT_TEST']
    if debian is not None:
        flags+=['-DS22_DEBIAN_HANDOFF']
        if debian['fault']:flags+=['-DS22_DEBIAN_FAULT='+str(debian['fault'])]
        extension.prepare_headers(out,run,debian,virt)
    if fault:flags+=['-DS22_SWITCH_ROOT_FAULT='+str(fault)]
    if checker_fault:
        flags+=['-DS22_STAGED_PREFLIGHT_FAULT']
        (out/'s22plus_native_userspace_probe_fault_v1.h').write_text(
            'static const char up_fault_script[]="";\n'
            'static const int up_fault_early_zero=0,up_fault_setup_error=0,up_fault_orphan=0;\n'
            'static const unsigned up_fault_timeout_ms=1000;\n'
            f'static const unsigned sp_fault_kind=1,sp_fault_mode={checker_fault};\n')
    binaries={}
    units=[('witness','s22plus_switch_root_witness_v1.c'),('prepare','s22plus_switch_root_v1.c')]
    if debian is not None:units.insert(0,('hook','s22plus_debian_handoff_hook_v1.c'))
    for label,filename in units:
        for side in ('a','b'):
            inspection.fs_build.run([compiler,*flags,NATIVE/filename,'-o',out/(label+'-'+side)],cwd=ROOT,
                stdout=out/(label+'-'+side+'.log'),timeout=60)
        require((out/(label+'-a')).read_bytes()==(out/(label+'-b')).read_bytes(),'switch ELF A/B differs')
        binaries[label]=inspection.fs_build.tool_identity(out/(label+'-a'))
        if label=='hook':extension.payload_header(out,binaries[label],virt)
        if label=='witness':
            (out/'s22plus_switch_root_payload_v1.h').write_bytes(payload_header(binaries[label]))
    for row in receipts:verify(row,maximum=4*1024*1024)
    require(inspection.fs_build.compiler_identity(compiler)==compiler_pin,'ARM64 compiler changed')
    extras={} if debian is None else extension.result_fields(out,binaries['hook'],debian,virt)
    return publish(out/'result.json',dict(schema='s22plus-switch-root-helpers-h0-v1' if debian is None else
        's22plus-debian-handoff-helpers-h0-v1',run_id_hex=run,
        key_sha256=hashlib.sha256(key).hexdigest(),sources=receipts,compiler=compiler_pin,virt=virt,
        fault=fault,checker_fault=checker_fault,
        **binaries,busybox=busybox(),checker=staged.execution_binding()['checker'],table=pin(out/'table.bin'),
        table_count=count,boot_count=boot,ab_identical=True,device_actions=0,live_authorized=False,**extras))


def audit(out,run,key):
    value=read(out/'result.json')
    require(value['schema']=='s22plus-switch-root-helpers-h0-v1' and not value['virt'] and
        value['fault']==value['checker_fault']==0 and
        value['run_id_hex']==run and value['key_sha256']==hashlib.sha256(key).hexdigest() and
        value['sources']==[pin(p,maximum=4*1024*1024) for p in source_files()] and
        (out/'s22plus_switch_root_seal_v1.h').read_bytes()==seal(run,key) and
        value['busybox']==busybox() and value['checker']==staged.execution_binding()['checker'] and
        value['ab_identical'] is True,'switch helper input identity differs')
    for label in ('witness','prepare'):
        require(inspection.fs_build.tool_identity(out/(label+'-a'))==value[label] and
            (out/(label+'-a')).read_bytes()==(out/(label+'-b')).read_bytes(),'switch actual ELF differs')
    table,count,boot=inspection.table_bytes()
    require(verify(value['table']).read_bytes()==table and value['table_count']==count and value['boot_count']==boot,
        'switch comparison table differs')
    generated={
        's22plus_native_ext4_seal_v1.h':inspection.fs_build.seal(inspection.profile.filesystem.BINDING,run,initialize=False),
        's22plus_native_root_inspect_seal_v1.h':inspection.header(table,count,boot),
        's22plus_native_userspace_probe_seal_v1.h':inspection.userspace_header(),
        's22plus_native_staged_preflight_seal_v1.h':staged.header(),
        's22plus_switch_root_payload_v1.h':payload_header(value['witness'])}
    require(all((out/name).read_bytes()==expected for name,expected in generated.items()),
        'switch compiled header identity differs')
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--key',type=Path,required=True);p.add_argument('--virt',action='store_true')
    p.add_argument('--fault',type=int,default=0);p.add_argument('--checker-fault',type=int,default=0)
    args=p.parse_args();print(build(args.output,args.run_id,args.key.read_bytes(),virt=args.virt,
        fault=args.fault,checker_fault=args.checker_fault)['sha256'])
