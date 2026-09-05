from __future__ import annotations

from pathlib import Path
import hashlib
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p342_open_read_branch_runtime as runtime  # noqa: E402


class P342RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p341/"
            "stock-candidate-build-v1-20260905-02/stock-sources/"
            "s22plus_fyg8_p290_e3_runtime.inc.c"
        ).read_bytes()
        self.key = runtime.predecessor._materialized_key(self.source)

    def test_binding_is_fresh_identity_only_and_four_session_metadata_is_external(self) -> None:
        audit = runtime.audit_binding()
        self.assertEqual(audit["run_id_hex"], runtime.P342_RUN_ID_HEX)
        self.assertEqual(runtime.OPEN_READ_BRANCHES, {
            0: "header-read-errno",
            1: "header-grammar",
            2: "body-read-errno",
            3: "crc",
            4: "open-semantic",
        })
        self.assertEqual(runtime.OPEN_HEADER_WORD_STAGES, (4, 5, 6, 7))
        self.assertTrue(audit["runtime_behavior_unchanged"])
        self.assertTrue(audit["idle_listener_unchanged"])
        self.assertTrue(audit["wire_frames_unchanged"])
        self.assertTrue(audit["authentication_unchanged"])
        self.assertTrue(audit["catalog_unchanged"])
        self.assertFalse(audit["device_contact"])
        for prefix in (
            "P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336",
            "P337", "P338", "P339", "P340", "P341",
        ):
            self.assertEqual(getattr(runtime, f"{prefix}_RUN_ID_HEX"), runtime.P342_RUN_ID_HEX)
            self.assertEqual(getattr(runtime, f"{prefix}_RUN_ID"), runtime.P342_RUN_ID)

    def test_transform_changes_only_the_fixed_command_identity(self) -> None:
        transformed = runtime.transform_runtime_include(self.source, self.key)
        self.assertNotEqual(transformed, self.source)
        digest = hashlib.sha256(self.key).hexdigest()
        receipt = runtime.validate_transform(
            self.source, transformed, auth_key_sha256=digest
        )
        self.assertEqual(receipt["changed_anchors"], ["p342_fixed_command_identity_only"])
        self.assertTrue(receipt["runtime_behavior_unchanged"])
        self.assertTrue(receipt["wire_frames_unchanged"])
        self.assertTrue(receipt["authentication_unchanged"])
        self.assertTrue(receipt["catalog_unchanged"])
        self.assertFalse(receipt["successful_wire_exchange_unchanged"])
        self.assertEqual(transformed.count(runtime.materialize_helper(self.key)), 1)
        self.assertEqual(transformed.count(runtime.predecessor.materialize_helper(self.key)), 0)
        self.assertEqual(
            transformed.count(runtime._c_string(runtime.P342_COMMAND)), 1
        )


if __name__ == "__main__":
    unittest.main()
