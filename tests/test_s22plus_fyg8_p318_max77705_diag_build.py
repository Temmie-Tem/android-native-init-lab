from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p318_max77705_diag_build as build  # noqa: E402


class P318TimedMax77705DiagBuildTests(unittest.TestCase):
    def test_current_a_b_build_reaudits(self) -> None:
        value = build.audit_build(ROOT, ROOT / build.DEFAULT_OUTPUT)
        self.assertEqual(value["verdict"], build.VERDICT)
        self.assertTrue(value["a_b_byte_identical"])
        self.assertEqual(
            value["linked_surface_delta_from_p317"]["added_undefined_imports"],
            ["ktime_get"],
        )
        self.assertEqual(
            value["linked_surface_delta_from_p317"]["ktime_get_call_relocations"],
            4,
        )


if __name__ == "__main__":
    unittest.main()
