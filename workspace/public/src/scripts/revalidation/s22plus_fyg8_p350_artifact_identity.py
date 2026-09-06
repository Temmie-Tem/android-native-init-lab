#!/usr/bin/env python3
"""P350 Image and boot/AP joins over the immutable P344 construction source.

Additional display asset and complete ramdisk checks belong to the P350 builder
and static promotion; this inherited validator does not claim those checks.
"""
from pathlib import Path
import hashlib

TEMPLATE_SOURCE = Path(__file__).with_name('s22plus_fyg8_p345_artifact_identity.py')
TEMPLATE_IDENTITY = {'size': 4090, 'sha256': 'db540159a31b3f82a67c91837e814aa873c74d2b373dd6eb2291bb2c107d5402'}
_template = TEMPLATE_SOURCE.read_bytes()
if {'size': len(_template), 'sha256': hashlib.sha256(_template).hexdigest()} != TEMPLATE_IDENTITY:
    raise ValueError('P350 artifact template identity differs')
_template = _template.replace(b'P345', b'P350').replace(b'p345', b'p350')
_template = _template.replace(b'c345f1e0a90b5e6d7c8a9b0c1d2e3f0a', b'c350f1e0a90b5e6d7c8a9b0c1d2e3f0a')
_template = _template.replace(b'b937b2aeb9d1b70a7b1a2de891412a94415960b91de7494cffd51fa1d0897ccf', b'b0cce78535eb553d493b8c7ca0117f390f4c4c5648899f8d2afcc182cb58276b')
exec(compile(_template, str(TEMPLATE_SOURCE) + '#p350', 'exec'), globals())

_base_identity = validate_p350_identity

def validate_p350_identity():
    value = _base_identity()
    value.update(read_only_child_required=False, normal_middle_command_readonly=True,
        fixed_display_once_child=True, arbitrary_root_shell=False,
        display_asset_validation_owner='P350 full ramdisk/static promotion',
        initial_session_count=3, same_fd_session_count=3,
        initial_reconnect_count=0, idle_seconds=0,
        total_session_count=3, total_command_count=9)
    return value

DISPLAY_MODULE_NAMES = ('msm_dma_iommu_mapping.ko','dev_ril_bridge.ko','sec_input_notifier.ko',
    'sec_panel_notifier.ko','lcd.ko','llcc-qcom.ko','msm-mmrm.ko','panel_event_notifier.ko','msm_drm.ko')
