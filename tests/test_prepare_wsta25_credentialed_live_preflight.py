from __future__ import annotations

import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


preflight = load_script("workspace/public/src/scripts/server-distro/prepare_wsta25_live_gate_preflight.py")


class PrepareWsta25CredentialedLivePreflightTests(unittest.TestCase):
    def write_env(self, path: Path, text: str, mode: int = 0o600) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(mode)

    def test_redacted_wifi_env_status_keeps_values_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / "wifi.env"
            self.write_env(env, "A90_WIFI_SSID='Lab Net'\nA90_WIFI_PSK='12345678'\n")

            status = preflight.redacted_wifi_env_status(env)

        self.assertTrue(status["ok"])
        self.assertTrue(status["owner_private"])
        self.assertEqual(status["ssid_len"], len("Lab Net"))
        self.assertEqual(status["psk_len"], 8)
        self.assertEqual(status["psk_format"], "passphrase")
        rendered = json.dumps(status, sort_keys=True)
        self.assertNotIn("Lab Net", rendered)
        self.assertNotIn("12345678", rendered)

    def test_redacted_wifi_env_status_requires_private_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / "wifi.env"
            self.write_env(env, "A90_WIFI_SSID=x\nA90_WIFI_PSK=12345678\n", mode=0o644)

            status = preflight.redacted_wifi_env_status(env)
            mode = stat.S_IMODE(env.stat().st_mode)

        self.assertFalse(status["ok"])
        self.assertEqual(status["reason"], "wifi-env-not-0600")
        self.assertFalse(status["owner_private"])
        self.assertEqual(mode, 0o644)

    def test_redacted_live_command_never_contains_real_token(self) -> None:
        args = SimpleNamespace(service_dir="/tmp/svc")

        command = preflight.redacted_live_command(args)

        self.assertIn("--allow-confirmed-live", command)
        self.assertIn("--ack-credentialed-wifi", command)
        self.assertIn("--confirm-token", command)
        self.assertIn(preflight.REDACTED_TOKEN, command)
        self.assertNotIn(preflight.wsta25.NATIVE_CONFIRM_TOKEN, command)

    def test_classify_requires_wifi_env_runner_surface_and_default_dry_run(self) -> None:
        result = {
            "wifi_env": {"ok": True},
            "runner_surface": {
                "exists": True,
                "explicit_gate": True,
                "confirm_token_arg": True,
                "status_readiness_gate": True,
                "redacted_stdin_executor": True,
                "no_public_tunnel": True,
                "no_direct_wifi_connect": True,
                "no_direct_dhcp_ping": True,
            },
            "default_dry_run": {
                "stdout_decision": "wsta25-blocked-explicit-live-allow-required",
                "returncode": 2,
            },
        }

        self.assertEqual(preflight.classify(result), preflight.PASS_DECISION)
        self.assertEqual(
            preflight.classify({**result, "wifi_env": {"ok": False}}),
            "wsta25-blocked-wifi-env",
        )
        bad_runner = {**result["runner_surface"], "redacted_stdin_executor": False}
        self.assertEqual(
            preflight.classify({**result, "runner_surface": bad_runner}),
            "wsta25-blocked-runner-surface",
        )
        bad_dry = {**result["default_dry_run"], "stdout_decision": "pass"}
        self.assertEqual(
            preflight.classify({**result, "default_dry_run": bad_dry}),
            "wsta25-blocked-runner-default-gate",
        )

    def test_run_default_dry_run_parses_decision_without_secrets(self) -> None:
        args = SimpleNamespace(dry_run_timeout=5.0)
        payload = {"decision": "wsta25-blocked-explicit-live-allow-required"}

        def fake_run(command, **_kwargs):  # type: ignore[no-untyped-def]
            return subprocess.CompletedProcess(command, 2, stdout=json.dumps(payload), stderr="")

        with mock.patch.object(preflight.subprocess, "run", side_effect=fake_run):
            record = preflight.run_default_dry_run(args)

        self.assertEqual(record["returncode"], 2)
        self.assertEqual(record["stdout_decision"], "wsta25-blocked-explicit-live-allow-required")
        self.assertEqual(record["secret_values_logged"], 0)
        self.assertNotIn(preflight.wsta25.NATIVE_CONFIRM_TOKEN, json.dumps(record))

    def test_full_run_writes_redacted_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = tmp_path / "wifi.env"
            run_dir = tmp_path / "run"
            self.write_env(env, "A90_WIFI_SSID='Lab Net'\nA90_WIFI_PSK='12345678'\n")
            args = SimpleNamespace(
                run_dir=run_dir,
                run_id=None,
                wifi_env=env,
                service_dir="/tmp/svc",
                dry_run_timeout=5.0,
                run_default_dry_run=False,
            )

            result = preflight.run(args)

            output = (run_dir / "wsta25_preflight.json").read_text(encoding="utf-8")
        self.assertEqual(result["decision"], "wsta25-blocked-runner-default-gate")
        self.assertIn(preflight.REDACTED_TOKEN, output)
        self.assertNotIn("Lab Net", output)
        self.assertNotIn("12345678", output)
        self.assertNotIn(preflight.wsta25.NATIVE_CONFIRM_TOKEN, output)


if __name__ == "__main__":
    unittest.main()
