"""Host-only tests for the strict native F1 effect receipt boundary."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OWNER = load(
    "a90_boot_only_f1_minimal_v1_receipt_test",
    ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py",
)
sys.modules["a90_boot_only_f1_minimal_v1"] = OWNER
ADAPTER = load(
    "a90_boot_only_f1_adapter_v1_receipt_test",
    ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_adapter_v1.py",
)
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
FLASH = load(
    "native_init_flash_receipt_test",
    ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py",
)


def receipt(**overrides: object) -> bytes:
    value = {
        "schema": ADAPTER.OWNER_RECEIPT_SCHEMA,
        "mode": ADAPTER.OWNER_RECEIPT_MODE,
        "outcome": "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        "writeStarted": True,
        "bootWrittenReadbackExact": True,
        "systemReturnAttempted": True,
        "systemReturnCommandOk": True,
        "systemReturnConfirmed": False,
    }
    value.update(overrides)
    return ADAPTER.canonical_json(value)


class OwnerReceiptTest(unittest.TestCase):
    def test_exact_uncertain_receipt_is_the_only_pending_candidate_input(self):
        self.assertEqual(
            ADAPTER._parse_owner_effect_receipt(receipt()),
            "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        )
        self.assertIn("23-candidate-return-pending.json", OWNER.RECORDS)
        self.assertEqual(
            OWNER.recovery_decision.__name__, "recovery_decision"
        )

    def test_generic_rc_prose_missing_and_malformed_receipts_are_unclassified(self):
        for raw in (b"", b"rc=1 twrp reboot uncertain", b"{}", b"{}\n"):
            with self.subTest(raw=raw):
                self.assertEqual(ADAPTER._parse_owner_effect_receipt(raw), "UNCLASSIFIED")
        duplicate = (
            b'{"schema":"a90-f1-owner-effect-receipt-v1",'
            b'"schema":"a90-f1-owner-effect-receipt-v1"}'
        )
        self.assertEqual(ADAPTER._parse_owner_effect_receipt(duplicate), "UNCLASSIFIED")

    def test_receipt_state_machine_rejects_inconsistent_flags(self):
        for changed in (
            {"systemReturnConfirmed": True},
            {"bootWrittenReadbackExact": False},
            {"writeStarted": False},
            {"systemReturnAttempted": False},
            {"systemReturnCommandOk": False},
        ):
            with self.subTest(changed=changed):
                self.assertEqual(
                    ADAPTER._parse_owner_effect_receipt(receipt(**changed)),
                    "UNCLASSIFIED",
                )
        missing = json.loads(receipt().decode("ascii"))
        del missing["systemReturnAttempted"]
        self.assertEqual(
            ADAPTER._parse_owner_effect_receipt(ADAPTER.canonical_json(missing)),
            "UNCLASSIFIED",
        )

    def test_native_owner_state_classifies_without_prose(self):
        state = FLASH.OwnerEffectState()
        self.assertEqual(state.outcome(), "PRE_WRITE_FAILURE")
        state.write_started = True
        self.assertEqual(state.outcome(), "WRITE_OR_READBACK_UNCLASSIFIED")
        state.boot_written_readback_exact = True
        self.assertEqual(state.outcome(), "WRITE_OR_READBACK_UNCLASSIFIED")
        state.system_return_attempted = True
        self.assertEqual(state.outcome(), "WRITE_OR_READBACK_UNCLASSIFIED")
        state.system_return_command_ok = True
        self.assertEqual(
            state.outcome(),
            "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        )
        state.system_return_confirmed = True
        self.assertEqual(
            state.outcome(),
            "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
        )

    def test_fixed_owner_mode_is_bound_to_helper_argv(self):
        argv = ADAPTER.fixed_flash_argv(
            {
                "path": "/candidate.img",
                "sha256": "a" * 64,
                "version": "candidate",
            },
            recovery_serial_sha256="b" * 64,
            timeout_sec=90,
            rollback=False,
        )
        self.assertIn("--owner-receipt-mode", argv)
        self.assertIn(ADAPTER.OWNER_RECEIPT_MODE, argv)
        self.assertNotIn("--serial", argv)
        self.assertNotIn("adb reboot", " ".join(argv))

    def test_twrp_nonzero_cannot_be_confirmed_by_endpoint_disappearance(self):
        state = FLASH.OwnerEffectState(
            write_started=True,
            boot_written_readback_exact=True,
        )
        old_state = FLASH.OWNER_EFFECT_STATE
        FLASH.OWNER_EFFECT_STATE = state
        args = types.SimpleNamespace(
            adb="adb",
            require_empty_adb_baseline=False,
            require_stable_adb_baseline=True,
            reuse_bound_recovery_or_from_native=False,
        )
        try:
            with mock.patch.object(
                FLASH,
                "run_command",
                return_value=subprocess.CompletedProcess(
                    ["adb"], 7, stdout=b"", stderr=b"failed"
                ),
            ), mock.patch.object(FLASH.time, "sleep"):
                with self.assertRaisesRegex(RuntimeError, "rc=7"):
                    FLASH.reboot_twrp_to_system(args, "recovery", adb_baseline=[])
        finally:
            FLASH.OWNER_EFFECT_STATE = old_state
        self.assertTrue(state.system_return_attempted)
        self.assertFalse(state.system_return_command_ok)
        self.assertEqual(state.outcome(), "WRITE_OR_READBACK_UNCLASSIFIED")

    def test_legacy_mode_preserves_disappearance_result_assumption(self):
        args = types.SimpleNamespace(
            adb="adb",
            require_empty_adb_baseline=False,
            require_stable_adb_baseline=True,
            reuse_bound_recovery_or_from_native=False,
        )
        old_state = FLASH.OWNER_EFFECT_STATE
        FLASH.OWNER_EFFECT_STATE = None
        try:
            with mock.patch.object(
                FLASH,
                "run_command",
                return_value=types.SimpleNamespace(
                    stdout="", stderr="", returncode=7
                ),
            ), mock.patch.object(
                FLASH, "wait_for_adb_baseline_restored", return_value=True
            ), mock.patch.object(FLASH.time, "sleep"):
                FLASH.reboot_twrp_to_system(args, "recovery", adb_baseline=[])
        finally:
            FLASH.OWNER_EFFECT_STATE = old_state


if __name__ == "__main__":
    unittest.main()
