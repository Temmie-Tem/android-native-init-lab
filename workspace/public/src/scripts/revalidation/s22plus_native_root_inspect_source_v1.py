"""The proved UFS/drain runtime with one separately bound inspection helper."""
from pathlib import Path
import s22plus_native_output_drain_source_v1 as previous
import s22plus_native_root_inspect_profile_v1 as profile

ROOT = previous.ROOT
ROOT_INSPECT_PROFILE = profile.PROFILE


def __getattr__(name):
    return getattr(previous, name)


def profile_contract():
    return dict(previous.profile_contract(), root_inspect_profile=ROOT_INSPECT_PROFILE,
        filesystem_binding=profile.filesystem.BINDING, rootfs_artifact=profile.ARTIFACT,
        consumed_terminal=profile.TERMINAL, block_ro='native-partition-until-reboot', persistent_writes=False)


def source_files():
    return tuple(sorted(set(previous.source_files()) | {Path(__file__), Path(profile.__file__),
        Path(profile.filesystem.__file__),
        ROOT / 'workspace/public/src/native-init/s22plus_native_root_inspect_v1.c',
        ROOT / 'workspace/public/src/native-init/s22plus_native_ext4_v1.c',
        ROOT / 'workspace/public/src/native-init/s22plus_native_ext4_core_v1.h',
        ROOT / 'workspace/public/src/scripts/analysis/s22plus_native_root_inspect_h0.py'}))
