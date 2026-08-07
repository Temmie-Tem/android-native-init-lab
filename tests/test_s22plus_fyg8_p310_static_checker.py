#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p310_candidate_static_checker as static_checker  # noqa: E402


class P310StaticCheckerTests(unittest.TestCase):
    def test_rootfs_context_binds_and_restores_the_isolated_legacy_entrypoints(
        self,
    ) -> None:
        legacy = static_checker.p310_closure.module_parent.p257.p253.isolated_legacy
        previous = legacy.EXPECTED_ELF_ENTRYPOINTS
        values = {"init": 0x408488, "child": 0x4000CC}
        with mock.patch.object(
            static_checker.base.e1_static,
            "inspect_static_elf",
            side_effect=(
                {"entrypoint": values["init"]},
                {"entrypoint": values["child"]},
            ),
        ):
            with static_checker.rootfs_entrypoint_context(
                None, None, {"init": b"init", "child": b"child"}
            ):
                self.assertEqual(legacy.EXPECTED_ELF_ENTRYPOINTS, values)
                self.assertIsNot(legacy.EXPECTED_ELF_ENTRYPOINTS, previous)
        self.assertIs(legacy.EXPECTED_ELF_ENTRYPOINTS, previous)

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
