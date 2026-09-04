from __future__ import annotations

from pathlib import Path
import hashlib
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p340_open_read_branch_runtime as runtime  # noqa: E402


class P340RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p339/"
            "stock-candidate-build-v1-20260905-04/stock-sources/"
            "s22plus_fyg8_p290_e3_runtime.inc.c"
        ).read_bytes()
        self.key = runtime.predecessor._materialized_key(self.source)

    def test_binding_and_compatibility_ids_are_fresh(self) -> None:
        audit = runtime.audit_binding()
        self.assertEqual(audit["run_id_hex"], runtime.P340_RUN_ID_HEX)
        self.assertEqual(runtime.OPEN_READ_BRANCHES, {
            0: "header-read-errno", 1: "header-grammar", 2: "body-read-errno",
            3: "crc", 4: "open-semantic",
        })
        self.assertEqual(runtime.OPEN_HEADER_WORD_STAGES, (4, 5, 6, 7))
        self.assertEqual(runtime.OPEN_HEADER_SIZE, 16)
        self.assertFalse(audit["retry_added"])
        self.assertFalse(audit["timeout_changed"])
        for prefix in ("P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336", "P337", "P338", "P339"):
            self.assertEqual(getattr(runtime, f"{prefix}_RUN_ID_HEX"), runtime.P340_RUN_ID_HEX)
            self.assertEqual(getattr(runtime, f"{prefix}_RUN_ID"), runtime.P340_RUN_ID)

    def test_transform_changes_only_fixed_command_marker(self) -> None:
        transformed = runtime.transform_runtime_include(self.source, self.key)
        self.assertEqual(len(transformed), len(self.source))
        self.assertEqual(transformed.replace(runtime.materialize_helper(self.key), runtime.predecessor.materialize_helper(self.key), 1), self.source)
        self.assertEqual(self.source.count(runtime.predecessor.materialize_helper(self.key)), 1)
        self.assertEqual(transformed.count(runtime.materialize_helper(self.key)), 1)
        receipt = runtime.validate_transform(
            self.source, transformed, auth_key_sha256=hashlib.sha256(self.key).hexdigest()
        )
        self.assertEqual(receipt["changed_anchors"], ["p340_fixed_command_identity_only"])
        self.assertEqual(receipt["open_read_branch_ordinals"][1], "header-grammar")
        self.assertEqual(receipt["open_read_branch_ordinals"][4], "open-semantic")
        self.assertEqual(receipt["open_header_word_stages"], (4, 5, 6, 7))
        self.assertTrue(receipt["diagnostic_payload_unchanged"])
        self.assertTrue(receipt["diagnostic_frame_type_unchanged"])
        self.assertFalse(receipt["retry_added"])
        self.assertFalse(receipt["timeout_changed"])


if __name__ == "__main__":
    unittest.main()
