from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import s22plus_fyg8_p331_process_v2_candidate_static as static  # noqa: E402


class P331CandidateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = static.DEFAULT_OUTPUT.read_bytes()
        cls.value = json.loads(cls.payload.decode("ascii"))

    def test_published_static_receipt_reopens_exactly(self) -> None:
        self.assertEqual(static.DEFAULT_OUTPUT.name, "process-v2-candidate-static-20260903-04.json")
        self.assertEqual(static.DEFAULT_OUTPUT.stat().st_mode & 0o777, 0o400)
        self.assertEqual(static.identity(self.payload), {"size": 30_639, "sha256": "22c73a1a83f18b655cf90a23ddcccceb82041c2f3f1343429d05d35ea0def4dc"})
        self.assertIs(static.validate_result(self.value), self.value)
        self.assertIs(static.validate_bound_result(self.value), self.value)

    def test_candidate_is_fresh_boot_only_and_rollback_is_exact(self) -> None:
        candidate = self.value["candidate"]
        self.assertEqual(candidate["a"], candidate["b"])
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["boot_only"])
        self.assertEqual(candidate["run_id_join"]["run_id_hex"], static.RUN_ID)
        self.assertNotEqual(candidate["a"]["ap_tar_md5"], static.P330_AP_IDENTITY)
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertEqual(self.value["artifact_identity"]["rollback"]["identity"], static.ROLLBACK_IDENTITY)

    def test_resident_observer_and_runtime_are_bounded(self) -> None:
        observer = self.value["observer_adapter"]
        self.assertEqual(observer["contract_id"], "s22plus-fyg8-p331-resident-acm-observer-v1")
        self.assertEqual(observer["proof_command_count"], 1)
        self.assertEqual(observer["session_cap"], 2)
        self.assertEqual(observer["reconnect_cap"], 1)
        self.assertTrue(observer["fixed_heartbeat_only"])
        runtime = self.value["runtime_repair"]
        self.assertEqual(runtime["run_id_hex"], static.RUN_ID)
        self.assertEqual(runtime["banner_scope"], "resident_loop_per_session")
        self.assertFalse(runtime["caller_selected_command"])

    def test_authority_flags_remain_false_and_p330_is_predecessor(self) -> None:
        self.assertEqual(self.value["predecessor_run_id"], static.PREDECESSOR_RUN_ID)
        self.assertEqual(
            self.value["builder_result"],
            {
                "path": "workspace/private/outputs/s22plus_fyg8_p331/stock-candidate-build-v1-20260903-03/result.json",
                **static.identity(static.BUILDER_RESULT.read_bytes()),
            },
        )
        safety = self.value["safety"]
        self.assertTrue(safety["host_only"])
        for name in (
            "device_contact", "device_write", "odin_invoked", "odin_transfer",
            "flash", "partition_write", "live_authorized", "d0_authorized",
            "d1_authorized", "f1_authorized", "replay_authorized",
            "causal_result_allowed", "candidate_success",
        ):
            self.assertIs(safety[name], False)

    def test_consumed_identity_mutation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.value)
        mutated["predecessor_run_id"] = static.RUN_ID
        with self.assertRaises(static.StaticContractError):
            static._validate_static_header(mutated)  # noqa: SLF001 - hostile H0 fixture


if __name__ == "__main__":
    unittest.main()
