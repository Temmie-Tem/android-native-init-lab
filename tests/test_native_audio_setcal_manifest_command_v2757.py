"""Tests for the V2757 native audio ACDB SET manifest command."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"


def source_text() -> str:
    return AUDIO_C.read_text(encoding="utf-8")


class NativeAudioSetcalManifestCommandV2757(unittest.TestCase):
    def test_setcal_command_is_exposed_as_explicit_audio_api(self) -> None:
        text = source_text()

        self.assertIn('strcmp(argv[1], "setcal") == 0', text)
        self.assertIn('return audio_setcal_cmd(argv, argc);', text)
        self.assertIn('usage: audio setcal [profile] [--dry-run|--execute] [--manifest PATH --verify]', text)
        self.assertIn('setcal [profile] [--dry-run|--execute] [--manifest PATH --verify]', text)

    def test_setcal_manifest_pins_corrected_replay_order_and_roles(self) -> None:
        text = source_text()

        self.assertIn('.acdb_set_order = {39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21}', text)
        for role in [
            "CORE_CUSTOM_TOPOLOGIES_BYTE_EXACT_SET",
            "AFE_FB_SPKR_PROT_HEADER_REAL_HAL_1",
            "AFE_FB_SPKR_PROT_HEADER_REAL_HAL_2",
            "APP_META_HEADER",
            "AFE_TOPOLOGY_HEADER",
            "AUDPROC_COMMON_PAYLOAD",
            "VOL_HEADER_NO_PAYLOAD",
            "ASM_STREAM_PAYLOAD",
            "AFE_TOPOLOGY_ID_HEADER",
            "AFE_COMMON_PAYLOAD",
            "SPEAKER_VI_HEADER",
        ]:
            with self.subTest(role=role):
                self.assertIn(f'.role = "{role}"', text)

    def test_setcal_manifest_rejects_stale_subsystem_topology_cals(self) -> None:
        text = source_text()

        self.assertIn('.forbidden_cal_types = {10, 14, 24}', text)
        self.assertIn('audio.setcal.forbidden_stale_cal_types', text)
        self.assertIn('audio_setcal_plan_matches_profile(profile)', text)
        self.assertIn('audio.setcal.error=plan-order-mismatch', text)

    def test_setcal_execute_mode_is_refused_before_any_ioctl(self) -> None:
        text = source_text()

        self.assertIn('audio.setcal.ioctl_attempted=0', text)
        self.assertIn('audio.setcal.execute_supported=0', text)
        self.assertIn('audio.setcal.refused=execute-not-implemented-native-setcal-ioctl', text)
        self.assertIn('return -EPERM;', text)
        execute_refusal = text.index('audio.setcal.refused=execute-not-implemented-native-setcal-ioctl')
        self.assertNotIn('AUDIO_SET_CALIBRATION', text[:execute_refusal])
        self.assertNotIn('SNDRV_CTL_IOCTL_ELEM_WRITE', text[text.index('static int audio_setcal_cmd'):execute_refusal])

    def test_setcal_manifest_declares_private_payload_boundary(self) -> None:
        text = source_text()

        self.assertIn('audio.setcal.private_payloads_required=1', text)
        self.assertIn('audio.setcal.exact_set_arg_replay=1', text)
        self.assertIn('audio.setcal.devices.msm_audio_cal=/dev/msm_audio_cal', text)
        self.assertIn('audio.setcal.devices.ion=/dev/ion', text)
        self.assertIn('audio.setcal.sequence=prepare_payloads,set_each,hold,deallocate_payload_entries_reverse', text)
        self.assertRegex(
            text,
            re.compile(r'\.cal_type = 39, .*?\.dmabuf_expected = true', re.DOTALL),
        )


if __name__ == "__main__":
    unittest.main()
