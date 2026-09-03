from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import s22plus_fyg8_p333_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p333_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p333_stock_process_v2_adapter as adapter  # noqa: E402


OUTPUT = builder.DEFAULT_OUTPUT_ROOT
RESULT = OUTPUT / "result.json"


class P333StockCandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads(RESULT.read_text(encoding="ascii"))

    def test_result_and_fresh_identity(self) -> None:
        payload = RESULT.read_bytes()
        self.assertEqual(len(payload), 48_548)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "9c3697ab3e9bba7a9d8e0ed038d0bbe69cf0e2c3da333cd433e338149398d03c",
        )
        self.assertEqual(self.value["schema"], builder.SCHEMA)
        self.assertEqual(self.value["verdict"], builder.VERDICT)
        self.assertEqual(self.value["run_id_hex"], builder.P333_RUN_ID_HEX)
        self.assertNotEqual(builder.P333_RUN_ID_HEX, builder.P332_RUN_ID_HEX)

    def test_ab_boot_only_candidate_is_new(self) -> None:
        candidate = self.value["phase2"]["candidate"]
        self.assertEqual(candidate["a"], candidate["b"])
        ap = candidate["a"]["ap_tar_md5"]
        self.assertEqual(
            ap,
            {
                "size": 28_631_081,
                "sha256": "1a6036b688ae92c94f459aee66e06a817e767aa615c6a7a9cb2a22b7d13487b3",
            },
        )
        self.assertNotEqual(ap, artifact.P332_AP_IDENTITY)
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertEqual(candidate["a"]["package"]["ap_tar_md5"], ap)

    def test_only_runtime_include_changes_from_p332_source_closure(self) -> None:
        predecessor = json.loads(builder.P332_RESULT.read_text(encoding="ascii"))
        changed = [
            name
            for name, receipt in predecessor["source_closure"].items()
            if self.value["source_closure"][name] != receipt
        ]
        self.assertEqual(changed, ["s22plus_fyg8_p290_e3_runtime.inc.c"])
        repair = self.value["lineage"]["runtime_repair"]
        self.assertEqual(repair["changed_anchors"], ["p332_publisher_entry"])
        self.assertTrue(repair["entry_diagnostic_before_console"])
        self.assertEqual(repair["entry_diagnostic_stage"], 0)

    def test_init_and_image_join_fresh_run(self) -> None:
        joined = self.value["phase2"]["candidate"]["run_id_join"]["a"]
        self.assertTrue(joined["joined"])
        self.assertEqual(joined["run_id_hex"], builder.P333_RUN_ID_HEX)
        self.assertEqual(
            joined["init"]["identity"],
            {
                "size": 82_264,
                "sha256": "e3d357a06de37578d6d013559fba0b724bfaf3a2dec467b600c80ece8bccffd4",
            },
        )
        self.assertEqual(
            joined["image"]["identity"],
            {
                "size": 41_490_944,
                "sha256": "f9b4465ba943bc4e1a473f0c133f5f3598e9e026f36791db140549b0edbd8e22",
            },
        )

    def test_adapter_binds_only_p333_and_entry_diagnostic(self) -> None:
        fixture = adapter.acceptance_fixture()
        self.assertEqual(fixture["run_id"], builder.P333_RUN_ID_HEX)
        self.assertEqual(fixture["entry_diagnostic_stage"], 0)
        self.assertTrue(fixture["entry_diagnostic_before_console"])
        self.assertIn(
            artifact.P332_PREDECESSOR_RUN_ID_HEX,
            fixture["predecessor_run_ids_rejected"],
        )
        self.assertEqual(
            adapter.audit()["verdict"],
            "PASS_P333_STOCK_PROCESS_V2_ADAPTER_H0_OPEN_ENTRY_DIAG",
        )

    def test_artifact_helper_rejects_consumed_p332_ap(self) -> None:
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.inspect_ap(
                builder.P332_OUTPUT / "candidate-a/odin4/AP.tar.md5"
            )
        self.assertEqual(
            artifact.validate_p333_identity()["run_id_hex"],
            builder.P333_RUN_ID_HEX,
        )

    def test_codegen_keeps_out_of_line_console_and_entry_diagnostics(self) -> None:
        init = OUTPUT / "userspace-a/init"
        symbols = subprocess.run(
            ["aarch64-linux-gnu-nm", "-S", "-n", str(init)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
        self.assertEqual(symbols.count(" p328_framed_console\n"), 1)
        disassembly = subprocess.run(
            ["aarch64-linux-gnu-objdump", "-d", "--disassemble=p318_run", str(init)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
        diagnostic = "<p330_write_diagnostic>"
        console = "<p328_framed_console>"
        self.assertEqual(disassembly.count(diagnostic), 2)
        self.assertEqual(disassembly.count(console), 2)
        first_diagnostic = disassembly.index(diagnostic)
        first_console = disassembly.index(console)
        second_diagnostic = disassembly.index(diagnostic, first_diagnostic + 1)
        second_console = disassembly.index(console, first_console + 1)
        self.assertLess(first_diagnostic, first_console)
        self.assertLess(first_console, second_diagnostic)
        self.assertLess(second_diagnostic, second_console)

    def test_audit_existing_reopens_exact_output(self) -> None:
        reopened = builder.audit_existing()
        self.assertEqual(reopened["verdict"], builder.VERDICT)
        self.assertEqual(reopened["phase2"]["candidate"]["a"], reopened["phase2"]["candidate"]["b"])


if __name__ == "__main__":
    unittest.main()
