from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import device_action_f1_live_v2 as live  # noqa: E402

SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "prepare_s22plus_fyg8_p325_process_v2.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p325_ready", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P325 ready builder cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P325ReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.manifest, cls.payloads, cls.verification = cls.module.build()

    def test_exact_p325_defaults_and_acm_primary_banner(self) -> None:
        module = self.module
        observation = self.manifest["observation"]
        self.assertEqual(self.manifest["manifest_id"], module.DEFAULT_MANIFEST_ID)
        self.assertEqual(self.manifest["run_id"], module.DEFAULT_LIVE_RUN_ID)
        self.assertEqual(
            observation[module.current_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY],
            module.current_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE,
        )
        run_id = module.p325_adapter.P325_RUN_ID_HEX
        self.assertEqual(observation["candidate_observer"]["usb_serial"], "S22E3" + run_id)
        expected_banner = ("S22PLUS-FYG8-E3:" + run_id + "\n").encode("ascii")
        self.assertEqual(
            bytes.fromhex(observation["candidate_observer"]["banner_hex"]),
            expected_banner,
        )
        self.assertEqual(module.P324_PREPARE_IDENTITY["size"], 14_117)
        self.assertEqual(module.p325_adapter.P324_PREDECESSOR_RUN_ID_HEX, "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b")

    def test_rehearsal_is_verified_and_non_authorizing(self) -> None:
        module = self.module
        run_manifest = json.loads(self.payloads["run_manifest"])
        self.assertEqual(
            run_manifest["schema"], module.current_evidence.P325_RUN_MANIFEST_SCHEMA
        )
        self.assertEqual(
            run_manifest["observation_contract"]["accepted_identity"],
            "P325_STOCK_OBSERVER_V4_RETAINED",
        )
        self.assertEqual(run_manifest["run_id"], module.p325_adapter.P325_RUN_ID_HEX)
        self.assertTrue(self.verification["verified"])
        self.assertFalse(self.verification["candidate_success"])
        self.assertIn("p325_guard_adapter_source", self.verification)
        for old in (
            "P321_STOCK_OBSERVER_V4_RETAINED",
            "P324_STOCK_OBSERVER_V4_RETAINED",
        ):
            self.assertNotEqual(
                run_manifest["observation_contract"]["accepted_identity"], old
            )

    def test_manifest_reopens_without_device_contact(self) -> None:
        module = self.module
        payload = module.manifest_bytes(self.manifest)
        module.verify_manifest(
            self.manifest, payload, promotion_payloads=self.payloads
        )
        self.assertTrue(module.DEFAULT_MANIFEST.exists())
        self.assertTrue(module.DEFAULT_PROMOTION.is_dir())
        published_bytes = module.DEFAULT_MANIFEST.read_bytes()
        module.core.verify_bundle(ROOT, module.DEFAULT_MANIFEST)
        self.assertEqual(module.DEFAULT_MANIFEST.read_bytes(), published_bytes)
        self.assertIn(stat.S_IMODE(module.DEFAULT_MANIFEST.stat().st_mode), {0o644, 0o664})
        self.assertEqual(stat.S_IMODE(module.DEFAULT_PROMOTION.stat().st_mode), 0o700)
        for name in ("candidate-static.json", "run-manifest.json", "static-check-result.json"):
            item = module.DEFAULT_PROMOTION / name
            self.assertEqual(stat.S_IMODE(item.stat().st_mode), 0o400)
            self.assertEqual(item.stat().st_nlink, 1)

    def test_p325_output_namespaces_and_exact_candidate_binding(self) -> None:
        module = self.module
        for path in (
            module.DEFAULT_BUILDER_OUTPUT,
            module.DEFAULT_STATIC_OUTPUT,
            module.DEFAULT_PROMOTION,
            module.DEFAULT_MANIFEST,
        ):
            self.assertIn("p325", str(path))
        self.assertEqual(
            self.manifest["candidate_ap"]["sha256"],
            "486fd1f2dcb8fbca9f31cb6bce438bb38945cf98e9bb9422f5d5301a7b0abdf4",
        )
        self.assertEqual(
            self.manifest["candidate_ap"]["size"],
            27_279_401,
        )
        self.assertEqual(
            self.manifest["rollback_ap"],
            {"path": module.relative(module.DEFAULT_ROLLBACK_AP), **module.ROLLBACK_IDENTITY},
        )
        contract = self.manifest["observation"]["acceptance"]["contract"]
        self.assertEqual(contract["candidate_static"]["size"], 23_312)
        self.assertEqual(
            contract["candidate_static"]["sha256"],
            "bd3f14fae735f8254136e7d04174e1d92fd02c6aeed256ae19f2a9ee13c1addf",
        )
        self.assertEqual(stat.S_IMODE(module.DEFAULT_ROLLBACK_AP.stat().st_mode), 0o600)

    def test_closed_state_omits_duplicate_carrier_and_stays_in_core_bound(self) -> None:
        bundle = SimpleNamespace(manifest=self.manifest)
        prepared = live.PreparedRun(
            ROOT,
            ROOT / "workspace/private/nonexistent-p325-size-fixture",
            bundle,
            {},
            {
                "schema": live.PRIVATE_TARGET_SCHEMA,
                "serial": "fixture",
                "topology": "usb:2-1.3",
            },
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
        }
        carrier = {
            "proof_class": "NONCAUSAL_SUCCESS_PATH",
            "stock": [{"bounded_fixture": "x" * 30_000}],
        }
        state = {
            "candidate_classification": "odin_transfer_completed",
            "candidate_completed": True,
            "download_endpoint_absent": True,
            "rollback_classification": "odin_transfer_completed",
            "rollback_completed": True,
            "final_verified": True,
            "marker_accepted": False,
            "final_evidence": {"observer": {"p325_stock": carrier}},
        }
        with (
            mock.patch.object(
                live, "_reopen_candidate_observation", return_value=durable
            ),
            mock.patch.object(
                live,
                "_reopen_candidate_guard_release",
                return_value={"status": "released", "released": True},
            ),
        ):
            projection = live._candidate_arrival_proof_projection(prepared, state)
        self.assertIsNotNone(projection)
        self.assertIsNone(projection["supplemental_carrier"])
        compact = json.dumps(
            {**state, "candidate_arrival_proof": projection},
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode() + b"\n"
        duplicated = {
            **projection,
            "supplemental_carrier": {
                "source": "retained_carrier",
                "field": "p325_stock",
                "projection": carrier,
                "marker_accepted": False,
            },
        }
        prior_shape = json.dumps(
            {**state, "candidate_arrival_proof": duplicated},
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode() + b"\n"
        self.assertLessEqual(len(compact), live.core.MAX_RECORD)
        self.assertGreater(len(prior_shape), live.core.MAX_RECORD)


if __name__ == "__main__":
    unittest.main()
