"""Host-only tests for the V2608 post-init send_audio_cal_v5 build."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import unittest

from _loader import load_revalidation

v2608 = load_revalidation("build_android_acdb_postinit_send_v5_combined_preload_v2608")


class V2608BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="a90-v2608-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def args(self, *, build: bool = False):
        class Args:
            pass

        args = Args()
        args.build = build
        args.write_report = False
        args.build_root = self.root / "build"
        args.manifest = args.build_root / "manifest.json"
        args.report = self.root / "report.md"
        args.clang = v2608.v2572.TOOLCHAIN_ROOT / "bin/clang"
        args.lld = v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld"
        args.readelf = "readelf"
        args.file = "file"
        return args

    def test_source_state_moves_send_v5_to_postinit_helper(self) -> None:
        state = v2608.source_state()
        required = state["required"]
        prohibited = state["prohibited"]
        self.assertTrue(required["helper_source_exists"])
        self.assertTrue(required["preinit_source_exists"])
        self.assertTrue(required["helper_calls_init_v3"])
        self.assertTrue(required["helper_arms_after_init_before_send"])
        self.assertTrue(required["helper_calls_send_v5_postinit"])
        self.assertTrue(required["preinit_patches_init_flag"])
        self.assertTrue(required["preinit_returns_after_patch"])
        self.assertFalse(prohibited["preinit_calls_send_audio_cal_v5"])
        self.assertFalse(prohibited["preinit_arms_capture"])
        self.assertFalse(prohibited["preinit_exits_process"])
        self.assertFalse(prohibited["combined_global_pthread_hooks"])
        self.assertTrue(state["required_ok"])
        self.assertTrue(state["prohibited_ok"])

    def test_payload_contract_documents_no_send_preinit_boundary(self) -> None:
        payload = v2608.make_payload(self.args(build=False))
        self.assertTrue(payload["ok"])
        contract = payload["capture_contract"]
        self.assertIn("V2600 acdbtap", contract["base"])
        self.assertIn("without arm/send/exit", contract["preinit"])
        self.assertIn("after init_v3 returns", contract["postinit"])
        self.assertIn("send_audio_cal_v5(15, 1, 0x11135", contract["per_device_call"])
        self.assertTrue(payload["measurement_boundary"]["no_native_replay"])
        self.assertTrue(payload["measurement_boundary"]["raw_payload_private_only"])

    def test_build_outputs_postinit_helper_and_no_pthread_preload_when_toolchain_present(self) -> None:
        if not ((v2608.v2572.TOOLCHAIN_ROOT / "bin/clang").exists() and (v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists()):
            self.skipTest("private Android ARM32 toolchain unavailable")
        payload = v2608.make_payload(self.args(build=True))
        self.assertTrue(payload["ok"], payload.get("build"))
        helper = payload["build"]["artifacts"]["helper"]
        preload = payload["build"]["artifacts"]["preload"]
        self.assertTrue(helper["checks"]["undefined_init_v3"])
        self.assertTrue(helper["checks"]["undefined_send_audio_cal_v5"])
        self.assertTrue(preload["checks"]["exports_acdb_ioctl"])
        self.assertTrue(preload["checks"]["exports_ioctl"])
        self.assertTrue(preload["checks"]["exports_common_topology"])
        self.assertTrue(preload["checks"]["exports_a90_arm_capture"])
        self.assertTrue(preload["checks"]["does_not_export_pthread_mutex_lock"])
        self.assertTrue(preload["checks"]["does_not_export_pthread_mutex_unlock"])
        self.assertTrue(preload["checks"]["does_not_export_android_log_print"])
        self.assertTrue(preload["checks"]["soname_v2608"])


if __name__ == "__main__":
    unittest.main()
