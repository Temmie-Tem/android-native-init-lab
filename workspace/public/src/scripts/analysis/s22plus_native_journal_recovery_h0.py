"""Build the fixed replay owner with the existing protected inspection table."""
import argparse
from pathlib import Path
import shutil
import s22plus_native_root_inspect_h0 as base
import s22plus_native_journal_recovery_profile_v1 as profile
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify

ROOT,NATIVE=base.ROOT,base.NATIVE


def source_files(virt=False):
    rows=set(base.source_files(userspace=True))|{Path(__file__),Path(profile.__file__),Path(profile.handoff.__file__),
        ROOT/'workspace/public/src/scripts/revalidation/s22plus_debian_autoboot_profile_v1.py',
        NATIVE/'s22plus_native_journal_recovery_v1.c',NATIVE/'s22plus_debian_handoff_root_v2.inc.c',
        NATIVE/'s22plus_journal_replay_strict_v1.inc.c',
        ROOT/'workspace/public/src/scripts/analysis/s22plus_journal_replay_tool_h0.py'}
    if virt:rows.add(ROOT/'workspace/public/src/debian/s22plus_v1/device/virt-binding.inc.c')
    return sorted(rows)


def headers(run,selection=None):
    if selection is not None:
        import s22plus_debian_autoboot_profile_v1 as automatic
        require(selection==automatic.HISTORY_SELECTION,'unselected journal history')
        return automatic.admission_headers(run,True)
    table,count,boot=base.table_bytes()
    return dict(table=table,count=count,boot=boot,headers={
        's22plus_native_ext4_seal_v1.h':base.fs_build.seal(profile.inspection.filesystem.BINDING,run,initialize=False),
        's22plus_native_root_inspect_seal_v1.h':base.header(table,count,boot),
        's22plus_native_userspace_probe_seal_v1.h':base.userspace_header(),
        's22plus_native_journal_recovery_seal_v1.h':profile.header(),
        's22plus_native_journal_mutable_seal_v1.h':profile.handoff.mutable_header().encode()})


def build(out,run,*,virt=False,selection=None):
    out=private_path(ROOT,out,exists=False);require(not out.exists(),'fresh recovery owner build required')
    source=[pin(p,maximum=4*1024*1024) for p in source_files(virt)]
    generated=headers(run,selection);out.mkdir(mode=0o700,parents=True)
    for name,data in generated['headers'].items():(out/name).write_bytes(data)
    (out/'table.bin').write_bytes(generated['table'])
    flags=['-std=c11','-static','-Os','-fno-ident','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable','-I',out,'-I',NATIVE]
    if virt:flags+=['-DS22_ROOT_INSPECT_VIRT_TEST']
    if selection is not None:flags+=['-DS22_AUTOBOOT_HISTORY']
    compiler=shutil.which('aarch64-linux-gnu-gcc');compiler_pin=base.fs_build.compiler_identity(compiler)
    for side in ('a','b'):
        base.fs_build.run([compiler,*flags,NATIVE/'s22plus_native_journal_recovery_v1.c','-o',out/('helper-'+side)],
            cwd=ROOT,stdout=out/('compile-'+side+'.log'),timeout=60)
    require((out/'helper-a').read_bytes()==(out/'helper-b').read_bytes(),'recovery owner A/B differs')
    require(source==[pin(p,maximum=4*1024*1024) for p in source_files(virt)] and
        compiler_pin==base.fs_build.compiler_identity(compiler),'recovery owner sources/toolchain changed')
    return publish(out/'result.json',dict(schema=profile.SCHEMA+'-helper-h0',run_id_hex=run,virt=virt,
        source_inputs=source,compiler=compiler_pin,helper=base.fs_build.tool_identity(out/'helper-a'),
        table=pin(out/'table.bin'),table_count=generated['count'],boot_count=generated['boot'],
        journal_recovery=profile.execution_binding(selection),ab_identical=True,device_effects=0,live_authorized=False))


def audit(out,run,selection=None):
    value=read(out/'result.json');generated=headers(run,selection)
    require(value['schema']==profile.SCHEMA+'-helper-h0' and value['virt'] is False and value['run_id_hex']==run and
        value['journal_recovery']==profile.execution_binding(selection) and value['ab_identical'] is True and
        value['source_inputs']==[pin(p,maximum=4*1024*1024) for p in source_files()], 'recovery owner provenance differs')
    require(all((out/name).read_bytes()==data for name,data in generated['headers'].items()) and
        verify(value['table']).read_bytes()==generated['table'] and value['table_count']==generated['count'] and
        value['boot_count']==generated['boot'],'recovery owner seal/table differs')
    require((out/'helper-a').read_bytes()==(out/'helper-b').read_bytes() and
        base.fs_build.tool_identity(out/'helper-a')==value['helper'],'recovery owner ELF differs')
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--virt',action='store_true');a=p.parse_args()
    print(build(a.output,a.run_id,virt=a.virt))
