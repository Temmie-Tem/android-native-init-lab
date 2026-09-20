"""Shared declarative first-Debian inputs; no device action or authority."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
NAMESPACE = 'p401'
VERSION = 'v0.4.0-rc.1'
ROOTFS_SHA = 'e6d8ec4ef0f85da6668d780c7357314be923946e386ddbbcefd9bc54c0f57789'
RETAINED = ROOT / 'workspace/private/outputs/s22plus-native-ext4-v1/p399/build-1'
RETAINED_RESULT = dict(path=str(RETAINED / 'result.json'), size=70172,
    sha256='b6566e725e797004104cd6951ac0c805541d7d680b09be5e8fbf42ba16c0e078')
PLATFORM_PLAN = dict(path=str(RETAINED / 'runtime/native-sources/s22plus_fyg8_p286_e3_plan.h'), size=5316,
    sha256='57d7467887797d2377186e46cafecd2efaa9e660a5c48f7b543441251102c9f1')
EXECUTION_FILES = (
    'workspace/public/src/debian/s22plus_v1/handoff.c',
    'workspace/public/src/debian/s22plus_v1/device/target.inc.c',
    'workspace/public/src/debian/s22plus_v1/device/lab-usb',
    'workspace/public/src/debian/s22plus_v1/device/lab-qualify',
    'workspace/public/src/native-init/s22plus_native_ext4_v1.c',
    'workspace/public/src/native-init/s22plus_native_ext4_core_v1.h',
    'workspace/public/src/native-init/s22plus_fyg8_max77705_result_parser.inc.c',
)
