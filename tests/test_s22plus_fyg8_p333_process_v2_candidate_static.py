from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
for directory in (
    ROOT / "workspace/public/src/scripts/analysis",
    ROOT / "workspace/public/src/scripts/revalidation",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import s22plus_fyg8_p333_process_v2_candidate_static as static  # noqa: E402


class P333CandidateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = static.build_result()

    def test_exact_candidate_and_single_runtime_delta(self) -> None:
        value = self.value
        self.assertEqual(value["run_id"], static.RUN_ID)
        self.assertEqual(value["predecessor_run_id"], static.PREDECESSOR_RUN_ID)
        self.assertEqual(value["candidate"]["a"], value["candidate"]["b"])
        self.assertEqual(
            value["candidate"]["a"]["ap_tar_md5"], static.P333_AP_IDENTITY
        )
        self.assertNotEqual(
            value["candidate"]["a"]["ap_tar_md5"], static.P332_AP_IDENTITY
        )
        self.assertEqual(
            value["runtime_repair"]["changed_anchors"], ["p332_publisher_entry"]
        )
        self.assertTrue(value["runtime_repair"]["entry_diagnostic_before_console"])

    def test_observer_and_source_closure_are_p333(self) -> None:
        observer = self.value["observer_adapter"]
        self.assertEqual(observer["entry_diagnostic_stage"], 0)
        self.assertEqual(observer["entry_diagnostic_count"], 2)
        self.assertTrue(observer["entry_diagnostic_before_console"])
        self.assertEqual(observer["session_cap"], 2)
        self.assertEqual(observer["reconnect_cap"], 0)
        self.assertTrue(observer["same_tty_fd"])
        self.assertEqual(
            {
                "p333_artifact_identity",
                "p333_open_entry_diag_acm_observer",
                "p333_open_entry_diag_runtime",
                "p333_stock_candidate_build",
                "p333_stock_process_v2_adapter",
            }
            - set(self.value["source_closure"]),
            set(),
        )

    def test_header_runtime_and_safety_mutations_reject(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["run_id"] = static.PREDECESSOR_RUN_ID
        with self.assertRaises(static.StaticContractError):
            static._validate_header(changed)  # noqa: SLF001
        changed = copy.deepcopy(self.value)
        changed["runtime_repair"]["entry_diagnostic_before_console"] = False
        with self.assertRaises(static.StaticContractError):
            static._validate_runtime(changed)  # noqa: SLF001
        changed = copy.deepcopy(self.value)
        changed["safety"]["live_authorized"] = True
        with self.assertRaises(static.StaticContractError):
            static._validate_safety(changed)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
