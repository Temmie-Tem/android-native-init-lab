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

import s22plus_fyg8_p334_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p334_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p334_stock_process_v2_adapter as adapter  # noqa: E402


OUTPUT = builder.DEFAULT_OUTPUT_ROOT
RESULT = OUTPUT / "result.json"


class P334StockCandidateBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = json.loads(RESULT.read_text(encoding="ascii"))

    def test_result_and_fresh_identity(self) -> None:
        payload = RESULT.read_bytes()
        self.assertEqual(len(payload), 50_133)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "765b70a794503e9819940926af3e975334368f551c5c766f5fd754fa8ea2868a",
        )
        self.assertEqual(self.value["schema"], builder.SCHEMA)
        self.assertEqual(self.value["verdict"], builder.VERDICT)
        self.assertEqual(self.value["run_id_hex"], builder.P334_RUN_ID_HEX)
        self.assertNotEqual(builder.P334_RUN_ID_HEX, builder.P333_RUN_ID_HEX)

    def test_ab_boot_only_candidate_is_new(self) -> None:
        candidate = self.value["phase2"]["candidate"]
        self.assertEqual(candidate["a"], candidate["b"])
        ap = candidate["a"]["ap_tar_md5"]
        self.assertEqual(
            ap,
            {
                "size": 28_631_081,
                "sha256": "d79ecf0721604dc30b32777e6a8bfdda54609198b09e3cf081d62446fcbaf7dc",
            },
        )
        self.assertNotEqual(ap, artifact.P333_AP_IDENTITY)
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertEqual(candidate["a"]["package"]["ap_tar_md5"], ap)

    def test_only_runtime_include_changes_from_p333_source_closure(self) -> None:
        predecessor = json.loads(builder.P333_RESULT.read_text(encoding="ascii"))
        changed = [
            name
            for name, receipt in predecessor["source_closure"].items()
            if self.value["source_closure"][name] != receipt
        ]
        self.assertEqual(changed, ["s22plus_fyg8_p290_e3_runtime.inc.c"])
        repair = self.value["lineage"]["runtime_repair"]
        self.assertEqual(
            repair["changed_anchors"],
            ["p333_publisher_entry", "stock_terminal_detail"],
        )
        self.assertTrue(repair["first_console_return_checkpoint_only"])
        self.assertTrue(repair["first_read_interpretation_requires_stage0_without_stage1"])
        self.assertFalse(repair["console_body_changed"])

    def test_init_and_image_join_fresh_run(self) -> None:
        joined = self.value["phase2"]["candidate"]["run_id_join"]["a"]
        self.assertTrue(joined["joined"])
        self.assertEqual(joined["run_id_hex"], builder.P334_RUN_ID_HEX)
        self.assertEqual(
            joined["init"]["identity"],
            {
                "size": 82_264,
                "sha256": "f4218f326d63b13f8ae6cea3034b3570476f6dd58ac31f525ecdf651ff9abdc9",
            },
        )
        self.assertEqual(
            joined["image"]["identity"],
            {
                "size": 41_490_944,
                "sha256": "7f1ecf568b474575d5258c91beeb9d721a3fee6ba527b3c88083ebf16af70cc2",
            },
        )

    def test_adapter_binds_only_p334_and_return_receipt(self) -> None:
        fixture = adapter.acceptance_fixture()
        self.assertEqual(fixture["run_id"], builder.P334_RUN_ID_HEX)
        self.assertTrue(fixture["first_console_return_checkpoint_only"])
        self.assertEqual(fixture["first_console_return_detail_prefix"], 0xB000)
        self.assertEqual(fixture["first_console_return_detail_sentinel"], 0xBFFF)
        self.assertIn(
            artifact.P333_PREDECESSOR_RUN_ID_HEX,
            fixture["predecessor_run_ids_rejected"],
        )
        self.assertEqual(
            adapter.audit()["verdict"],
            "PASS_P334_STOCK_PROCESS_V2_ADAPTER_H0_FIRST_CONSOLE_RETURN",
        )

    def test_artifact_helper_rejects_consumed_p333_ap(self) -> None:
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.inspect_ap(
                builder.P333_OUTPUT / "candidate-a/odin4/AP.tar.md5"
            )
        self.assertEqual(
            artifact.validate_p334_identity()["run_id_hex"],
            builder.P334_RUN_ID_HEX,
        )

    def test_codegen_preserves_console_body_exactly(self) -> None:
        p333_init = builder.P333_OUTPUT / "userspace-a/init"
        p334_init = OUTPUT / "userspace-a/init"
        command = [
            "aarch64-linux-gnu-objdump",
            "-d",
            "--disassemble=p328_framed_console",
        ]
        predecessor_text = subprocess.run(
            [*command, str(p333_init)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
        current_text = subprocess.run(
            [*command, str(p334_init)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout

        def instructions(value: str) -> list[tuple[int, int]]:
            result: list[tuple[int, int]] = []
            for line in value.splitlines():
                fields = line.strip().split()
                if len(fields) >= 2 and fields[0].endswith(":"):
                    try:
                        result.append((int(fields[0][:-1], 16), int(fields[1], 16)))
                    except ValueError:
                        pass
            return result

        predecessor = instructions(predecessor_text)
        current = instructions(current_text)
        self.assertEqual([address for address, _ in current], [address for address, _ in predecessor])
        self.assertEqual(len(current), 534)
        differences = [
            (old, new)
            for (_, old), (_, new) in zip(predecessor, current)
            if old != new
        ]
        self.assertEqual(len(differences), 9)
        immediate_mask = 0xFFF << 10
        for old, new in differences:
            self.assertEqual(old & ~immediate_mask, new & ~immediate_mask)
            self.assertEqual(((new >> 10) & 0xFFF) - ((old >> 10) & 0xFFF), 44)
        symbols = subprocess.run(
            ["aarch64-linux-gnu-nm", "-S", "-n", str(p334_init)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout
        line = next(item for item in symbols.splitlines() if item.endswith(" p328_framed_console"))
        self.assertEqual(line.split()[1], "0000000000000858")
        self.assertFalse(self.value["preservation"]["console_body_changed"])

    def test_audit_existing_reopens_exact_output(self) -> None:
        reopened = builder.audit_existing()
        self.assertEqual(reopened["verdict"], builder.VERDICT)
        self.assertEqual(
            reopened["phase2"]["candidate"]["a"],
            reopened["phase2"]["candidate"]["b"],
        )


if __name__ == "__main__":
    unittest.main()
