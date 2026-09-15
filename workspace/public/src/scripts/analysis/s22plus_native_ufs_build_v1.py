"""Build the fixed UFS loader without changing kernel or ramdisk inventories."""
from pathlib import Path
import hashlib

import s22plus_native_reconnect_build_v1 as previous
import s22plus_native_ufs_source_v1 as source
import s22plus_memory_manifest_v1 as memory

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_native_ufs_source_v1.py',
    'docs/operations/S22PLUS_NATIVE_UFS_V1.md']


def stock_inputs():
    vendor=memory.vendor
    expected=dict(size=vendor.EXPECTED_VENDOR_RAMDISK_SIZE,sha256=vendor.EXPECTED_VENDOR_RAMDISK_SHA256)
    compressed=memory.base.stable(ROOT/vendor.DEFAULT_VENDOR_RAMDISK,expected)
    raw=memory.boot_verify.decompress_lz4_stream_python(compressed,maximum=128*1024*1024)
    if len(raw)!=vendor.EXPECTED_VENDOR_NEWC_SIZE:raise ValueError('UFS vendor archive size differs')
    entries=memory.boot_verify.parse_newc(raw);files={row.name:row for row in entries}
    if len(files)!=len(entries):raise ValueError('duplicate UFS vendor archive name')
    rows=[]
    for name,runtime,size,sha in source.MODULES:
        entry=files['lib/modules/'+name]
        if ((entry.mode,entry.uid,entry.gid,entry.nlink)!=(0o100644,0,0,1)
                or len(entry.data)!=size or hashlib.sha256(entry.data).hexdigest()!=sha):
            raise ValueError('stock UFS module identity differs: '+name)
        rows.append(dict(name=name,runtime_name=runtime,size=size,sha256=sha,mode=0o100644))
    return dict(vendor_ramdisk=dict(path=str(vendor.DEFAULT_VENDOR_RAMDISK),**expected),modules=rows)


class Builder(previous.Builder):
    __file__=__file__
    source=source

    def __init__(self,declaration):
        super().__init__(declaration)
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-ufs-v1/'
            +declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows=super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))]=packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def runtime_value(self,out,resident,thermal):
        return dict(super().runtime_value(out,resident,thermal),
            schema='s22plus-native-ufs-runtime-v1',ufs=stock_inputs())
