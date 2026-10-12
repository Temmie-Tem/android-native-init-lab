"""Unchanged native UFS/drain carrier with one fixed child calibration helper."""
from pathlib import Path
import s22plus_native_output_drain_source_v1 as previous
import s22plus_native_log_profile_v1 as profile

ROOT=previous.ROOT
LOG_CALIBRATION_PROFILE=profile.PROFILE


def __getattr__(name):return getattr(previous,name)


def profile_contract():
    return dict(previous.profile_contract(),log_calibration_profile=LOG_CALIBRATION_PROFILE,
        log_calibration_logger=profile.LOGGER,log_calibration_maximum=4*1024**2,
        log_calibration_owner='one-fixed-root-child',persistent_data_writes=False)


def source_files():
    return tuple(sorted(set(previous.source_files())|{Path(__file__),Path(profile.__file__),
        Path(profile.protocol.__file__),ROOT/'workspace/public/src/native-init/s22plus_native_log_calibration_v1.c',
        ROOT/'workspace/public/src/debian/s22plus_initramfs_h0/early-protocol.h',
        ROOT/'workspace/public/src/scripts/analysis/s22plus_native_log_h0.py'}))
