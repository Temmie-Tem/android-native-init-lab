"""Build the mountless evidence reader using the retained ARM64 toolchain."""
import argparse
from pathlib import Path
import shutil
import s22plus_native_root_inspect_h0 as base
import s22plus_native_evidence_profile_v1 as profile
from s22plus_native_records_v3 import pin,private_path,publish,read,require,verify

ROOT,NATIVE=base.ROOT,base.NATIVE


def build_libraries(archive,out):
    # Reuse the pinned upstream/configuration/toolchain builder. Its formatter
    # and checker outputs remain H0 inputs and are not packaged in this reader.
    base.fs_build.build_tools(archive,out)
    return seal_libraries(out)


def seal_libraries(out):
    result=pin(out/'result.json');value=read(verify(result))
    require(value['schema']=='s22plus-native-ext4-tools-h0-v1' and
        value['upstream']['sha256']==base.fs_build.UPSTREAM_SHA256,'unselected library build')
    source=out/'e2fsprogs-1.47.2';build=out/'build'
    headers=sorted(set((source/'lib/ext2fs').glob('*.h'))|set((source/'lib/et').glob('*.h'))|
        set((build/'lib/ext2fs').glob('*.h'))|set((build/'lib/et').glob('*.h'))|{build/'lib/config.h'})
    libraries=[build/'lib/libext2fs.a',build/'lib/libcom_err.a']
    selected=out/'sealed-inputs';selected.mkdir(mode=0o700)
    sealed_headers=[];sealed_libraries=[]
    # Upstream make uses hardlink aliases. Pin independent read-only copies,
    # preserving generated-header precedence without changing build outputs.
    for original in headers:
        tree=build/'lib' if original.is_relative_to(build) else source/'lib'
        copy=selected/('generated' if original.is_relative_to(build) else 'source')/original.relative_to(tree)
        copy.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,copy);copy.chmod(0o400)
        sealed_headers.append(pin(copy))
    for original in libraries:
        copy=selected/original.name;shutil.copyfile(original,copy);copy.chmod(0o400)
        sealed_libraries.append(pin(copy,maximum=16*1024*1024))
    return publish(out/'reader-libraries.json',dict(schema='s22plus-native-evidence-libraries-h0-v1',
        tools_result=result,upstream=value['upstream'],libraries=sealed_libraries,
        headers=sealed_headers,include_directories=[str(selected/'generated'),str(selected/'source'),str(selected/'source/et')],
        device_actions=0,live_authorized=False))


def source_files(virt=False):
    rows=set(base.source_files(userspace=True))|{Path(__file__),Path(profile.__file__),
        NATIVE/'s22plus_native_evidence_v1.c',NATIVE/'s22plus_native_evidence_reader_v1.inc.c'}
    if virt:rows.add(ROOT/'workspace/public/src/debian/s22plus_v1/device/virt-binding.inc.c')
    return sorted(rows)


def generated(run,record_run):
    table,count,boot=base.table_bytes()
    return dict(table=table,count=count,boot=boot,headers={
        's22plus_native_ext4_seal_v1.h':base.fs_build.seal(profile.inspection.filesystem.BINDING,run,initialize=False),
        's22plus_native_root_inspect_seal_v1.h':base.header(table,count,boot),
        's22plus_native_userspace_probe_seal_v1.h':base.userspace_header(),
        's22plus_native_evidence_seal_v1.h':profile.header(record_run)})


def evidence_binding(record_run):
    return dict(libraries=profile.LIBRARIES,record_run=record_run,files=[list(row) for row in profile.paths(record_run)],
        max_output=profile.MAXIMUM,mount=False,journal_replay=False,filesystem_writes=False)


def build(out,run,*,record_run=None,virt=False):
    out=private_path(ROOT,out,exists=False);require(not out.exists(),'fresh evidence reader build required')
    library=profile.library_inputs();sources=[pin(p,maximum=4*1024*1024) for p in source_files(virt)]
    seal=generated(run,record_run);out.mkdir(mode=0o700,parents=True)
    for name,body in seal['headers'].items():(out/name).write_bytes(body)
    (out/'table.bin').write_bytes(seal['table'])
    for row in sources:
        copy=out/'source-snapshot'/str(Path(row['path']).relative_to(ROOT));copy.parent.mkdir(parents=True,exist_ok=True)
        copy.write_bytes(verify(row).read_bytes());copy.chmod(0o400)
    compiler=shutil.which('aarch64-linux-gnu-gcc');require(compiler is not None,'ARM64 compiler absent')
    identity=base.fs_build.compiler_identity(compiler)
    flags=['-std=c11','-static','-Os','-fno-ident','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
        '-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable','-I',out,'-I',NATIVE]
    for path in library['include_directories']:flags+=['-I',path]
    if virt:flags+=['-DS22_ROOT_INSPECT_VIRT_TEST']
    for side in ('a','b'):
        base.fs_build.run([compiler,*flags,NATIVE/'s22plus_native_evidence_v1.c',
            *(verify(row) for row in library['libraries']),'-o',out/('helper-'+side)],
            cwd=ROOT,stdout=out/('compile-'+side+'.log'),timeout=60)
    require((out/'helper-a').read_bytes()==(out/'helper-b').read_bytes(),'evidence reader A/B differs')
    require(identity==base.fs_build.compiler_identity(compiler) and sources==[pin(p,maximum=4*1024*1024)
        for p in source_files(virt)],'evidence sources/compiler changed')
    profile.library_inputs()
    return publish(out/'result.json',dict(schema=profile.SCHEMA+'-helper-h0',run_id_hex=run,virt=virt,
        source_inputs=sources,compiler=identity,helper=base.fs_build.tool_identity(out/'helper-a'),
        table=pin(out/'table.bin'),table_count=seal['count'],boot_count=seal['boot'],
        root_evidence=evidence_binding(record_run),ab_identical=True,device_actions=0,live_authorized=False))


def audit(out,run,*,record_run=None):
    value=read(out/'result.json');seal=generated(run,record_run)
    require(value['schema']==profile.SCHEMA+'-helper-h0' and value['virt'] is False and
        value['run_id_hex']==run and value['root_evidence']==evidence_binding(record_run) and value['ab_identical'] is True and
        value['source_inputs']==[pin(p,maximum=4*1024*1024) for p in source_files()], 'evidence helper provenance differs')
    require(all((out/name).read_bytes()==body for name,body in seal['headers'].items()) and
        verify(value['table']).read_bytes()==seal['table'] and value['table_count']==seal['count'] and
        value['boot_count']==seal['boot'],'evidence reader seal/table differs')
    require((out/'helper-a').read_bytes()==(out/'helper-b').read_bytes() and
        base.fs_build.tool_identity(out/'helper-a')==value['helper'],'evidence helper ELF differs')
    profile.library_inputs();return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run-id');p.add_argument('--record-run');p.add_argument('--virt',action='store_true')
    p.add_argument('--libraries-from',type=Path);a=p.parse_args()
    print((build_libraries(a.libraries_from,a.output.absolute()) if a.libraries_from else
        build(a.output.absolute(),a.run_id,record_run=a.record_run,virt=a.virt))['sha256'])
