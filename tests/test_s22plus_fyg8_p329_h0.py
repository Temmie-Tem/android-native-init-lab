from __future__ import annotations

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

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import prepare_s22plus_fyg8_p329_process_v2 as prepare  # noqa: E402
import s22plus_fyg8_p329_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p329_auth_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p329_auth_exec_runtime as runtime  # noqa: E402
import s22plus_fyg8_p329_process_v2_candidate_static as static  # noqa: E402
import s22plus_fyg8_p329_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p329_stock_process_v2_adapter as adapter  # noqa: E402


class P329H0Tests(unittest.TestCase):
    def test_identity_only_successor_is_distinct_from_consumed_p328(self) -> None:
        value = json.loads((builder.DEFAULT_OUTPUT_ROOT / "result.json").read_text())
        candidate = value["phase2"]["candidate"]
        self.assertEqual(value["run_id_hex"], artifact.P329_RUN_ID_HEX)
        self.assertEqual(value["lineage"]["predecessor_run_id"], artifact.P328_PREDECESSOR_RUN_ID_HEX)
        self.assertTrue(candidate["differs_from_consumed_p328"])
        self.assertEqual(candidate["a"]["ap_tar_md5"], candidate["b"]["ap_tar_md5"])
        self.assertNotEqual(candidate["a"]["ap_tar_md5"], builder.P328_AP_IDENTITY)
        self.assertEqual(value["framed_exec"]["wire_magic"], "S328")
        self.assertTrue(value["preservation"]["observer_udev_settle_host_only"])

    def test_protocol_and_key_are_reused_but_run_is_fresh(self) -> None:
        self.assertEqual(runtime.P329_RUN_ID_HEX, adapter.P329_RUN_ID_HEX)
        self.assertEqual(runtime.FRAME_MAGIC, b"S328")
        self.assertIn(runtime.P329_RUN_ID_HEX.encode(), runtime.DEVICE_BANNER)
        self.assertIn(runtime.P329_RUN_ID_HEX.encode(), observer.DEFAULT_COMMANDS[-1])
        self.assertTrue(observer.DEFAULT_COMMANDS[-1].startswith(b"/bin/busybox echo P328-NONCE "))
        self.assertEqual(
            artifact.auth_key_identity(), evidence.P329_AUTH_EXEC_AUTH_KEY_IDENTITY
        )

    def test_adapter_and_arrival_role_reject_predecessor(self) -> None:
        with self.assertRaises(adapter.DecodeError):
            adapter.classify_observation(artifact.P328_PREDECESSOR_RUN_ID)
        spec = evidence.p329_authenticated_framed_observer_spec()
        self.assertEqual(
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE,
                spec,
                expected_run_id=evidence.P329_RUN_ID,
            ),
            evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE,
        )
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE,
                spec,
                expected_run_id=evidence.P328_RUN_ID,
            )

    def test_static_receipt_reopens(self) -> None:
        value = json.loads(static.DEFAULT_OUTPUT.read_text())
        self.assertEqual(static.validate_result(value), value)
        self.assertEqual(value["schema"], evidence.P329_CANDIDATE_STATIC_SCHEMA)
        self.assertEqual(value["candidate"]["a"]["ap_tar_md5"], static.P329_AP_IDENTITY)

    def test_prepare_build_verifies_without_publishing(self) -> None:
        manifest, payloads, verification = prepare.build()
        self.assertEqual(manifest["manifest_id"], prepare.DEFAULT_MANIFEST_ID)
        self.assertEqual(
            manifest["observation"][evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY],
            evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE,
        )
        self.assertEqual(verification["schema"], "device_action_f1_p329_stock_offline_contract_v1")
        self.assertTrue(verification["udev_guard_settle_bounded"])
        self.assertFalse(prepare.DEFAULT_MANIFEST.exists())
        self.assertFalse(prepare.DEFAULT_PROMOTION.exists())
        self.assertEqual(set(payloads), {"candidate_static", "run_manifest", "static_check"})


if __name__ == "__main__":
    unittest.main()
