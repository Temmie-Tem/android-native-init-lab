"""Package the fixed filesystem endpoint and pinned ARM64 tools in fresh images."""
from pathlib import Path

import s22plus_native_output_drain_build_v1 as previous
import s22plus_native_ext4_source_v1 as source
import s22plus_native_ext4_profile_v1 as profile
import s22plus_native_ext4_h0 as producer
from s22plus_native_records_v3 import pin, read, require, verify

ROOT, packaging, shared = previous.ROOT, previous.packaging, previous.shared
EXTRA_SOURCES = previous.EXTRA_SOURCES + [
    'workspace/public/src/scripts/revalidation/s22plus_native_ext4_source_v1.py',
    'workspace/public/src/scripts/revalidation/s22plus_native_ext4_profile_v1.py',
    'workspace/public/src/scripts/analysis/s22plus_native_ext4_h0.py',
    'docs/operations/S22PLUS_NATIVE_EXT4_V1.md']


class Builder(previous.Builder):
    __file__ = __file__
    extra_member_modes = {'s22-fs': 0o500, 's22-fs-mke2fs': 0o500,
                          's22-fs-e2fsck': 0o500, 's22-fs-mke2fs.conf': 0o400}

    def __init__(self, declaration):
        super().__init__(declaration)
        require(declaration.FILESYSTEM_PROFILE in profile.PROFILES, 'unrecognized filesystem image role')
        self.source = source.INITIALIZER if declaration.FILESYSTEM_PROFILE == profile.INITIALIZER_PROFILE else source.READER
        self.DEFAULT_OUTPUT_ROOT = ROOT / ('workspace/private/outputs/s22plus-native-ext4-v1/'
                                           + declaration.IDENTITY.namespace + '/build-1')

    def source_receipts(self):
        rows = super().source_receipts()
        rows[str(Path(__file__).relative_to(ROOT))] = packaging.identity(packaging.stable(Path(__file__)))
        return dict(sorted(rows.items()))

    def build_native_init(self, out, resident):
        super().build_native_init(out, resident)
        producer.build_helper(source.BINDING, out / 'filesystem', self.declaration.IDENTITY.run_id_hex,
                              initialize=self.source.INITIALIZE)

    def filesystem_value(self, out):
        folder = out / 'filesystem'; value = read(folder / 'result.json')
        run = self.declaration.IDENTITY.run_id_hex
        require(value['schema'] == 's22plus-native-ext4-helper-h0-v1' and
                value['binding'] == source.BINDING and value['run_id_hex'] == run and
                value['initialize'] is self.source.INITIALIZE and value['ab_identical'] is True and
                value['source_inputs'] == [pin(path) for path in producer.SOURCE_FILES],
                'filesystem helper role or source differs')
        require((folder / 's22plus_native_ext4_seal_v1.h').read_bytes() ==
                producer.seal(source.BINDING, run, initialize=self.source.INITIALIZE),
                'filesystem compiled seal differs')
        require((folder / 'helper-a').read_bytes() == (folder / 'helper-b').read_bytes() and
                producer.tool_identity(folder / 'helper-a') == value['helper'],
                'filesystem helper bytes differ')
        verify(value['helper'])
        return value

    def runtime_value(self, out, resident, thermal):
        return dict(super().runtime_value(out, resident, thermal),
                    schema='s22plus-native-ext4-runtime-v1', filesystem=self.filesystem_value(out))

    def replacements(self, runtime):
        rows = super().replacements(runtime); binding = source.binding_inputs()
        helper = self.filesystem_value(self.DEFAULT_OUTPUT_ROOT / 'runtime')
        rows['s22-fs'] = Path(verify(helper['helper'])).read_bytes()
        for member, key in (('s22-fs-mke2fs', 'formatter'), ('s22-fs-e2fsck', 'checker'),
                            ('s22-fs-mke2fs.conf', 'configuration')):
            rows[member] = Path(verify(binding[key])).read_bytes()
        return rows

    def result_value(self, runtime, image, transform, packages):
        return dict(super().result_value(runtime, image, transform, packages),
                    filesystem=dict(binding=source.BINDING, helper=runtime['filesystem']['helper'],
                                    initialize=self.source.INITIALIZE))
