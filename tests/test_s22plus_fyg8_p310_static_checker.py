#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p310_candidate_static_checker as static_checker  # noqa: E402


class P310StaticCheckerTests(unittest.TestCase):
    def test_repro_comparison_uses_strict_persisted_json_shape(self) -> None:
        fresh = {
            "linked_audit": {
                "postbuild_audit": {
                    "carrier_v2_linked_pair": {
                        "boundary_matrix": {0: "ZERO_AMBIGUOUS", 24: "UNSAT"}
                    }
                }
            }
        }
        self.assertEqual(
            static_checker._json_document(fresh),  # noqa: SLF001
            {
                "linked_audit": {
                    "postbuild_audit": {
                        "carrier_v2_linked_pair": {
                            "boundary_matrix": {
                                "0": "ZERO_AMBIGUOUS",
                                "24": "UNSAT",
                            }
                        }
                    }
                }
            },
        )
        with self.assertRaises(static_checker.CheckError):
            static_checker._json_document(  # noqa: SLF001
                {"non_json_number": float("inf")}
            )


if __name__ == "__main__":
    unittest.main()
