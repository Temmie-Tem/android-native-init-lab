"""Host-only tests for the A90 Phase 2D connected preflight."""

from __future__ import annotations

import hashlib
import os
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

from _loader import load_script


preflight = load_script(
    "workspace/public/src/scripts/server-distro/"
    "a90_phase2d_connected_preflight.py"
)
SOURCE = Path(
    "workspace/public/src/scripts/server-distro/"
    "a90_phase2d_connected_preflight.py"
)


class A90Phase2DConnectedPreflightTests(unittest.TestCase):
    def test_source_contract_is_closed(self) -> None:
        self.assertEqual(
            preflight.source_contract_issues(SOURCE.read_text(encoding="utf-8")),
            (),
        )

    def test_audit_mode_has_no_connected_authority(self) -> None:
        result = preflight.audit_payload()
        self.assertTrue(result["ready_for_connected_d0"])
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["device_write"])
        self.assertFalse(result["f1_authorized"])
        self.assertFalse(result["live_authority"])

    def test_default_parser_requires_explicit_mode(self) -> None:
        parser = preflight.build_parser()
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parser.parse_args([])
        args = parser.parse_args(["--audit-only"])
        self.assertTrue(args.audit_only)
        self.assertFalse(args.execute_connected_d0)

    def test_path_script_contains_only_exact_reads(self) -> None:
        script = preflight.path_read_script(
            "/mnt/sdext/a90/runtime/final.img",
            "/mnt/sdext/a90/runtime/work.img",
            "/mnt/sdext/a90/runtime/stage",
        )
        for token in ("FINAL=", "WORK=", "STAGE=", "[ -e", "[ -L", "printf"):
            self.assertIn(token, script)
        for forbidden in ("rm ", "mv ", "cp ", "dd ", "mount ", "reboot"):
            self.assertNotIn(forbidden, script)

    def test_health_parser_requires_zero_fail_and_pstore(self) -> None:
        baseline = {
            "version": {"rc": 0, "text": "0.9.285"},
            "status": {"rc": 0, "text": "pstore=ok entries=0"},
            "selftest": {
                "rc": 0,
                "text": "pass=11 warn=1 fail=0 duration_ms=49",
            },
        }
        result = preflight.parse_health(baseline)
        self.assertEqual(result["selftest"]["fail"], 0)
        self.assertEqual(result["pstore_entries"], 0)
        broken = {
            **baseline,
            "selftest": {
                "rc": 0,
                "text": "pass=10 warn=1 fail=1 duration_ms=49",
            },
        }
        with self.assertRaises(preflight.ContractError):
            preflight.parse_health(broken)

    def test_exact_bridge_requires_by_id_and_expected_realpath(self) -> None:
        args = types.SimpleNamespace()
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "ttyACM7"
            target.write_bytes(b"")
            link = Path(temp_dir) / "by-id-device"
            link.symlink_to(target)
            old_prefix = preflight.BRIDGE_DEVICE_PREFIX
            try:
                preflight.BRIDGE_DEVICE_PREFIX = str(Path(temp_dir)) + "/"
                with mock.patch.object(
                    preflight.staging,
                    "require_exact_bridge",
                    return_value={
                        "selected_realpath": str(target),
                        "ok": True,
                    },
                ) as helper:
                    result = preflight.require_exact_bridge(
                        str(link),
                        str(target),
                        args,
                    )
                self.assertTrue(result["ok"])
                helper.assert_called_once()
                with self.assertRaises(preflight.ContractError):
                    preflight.require_exact_bridge(
                        str(link),
                        str(Path(temp_dir) / "different"),
                        args,
                    )
            finally:
                preflight.BRIDGE_DEVICE_PREFIX = old_prefix

    def test_private_artifact_hash_and_mode_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=preflight.staging.PRIVATE_ROOT
        ) as temp_dir:
            path = Path(temp_dir) / "boot.img"
            path.write_bytes(b"boot")
            path.chmod(0o600)
            digest = hashlib.sha256(b"boot").hexdigest()
            info = preflight.require_regular_private(
                path,
                expected_sha256=digest,
            )
            self.assertEqual(info.st_size, 4)
            path.chmod(0o666)
            with self.assertRaises(preflight.ContractError):
                preflight.require_regular_private(
                    path,
                    expected_sha256=digest,
                )
            path.chmod(0o600)
            link = Path(temp_dir) / "boot-link.img"
            link.symlink_to(path)
            with self.assertRaisesRegex(
                preflight.ContractError,
                "symbolic link",
            ):
                preflight.require_regular_private(
                    link,
                    expected_sha256=digest,
                )

    def test_private_writer_is_exclusive_and_mode_0600(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "result.json"
            preflight.write_private_json_exclusive(path, {"ok": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(preflight.staging.ContractError):
                preflight.write_private_json_exclusive(path, {"ok": False})

    def test_source_mutations_are_detected(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for before, after, reverse in (
            ('"device_write": False', '"device_write": True', False),
            ("staging.require_baseline(", "removed_baseline(", False),
            (
                'mode.add_argument("--audit-only"',
                'mode.add_argument("--audit"',
                True,
            ),
        ):
            with self.subTest(before=before):
                if reverse:
                    prefix, match, suffix = source.rpartition(before)
                    self.assertTrue(match)
                    mutated = prefix + after + suffix
                else:
                    mutated = source.replace(before, after, 1)
                self.assertTrue(preflight.source_contract_issues(mutated))
        self.assertTrue(
            preflight.source_contract_issues(
                source.replace(
                    "def audit_payload()",
                    "def hidden():\n    flash_command()\n\ndef audit_payload()",
                    1,
                )
            )
        )

    def test_no_concrete_device_identity_is_tracked(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"/dev/serial/by-id/[^\"']+")
        self.assertNotRegex(text, r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
        self.assertNotIn("ttyACM0", text)


if __name__ == "__main__":
    unittest.main()
