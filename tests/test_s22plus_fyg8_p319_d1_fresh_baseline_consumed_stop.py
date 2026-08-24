from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
D1_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_d1_fresh_baseline.py"
)
TAXONOMY = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_campaign_ledger_taxonomy.py"
)
BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v1.json"
)
RUN_PARENT = ROOT / "workspace/private/runs/device-action-d1-p319-fresh-baseline"
RUN_DIR = RUN_PARENT / "p319-fresh-baseline-1"
ARM = RUN_PARENT / "p319-fresh-baseline-1.arm.json"
START = RUN_DIR / "start.json"
RESULT = RUN_DIR / "result.json"
STOP = RUN_DIR / "stop.json"
ADB_SNAPSHOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/d1-fresh-baseline-v1/"
    "adb-05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
)
D0_RUN = RUN_PARENT / "d0-p319-fresh-baseline-1"
D0_ARM = RUN_PARENT / "d0-p319-fresh-baseline-1.arm.json"
D0_STOP = RUN_PARENT / "d0-p319-fresh-baseline-1.stop.json"
FRESH_RESULT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/fresh-baseline-v1/result.json"
)
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_D1_FRESH_BASELINE_CONSUMED_STOP_2026-08-24.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identity(path: Path) -> tuple[int, str, int, int]:
    info = path.lstat()
    payload = path.read_bytes()
    return (
        len(payload),
        hashlib.sha256(payload).hexdigest(),
        stat.S_IMODE(info.st_mode),
        info.st_nlink,
    )


class P319D1FreshBaselineConsumedStopTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d1 = load_module("p319_d1_consumed_stop_tested", D1_SOURCE)
        cls.taxonomy = load_module("p319_d1_stop_taxonomy_tested", TAXONOMY)
        cls.arm = json.loads(ARM.read_bytes())
        cls.stop = json.loads(STOP.read_bytes())
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.ledger = LEDGER.read_text(encoding="utf-8")
        cls.goal = GOAL.read_text(encoding="utf-8")

    def test_exact_arm_snapshot_stop_and_reviewed_validator(self):
        self.assertEqual(
            identity(ARM),
            (
                708,
                "1d64712e342968ae6a3574104248ea93f485cd8247db6c646bc47f57275d8aa7",
                0o400,
                1,
            ),
        )
        self.assertEqual(
            identity(ADB_SNAPSHOT),
            (
                716968,
                "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226",
                0o500,
                1,
            ),
        )
        self.assertEqual(
            identity(STOP),
            (
                943,
                "ad0cae49fd88cadbcb6f7be54afca6448b3fa4cd2cb2b02a1c0bfab2ab6bc326",
                0o400,
                1,
            ),
        )
        self.assertEqual(self.d1.validate_stop_file(STOP.resolve()), self.stop)

    def test_fixed_namespace_and_downstream_artifacts_are_absent(self):
        run_info = RUN_DIR.lstat()
        self.assertTrue(stat.S_ISDIR(run_info.st_mode))
        self.assertEqual(stat.S_IMODE(run_info.st_mode), 0o700)
        self.assertEqual({path.name for path in RUN_DIR.iterdir()}, {"stop.json"})
        self.assertEqual(
            {path.name for path in RUN_PARENT.iterdir()},
            {"p319-fresh-baseline-1", "p319-fresh-baseline-1.arm.json"},
        )
        for path in (START, RESULT, D0_RUN, D0_ARM, D0_STOP, FRESH_RESULT):
            with self.subTest(path=path):
                self.assertFalse(path.exists())
                self.assertFalse(path.is_symlink())

    def test_stop_is_consumed_before_start_and_cannot_replay(self):
        manifest = {
            "path": (
                "workspace/public/src/device-action/bindings/"
                "s22plus_fyg8_p319_d1_fresh_baseline_v1.json"
            ),
            "sha256": "0a91beec8cad13622bb29c2f7865a08d37fd4531da984b9423024f6f7b9dd63b",
            "size": 4128,
        }
        self.assertEqual(identity(BINDING)[:2], (4128, manifest["sha256"]))
        self.assertEqual(self.arm["execution_manifest"], manifest)
        self.assertEqual(self.stop["execution_manifest"], manifest)
        self.assertTrue(self.arm["consumed"])
        self.assertEqual(self.arm["attempt"], 1)
        self.assertEqual(self.stop["stage"], "after-arm-before-start")
        self.assertEqual(self.stop["error_type"], "D0Error")
        self.assertEqual(self.stop["approval_sha256"], self.arm["approval_sha256"])
        self.assertTrue(self.stop["arm_present"])
        self.assertTrue(self.stop["arm_bytes_complete"])
        self.assertTrue(self.stop["device_contact_unknown"])
        for key in (
            "start_present",
            "start_bytes_complete",
            "result_present",
            "result_bytes_complete",
            "result_reusable",
            "reboot_dispatch_possible",
            "candidate_transfer",
            "partition_payload",
            "odin",
            "download_transition",
            "f1_authorized",
            "replay_authorized",
        ):
            with self.subTest(key=key):
                self.assertFalse(self.stop[key])

    def test_report_goal_and_ledger_preserve_no_replay_and_accounting(self):
        for token in (
            "2026-08-24T11:17:59Z",
            "20:17:59 KST",
            "after-arm-before-start",
            "HEALTH_PENDING / NO_PROOF_OBSERVER",
            "does not infer a cause",
            "no reboot command was dispatched",
            "D0 fresh-baseline acquisition cannot begin",
            "There was no retry",
        ):
            self.assertIn(token, self.report)
        self.assertIn("d1-fresh-baseline-1", self.goal)
        self.assertIn("device contact is unknown", self.goal)
        self.assertIn("formal health is pending", self.goal)
        rows = [
            line
            for line in self.ledger.splitlines()
            if " | d1-fresh-baseline-1 | " in line
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn(" | D1 | ", row)
        self.assertIn(
            "P319_D1_FRESH_BASELINE_STOP_AFTER_ARM_BEFORE_START_NO_REPLAY", row
        )
        self.assertIn(" | HEALTH_PENDING | NO_PROOF_OBSERVER | 0/0 | ", row)
        self.assertNotIn("PASS_GO_", row)
        self.assertNotIn("_REVIEW_PENDING", row)
        data = LEDGER.read_bytes()
        lines = data.split(self.taxonomy.MARKER, 1)[1].splitlines(keepends=True)
        parsed, _, _ = self.taxonomy.parse_log_rows(lines)
        accounting = self.taxonomy.audit_review_obligations(parsed)
        self.assertEqual(
            (
                accounting["total"],
                accounting["resolved_count"],
                accounting["unresolved_count"],
            ),
            (60, 43, 17),
        )


if __name__ == "__main__":
    unittest.main()
