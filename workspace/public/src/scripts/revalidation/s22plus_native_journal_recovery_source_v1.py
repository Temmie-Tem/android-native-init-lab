"""Fixed existing native transport with a separately selected replay command."""
from pathlib import Path
import s22plus_native_root_inspect_source_v1 as previous
import s22plus_native_journal_recovery_profile_v1 as profile

ROOT=previous.ROOT
JOURNAL_RECOVERY_PROFILE=profile.PROFILE


def __getattr__(name):return getattr(previous,name)


def profile_contract(selection=None):
    return dict(previous.profile_contract(),journal_recovery_profile=JOURNAL_RECOVERY_PROFILE,
        journal_recovery=profile.execution_binding(selection),persistent_writes=True,
        block_ro='native-partition-restored-after-settled-replay')


def source_files():
    return tuple(sorted(set(previous.source_files())|{Path(__file__),Path(profile.__file__),
        Path(profile.handoff.__file__),
        ROOT/'workspace/public/src/scripts/revalidation/s22plus_debian_autoboot_profile_v1.py',ROOT/'workspace/public/src/native-init/s22plus_native_journal_recovery_v1.c',
        ROOT/'workspace/public/src/native-init/s22plus_journal_replay_strict_v1.inc.c',
        ROOT/'workspace/public/src/native-init/s22plus_native_userspace_probe_v1.c',
        ROOT/'workspace/public/src/native-init/s22plus_debian_handoff_root_v2.inc.c',
        ROOT/'workspace/public/src/scripts/analysis/s22plus_native_journal_recovery_h0.py',
        ROOT/'workspace/public/src/scripts/analysis/s22plus_journal_replay_tool_h0.py'}))
