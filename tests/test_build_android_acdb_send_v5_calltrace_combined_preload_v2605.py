"""Host-only tests for the V2605 send_audio_cal_v5 calltrace build."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import unittest

from _loader import load_revalidation

v2605 = load_revalidation("build_android_acdb_send_v5_calltrace_combined_preload_v2605")


class V2605BuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="a90-v2605-test-"))

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
        args.clang = v2605.v2572.TOOLCHAIN_ROOT / "bin/clang"
        args.lld = v2605.v2572.TOOLCHAIN_ROOT / "bin/ld.lld"
        args.readelf = "readelf"
        args.file = "file"
        return args

    def test_source_state_adds_metadata_only_calltrace(self) -> None:
        state = v2605.source_state()
        required = state["required"]
        prohibited = state["prohibited"]
        self.assertTrue(required["calltrace_source_exists"])
        self.assertTrue(required["calltrace_exports_mutex_lock"])
        self.assertTrue(required["calltrace_exports_mutex_unlock"])
        self.assertTrue(required["calltrace_exports_android_log_print"])
        self.assertTrue(required["calltrace_filters_send_v5_offsets"])
        self.assertTrue(required["calltrace_uses_send_symbol_base"])
        self.assertTrue(required["calltrace_logs_metadata_only"])
        self.assertFalse(prohibited["calltrace_opens_msm_audio_cal"])
        self.assertFalse(prohibited["calltrace_calls_acdb_ioctl"])
        self.assertFalse(prohibited["calltrace_calls_audio_set"])
        self.assertTrue(state["required_ok"])
        self.assertTrue(state["prohibited_ok"])

    def test_payload_contract_documents_calltrace_boundary(self) -> None:
        payload = v2605.make_payload(self.args(build=False))
        self.assertTrue(payload["ok"])
        contract = payload["capture_contract"]
        self.assertEqual(contract["base"], "V2603 combined preload")
        self.assertIn("pthread_mutex_lock", contract["traced_hooks"])
        self.assertIn("__android_log_print", contract["traced_hooks"])
        self.assertIn("send-v5-calltrace", contract["event_path"])
        self.assertTrue(payload["measurement_boundary"]["no_native_replay"])
        self.assertTrue(payload["measurement_boundary"]["raw_payload_private_only"])

    def test_build_outputs_export_calltrace_hooks_when_toolchain_present(self) -> None:
        if not ((v2605.v2572.TOOLCHAIN_ROOT / "bin/clang").exists() and (v2605.v2572.TOOLCHAIN_ROOT / "bin/ld.lld").exists()):
            self.skipTest("private Android ARM32 toolchain unavailable")
        payload = v2605.make_payload(self.args(build=True))
        self.assertTrue(payload["ok"], payload.get("build"))
        preload = payload["build"]["artifacts"]["preload"]
        checks = preload["checks"]
        self.assertTrue(checks["exports_acdb_ioctl"])
        self.assertTrue(checks["exports_ioctl"])
        self.assertTrue(checks["exports_common_topology"])
        self.assertTrue(checks["exports_a90_arm_capture"])
        self.assertTrue(checks["exports_pthread_mutex_lock"])
        self.assertTrue(checks["exports_pthread_mutex_unlock"])
        self.assertTrue(checks["exports_android_log_print"])


if __name__ == "__main__":
    unittest.main()
