from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py"
)
SCRIPTS = SOURCE.parent


def load_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("p324_live_integration", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("F1 live v2 cannot load")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P324LiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def prepared(self):
        module = self.module
        run_id = module.typed_evidence.P324_RUN_ID
        banner = ("S22PLUS-FYG8-E3:" + run_id + "\n").encode("ascii")
        acceptance = (
            module.typed_evidence.p324_stock_adapter.acceptance_fixture()
        )
        bundle = types.SimpleNamespace(
            manifest={
                "observation": {
                    "timeout_sec": 300,
                    "acceptance": acceptance,
                    "candidate_observer": {
                        "kind": "exact_cdc_acm_banner_v1",
                        "usb_vendor_id": "04e8",
                        "usb_product_id": "6861",
                        "usb_serial": "S22E3" + run_id,
                        "usb_driver": "cdc_acm",
                        "usb_interface_number": "00",
                        "banner_hex": banner.hex(),
                    },
                    module.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: (
                        module.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE
                    ),
                }
            }
        )
        return module.PreparedRun(
            self.root,
            self.run_dir,
            bundle,
            {
                "approval_binding_sha256": "f" * 64,
                "p324_typec_lane_binding": {
                    "path": str(self.run_dir / "p324-typec-lane-binding.json"),
                    "size": 1,
                    "sha256": "a" * 64,
                },
            },
            {
                "schema": module.PRIVATE_TARGET_SCHEMA,
                "serial": "private-fixture",
                "topology": module.p324_typec_lane.SOURCE_TOPOLOGY,
            },
        )

    def durable_observer(self) -> dict[str, object]:
        module = self.module
        candidate = module.p324_typec_lane.CANDIDATE_TOPOLOGY.removeprefix(
            "usb:"
        )
        return {
            "classification": "accepted",
            "accepted": True,
            "receipt_sha256": "a" * 64,
            "valid_receipt": True,
            "download_endpoint_absent": True,
            "endpoint_identity_sha256": "b" * 64,
            "topology_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
            "bounded": True,
            "source_topology_sha256": hashlib.sha256(b"2-1.3").hexdigest(),
            "candidate_topology_sha256": hashlib.sha256(
                candidate.encode()
            ).hexdigest(),
            "both_topologies_inventory_complete": True,
            "accepted_inventory_exact": True,
            "same_run_typec_partner_continuity": True,
            "accepted_for_p324": True,
        }

    @staticmethod
    def live_state() -> dict[str, object]:
        return {
            "candidate_classification": "odin_transfer_completed",
            "candidate_completed": True,
            "download_endpoint_absent": True,
            "rollback_classification": "odin_transfer_completed",
            "rollback_completed": True,
            "final_verified": True,
            "marker_accepted": False,
            "final_evidence": {"observer": {}},
        }

    def projection(self, durable: dict[str, object]) -> dict[str, object]:
        module = self.module
        with (
            mock.patch.object(
                module, "_reopen_candidate_observation", return_value=durable
            ),
            mock.patch.object(
                module,
                "_reopen_candidate_guard_release",
                return_value={
                    "status": "released",
                    "released": True,
                    "warning": None,
                    "receipt_sha256": "c" * 64,
                },
            ),
        ):
            value = module._candidate_arrival_proof_projection(  # noqa: SLF001
                self.prepared(), self.live_state()
            )
        if not isinstance(value, dict):
            raise AssertionError("P324 projection is absent")
        return value

    def test_exact_candidate_lane_can_produce_p324_primary_proof(self) -> None:
        value = self.projection(self.durable_observer())
        self.assertTrue(value["proof"])
        self.assertTrue(value["target_topology_continuity"])
        self.assertTrue(value["same_run_typec_partner_continuity"])
        self.assertTrue(value["candidate_lane_inventory_exact"])
        self.assertEqual(
            value["banner_size"],
            self.module.typed_evidence.P324_ACM_PRIMARY_BANNER_SIZE,
        )

    def test_every_lane_continuity_predicate_fails_closed(self) -> None:
        for key in (
            "both_topologies_inventory_complete",
            "accepted_inventory_exact",
            "same_run_typec_partner_continuity",
            "accepted_for_p324",
        ):
            with self.subTest(key=key):
                durable = self.durable_observer()
                durable[key] = False
                self.assertFalse(self.projection(durable)["proof"])

        durable = self.durable_observer()
        durable["candidate_topology_sha256"] = hashlib.sha256(
            b"2-1.3"
        ).hexdigest()
        self.assertFalse(self.projection(durable)["proof"])

    def test_p324_overlay_rejects_p323_banner_identity(self) -> None:
        prepared = self.prepared()
        observer = prepared.bundle.manifest["observation"]["candidate_observer"]
        p323 = self.module.typed_evidence.P323_RUN_ID
        observer["usb_serial"] = "S22E3" + p323
        observer["banner_hex"] = (
            "S22PLUS-FYG8-E3:" + p323 + "\n"
        ).encode("ascii").hex()
        with self.assertRaisesRegex(
            self.module.F1LiveError, "exact P3.24 ACM identity"
        ):
            self.module._candidate_arrival_proof_role(  # noqa: SLF001
                prepared.bundle
            )

    def test_only_exact_consumed_p323_receipt_is_a_p324_baseline(self) -> None:
        raw_path = ROOT / (
            "workspace/private/runs/device-action-f1-live-v2/"
            "f1-2026-09-01T100714815943Z-1788257234815987455/"
            "rollback-observer-1.bin"
        )
        raw = raw_path.read_bytes()
        acceptance = (
            self.module.typed_evidence.p324_stock_adapter.acceptance_fixture()
        )
        value = self.module.typed_evidence.classify_clean_baseline(
            raw, acceptance
        )
        self.assertEqual(
            value["classification"],
            "P324_CURRENT_RUN_ABSENT_P323_PREDECESSOR_EXACT",
        )
        self.assertTrue(value["baseline_clean"])
        changed = bytearray(raw)
        changed[0] ^= 1
        with self.assertRaisesRegex(
            self.module.typed_evidence.EvidenceError,
            "predecessor baseline raw identity differs",
        ):
            self.module.typed_evidence.classify_clean_baseline(
                bytes(changed), acceptance
            )

    def test_candidate_lane_recheck_is_after_download_and_before_claim(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        function = source[
            source.index("def _execute_prepared_locked(") : source.index(
                "def execute_prepared(", source.index("def _execute_prepared_locked(")
            )
        ]
        self.assertLess(
            function.index("backend.wait_download("),
            function.index("backend.revalidate_candidate_lane(prepared)"),
        )
        self.assertLess(
            function.index("backend.revalidate_candidate_lane(prepared)"),
            function.index("_claim_candidate_global(prepared, candidate_identity)"),
        )


if __name__ == "__main__":
    unittest.main()
