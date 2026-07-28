#!/usr/bin/env python3
"""Tests for the source-bound P2.84 sysfs ingestion oracle."""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p284_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p284_sysfs_ingestion_oracle as oracle  # noqa: E402


class P284SysfsIngestionOracleTests(unittest.TestCase):
    def test_token_is_single_source_for_write_and_readback(self) -> None:
        spec.validate()
        self.assertEqual(spec.ROLE_NONE_WRITE, "none\n")
        self.assertEqual(spec.ROLE_NONE_READBACK, "none")
        self.assertEqual(spec.ROLE_PERIPHERAL_WRITE, "peripheral\n")
        self.assertEqual(spec.ROLE_PERIPHERAL_READBACK, "peripheral")
        self.assertEqual(spec.CHILD_SUSPENDED_READBACK, "suspended")
        self.assertEqual(spec.CHILD_ACTIVE_READBACK, "active")

    def test_readback_framing_and_write_framing_mutations_fail(self) -> None:
        with mock.patch.object(spec, "ROLE_NONE_READBACK", "none\n"):
            with self.assertRaisesRegex(
                spec.SpecError, "readback contains wire framing"
            ):
                spec.validate()
        with mock.patch.object(spec, "ROLE_NONE_WRITE", "none"):
            with self.assertRaisesRegex(
                spec.SpecError, "none write/readback token drifted"
            ):
                spec.validate()

    def test_source_token_sets_are_complete(self) -> None:
        self.assertEqual(
            spec.MODE_SHOW_TOKENS,
            ("peripheral", "host", "none"),
        )
        self.assertEqual(
            spec.RUNTIME_STATUS_SHOW_TOKENS,
            (
                "error",
                "unsupported",
                "suspended",
                "suspending",
                "resuming",
                "active",
            ),
        )

    def test_retry_policy_does_not_mask_structural_errors(self) -> None:
        self.assertEqual(spec.EXACT_VALUE_RETRY_ERRNOS, (2, 19, 5))
        with mock.patch.object(
            spec, "EXACT_VALUE_RETRY_ERRNOS", (2, 19, 5, 6)
        ):
            with self.assertRaisesRegex(
                spec.SpecError, "retry errno policy changed"
            ):
                spec.validate()

    def test_exact_fyg8_sources_and_aarch64_harness_pass(self) -> None:
        paths = (
            ROOT / oracle.DEFAULT_DWC3_SOURCE,
            ROOT / oracle.DEFAULT_POWER_SOURCE,
            ROOT / oracle.DEFAULT_RUNTIME_SOURCE,
            ROOT / oracle.DEFAULT_P282_RUNTIME_SOURCE,
        )
        compiler = shutil.which("aarch64-linux-gnu-gcc")
        qemu = shutil.which("qemu-aarch64")
        if (
            compiler is None
            or qemu is None
            or any(not path.is_file() for path in paths)
        ):
            self.skipTest("private FYG8 sources or AArch64 harness tools absent")
        result = oracle.run_oracle(
            dwc3_source_path=paths[0],
            power_source_path=paths[1],
            p260_runtime_path=paths[2],
            p282_runtime_path=paths[3],
            compiler=compiler,
            qemu=qemu,
        )
        self.assertEqual(result["verdict"], oracle.VERDICT)
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["harness"]["cases"],
            {
                "source_tokens": 9,
                "valid_mismatch_retry": True,
                "empty_read_retry": True,
                "missing_newline_hard": True,
                "overflow_hard": True,
                "retry_errno_count": 3,
                "representative_hard_errno_count": 8,
            },
        )

    def test_source_and_reader_mutations_fail_closed(self) -> None:
        dwc3_path = ROOT / oracle.DEFAULT_DWC3_SOURCE
        power_path = ROOT / oracle.DEFAULT_POWER_SOURCE
        runtime_path = ROOT / oracle.DEFAULT_RUNTIME_SOURCE
        p282_runtime_path = ROOT / oracle.DEFAULT_P282_RUNTIME_SOURCE
        if any(
            not path.is_file()
            for path in (
                dwc3_path,
                power_path,
                runtime_path,
                p282_runtime_path,
            )
        ):
            self.skipTest("private FYG8 source inputs absent")

        dwc3 = dwc3_path.read_bytes()
        power = power_path.read_bytes()
        with self.assertRaisesRegex(oracle.OracleError, "source hash mismatch"):
            oracle._verify_source_contract(
                dwc3.replace(b'"none\\n"', b'"none"', 1),
                power,
            )

        p260 = runtime_path.read_bytes()
        p282 = p282_runtime_path.read_bytes()
        with self.assertRaisesRegex(
            oracle.OracleError, "p282_wait_exact_value body hash mismatch"
        ):
            oracle._verify_runtime_sources(
                p260,
                p282.replace(
                    b"&& rc != -ENODEV",
                    b"&& rc != -ENXIO",
                    1,
                ),
            )


if __name__ == "__main__":
    unittest.main()
