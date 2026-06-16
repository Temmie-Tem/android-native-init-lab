"""Host-only tests for the V2553 ACDB full-manifest capture build gate."""

from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2553 = load_revalidation("build_android_acdb_full_manifest_v2553")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2553-build-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "build_root": root / "build",
        "manifest_path": root / "manifest.json",
        "clang": v2553.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2553.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class AcdbFullManifestBuildV2553(unittest.TestCase):
    def test_source_state_pins_full_manifest_path_and_boundaries(self) -> None:
        state = v2553.source_state()

        self.assertTrue(state["required_ok"], [k for k, value in state["required"].items() if not value])
        self.assertTrue(state["prohibited_ok"], [k for k, value in state["prohibited"].items() if value])
        self.assertTrue(state["required"]["helper_calls_common_topology"])
        self.assertTrue(state["required"]["helper_calls_send_audio_cal_v5"])
        self.assertTrue(state["required"]["helper_speaker_acdb_id_15"])
        self.assertTrue(state["required"]["helper_app_type_69941"])
        self.assertTrue(state["required"]["tap_post_initialize_auto_arm"])
        self.assertTrue(state["required"]["tap_unarmed_path_has_no_dump_before_real"])
        self.assertTrue(state["required"]["tap_has_no_exit_macro"])
        self.assertFalse(state["prohibited"]["helper_issues_ioctl"])

    def test_manifest_dry_run_is_host_only_and_ready(self) -> None:
        payload = v2553.manifest(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["flash_action"], "none")
        self.assertEqual(payload["capture_contract"]["per_device_call"], "acdb_loader_send_audio_cal_v5(15, 0, 0x11135, 48000, 48000, 0, 1)")
        self.assertEqual(payload["build"]["built"], False)
        self.assertIn("post-INITIALIZE_V2 auto-arm", payload["capture_contract"]["preload_policy"])

    def test_private_build_outputs_helper_and_noexit_preload(self) -> None:
        payload = v2553.manifest(args(build=True))

        self.assertTrue(payload["ok"], payload.get("build"))
        helper = payload["build"]["helper"]
        preload = payload["build"]["preload"]
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertEqual(helper["mode"], "0o600")
        self.assertEqual(preload["mode"], "0o600")
        self.assertTrue(helper["checks"]["undefined_send_audio_cal_v5"])
        self.assertTrue(helper["checks"]["undefined_arm_capture"])
        self.assertTrue(preload["checks"]["exports_a90_arm_capture"])
        self.assertTrue(preload["checks"]["exports_acdb_ioctl"])
        self.assertTrue(preload["checks"]["exports_ioctl"])


if __name__ == "__main__":
    unittest.main()
