"""Host-only tests for the V2559 ACDB per-device manifest build gate."""

from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2559 = load_revalidation("build_android_acdb_per_device_manifest_v2559")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2559-build-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "build_root": root / "build",
        "manifest_path": root / "manifest.json",
        "clang": v2559.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2559.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class AcdbPerDeviceManifestBuildV2559(unittest.TestCase):
    def test_source_state_skips_common_topology_and_pins_per_device_path(self) -> None:
        state = v2559.source_state()

        self.assertTrue(state["required_ok"], [k for k, value in state["required"].items() if not value])
        self.assertTrue(state["prohibited_ok"], [k for k, value in state["prohibited"].items() if value])
        self.assertTrue(state["required"]["helper_no_decl_common_topology"])
        self.assertTrue(state["required"]["helper_skips_known_topology"])
        self.assertTrue(state["required"]["helper_pins_topology_sha"])
        self.assertTrue(state["required"]["helper_calls_send_audio_cal_v5"])
        self.assertTrue(state["required"]["helper_speaker_acdb_id_15"])
        self.assertTrue(state["required"]["helper_app_type_69941"])
        self.assertFalse(state["prohibited"]["helper_calls_common_topology"])
        self.assertFalse(state["prohibited"]["helper_issues_ioctl"])

    def test_manifest_dry_run_is_host_only_and_ready(self) -> None:
        payload = v2559.manifest(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["flash_action"], "none")
        self.assertEqual(payload["capture_contract"]["pinned_topology_sha256"], v2559.EXPECTED_TOPOLOGY_SHA256)
        self.assertEqual(payload["capture_contract"]["common_topology_call"], "skipped: payload already pinned by V2548/V2557 SHA-256")
        self.assertEqual(payload["capture_contract"]["per_device_call"], "acdb_loader_send_audio_cal_v5(15, 0, 0x11135, 48000, 48000, 0, 1)")
        self.assertEqual(payload["build"]["built"], False)

    def test_private_build_outputs_per_device_helper_and_noexit_preload(self) -> None:
        payload = v2559.manifest(args(build=True))

        self.assertTrue(payload["ok"], payload.get("build"))
        helper = payload["build"]["helper"]
        preload = payload["build"]["preload"]
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertEqual(helper["mode"], "0o600")
        self.assertEqual(preload["mode"], "0o600")
        self.assertTrue(helper["checks"]["undefined_send_audio_cal_v5"])
        self.assertTrue(helper["checks"]["undefined_arm_capture"])
        self.assertTrue(helper["checks"]["does_not_reference_common_topology"])
        self.assertTrue(preload["checks"]["exports_a90_arm_capture"])
        self.assertTrue(preload["checks"]["exports_acdb_ioctl"])
        self.assertTrue(preload["checks"]["exports_ioctl"])


if __name__ == "__main__":
    unittest.main()
