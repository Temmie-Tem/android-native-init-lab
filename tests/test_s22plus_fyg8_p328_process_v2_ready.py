"""Focused host-only checks for the P3.28 promotion/ready seam."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PREPARE_PATH = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "prepare_s22plus_fyg8_p328_process_v2.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("p328_ready_prepare", PREPARE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.28 prepare module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = _load()


class P328ReadyTests(unittest.TestCase):
    def test_final_bindings_are_fresh_and_host_only(self) -> None:
        self.assertEqual(
            prepare.adapter.P328_RUN_ID_HEX,
            "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b",
        )
        self.assertNotEqual(
            prepare.adapter.P328_RUN_ID_HEX,
            prepare.adapter.P327_RUN_ID_HEX,
        )
        self.assertEqual(prepare.AUTH_KEY_IDENTITY["size"], 32)
        self.assertEqual(
            prepare.AUTH_KEY_IDENTITY["sha256"],
            "7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b",
        )
        self.assertFalse(prepare.DEFAULT_PROMOTION.exists())
        self.assertFalse(prepare.DEFAULT_MANIFEST.exists())

    def test_observer_spec_contains_metadata_not_key_material(self) -> None:
        value = prepare._observer_spec()
        self.assertEqual(
            value["kind"], "exact_cdc_acm_authenticated_framed_commands_v1"
        )
        self.assertEqual(value["wire_magic"], "S328")
        self.assertEqual(value["max_commands"], 16)
        self.assertEqual(value["proof_command_count"], 3)
        self.assertTrue(value["caller_selected_command"])
        self.assertEqual(value["auth_key"], prepare.AUTH_KEY_IDENTITY)
        encoded = json.dumps(value, sort_keys=True).encode("ascii")
        self.assertNotIn(b"auth-key-v1.bin", encoded)
        self.assertNotIn(b"workspace/private", encoded)

    def test_promotion_payloads_keep_three_contract_artifacts(self) -> None:
        identity = {"size": 1, "sha256": "1" * 64}
        candidate = {
            "a": {
                "ap_tar_md5": identity,
                "boot_img": identity,
                "boot_img_lz4": identity,
            },
            "image": identity,
            "init": identity,
            "child": identity,
            "busybox": identity,
        }
        static_value = {
            "candidate": candidate,
            "authentication": {
                "required": True,
                "scheme": "auth-key-v1",
                "key": prepare.AUTH_KEY_IDENTITY,
                "embedded_key_occurrences_in_init": 1,
                "hardware_backed": False,
                "candidate_possession_implies_key_possession": True,
                "path_published": False,
            },
        }
        static_payload = b"{}\n"
        ap_receipt = {"size": 1, "sha256": "2" * 64, "member": identity}
        payloads = prepare._promotion_payloads(
            static_value, static_payload, ap_receipt
        )
        self.assertEqual(
            set(payloads), {"candidate_static", "run_manifest", "static_check"}
        )
        self.assertIs(payloads["candidate_static"], static_payload)
        static_check = json.loads(payloads["static_check"])
        self.assertEqual(static_check["schema"], prepare.evidence.P328_STATIC_RESULT_SCHEMA)
        self.assertTrue(static_check["candidate"]["boot_only_ap"])
        self.assertFalse(static_check["safety"]["device_contact"])
        self.assertNotIn(b"auth-key-v1.bin", payloads["static_check"])

    def test_audit_only_does_not_publish_final_paths(self) -> None:
        # The common P328 offline verifier is completed by the parallel
        # integration unit.  This check remains intentionally structural and
        # never calls the normal publisher or touches a device.
        self.assertFalse(prepare.DEFAULT_PROMOTION.exists())
        self.assertFalse(prepare.DEFAULT_MANIFEST.exists())
        self.assertFalse(prepare.PRIVATE_PARENT.joinpath("run").exists())

    def test_runtime_bound_static_reopen_does_not_read_key_bytes(self) -> None:
        value = prepare.candidate_static.build_result()
        with (
            mock.patch.object(
                prepare.candidate_static.artifact,
                "read_auth_key",
                side_effect=AssertionError("bound reopen read key bytes"),
            ),
            mock.patch.object(
                prepare.candidate_static.artifact,
                "auth_key_identity",
                side_effect=AssertionError("bound reopen read key identity"),
            ),
        ):
            self.assertIs(
                prepare.candidate_static.validate_bound_result(value),
                value,
            )


if __name__ == "__main__":
    unittest.main()
