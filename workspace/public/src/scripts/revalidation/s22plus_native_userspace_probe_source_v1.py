"""The retained UFS/ACM runtime with a fixed protected Debian userspace probe."""
from pathlib import Path
import s22plus_native_root_inspect_source_v1 as previous
import s22plus_native_userspace_probe_profile_v1 as profile

ROOT = previous.ROOT
USERSPACE_PROBE_PROFILE = profile.PROFILE


def __getattr__(name):
    return getattr(previous, name)


def profile_contract():
    return dict(previous.profile_contract(), userspace_probe_profile=USERSPACE_PROBE_PROFILE,
        userspace_probe=profile.execution_binding())


def source_files():
    return tuple(sorted(set(previous.source_files()) | {Path(__file__), Path(profile.__file__),
        ROOT / 'workspace/public/src/native-init/s22plus_native_userspace_probe_v1.c'}))
