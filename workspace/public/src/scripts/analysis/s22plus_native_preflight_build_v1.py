"""Package the pre-handoff producer and its sealed-record native observer."""
from pathlib import Path
import hashlib
import s22plus_native_output_drain_build_v1 as previous
import s22plus_native_preflight_source_v1 as source
import s22plus_native_preflight_h0 as producer
import s22plus_memory_manifest_v1 as memory
from s22plus_native_records_v3 import read, require, verify

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_native_preflight_source_v1.py',
    'workspace/public/src/scripts/analysis/s22plus_native_preflight_h0.py']


class Builder(previous.Builder):
    __file__=__file__
    source=source
    extra_member_modes={name:mode for name,(_,mode) in producer.MEMBERS.items()}

    def __init__(self,declaration):
        super().__init__(declaration)
        require(declaration.PREFLIGHT_PROFILE==source.PREFLIGHT_PROFILE,'unselected preflight composition')
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-preflight-v1/'+declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows=super().source_receipts()
        for path in (*producer.SOURCE_FILES,Path(__file__)):
            rows[str(path.relative_to(ROOT))]=packaging.identity(packaging.stable(path))
        return dict(sorted(rows.items()))

    def native_sources(self):
        return source.native_sources(super().native_sources())

    def build_native_init(self,out,resident):
        super().build_native_init(out,resident)
        producer.build(out/'preflight',self.declaration.IDENTITY.run_id_hex)

    def preflight_value(self,out):
        return producer.audit(out/'preflight',self.declaration.IDENTITY.run_id_hex)

    def runtime_value(self,out,resident,thermal):
        return dict(super().runtime_value(out,resident,thermal),preflight=self.preflight_value(out))

    def replacements(self,runtime):
        rows=super().replacements(runtime)
        value=self.preflight_value(self.DEFAULT_OUTPUT_ROOT/'runtime')
        _,old=shared.entries(packaging.stable(shared.REFERENCE/'candidate-a/boot.img'))
        artifact,_,_=producer.retained.prior_inputs()
        # The kernel combines the fixed vendor ramdisk with this boot ramdisk.
        # Match the exact retained source bytes, including the boot override.
        vendor=memory.vendor
        compressed=memory.base.stable(ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
            dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
        entries=memory.boot_verify.parse_newc(memory.boot_verify.decompress_lz4_stream_python(
            compressed,maximum=128*1024*1024))
        stock={row.name:row for row in entries}
        require(len(stock)==len(entries),'vendor module source has duplicate members')
        for module in artifact['modules']:
            name='lib/modules/'+module['name']
            member=old[name] if name in old else stock[name]
            require(len(member.data)==module['size'] and hashlib.sha256(member.data).hexdigest()==module['sha256'],
                'measured module bytes do not match the combined ramdisk')
        # Keep the observer's /bin/busybox intact. /busybox is the exact P405
        # static binary used only by the measurement's fixed child workloads.
        rows.update({name:verify(item['file']).read_bytes() for name,item in value['members'].items()})
        return rows

    def result_value(self,runtime,image,transform,packages):
        return dict(super().result_value(runtime,image,transform,packages),preflight=runtime['preflight'])
