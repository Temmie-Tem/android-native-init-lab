"""The proven native startup with a separately invoked streamed preparation."""
from pathlib import Path
import s22plus_native_root_inspect_source_v1 as previous
import s22plus_native_staged_preflight_profile_v1 as profile

ROOT=previous.ROOT
STAGED_PREFLIGHT_PROFILE=profile.PROFILE


def __getattr__(name):return getattr(previous,name)


def profile_contract():
    return dict(previous.profile_contract(),staged_preflight_profile=STAGED_PREFLIGHT_PROFILE,
        staged_preflight=profile.execution_binding())


def source_files():
    return tuple(sorted(set(previous.source_files())|{Path(__file__),Path(profile.__file__),
        ROOT/'workspace/public/src/native-init/s22plus_native_staged_preflight_v1.c',
        ROOT/'workspace/public/src/native-init/s22plus_native_userspace_probe_v1.c'}))
