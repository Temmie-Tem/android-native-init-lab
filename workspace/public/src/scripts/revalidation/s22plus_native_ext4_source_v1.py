"""Fixed filesystem roles over the admitted UFS/drain native runtime; H0 only."""
from pathlib import Path

import s22plus_native_output_drain_source_v1 as previous
import s22plus_native_ext4_profile_v1 as profile
from s22plus_native_records_v3 import read, verify

ROOT = previous.ROOT
BINDING = dict(path=str(ROOT / 'workspace/private/outputs/s22plus-native-ext4-h0-20260917-1/sealed-binding-4/binding.json'),
               size=4036, sha256='c1d4fdefc43c67a83b0a8f30867084c6bc0b1895f6866d29de5c43c5b88f6c94')


class Source:
    __file__ = __file__

    def __init__(self, initialize):
        self.INITIALIZE = initialize
        self.FILESYSTEM_PROFILE = profile.INITIALIZER_PROFILE if initialize else profile.READER_PROFILE

    def __getattr__(self, name):
        return getattr(previous, name)

    def profile_contract(self):
        return dict(previous.profile_contract(), filesystem_profile=self.FILESYSTEM_PROFILE,
                    format_compiled=self.INITIALIZE, binding=BINDING,
                    filesystem_witness_sha256=profile.WITNESS_SHA256)

    def source_files(self):
        return tuple(sorted(set(previous.source_files()) | {Path(__file__), Path(profile.__file__),
            previous.NATIVE / 's22plus_native_ext4_v1.c',
            previous.NATIVE / 's22plus_native_ext4_core_v1.h',
            ROOT / 'workspace/public/src/scripts/analysis/s22plus_native_ext4_h0.py'}))


READER = Source(False)
INITIALIZER = Source(True)


def binding_inputs():
    return read(verify(BINDING))
