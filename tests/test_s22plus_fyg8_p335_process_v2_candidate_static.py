from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import s22plus_fyg8_p335_process_v2_candidate_static as static  # noqa: E402


class P335CandidateStaticTests(unittest.TestCase):
    def test_header_identity_and_observer_projection(self) -> None:
        self.assertEqual(static.RUN_ID, "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b")
        self.assertEqual(static.PREDECESSOR_RUN_ID, "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b")
        observer = static._observer_projection()  # noqa: SLF001
        self.assertEqual(observer["run_id_hex"], static.RUN_ID)
        self.assertEqual(observer["initial_same_fd_sessions"], 2)
        self.assertEqual(observer["physical_reopen_count"], 1)
        self.assertTrue(observer["per_boot_identity_required"])
        self.assertTrue(observer["host_tty_close_reopen"])
        self.assertFalse(observer["action_retry"])

    def test_safety_projection_cannot_claim_authority(self) -> None:
        value = {"safety": {"host_only": True}}
        for key in (
            "device_contact", "device_write", "odin_invoked", "odin_transfer",
            "flash", "partition_write", "live_authorized", "d0_authorized",
            "d1_authorized", "f1_authorized", "replay_authorized",
            "causal_result_allowed", "candidate_success",
        ):
            value["safety"][key] = False
        static._validate_safety(value)  # noqa: SLF001
        changed = copy.deepcopy(value)
        changed["safety"]["live_authorized"] = True
        with self.assertRaises(static.StaticContractError):
            static._validate_safety(changed)  # noqa: SLF001

    def test_static_source_pin_and_clean_output_path(self) -> None:
        self.assertEqual(static.P334_STATIC_SOURCE.stat().st_size, static.P334_STATIC_SOURCE_IDENTITY["size"])
        self.assertEqual(static.identity(static.P334_STATIC_SOURCE.read_bytes()), static.P334_STATIC_SOURCE_IDENTITY)
        self.assertEqual(static.DEFAULT_OUTPUT.parent.name, "s22plus_fyg8_p335")
        self.assertEqual(static.DEFAULT_OUTPUT.name, "process-v2-candidate-static-20260904-04.json")

    def test_static_build_rederives_pinned_candidate_result(self) -> None:
        value = static.build_result()
        self.assertEqual(value["run_id"], static.RUN_ID)
        self.assertEqual(value["candidate"]["a"], value["candidate"]["b"])
        self.assertEqual(value["candidate"]["a"]["ap_tar_md5"], static.P335_AP_IDENTITY)


if __name__ == "__main__":
    unittest.main()
