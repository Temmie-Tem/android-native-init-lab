"""Build the post-reap drain correction without modifying historical inputs."""
from pathlib import Path

import s22plus_native_ufs_build_v1 as previous
import s22plus_native_output_drain_source_v1 as source

ROOT,packaging,shared=previous.ROOT,previous.packaging,previous.shared
EXTRA_SOURCES=previous.EXTRA_SOURCES+[
    'workspace/public/src/scripts/revalidation/s22plus_native_output_drain_source_v1.py']


class Builder(previous.Builder):
    __file__=__file__
    source=source

    def __init__(self,declaration):
        super().__init__(declaration)
        self.DEFAULT_OUTPUT_ROOT=ROOT/('workspace/private/outputs/s22plus-native-output-drain-v1/'
            +declaration.IDENTITY.namespace+'/build-1')

    def source_receipts(self):
        rows=super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))]=packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def native_sources(self):
        rows=super().native_sources()
        helper=shared.packager.RUNTIME_INCLUDE_NAME
        rows[helper]=source.upgrade_native(rows[helper])
        return rows
