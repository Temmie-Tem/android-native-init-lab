"""Host-only tests for the V2561 ACDB topology-skip per-device build gate."""

from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2561 = load_revalidation("build_android_acdb_toposkip_per_device_manifest_v2561")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2561-build-test-"))
    defaults: dict[str, object] = {
        "build": False,
        "build_root": root / "build",
        "manifest_path": root / "manifest.json",
        "clang": v2561.TOOLCHAIN_ROOT / "bin/clang",
        "lld": v2561.TOOLCHAIN_ROOT / "bin/ld.lld",
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class AcdbToposkipPerDeviceManifestBuildV2561(unittest.TestCase):
    def test_source_state_adds_topology_skip_interposer(self) -> None:
        state = v2561.source_state()

        self.assertTrue(state["required_ok"], [k for k, value in state["required"].items() if not value])
        self.assertTrue(state["prohibited_ok"], [k for k, value in state["prohibited"].items() if value])
        self.assertTrue(state["required"]["toposkip_exports_common_topology"])
        self.assertTrue(state["required"]["toposkip_default_visibility"])
        self.assertTrue(state["required"]["toposkip_returns_success"])
        self.assertTrue(state["required"]["toposkip_logs_private_marker"])
        self.assertFalse(state["prohibited"]["toposkip_calls_real_common_topology"])
        self.assertTrue(state["required"]["helper_calls_send_audio_cal_v5"])

    def test_manifest_dry_run_records_short_circuit_contract(self) -> None:
        payload = v2561.manifest(args())

        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertIn("short-circuits", payload["capture_contract"]["common_topology_call"])
        self.assertIn("common-topology short-circuit", payload["capture_contract"]["preload_policy"])
        self.assertEqual(payload["build"]["built"], False)

    def test_private_build_exports_common_topology_skip(self) -> None:
        payload = v2561.manifest(args(build=True))

        self.assertTrue(payload["ok"], payload.get("build"))
        helper = payload["build"]["helper"]
        preload = payload["build"]["preload"]
        self.assertTrue(helper["ok"], helper)
        self.assertTrue(preload["ok"], preload)
        self.assertEqual(helper["mode"], "0o600")
        self.assertEqual(preload["mode"], "0o600")
        self.assertTrue(preload["checks"]["exports_common_topology_skip"])
        self.assertTrue(preload["checks"]["does_not_hide_common_topology_skip"])
        self.assertTrue(preload["checks"]["exports_a90_arm_capture"])
        self.assertTrue(preload["checks"]["exports_acdb_ioctl"])
        self.assertTrue(preload["checks"]["exports_ioctl"])


if __name__ == "__main__":
    unittest.main()
