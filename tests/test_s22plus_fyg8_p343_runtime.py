from __future__ import annotations

from pathlib import Path
import hashlib
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p343_open_read_branch_runtime as runtime  # noqa: E402


class P343RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p342/"
            "stock-candidate-build-v1-20260905-02/stock-sources/"
            "s22plus_fyg8_p290_e3_runtime.inc.c"
        ).read_bytes()
        self.key = runtime.predecessor._materialized_key(self.source)

    def test_fresh_identity_and_preserved_p342_idle_geometry(self) -> None:
        value = runtime.audit_binding()
        self.assertEqual(value["run_id_hex"], runtime.P343_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], runtime.P342_PREDECESSOR_RUN_ID_HEX)
        self.assertTrue(value["host_first_open"])
        self.assertTrue(value["idle_listener_unchanged"])
        self.assertTrue(value["wire_frames_unchanged"])
        self.assertTrue(value["authentication_unchanged"])
        self.assertFalse(value["runtime_behavior_unchanged"])
        self.assertTrue(value["default_runtime_behavior_unchanged"])
        self.assertTrue(value["catalog_allowlist_expanded"])
        self.assertEqual(value["catalog_allowlist_actions"], (
            "kernel", "processes", "mounts", "memory", "usb-state"
        ))
        self.assertEqual(value["initial_proof_default_action"], "kernel")
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_transform_changes_nonce_and_middle_validator_only(self) -> None:
        transformed = runtime.transform_runtime_include(self.source, self.key)
        receipt = runtime.validate_transform(
            self.source,
            transformed,
            auth_key_sha256=hashlib.sha256(self.key).hexdigest(),
        )
        self.assertEqual(receipt["changed_anchors"], [
            "p343_fixed_command_identity_only",
            "p343_middle_command_named_allowlist",
        ])
        self.assertTrue(receipt["wire_frames_unchanged"])
        self.assertTrue(receipt["authentication_unchanged"])
        self.assertTrue(receipt["idle_listener_unchanged"])
        self.assertFalse(receipt["runtime_behavior_unchanged"])
        self.assertEqual(transformed.count(b"p335_command_2"), 0)
        self.assertEqual(transformed.count(runtime._c_string(runtime.P343_COMMAND)), 1)
        for command in runtime.CATALOG.values():
            self.assertIn(command, transformed)

    def test_predecessor_materialized_runtime_is_not_current(self) -> None:
        with self.assertRaises(runtime.RuntimeIdentityError):
            runtime.validate_p343_runtime(
                runtime.predecessor.materialize_helper(self.key),
                auth_key_sha256=hashlib.sha256(self.key).hexdigest(),
            )

    def test_transform_artifacts_changes_only_runtime_key(self) -> None:
        result = runtime.transform_artifacts(
            {runtime.RUNTIME_KEY: self.source, "other": b"unchanged"},
            self.key,
        )
        self.assertEqual(result["other"], b"unchanged")
        self.assertNotEqual(result[runtime.RUNTIME_KEY], self.source)
        self.assertEqual(
            runtime.validate_p343_runtime(result[runtime.RUNTIME_KEY])["run_id_hex"],
            runtime.P343_RUN_ID_HEX,
        )


if __name__ == "__main__":
    unittest.main()
