from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import prepare_s22plus_fyg8_p336_process_v2 as prepare  # noqa: E402
import device_action_f1_evidence_v2 as evidence  # noqa: E402


class P336PrepareTests(unittest.TestCase):
    def test_defaults_bind_fresh_p336_and_exact_rollback(self) -> None:
        self.assertEqual(prepare.SCHEMA, "s22plus_fyg8_p336_process_v2_promotion_v1")
        self.assertEqual(prepare.READY_SCHEMA, "s22plus_fyg8_p336_ready_manifest_builder_v1")
        self.assertEqual(prepare.DEFAULT_MANIFEST_ID, "s22plus-fyg8-p336-process-v2-ready-1")
        self.assertEqual(prepare.DEFAULT_LIVE_RUN_ID, "s22plus-fyg8-p336-live-1")
        self.assertEqual(prepare.DEFAULT_BUILDER_OUTPUT.parent.name, "s22plus_fyg8_p336")
        self.assertEqual(
            prepare.ROLLBACK_IDENTITY["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )

    def test_exact_loaded_source_and_observer_spec_are_host_only(self) -> None:
        self.assertEqual(
            prepare.identity(prepare.P335_PREPARE_SOURCE.read_bytes()),
            prepare.P335_PREPARE_IDENTITY,
        )
        spec = prepare._p336_observer_spec()  # noqa: SLF001
        self.assertEqual(spec["protocol_contract"], prepare.framed_observer.CONTRACT_ID)
        self.assertTrue(spec["long_idle_host_resync"])
        self.assertTrue(spec["later_action_open_before_resync"])
        self.assertFalse(spec["device_contact"])

    def test_graph_reuses_exact_inner_engine_without_device_authority(self) -> None:
        self.assertIsNotNone(prepare._INNER)  # exact predecessor is available
        self.assertEqual(prepare._INNER.build.__kwdefaults__["manifest_id"], prepare.DEFAULT_MANIFEST_ID)
        self.assertEqual(prepare._INNER.build.__kwdefaults__["live_run_id"], prepare.DEFAULT_LIVE_RUN_ID)
        self.assertEqual(prepare.DEFAULT_ROLLBACK_AP.name, "AP.tar.md5")

    def test_reuses_existing_logical_resident_evidence_role(self) -> None:
        self.assertEqual(
            prepare._EvidenceProxy.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
            evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
        )


if __name__ == "__main__":
    unittest.main()
