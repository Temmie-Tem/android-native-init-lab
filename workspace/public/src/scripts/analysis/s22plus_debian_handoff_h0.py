"""Build the fixed installed-Debian extension, including its first sysinit hook."""
import argparse
import hashlib
import json
from pathlib import Path
import s22plus_switch_root_h0 as base
import s22plus_debian_handoff_profile_v1 as profile
from s22plus_native_records_v3 import pin,read,require,verify

ROOT,NATIVE=base.ROOT,base.NATIVE


def source_files(virt=False):
    return sorted(set(base.source_files(virt))|{Path(__file__),Path(profile.__file__),
        *(NATIVE/n for n in ('s22plus_debian_handoff_v1.h','s22plus_debian_handoff_common_v1.inc.c',
        's22plus_debian_handoff_prepare_v1.inc.c','s22plus_debian_handoff_witness_v1.inc.c',
        's22plus_debian_handoff_hook_v1.c'))})


def validate_options(options,virt):
    require(set(options)=={'namespace','version','fault'} and type(options['fault']) is int and
        options['fault'] in range(7) and (not options['fault'] or virt),'Debian build options differ')


def prepare_headers(out,run,options,virt):
    (out/'s22plus_debian_handoff_seal_v1.h').write_bytes(
        profile.header(options['namespace'],options['version'],run,virt=virt))
    _,assets=profile.payloads(virt=virt)
    for name,data in assets.items():
        (out/name).write_bytes(data);(out/name).chmod(0o400 if name=='inittab' else 0o500)


def asset_rows(out,hook,virt):
    return [('hook',hook),*((name,pin(out/name)) for name in ('inittab','qualify',*(('usb',) if virt else ())))]


def payload_bytes(out,hook,virt):
    text='struct dh_asset { const char *source,*name; uint64_t size; unsigned mode; uint8_t digest[32]; };\n'
    text+='static const struct dh_asset dh_assets[]={\n'
    for name,row in asset_rows(out,hook,virt):
        text+='{'+json.dumps('/s22-debian-'+name)+','+json.dumps(name)+','+str(row['size'])+'ULL,'
        text+=('0400' if name=='inittab' else '0500')+',{'+','.join(map(str,bytes.fromhex(row['sha256'])))+'}},\n'
    return (text+'};\n').encode()


def payload_header(out,hook,virt):
    (out/'s22plus_debian_handoff_payload_v1.h').write_bytes(payload_bytes(out,hook,virt))


def result_fields(out,hook,options,virt):
    init,_=profile.payloads(virt=virt)
    return dict(debian=options,assets=dict(asset_rows(out,hook,virt)),
        installed_init=dict(size=len(init),sha256=hashlib.sha256(init).hexdigest()))


def build(out,run,key,*,namespace,version,virt=False,fault=0):
    return base.build(out,run,key,virt=virt,debian=dict(namespace=namespace,version=version,fault=fault))


def audit(out,run,key,*,namespace,version):
    value=read(out/'result.json');options=dict(namespace=namespace,version=version,fault=0)
    require(value['schema']=='s22plus-debian-handoff-helpers-h0-v1' and value['virt'] is False and
        value['debian']==options and value['fault']==value['checker_fault']==0 and value['run_id_hex']==run and
        value['key_sha256']==hashlib.sha256(key).hexdigest() and
        value['sources']==[pin(p,maximum=4*1024*1024) for p in source_files()] and value['ab_identical'] is True,
        'Debian helper provenance differs')
    for label in ('hook','witness','prepare'):
        require(base.inspection.fs_build.tool_identity(out/(label+'-a'))==value[label] and
            (out/(label+'-a')).read_bytes()==(out/(label+'-b')).read_bytes(),'Debian helper ELF differs')
    table,count,boot=base.inspection.table_bytes()
    require(value['table_count']==count and value['boot_count']==boot and verify(value['table']).read_bytes()==table and
        value['busybox']==base.busybox() and value['checker']==base.staged.execution_binding()['checker'],
        'Debian admission or tool identity differs')
    generated={
        's22plus_native_ext4_seal_v1.h':base.inspection.fs_build.seal(profile.inspection.filesystem.BINDING,run,initialize=False),
        's22plus_native_root_inspect_seal_v1.h':base.inspection.header(table,count,boot),
        's22plus_native_userspace_probe_seal_v1.h':base.inspection.userspace_header(),
        's22plus_native_staged_preflight_seal_v1.h':base.staged.header(),
        's22plus_switch_root_seal_v1.h':base.seal(run,key),
        's22plus_switch_root_payload_v1.h':base.payload_header(value['witness']),
        's22plus_debian_handoff_seal_v1.h':profile.header(namespace,version,run),
        's22plus_debian_handoff_payload_v1.h':payload_bytes(out,value['hook'],False)}
    require(all((out/name).read_bytes()==data for name,data in generated.items()),'Debian generated header differs')
    _,assets=profile.payloads()
    require(all(verify(value['assets'][name]).read_bytes()==data for name,data in assets.items()) and
        all(value[k]==v for k,v in result_fields(out,value['hook'],options,False).items()),'Debian RAM asset differs')
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--key',type=Path,required=True)
    p.add_argument('--namespace',required=True);p.add_argument('--version',required=True)
    p.add_argument('--virt',action='store_true');p.add_argument('--fault',type=int,default=0)
    args=p.parse_args();print(build(args.output,args.run_id,args.key.read_bytes(),namespace=args.namespace,
        version=args.version,virt=args.virt,fault=args.fault)['sha256'])
