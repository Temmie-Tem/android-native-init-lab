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

import s22plus_fyg8_p332_process_v2_candidate_static as static  # noqa: E402


class P332CandidateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = static.DEFAULT_OUTPUT.read_bytes()
        cls.value = json.loads(cls.payload.decode("ascii"))

    def test_published_static_receipt_reopens_exactly(self) -> None:
        self.assertEqual(static.DEFAULT_OUTPUT.name, "process-v2-candidate-static-20260903-01.json")
        self.assertEqual(static.DEFAULT_OUTPUT.stat().st_mode & 0o777, 0o400)
        self.assertEqual(static.identity(self.payload)["size"], len(self.payload))
        self.assertEqual(len(static.identity(self.payload)["sha256"]), 64)
        self.assertIs(static.validate_result(self.value), self.value)
        self.assertIs(static.validate_bound_result(self.value), self.value)

    def test_candidate_is_fresh_boot_only_and_rollback_is_exact(self) -> None:
        candidate = self.value["candidate"]
        self.assertEqual(candidate["a"], candidate["b"])
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["boot_only"])
        self.assertEqual(candidate["run_id_join"]["run_id_hex"], static.RUN_ID)
        self.assertNotIn(
            candidate["a"]["ap_tar_md5"],
            (static.P330_AP_IDENTITY, static.P331_AP_IDENTITY),
        )
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertEqual(self.value["artifact_identity"]["rollback"]["identity"], static.ROLLBACK_IDENTITY)

    def test_resident_observer_and_runtime_are_bounded(self) -> None:
        observer = self.value["observer_adapter"]
        self.assertEqual(observer["contract_id"], static.resident_observer.CONTRACT_ID)
        self.assertEqual(observer["proof_command_count"], 3)
        self.assertEqual(observer["session_cap"], 2)
        self.assertEqual(observer["reconnect_cap"], 0)
        self.assertFalse(observer["fixed_heartbeat_only"])
        self.assertTrue(observer["fixed_p330_commands"])
        self.assertTrue(observer["same_tty_fd"])
        self.assertFalse(observer["host_tty_close_reopen"])
        self.assertFalse(observer["transport_reconnect"])
        runtime = self.value["runtime_repair"]
        self.assertEqual(runtime["run_id_hex"], static.RUN_ID)
        self.assertEqual(runtime["session_count"], 2)
        self.assertTrue(runtime["same_tty_fd"])
        self.assertFalse(runtime["close_open"])
        self.assertEqual(runtime["physical_reopen_count"], 0)
        self.assertFalse(runtime["caller_selected_command"])

    def test_authority_flags_remain_false_and_p330_is_predecessor(self) -> None:
        self.assertEqual(self.value["predecessor_run_id"], static.PREDECESSOR_RUN_ID)
        self.assertEqual(
            self.value["builder_result"],
            {
                "path": str(static.BUILDER_RESULT.relative_to(static.ROOT)),
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
