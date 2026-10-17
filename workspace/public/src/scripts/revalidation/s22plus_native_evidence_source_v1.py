"""Existing native transport with a separate fixed mountless evidence reader."""
from pathlib import Path
import s22plus_native_root_inspect_source_v1 as previous
import s22plus_native_evidence_profile_v1 as profile

ROOT=previous.ROOT
ROOT_EVIDENCE_PROFILE=profile.PROFILE


def __getattr__(name):return getattr(previous,name)


def profile_contract(record_run=None,selection=None):
    return dict(previous.profile_contract(),root_evidence_profile=ROOT_EVIDENCE_PROFILE,
        root_evidence=profile.binding(record_run,selection),persistent_writes=False)


def source_files():
    return tuple(sorted(set(previous.source_files())|{Path(__file__),Path(profile.__file__),
        ROOT/'workspace/public/src/native-init/s22plus_native_evidence_v1.c',
        ROOT/'workspace/public/src/native-init/s22plus_native_evidence_reader_v1.inc.c',
        ROOT/'workspace/public/src/native-init/s22plus_native_userspace_probe_v1.c',
        ROOT/'workspace/public/src/scripts/analysis/s22plus_native_evidence_h0.py'}))
