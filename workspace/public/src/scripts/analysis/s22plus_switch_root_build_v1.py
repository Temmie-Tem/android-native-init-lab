"""Package one native-first readonly transition and its separate RAM witness."""
from pathlib import Path
import re
import s22plus_native_output_drain_build_v1 as previous
import s22plus_switch_root_source_v1 as source
import s22plus_switch_root_h0 as producer
from s22plus_native_records_v3 import pin,require,verify

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_switch_root_source_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_switch_root_profile_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_switch_root_protocol_v1.py',
    'docs/operations/S22PLUS_SWITCH_ROOT_WITNESS_V1.md']


class Builder(previous.Builder):
    __file__=__file__
    source=source
    producer=producer
    profile_attribute='SWITCH_ROOT_PROFILE'
    extra_member_modes={'s22-switch-root':0o500,'s22-switch-witness':0o500,'s22-switch-busybox':0o500,
        's22-root-inspect.table':0o400,'s22-fs-e2fsck':0o500}

    def __init__(self,declaration):
        super().__init__(declaration)
        require(getattr(declaration,self.profile_attribute)==self.source.PROFILE,'unselected switch-root role')
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-switch-root-v1/'+declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows=super().source_receipts()
        for path in (*self.producer.source_files(),Path(__file__)):
            rows[str(path.relative_to(ROOT))]=packaging.identity(packaging.stable(path))
        return dict(sorted(rows.items()))

    def native_sources(self):
        rows=super().native_sources();name=shared.packager.RUNTIME_INCLUDE_NAME
        rows[name]=self.source.upgrade_native(rows[name],self.declaration.IDENTITY)
        return rows

    def key(self):
        _,sources=shared.reference_inputs();raw=sources[shared.packager.RUNTIME_INCLUDE_NAME]
        matches=re.findall(rb'static const uint8_t p328_auth_key\[P328_AUTH_KEY_SIZE\] = \{ ([^}]+) \};',raw)
        require(len(matches)==1,'native key declaration differs')
        key=bytes(int(v.strip().removesuffix(b'U'),16) for v in matches[0].split(b','))
        require(packaging.identity(key)==self.declaration.artifact.auth_key_identity(),'native key binding differs')
        return key

    def build_native_init(self,out,resident):
        super().build_native_init(out,resident)
        self.producer.build(out/'switch-root',self.declaration.IDENTITY.run_id_hex,self.key(),**self.helper_options())

    def helper_options(self):return {}

    def helper_value(self,out):
        return self.producer.audit(out/'switch-root',self.declaration.IDENTITY.run_id_hex,self.key(),**self.helper_options())

    def runtime_value(self,out,resident,thermal):
        return dict(super().runtime_value(out,resident,thermal),switch_root_helpers=self.helper_value(out))

    def replacements(self,runtime):
        rows=super().replacements(runtime);helpers=self.helper_value(self.DEFAULT_OUTPUT_ROOT/'runtime')
        for member,label in (('s22-switch-root','prepare'),('s22-switch-witness','witness'),
                ('s22-switch-busybox','busybox'),('s22-root-inspect.table','table'),('s22-fs-e2fsck','checker')):
            rows[member]=verify(helpers[label]).read_bytes()
        # Same no-ambient-configuration invariant as the staged checker.
        _,boot=shared.entries(packaging.stable(shared.REFERENCE/'candidate-a/boot.img'))
        import s22plus_memory_manifest_v1 as memory
        vendor=memory.vendor
        raw=memory.base.stable(ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
            dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
        names={r.name for r in memory.boot_verify.parse_newc(memory.boot_verify.decompress_lz4_stream_python(raw,maximum=128*1024*1024))}
        require('etc/e2fsck.conf' not in boot and 'etc/e2fsck.conf' not in names,'ambient checker configuration exists')
        return rows

    def result_value(self,runtime,image,transform,packages):
        helpers=runtime['switch_root_helpers'];folder=self.DEFAULT_OUTPUT_ROOT/'runtime/switch-root'
        root=dict(binding=producer.inspection.profile.filesystem.BINDING,artifact=producer.inspection.profile.ARTIFACT,
            terminal=producer.inspection.profile.TERMINAL,helper=helpers['prepare'],table=helpers['table'],
            table_count=helpers['table_count'],boot_count=helpers['boot_count'],max_hashed_bytes=512*1024*1024,
            kernel_partition_ro=True,persistent_writes=False)
        selection={name:helpers[name] for name in ('prepare','witness','busybox','checker')}
        selection.update(seconds=300,request=37,return_request=38,root_readonly=True,installed_exec=False,
            same_transport=True,helpers_result=pin(folder/'result.json'))
        return dict(super().result_value(runtime,image,transform,packages),root_inspection=root,switch_root=selection)
