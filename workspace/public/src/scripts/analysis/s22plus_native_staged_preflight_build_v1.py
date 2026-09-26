"""Package the stage helper, comparison table and fixed readonly checker."""
from pathlib import Path
import s22plus_native_root_inspect_build_v1 as previous
import s22plus_native_staged_preflight_source_v1 as source
from s22plus_native_records_v3 import require,verify

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_native_staged_preflight_source_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_staged_preflight_profile_v1.py',
    'docs/operations/S22PLUS_NATIVE_STAGED_PREFLIGHT_V1.md']


class Builder(previous.Builder):
    __file__=__file__
    source=source
    staged=True
    helper_member='s22-staged-preflight'
    extra_member_modes={helper_member:0o500,'s22-root-inspect.table':0o400,'s22-fs-e2fsck':0o500}

    def __init__(self,declaration):
        super().__init__(declaration)
        require(declaration.STAGED_PREFLIGHT_PROFILE==source.STAGED_PREFLIGHT_PROFILE,'unselected staged preparation')
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-staged-preflight-v1/'+declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows=super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))]=packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def replacements(self,runtime):
        rows=super().replacements(runtime)
        rows['s22-fs-e2fsck']=verify(source.profile.execution_binding()['checker']).read_bytes()
        # No ambient e2fsck settings may be introduced by either ramdisk.
        import s22plus_memory_manifest_v1 as memory
        _,boot=shared.entries(packaging.stable(shared.REFERENCE/'candidate-a/boot.img'))
        vendor=memory.vendor
        raw=memory.base.stable(ROOT/vendor.DEFAULT_VENDOR_RAMDISK,
            dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256))
        vendor_names={r.name for r in memory.boot_verify.parse_newc(memory.boot_verify.decompress_lz4_stream_python(raw,maximum=128*1024*1024))}
        require('etc/e2fsck.conf' not in boot and 'etc/e2fsck.conf' not in vendor_names,'ambient checker configuration exists')
        return rows

    def result_value(self,runtime,image,transform,packages):
        return dict(super().result_value(runtime,image,transform,packages),staged_preflight=source.profile.execution_binding())
