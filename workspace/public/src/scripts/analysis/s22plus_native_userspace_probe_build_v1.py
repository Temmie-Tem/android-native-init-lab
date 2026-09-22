"""Package the fixed unprivileged userspace callback with the existing root inspector."""
from pathlib import Path
import s22plus_native_root_inspect_build_v1 as previous
import s22plus_native_userspace_probe_source_v1 as source
from s22plus_native_records_v3 import require

ROOT, packaging = previous.ROOT, previous.packaging
EXTRA_SOURCES = previous.EXTRA_SOURCES + [
    'workspace/public/src/scripts/revalidation/s22plus_native_userspace_probe_source_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_userspace_probe_profile_v1.py',
    'docs/operations/S22PLUS_NATIVE_USERSPACE_PROBE_V1.md']


class Builder(previous.Builder):
    __file__ = __file__
    source = source
    userspace = True
    helper_member = 's22-userspace-probe'
    extra_member_modes = {helper_member: 0o500, 's22-root-inspect.table': 0o400}

    def __init__(self, declaration):
        super().__init__(declaration)
        require(declaration.USERSPACE_PROBE_PROFILE == source.USERSPACE_PROBE_PROFILE, 'unrecognized userspace probe')
        self.DEFAULT_OUTPUT_ROOT = ROOT / ('workspace/private/outputs/s22plus-native-userspace-probe-v1/' +
            declaration.IDENTITY.namespace + '/build-1')

    def source_receipts(self):
        rows = super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))] = packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def runtime_value(self, out, resident, thermal):
        return dict(super().runtime_value(out, resident, thermal), schema='s22plus-native-userspace-probe-runtime-v1')

    def result_value(self, runtime, image, transform, packages):
        return dict(super().result_value(runtime, image, transform, packages),
            userspace_probe=source.profile.execution_binding())
