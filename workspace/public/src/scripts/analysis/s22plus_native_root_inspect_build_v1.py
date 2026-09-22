"""Package a fixed read-only inspector over the retained native UFS runtime."""
from pathlib import Path
import s22plus_native_output_drain_build_v1 as previous
import s22plus_native_root_inspect_source_v1 as source
import s22plus_native_root_inspect_h0 as producer
from s22plus_native_records_v3 import read, require, verify

ROOT, packaging, shared = previous.ROOT, previous.packaging, previous.shared
EXTRA_SOURCES = previous.EXTRA_SOURCES + [
    'workspace/public/src/scripts/revalidation/s22plus_native_root_inspect_source_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_root_inspect_profile_v1.py',
    'workspace/public/src/scripts/analysis/s22plus_native_root_inspect_h0.py',
    'docs/operations/S22PLUS_NATIVE_ROOT_INSPECT_V1.md']


class Builder(previous.Builder):
    __file__ = __file__
    source = source
    extra_member_modes = {'s22-root-inspect': 0o500, 's22-root-inspect.table': 0o400}

    def __init__(self, declaration):
        super().__init__(declaration)
        require(declaration.ROOT_INSPECT_PROFILE == source.ROOT_INSPECT_PROFILE, 'unrecognized inspector role')
        self.DEFAULT_OUTPUT_ROOT = ROOT / ('workspace/private/outputs/s22plus-native-root-inspect-v1/' +
            declaration.IDENTITY.namespace + '/build-1')

    def source_receipts(self):
        rows = super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))] = packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def build_native_init(self, out, resident):
        super().build_native_init(out, resident)
        producer.build(out / 'root-inspector', self.declaration.IDENTITY.run_id_hex)

    def inspection_value(self, out):
        return producer.audit(out / 'root-inspector', self.declaration.IDENTITY.run_id_hex)

    def runtime_value(self, out, resident, thermal):
        return dict(super().runtime_value(out, resident, thermal),
            schema='s22plus-native-root-inspect-runtime-v1', root_inspection=self.inspection_value(out))

    def replacements(self, runtime):
        rows = super().replacements(runtime)
        value = self.inspection_value(self.DEFAULT_OUTPUT_ROOT / 'runtime')
        rows['s22-root-inspect'] = verify(value['helper']).read_bytes()
        rows['s22-root-inspect.table'] = verify(value['table']).read_bytes()
        return rows

    def result_value(self, runtime, image, transform, packages):
        folder = self.DEFAULT_OUTPUT_ROOT / 'runtime/root-inspector'
        return dict(super().result_value(runtime, image, transform, packages),
            root_inspection=producer.binding(folder, runtime['root_inspection']['helper']))
