"""Tests for the V2805 card-first audio play discriminator."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIVE = REPO / "workspace/public/src/scripts/revalidation/native_audio_card_first_play_live_handoff_v2805.py"


def load_module():
    sys.path.insert(0, str(LIVE.parent))
    spec = importlib.util.spec_from_file_location("v2805_live", LIVE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NativeAudioCardFirstPlayV2805(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live = load_module()

    def test_preflight_reuses_v2804_candidate_and_v2321_rollback(self) -> None:
        module = self.live
        args = module.parse_args(["--dry-run"])
        state = module.preflight_state()
        payload = module.dry_run_payload(args, state)

        self.assertEqual(module.CYCLE, "V2805")
        self.assertEqual(module.base.CANDIDATE_VERSION, "0.9.314")
        self.assertEqual(module.base.CANDIDATE_TAG, "v2804-audio-adsp-kick-no-wait")
        self.assertIn("boot_linux_v2804_audio_adsp_kick_no_wait.img", str(module.base.CANDIDATE_IMAGE))
        self.assertIn("boot_linux_v2321_usb_clean_identity_rodata.img", " ".join(payload["commands"]["rollback"]))
        self.assertEqual(payload["commands"]["direct_adsp_boot"], ["audio", "adsp-boot-once", module.ADSP_TOKEN])
        self.assertTrue(payload["preflight_ok"], payload)

    def test_runner_orders_direct_adsp_before_deploy_before_play(self) -> None:
        text = LIVE.read_text(encoding="utf-8")

        self.assertLess(
            text.index('"candidate-audio-direct-adsp-boot-once"'),
            text.index("card_wait = wait_for_sound_card"),
        )
        self.assertLess(
            text.index("card_wait = wait_for_sound_card"),
            text.index("play_result = run_play_sequence"),
        )
        self.assertLess(
            text.index('hide_auto_menu(out_dir, steps, "before-direct-adsp")'),
            text.index('"candidate-audio-direct-adsp-boot-once"'),
        )
        self.assertLess(
            text.index('"runtime_artifacts": base.install_runtime_artifacts'),
            text.index('"candidate-audio-play-execute-listen"'),
        )
        self.assertLess(
            text.index('hide_auto_menu(out_dir, steps, "before-play")'),
            text.index('"candidate-audio-play-execute-listen"'),
        )
        self.assertIn('"run direct audio adsp-boot-once before runtime ACDB staging"', text)
        self.assertIn('"stage ACDB artifacts only after card publication"', text)

    def test_audio_status_parser_and_ready_gate(self) -> None:
        module = self.live
        summary = module.parse_audio_status(
            "\n".join([
                "audio.rpmsg.count=20 adsp_like=7 cdsp_like=0",
                "audio.sound_class.count=128 card_like=1 control_like=1",
                "audio.dev_snd.count=61 control_like=1 pcm_like=12",
                "audio.proc_asound_cards= 0 [sm8150tavilsndc]: sm8150-tavil-sn - sm8150-tavil-snd-card",
            ])
        )

        self.assertTrue(summary["has_adsp_rpmsg"], summary)
        self.assertTrue(summary["has_sound_card"], summary)
        self.assertTrue(summary["has_sound_control"], summary)
        self.assertTrue(module.status_ready(summary), summary)

    def test_report_path_and_decision_names_are_v2805_scoped(self) -> None:
        module = self.live
        text = LIVE.read_text(encoding="utf-8")

        self.assertIn("NATIVE_INIT_V2805_AUDIO_CARD_FIRST_PLAY_LIVE", str(module.REPORT_PATH))
        self.assertIn("v2805-card-first-direct-adsp-no-card-before-rollback", text)
        self.assertIn("v2805-card-first-deploy-lost-card-before-rollback", text)
        self.assertIn("v2805-card-first-play-pass-before-rollback", text)


if __name__ == "__main__":
    unittest.main()
