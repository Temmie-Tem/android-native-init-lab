"""Build/audit the VALID-based thermal profile through the shared A/B readers."""
from pathlib import Path

import s22plus_native_thermal_build_v2 as previous
import s22plus_native_thermal_source_v3 as source

ROOT, packaging, shared = previous.ROOT, previous.packaging, previous.shared
EXTRA_SOURCES = previous.EXTRA_SOURCES + [
    'workspace/public/src/scripts/revalidation/s22plus_native_thermal_source_v3.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_thermal_observer_v3.py',
    'docs/operations/S22PLUS_NATIVE_THERMAL_V3.md']


class Builder(previous.Builder):
    __file__ = __file__
    source = source
    provider_profile = source

    def __init__(self, declaration):
        super().__init__(declaration)
        self.DEFAULT_OUTPUT_ROOT = ROOT/('workspace/private/outputs/s22plus-native-thermal-v3/'
            + declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows = super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))] = packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def native_sources(self):
        rows = super().native_sources()
        helper = shared.packager.RUNTIME_INCLUDE_NAME
        rows[helper] = source.upgrade_wire(rows[helper])
        return rows

    def native_init_value(self, out):
        value = super().native_init_value(out)
        return dict(value, private_ipc=dict(value['private_ipc'],
            sample_magic=source.SAMPLE_MAGIC, view_magic=source.VIEW_MAGIC))

    def runtime_value(self, out, resident, thermal):
        return dict(super().runtime_value(out, resident, thermal), schema='s22plus-native-thermal-runtime-v3')
