from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta48_redacted_result_aggregate.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta48_redacted_result_aggregate.py")


class ServerDistroWsta48RedactedResultAggregateTests(unittest.TestCase):
    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def test_aggregate_redacts_nested_wsta45_live_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "wsta45_result.json"
            payload = {
                "scope": "WSTA45 appliance operator wrapper for native-uplink D-public publish",
                "started_utc": "20260704T010000Z",
                "ended_utc": "20260704T010030Z",
                "decision": runner.wsta45.PASS_DECISION,
                "run_dir": "workspace/private/runs/server-distro/example",
                "mode": "publish",
                "gate_decision": "ok",
                "operator_publish_template": runner.wsta45.operator_publish_template(),
                "profile_contract": {"ok": True, "secret_values_logged": 0},
                "operator_menu": [],
                "checks": {"wsta43_pass": True, "wsta43_profile_requested": True},
                "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
                "wsta43": {
                    "decision": runner.wsta43.PASS_DECISION,
                    "run_dir": "workspace/private/runs/server-distro/example/wsta43",
                    "gate_decision": "ok",
                    "checks": {"explicit_live_gate": True, "wsta28_scan_green": True, "wsta42_pass": True},
                    "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
                    "wsta28": {"decision": "wsta28-reboot-materialization-scan-gate-pass"},
                    "wsta42": {
                        "decision": runner.wsta42.PASS_DECISION,
                        "run_dir": "workspace/private/runs/server-distro/example/wsta42",
                        "checks": {
                            "use_native_uplink_profile": True,
                            "native_uplink_profile_confirmed": True,
                            "public_url_value_logged": False,
                        },
                        "resolver_sync": {"ready": True, "nameserver_count": 2},
                        "smoke_start": {"local_smoke_ok": True, "loopback_up_rc": 0},
                        "cloudflared_start": {
                            "url_observed": True,
                            "url": "https://leak.example.trycloudflare.com",
                        },
                        "public_url_fetch": {
                            "url_observed": True,
                            "url_len": 53,
                            "stdout_redacted": True,
                            "private_path": "workspace/private/runs/example/public-url.txt",
                        },
                        "host_public_smoke": {
                            "http_status": 200,
                            "marker_ok": True,
                            "service_ok": True,
                            "public_exposure_marker_ok": True,
                            "url_redacted": True,
                            "url": "https://leak.example.trycloudflare.com",
                        },
                    },
                },
            }
            self.write_json(result_path, payload)

            aggregate = runner.build_aggregate([result_path])

        text = json.dumps(aggregate, sort_keys=True)
        self.assertEqual(aggregate["result_count"], 1)
        self.assertTrue(aggregate["all_pass"])
        self.assertEqual(aggregate["entries"][0]["elapsed_sec"], 30.0)
        self.assertIn("<native-confirm-token>", text)
        self.assertNotIn("trycloudflare.com", text)
        self.assertNotIn("public-url.txt", text)
        self.assertNotIn(runner.wsta25.NATIVE_CONFIRM_TOKEN, text)
        self.assertNotIn(runner.wsta43.PUBLIC_CONFIRM_TOKEN, text)

    def test_discovers_directory_and_summarizes_wsta42_elapsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            self.write_json(run_dir / "wsta42_result.json", {
                "scope": "WSTA42 native-owned STA uplink plus Debian D-public quick Tunnel",
                "started_utc": "20260704T010000Z",
                "ended_utc": "20260704T010005Z",
                "decision": runner.wsta42.PASS_DECISION,
                "run_dir": "workspace/private/runs/server-distro/wsta42",
                "checks": {
                    "public_url_value_logged": False,
                    "secret_values_logged": 0,
                    "public_smoke_ok": True,
                },
                "safety": {"public_url_value_logged": False, "secret_values_logged": 0},
                "public_url_fetch": {
                    "url_observed": True,
                    "url_len": 52,
                    "stdout_redacted": True,
                },
                "host_public_smoke": {"http_status": 200, "url_redacted": True},
            })

            aggregate = runner.build_aggregate([run_dir])

        self.assertEqual(aggregate["result_count"], 1)
        self.assertEqual(aggregate["entries"][0]["kind"], "wsta42")
        self.assertEqual(aggregate["entries"][0]["elapsed_sec"], 5.0)
        self.assertEqual(aggregate["decisions"], {runner.wsta42.PASS_DECISION: 1})

    def test_redaction_guard_fails_on_forbidden_unknown_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "wsta99_result.json"
            self.write_json(result_path, {
                "scope": "unknown",
                "decision": "example-pass",
                "safety": {"secret": runner.wsta25.NATIVE_CONFIRM_TOKEN},
            })

            with self.assertRaises(ValueError):
                runner.build_aggregate([result_path])

    def test_cli_writes_output_without_running_device_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "wsta42_result.json"
            output_path = Path(tmp) / "aggregate.json"
            self.write_json(result_path, {
                "scope": "WSTA42 native-owned STA uplink plus Debian D-public quick Tunnel",
                "decision": runner.wsta42.PASS_DECISION,
                "checks": {"public_url_value_logged": False},
                "safety": {"boot_flash": False, "public_url_value_logged": False},
            })

            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--input", str(result_path), "--output", str(output_path)])

            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(written["result_count"], 1)
        self.assertTrue(printed.called)
        self.assertEqual(written["entries"][0]["kind"], "wsta42")

    def test_source_surface_is_host_only_and_fail_closed(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("redaction_findings", source)
        self.assertIn("trycloudflare.com", source)
        self.assertIn("public-url.txt", source)
        self.assertIn("FORBIDDEN_LITERAL_VALUES", source)
        self.assertIn("wsta45.public_summary", source)
        self.assertIn("wsta43.public_summary", source)
        self.assertIn("summarize_wsta42", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("wifi connect", source.lower())


if __name__ == "__main__":
    unittest.main()
