"""Host-only tests for the V2611 meta-list post-init send_audio_cal_v5 build."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import unittest

from _loader import load_revalidation

v2611 = load_revalidation("build_android_acdb_meta_list_postinit_send_v5_combined_preload_v2611")


class V2611BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="a90-v2611-test-"))

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
        args.clang = v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang"
        args.lld = v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld"
        args.readelf = "readelf"
        args.file = "file"
        return args

    def test_source_state_uses_empty_meta_list_head(self) -> None:
        state = v2611.source_state()
        required = state["required"]
        prohibited = state["prohibited"]
        self.assertTrue(required["helper_source_exists"])
        self.assertTrue(required["helper_prepares_empty_meta_list"])
        self.assertTrue(required["helper_logs_meta_list_before_init"])
        self.assertTrue(required["helper_calls_init_v3_with_meta_head"])
        self.assertTrue(required["helper_arms_after_init_before_send"])
        self.assertTrue(required["helper_calls_send_v5_corrected_order"])
        self.assertTrue(required["preinit_still_no_send"])
        self.assertTrue(required["preinit_still_patches_init_flag"])
        self.assertFalse(prohibited["helper_passes_zero_arg3"])
        self.assertFalse(prohibited["preinit_exits_process"])
        self.assertFalse(prohibited["helper_native_speaker_write"])
        self.assertFalse(prohibited["helper_real_audio_set_literal"])
        self.assertTrue(state["required_ok"])
        self.assertTrue(state["prohibited_ok"])

    def test_payload_contract_documents_meta_list_boundary(self) -> None:
        payload = v2611.make_payload(self.args(build=False))
        self.assertTrue(payload["ok"])
        contract = payload["capture_contract"]
        self.assertIn("meta-list", contract["base"])
        self.assertIn("empty circular meta-list", contract["init_arg3"])
        self.assertIn("after init_v3 returns", contract["postinit"])
        self.assertIn("send_audio_cal_v5(15, 1, 0x11135", contract["per_device_call"])
        self.assertTrue(payload["measurement_boundary"]["no_native_replay"])
        self.assertTrue(payload["measurement_boundary"]["raw_payload_private_only"])

    def test_build_outputs_meta_list_helper_when_toolchain_present(self) -> None:
        toolchain = v2611.v2608.v2572.TOOLCHAIN_ROOT
        if not ((toolchain / "bin/clang").exists() and (toolchain / "bin/ld.lld").exists()):
            self.skipTest("private Android ARM32 toolchain unavailable")
        payload = v2611.make_payload(self.args(build=True))
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
        self.assertTrue(preload["checks"]["soname_v2611"])


if __name__ == "__main__":
    unittest.main()
