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

import s22plus_fyg8_p330_process_v2_candidate_static as static  # noqa: E402


class P330CandidateStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = static.DEFAULT_OUTPUT.read_bytes()
        cls.value = json.loads(cls.payload.decode("ascii"))

    def test_final_build_and_static_identity_are_bound(self) -> None:
        self.assertEqual(static.BUILDER_OUTPUT.name, "stock-candidate-build-v1-20260903-07")
        self.assertEqual(static.BUILDER_RESULT_IDENTITY["size"], 45_820)
        self.assertEqual(static.BUILDER_RESULT_IDENTITY["sha256"], "d2186404aaab0c1472d41d93a241c0ab32119561fe0a07ca231eb0b0ca3bacf1")
        self.assertEqual(static.RUN_ID, "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b")
        self.assertEqual(static.PREDECESSOR_RUN_ID, "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b")
        self.assertEqual(static.P330_AP_IDENTITY["sha256"], "f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b")
        self.assertEqual(static.ROLLBACK_IDENTITY["sha256"], "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56")
        self.assertEqual(static.validate_result(self.value), self.value)

    def test_candidate_is_boot_only_and_diagnostic_is_non_authoritative(self) -> None:
        candidate = self.value["candidate"]
        self.assertEqual(candidate["a"], candidate["b"])
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["boot_only"])
        self.assertEqual(candidate["a"]["ap_tar_md5"], static.P330_AP_IDENTITY)
        self.assertEqual(candidate["image"], static.P330_IMAGE_IDENTITY)
        self.assertEqual(candidate["init"], static.P330_INIT_IDENTITY)
        self.assertEqual(candidate["run_id_join"]["run_id_hex"], static.RUN_ID)
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        observer = self.value["observer_adapter"]
        self.assertEqual(observer["preauth_diagnostic_frame"], 0x86)
        self.assertEqual(observer["diagnostic_stages"], [1, 2])
        self.assertTrue(observer["eagain_only_retry"])
        self.assertTrue(observer["diagnostics_non_authoritative"])

    def test_all_device_and_authority_flags_remain_false(self) -> None:
        safety = self.value["safety"]
        self.assertTrue(safety["host_only"])
        for name in (
            "device_contact", "device_write", "odin_invoked", "odin_transfer",
            "flash", "partition_write", "live_authorized", "d0_authorized",
            "d1_authorized", "f1_authorized", "replay_authorized",
            "causal_result_allowed", "candidate_success",
        ):
            self.assertIs(safety[name], False)

    def test_consumed_p329_identity_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.value)
        mutated["run_id"] = static.PREDECESSOR_RUN_ID
        with self.assertRaises(static.StaticContractError):
            static._validate_p330(mutated)  # noqa: SLF001 - hostile H0 fixture


if __name__ == "__main__":
    unittest.main()
