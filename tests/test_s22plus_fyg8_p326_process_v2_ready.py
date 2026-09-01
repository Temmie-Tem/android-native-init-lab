from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import device_action_f1_live_v2 as live  # noqa: E402

SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "prepare_s22plus_fyg8_p326_process_v2.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p326_ready_test", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P326 ready builder cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P326ProcessV2ReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.manifest, cls.payloads, cls.verification = cls.module.build()

    def test_manifest_binds_exact_bidirectional_transcript(self) -> None:
        module = self.module
        observation = self.manifest["observation"]
        self.assertEqual(
            observation[module.current_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY],
            module.current_evidence.CANDIDATE_BIDIRECTIONAL_CONSOLE_ROLE,
        )
        self.assertEqual(
            bytes.fromhex(observation["candidate_observer"]["banner_hex"]),
            module.console.DEVICE_TRANSCRIPT,
        )
        self.assertEqual(
            observation["candidate_observer"]["usb_serial"],
            "S22E3" + module.p326_adapter.P326_RUN_ID_HEX,
        )

    def test_offline_verification_includes_busybox_and_observer(self) -> None:
        verification = self.verification
        self.assertTrue(verification["verified"])
        self.assertEqual(
            verification["schema"],
            "device_action_f1_p326_stock_offline_contract_v1",
        )
        closure = verification["ap_payload_closure"]
        self.assertEqual(closure["busybox"], self.module.p326_build.BUSYBOX_IDENTITY)
        static_value = json.loads(self.module.DEFAULT_STATIC_OUTPUT.read_bytes())
        self.assertEqual(
            verification["p326_observer_source"]["sha256"],
            static_value["observer_adapter"]["source"]["sha256"],
        )
        self.assertEqual(
            static_value["observer_adapter"]["trailing_bytes_policy"],
            "reject-and-retain",
        )
        self.assertTrue(
            static_value["observer_adapter"]["busybox_ash_exits_after_proof"]
        )
        self.assertFalse(verification["candidate_success"])
        self.assertFalse(verification["causal_result_allowed"])

    def test_promotion_payloads_are_p326_and_boot_only(self) -> None:
        run_manifest = json.loads(self.payloads["run_manifest"])
        static_result = json.loads(self.payloads["static_check"])
        self.assertEqual(
            run_manifest["observation_contract"]["accepted_identity"],
            "P326_STOCK_OBSERVER_V4_RETAINED",
        )
        self.assertEqual(
            static_result["candidate"]["artifacts"]["busybox"],
            self.module.p326_build.BUSYBOX_IDENTITY,
        )
        self.assertTrue(static_result["candidate"]["boot_only_ap"])
        self.assertEqual(
            self.manifest["candidate_ap"]["sha256"],
            "954b560309e5c7a1f99484dbe00efc08743cc97bc228bad5c7f8924e8c7c2712",
        )

    def test_live_projection_requires_both_round_trip_proofs(self) -> None:
        bundle = SimpleNamespace(manifest=self.manifest)
        prepared = live.PreparedRun(
            ROOT,
            ROOT / "workspace/private/nonexistent-p326-proof-fixture",
            bundle,
            {},
            {"schema": live.PRIVATE_TARGET_SCHEMA, "serial": "fixture", "topology": "usb:2-1.3"},
        )
        candidate_topology = hashlib.sha256(b"3-1.3").hexdigest()
        durable = {
            "classification": "accepted",
            "accepted": True,
            "receipt_sha256": "b" * 64,
            "valid_receipt": True,
            "download_endpoint_absent": True,
            "endpoint_identity_sha256": "c" * 64,
            "topology_sha256": candidate_topology,
            "bounded": True,
            "source_topology_sha256": hashlib.sha256(b"2-1.3").hexdigest(),
            "candidate_topology_sha256": candidate_topology,
            "both_topologies_inventory_complete": True,
            "accepted_inventory_exact": True,
            "same_run_typec_partner_continuity": True,
            "accepted_for_p324": True,
            "pid1_bidirectional_proof": True,
            "busybox_shell_roundtrip_proof": True,
        }
        state = {
            "candidate_classification": "odin_transfer_completed",
            "candidate_completed": True,
            "download_endpoint_absent": True,
            "rollback_classification": "odin_transfer_completed",
            "rollback_completed": True,
            "final_verified": True,
        }
        with (
            mock.patch.object(live, "_reopen_candidate_observation", return_value=durable),
            mock.patch.object(
                live,
                "_reopen_candidate_guard_release",
                return_value={"status": "released", "released": True},
            ),
        ):
            projection = live._candidate_arrival_proof_projection(prepared, state)
            self.assertTrue(projection["proof"])
            self.assertTrue(projection["pid1_bidirectional_proof"])
            changed = dict(durable)
            changed["busybox_shell_roundtrip_proof"] = False
            with mock.patch.object(
                live, "_reopen_candidate_observation", return_value=changed
            ):
                self.assertFalse(
                    live._candidate_arrival_proof_projection(prepared, state)["proof"]
                )

    def test_predecessor_role_and_ap_fail_closed(self) -> None:
        module = self.module
        observer = dict(self.manifest["observation"]["candidate_observer"])
        observer["banner_hex"] = (
            "S22PLUS-FYG8-E3:" + module.p326_adapter.P325_RUN_ID_HEX + "\n"
        ).encode().hex()
        with self.assertRaises(module.current_evidence.EvidenceError):
            module.current_evidence.validate_candidate_arrival_proof_role(
                module.current_evidence.CANDIDATE_BIDIRECTIONAL_CONSOLE_ROLE,
                observer,
                expected_run_id=module.p326_adapter.P326_RUN_ID_HEX,
            )
        changed = dict(self.verification["ap_payload_closure"])
        changed["run_id"] = module.p326_adapter.P325_RUN_ID_HEX
        with self.assertRaises(module.current_evidence.EvidenceError):
            module.current_evidence.validate_e2_ap_payload(b"", changed)


if __name__ == "__main__":
    unittest.main()
