from __future__ import annotations

from pathlib import Path
import hashlib
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p341_open_read_branch_runtime as runtime  # noqa: E402


class P341RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p340/"
            "stock-candidate-build-v1-20260905-01/stock-sources/"
            "s22plus_fyg8_p290_e3_runtime.inc.c"
        ).read_bytes()
        self.key = runtime.predecessor._materialized_key(self.source)

    def test_binding_is_fresh_and_host_first(self) -> None:
        audit = runtime.audit_binding()
        self.assertEqual(audit["run_id_hex"], runtime.P341_RUN_ID_HEX)
        self.assertEqual(runtime.OPEN_READ_BRANCHES, {
            0: "header-read-errno", 1: "header-grammar", 2: "body-read-errno",
            3: "crc", 4: "open-semantic",
        })
        self.assertEqual(runtime.OPEN_HEADER_WORD_STAGES, (4, 5, 6, 7))
        self.assertTrue(audit["host_first_open"])
        self.assertTrue(audit["host_open_before_banner"])
        self.assertTrue(audit["stage_zero_after_banner"])
        self.assertFalse(audit["successful_wire_exchange_unchanged"])
        for prefix in (
            "P328", "P330", "P331", "P332", "P333", "P334", "P335", "P336",
            "P337", "P338", "P339", "P340",
        ):
            self.assertEqual(getattr(runtime, f"{prefix}_RUN_ID_HEX"), runtime.P341_RUN_ID_HEX)
            self.assertEqual(getattr(runtime, f"{prefix}_RUN_ID"), runtime.P341_RUN_ID)

    def test_transform_changes_only_bound_runtime_seams(self) -> None:
        transformed = runtime.transform_runtime_include(self.source, self.key)
        self.assertNotEqual(transformed, self.source)
        self.assertEqual(
            len(transformed),
            len(runtime.host_first.helper(runtime.predecessor.P340_HELPER_TEMPLATE))
            + len(runtime.P341_ENTRY)
            - len(runtime.predecessor.P340_ENTRY)
            - len(runtime.predecessor.P340_HELPER_TEMPLATE)
            + len(self.source),
        )
        digest = hashlib.sha256(self.key).hexdigest()
        receipt = runtime.validate_transform(self.source, transformed, auth_key_sha256=digest)
        self.assertEqual(
            receipt["changed_anchors"],
            [
                "p341_host_first_open_order",
                "p341_host_first_banner_stage_order",
                "p341_fixed_command_identity_only",
            ],
        )
        self.assertTrue(receipt["host_first_open"])
        self.assertTrue(receipt["wire_frames_unchanged"])
        self.assertTrue(receipt["authentication_unchanged"])
        self.assertTrue(receipt["catalog_unchanged"])
        self.assertFalse(receipt["successful_wire_exchange_unchanged"])
        self.assertEqual(transformed.count(runtime.materialize_helper(self.key)), 1)
        self.assertEqual(transformed.count(runtime.predecessor.materialize_helper(self.key)), 0)
        self.assertEqual(transformed.count(runtime.P341_ENTRY), 1)
        self.assertEqual(transformed.count(runtime.predecessor.P340_ENTRY), 0)
        self.assertIn(b"p341_read_exact", transformed)


if __name__ == "__main__":
    unittest.main()
