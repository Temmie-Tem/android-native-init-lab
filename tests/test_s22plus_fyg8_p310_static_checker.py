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
    def test_rootfs_context_binds_the_actual_p260_consumer_and_restores_it(
        self,
    ) -> None:
        entrypoint_api = static_checker.p310_closure.parent.p286.p282.p280
        p260 = entrypoint_api.isolated_p260
        previous_adapter = p260.EXPECTED_ELF_ENTRYPOINTS
        previous_legacy = p260.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS
        previous_p253_legacy = p260.p253.isolated_legacy
        values = {"init": 0x408488, "child": 0x4000CC}

        def fail_after_actual_swap(*_args, **_kwargs) -> None:
            self.assertEqual(p260.EXPECTED_ELF_ENTRYPOINTS, values)
            self.assertIs(p260.p253.isolated_legacy, p260.isolated_legacy)
            self.assertEqual(
                p260.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS, values
            )
            raise RuntimeError("actual P2.60 consumer reached")

        with mock.patch.object(
            static_checker.base.e1_static,
            "inspect_static_elf",
            side_effect=(
                {"entrypoint": values["init"]},
                {"entrypoint": values["child"]},
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "actual P2.60 consumer reached"
            ):
                with static_checker.rootfs_entrypoint_context(
                    None, None, {"init": b"init", "child": b"child"}
                ):
                    with mock.patch.object(
                        p260.p257,
                        "rootfs_audit",
                        side_effect=fail_after_actual_swap,
                    ):
                        p260.rootfs_audit(
                            b"boot",
                            b"vendor_boot",
                            Path("lz4"),
                            expected_init={},
                            expected_child={},
                            run_id=b"run-id",
                            module_closure={},
                        )
        self.assertIs(p260.EXPECTED_ELF_ENTRYPOINTS, previous_adapter)
        self.assertIs(
            p260.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS, previous_legacy
        )
        self.assertIs(p260.p253.isolated_legacy, previous_p253_legacy)

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
