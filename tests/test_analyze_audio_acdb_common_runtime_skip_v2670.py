import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "workspace/public/src/scripts/revalidation/analyze_audio_acdb_common_runtime_skip_v2670.py"
spec = importlib.util.spec_from_file_location("v2670", MODULE)
v2670 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = v2670
spec.loader.exec_module(v2670)


class AnalyzeAcdbCommonRuntimeSkipV2670(unittest.TestCase):
    def write_artifact_fixture(self, root: Path) -> None:
        (root / "acdb-v2668-direct-real-common-events.jsonl").write_text(
            "\n".join(
                [
                    '{"event":"v2668_direct_real_common","stage":"direct_loader_base","value":0xf3991000,"phase":0}',
                    json.dumps({"event": "v2668_direct_real_common", "stage": "init_common_enter", "code": 0}),
                    json.dumps({"event": "v2668_direct_real_common", "stage": "init_real_common_return", "code": 0}),
                    json.dumps({"event": "v2668_direct_real_common", "stage": "init_exit_after_real_common", "code": 0}),
                ]
            )
            + "\n"
        )
        ioctl_rows = []
        for cal_type in (2, 10, 14, 24, 39):
            ioctl_rows.append(
                {
                    "event": "ioctl_trace",
                    "name": "AUDIO_ALLOCATE_CALIBRATION",
                    "arg_snapshot": {"available": True, "cal_type": cal_type},
                }
            )
        ioctl_rows.append(
            {
                "event": "ioctl_trace",
                "name": "AUDIO_SET_CALIBRATION",
                "arg_snapshot": {"available": True, "cal_type": 39},
            }
        )
        (root / "ioctl-trace-events.jsonl").write_text("\n".join(json.dumps(row) for row in ioctl_rows) + "\n")
        (root / "setcal-events.jsonl").write_text(
            json.dumps(
                {
                    "event": "setcal_capture",
                    "sequence": 1,
                    "cal_type": 39,
                    "data_size": 32,
                    "cal_size": 4916,
                    "mem_handle": 30,
                    "set_arg": {"sha256": "a" * 64},
                    "dmabuf": {"status": "dumped", "sha256": "b" * 64},
                }
            )
            + "\n"
        )
        (root / "logcat-acdb-loader.txt").write_text(
            "ACDB -> CORE_CUSTOM_TOPOLOGIES\n"
            "ACDB -> acdb_loader_send_common_custom_topology: Common custom topology in use\n"
        )

    def sample_disassembly(self) -> str:
        return """
    90ea:       movs    r0, #24
    9160:       blx     #1
    91c8:       blx     #1
    924a:       movs    r0, #10
    92c6:       blx     #1
    92fc:       blx     #1
    93f6:       movs    r0, #14
    946a:       blx     #1
    94a0:       blx     #1
    9524:       movs    r0, #25
    959a:       blx     #1
    95d0:       blx     #1
"""

    def test_jsonl_stage_fallback_handles_unquoted_hex(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"stage":"direct_loader_base","value":0xf3991000,"phase":0}\n')
            rows = v2670.parse_jsonl_with_stage_fallback(path)
        self.assertEqual(rows[0]["stage"], "direct_loader_base")
        self.assertTrue(rows[0]["_parse_error"])
        self.assertEqual(rows[0]["phase"], 0)

    def test_analysis_classifies_common_runtime_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_artifact_fixture(root)
            analysis = v2670.analyze(root, disassembly_text=self.sample_disassembly())
        self.assertTrue(analysis.ok)
        self.assertEqual(analysis.set_cal_types_seen, [39])
        self.assertEqual(analysis.target_allocate_cal_types_seen, [10, 14, 24])
        self.assertEqual(analysis.missing_target_set_cal_types, [10, 14, 24])
        self.assertTrue(analysis.public_common_export_runtime_skips_lower_sets)
        self.assertTrue(analysis.lower_blocks_present)

    def test_markdown_records_redirect_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_artifact_fixture(root)
            analysis = v2670.analyze(root, disassembly_text=self.sample_disassembly())
            report = v2670.markdown(analysis)
        self.assertIn("another unchanged public-common capture run is low-information churn", report)
        self.assertIn("recover hidden ADM/ASM/AFE", report)
        self.assertIn("fake `AUDIO_SET_CALIBRATION`", report)
        self.assertNotIn("setcal-dmabuf", report)


if __name__ == "__main__":
    unittest.main()
