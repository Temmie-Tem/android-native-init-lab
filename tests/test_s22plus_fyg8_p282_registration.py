#!/usr/bin/env python3
"""Focused P2.82 stock-closure registration tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p253_e2_stock_closure as selector  # noqa: E402
import s22plus_fyg8_p280_e2_stock_closure as p280  # noqa: E402
import s22plus_fyg8_p282_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p282_e2_stock_closure as p282  # noqa: E402
import s22plus_fyg8_p282_source_contract as source  # noqa: E402


def _authority_data(*, host_write: bool = False) -> bytes:
    values = set(p282.REQUIRED_ABSOLUTE_PATH_STRINGS)
    values.update(p282._HISTORICAL_SPEC.E3_REQUIRED_CONTROL_STRINGS)
    data = b"\0".join(value.encode("ascii") for value in sorted(values)) + b"\0"
    if host_write:
        data += b"host\n\0"
    return data


class P282RegistrationTests(unittest.TestCase):
    def test_central_selector_dispatches_exact_p282_contract(self):
        self.assertEqual(selector.P282_CONTRACT_ID, source.CONTRACT_ID)
        self.assertIs(selector.select(source.CONTRACT_ID), p282)
        self.assertIs(p282.select(source.CONTRACT_ID), p282)
        with self.assertRaises(p282.ClosureError):
            p282.select(selector.P280_CONTRACT_ID)

    def test_unchanged_module_plan_and_rootfs_contract_are_inherited(self):
        self.assertEqual(p282.EXPECTED_MODULE_COUNT, 60)
        self.assertEqual(
            p282.EXPECTED_MODULE_COUNT, p280.EXPECTED_MODULE_COUNT
        )
        self.assertEqual(
            p282.EXPECTED_PLAN_TSV_SHA256,
            p280.EXPECTED_PLAN_TSV_SHA256,
        )
        self.assertEqual(
            p282.EXPECTED_MODULE_CLOSURE_SHA256,
            p280.EXPECTED_MODULE_CLOSURE_SHA256,
        )
        self.assertIs(p282.boot_verify, p280.boot_verify)
        self.assertIs(p282.receipt, p280.receipt)

    def test_entrypoints_are_derived_from_each_candidate_elf(self):
        entries = [
            SimpleNamespace(name="init", data=b"init"),
            SimpleNamespace(name="s22-e1-child", data=b"child"),
        ]
        inspector = (
            p280.isolated_p260.isolated_legacy.e1_static.inspect_static_elf
        )
        with mock.patch.object(
            p280.isolated_p260.isolated_legacy.e1_static,
            "inspect_static_elf",
            side_effect=({"entrypoint": 0x411234}, {"entrypoint": 0x400ABC}),
        ) as inspect:
            self.assertEqual(
                p282._entrypoints(entries),
                {"init": 0x411234, "child": 0x400ABC},
            )
        self.assertIs(
            p280.isolated_p260.isolated_legacy.e1_static.inspect_static_elf,
            inspector,
        )
        self.assertEqual(inspect.call_count, 2)

    def test_p282_authority_adds_exact_trace_and_child_runtime_paths(self):
        p282._validate_p282_authority_strings(_authority_data())
        self.assertIn(
            spec.CHILD_RUNTIME_STATUS_PATH,
            p282.REQUIRED_ABSOLUTE_PATH_STRINGS,
        )
        self.assertTrue(
            set(spec.TRACEFS_ABSOLUTE_PATHS).issubset(
                p282.REQUIRED_ABSOLUTE_PATH_STRINGS
            )
        )
        self.assertFalse(
            set(
                value
                for value in p280.REQUIRED_ABSOLUTE_PATH_STRINGS
                if value.startswith("/sys/kernel/tracing")
            ).issubset(p282.REQUIRED_ABSOLUTE_PATH_STRINGS)
        )

        for path in (
            spec.CHILD_RUNTIME_STATUS_PATH,
            spec.TRACEFS_ABSOLUTE_PATHS[0],
        ):
            token = path.encode("ascii") + b"\0"
            with self.assertRaisesRegex(
                p282.ClosureError, "required absolute path is missing"
            ):
                p282._validate_p282_authority_strings(
                    _authority_data().replace(token, b"", 1)
                )

    def test_role_reads_are_allowed_but_host_write_is_forbidden(self):
        p282._validate_p282_authority_strings(_authority_data())
        self.assertEqual(
            p282._HISTORICAL_SPEC.E3_ROLE_CONTROL_STRINGS,
            frozenset(("host", "none", "peripheral")),
        )
        self.assertEqual(
            p282._runtime_operation_contract()["parent-mode-host-write"],
            ('"host\\n"', 0),
        )
        with self.assertRaisesRegex(
            p282.ClosureError, "forbidden host role write"
        ):
            p282._validate_p282_authority_strings(
                _authority_data(host_write=True)
            )

    def test_runtime_operation_contract_mutations_fail_closed(self):
        changed = tuple(
            (
                name,
                token,
                1 if name == "parent-mode-host-write" else count,
            )
            for name, token, count in spec.RUNTIME_OPERATION_TOKENS
        )
        with mock.patch.object(spec, "RUNTIME_OPERATION_TOKENS", changed):
            with self.assertRaisesRegex(
                p282.ClosureError, "role operation contract mismatch"
            ):
                p282._runtime_operation_contract()

        with mock.patch.dict(
            spec.RUNTIME_AUTHORITY,
            {"host_role_authority": True},
        ):
            with self.assertRaisesRegex(
                p282.ClosureError, "parent role authority mismatch"
            ):
                p282._runtime_operation_contract()

    def test_scoped_authority_override_restores_p280_state(self):
        historical = p280.isolated_p260._validate_p260_authority_strings
        with p282._p282_authority_override():
            self.assertIs(
                p280.isolated_p260._validate_p260_authority_strings,
                p282._validate_p282_authority_strings,
            )
        self.assertIs(
            p280.isolated_p260._validate_p260_authority_strings,
            historical,
        )

    def test_rootfs_audit_delegates_under_scoped_p282_authority(self):
        historical = p280.isolated_p260._validate_p260_authority_strings
        expected = {"verified": True}

        def delegated(*_args, **_kwargs):
            self.assertIs(
                p280.isolated_p260._validate_p260_authority_strings,
                p282._validate_p282_authority_strings,
            )
            return expected

        with mock.patch.object(
            p280, "rootfs_audit", side_effect=delegated
        ) as audit:
            result = p282.rootfs_audit(
                b"candidate",
                b"vendor-boot",
                Path("/lz4"),
                expected_init={},
                expected_child={},
                run_id=b"0" * 16,
                module_closure={},
            )
        self.assertIs(result, expected)
        audit.assert_called_once()
        self.assertIs(
            p280.isolated_p260._validate_p260_authority_strings,
            historical,
        )

    def test_unexpected_absolute_path_is_rejected(self):
        with self.assertRaisesRegex(
            p282.ClosureError, "absolute-path authority mismatch"
        ):
            p282._validate_p282_authority_strings(
                _authority_data() + b"/sys/kernel/debug/tracing\0"
            )

    def test_short_elf_slash_artifacts_do_not_expand_path_authority(self):
        p282._validate_p282_authority_strings(
            _authority_data() + b"/B\0/q\0/8@\0"
        )
        with self.assertRaisesRegex(
            p282.ClosureError, "absolute-path authority mismatch"
        ):
            p282._validate_p282_authority_strings(
                _authority_data() + b"/tmp\0"
            )

    def test_read_only_canonical_speed_strings_do_not_expand_authority(self):
        p282._validate_p282_authority_strings(
            _authority_data()
            + b"low-speed\0full-speed\0super-speed\0"
        )
        with self.assertRaisesRegex(
            p282.ClosureError, "speed control authority mismatch"
        ):
            p282._validate_p282_authority_strings(
                _authority_data() + b"private-speed\0"
            )


if __name__ == "__main__":
    unittest.main()
