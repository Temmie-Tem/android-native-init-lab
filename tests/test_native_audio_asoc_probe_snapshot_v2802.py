"""Tests for the V2802 ADSP -> ASoC probe snapshot runner."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIVE = REPO / "workspace/public/src/scripts/revalidation/native_audio_asoc_probe_snapshot_live_handoff_v2802.py"


def load_module():
    sys.path.insert(0, str(LIVE.parent))
    spec = importlib.util.spec_from_file_location("v2802_live", LIVE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NativeAudioAsocProbeSnapshotV2802(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live = load_module()

    def test_preflight_targets_v2799_candidate_and_v2321_rollback(self) -> None:
        module = self.live
        args = module.parse_args(["--dry-run"])
        state = module.preflight_state()
        payload = module.dry_run_payload(args, state)

        self.assertEqual(module.CYCLE, "V2802")
        self.assertEqual(module.CANDIDATE_VERSION, "0.9.312")
        self.assertEqual(module.CANDIDATE_TAG, "v2799-audio-native-ioctl-width")
        self.assertIn("boot_linux_v2799_audio_native_ioctl_width.img", str(module.CANDIDATE_IMAGE))
        self.assertIn("boot_linux_v2321_usb_clean_identity_rodata.img", " ".join(payload["commands"]["rollback"]))
        self.assertTrue(payload["preflight_ok"], payload)

    def test_scope_is_adsp_probe_only_not_playback_or_setcal(self) -> None:
        text = LIVE.read_text(encoding="utf-8")

        self.assertIn('ADSP_TOKEN = "AUD2_ONE_SHOT_ADSP_BOOT"', text)
        self.assertIn('["audio", "adsp-boot-once", ADSP_TOKEN]', text)
        self.assertIn('"no ACDB SET-cal, no route, no PCM, no playback"', text)
        self.assertNotIn('audio", "play"', text)
        self.assertNotIn('setcal_hold', text)
        self.assertNotIn('audio route', text)
        self.assertNotIn('pcm_write', text)

    def test_snapshot_captures_full_dmesg_platform_and_debug_asoc(self) -> None:
        text = LIVE.read_text(encoding="utf-8")

        self.assertIn('"dmesg_full": ["run", "/bin/busybox", "dmesg"]', text)
        self.assertIn("/sys/bus/platform/devices /sys/bus/platform/drivers", text)
        self.assertIn("/sys/kernel/debug/asoc", text)
        self.assertIn('f"candidate-{label}-{key}"', text)
        self.assertIn('result["snapshot_before"] = capture_snapshot(out_dir, steps, "before-adsp")', text)
        self.assertIn('result["snapshot_after"] = capture_snapshot(out_dir, steps, "after-adsp")', text)
        self.assertIn("candidate-audio-adsp-status-poll-", text)

    def test_audio_status_parser_extracts_card_and_control_state(self) -> None:
        module = self.live
        summary = module.parse_audio_status(
            "\n".join([
                "audio.rpmsg.count=20 adsp_like=7 cdsp_like=0",
                "audio.sound_class.count=128 card_like=1 control_like=1",
                "audio.dev_snd.count=61 control_like=1 pcm_like=12",
                "audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card sm8150-tavil-snd-card",
            ])
        )

        self.assertTrue(summary["has_adsp_rpmsg"], summary)
        self.assertTrue(summary["has_sound_card"], summary)
        self.assertTrue(summary["has_sound_control"], summary)
        self.assertFalse(summary["no_soundcards"], summary)


if __name__ == "__main__":
    unittest.main()
