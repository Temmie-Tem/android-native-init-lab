from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta198SeccompLoadCanarySshAdapterTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_transport_gate(self, root: Path, *, mutate: dict | None = None) -> Path:
        gate_path = root / "wsta197" / runner.wsta197.TRANSPORT_JSON_NAME
        payload = {
            "schema": "a90-wsta197-seccomp-load-canary-transport-gate-v1",
            "state": "TRANSPORT_DECIDED_WSTA196_LIVE_BLOCKED_UNTIL_ADAPTER",
            "selected_transport": runner.wsta197.SELECTED_TRANSPORT,
            "transport_gate_json": runner.rel(gate_path),
            "transport_gate_markdown": runner.rel(root / "wsta197" / runner.wsta197.TRANSPORT_MD_NAME),
            "source_wsta196_result": "workspace/private/wsta196_result.json",
            "source_wsta196_source_gate": "workspace/private/wsta196_source_gate.json",
            "source_wsta149_live_transport_proof": "workspace/private/wsta149_result.json",
            "source_wsta167_seccomp_asset_source_gate": "workspace/private/wsta167_result.json",
            "canary_service": "dpublic-hud",
            "policy_service": "dpublic-hud-intent",
            "launcher_command": ["/usr/local/bin/a90-service-launch", "dpublic-hud", "/bin/true"],
            "single_service_canary": True,
            "private_token_env": runner.wsta193.PRIVATE_TOKEN_ENV,
            "token_value_included": False,
            "correct_wsta161_token_supplied": False,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
            "wsta196_direct_host_subprocess_execute_allowed": False,
            "wsta196_direct_host_subprocess_reason": "host subprocess disallowed",
            "ready_for_wsta198_transport_adapter": True,
            "ready_for_wsta196_live_execute": False,
            "execution_sequence": [
                "fresh-native-readonly-health",
                "mount-debian-chroot",
                "start-temporary-dropbear-over-ncm",
                "run-single-service-canary-via-ssh-with-private-token-env",
                "post-native-readonly-health",
            ],
            "adapter_contract": {
                "runner": "workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py",
                "input_transport_gate": runner.rel(gate_path),
                "must_not_put_token_on_command_line": True,
                "must_redact_token_from_stdout_stderr": True,
                "must_fail_closed_without_wsta196_ack_flags": True,
                "must_fail_closed_without_private_token_env": True,
                "must_fail_closed_without_fresh_health": True,
                "must_cleanup_chroot_dropbear_even_on_failure": True,
            },
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        if mutate:
            payload.update(mutate)
        self.write_json(gate_path, payload)
        return gate_path

    def source_args(self, root: Path, gate: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta198"),
            "--wsta197-transport-gate-json",
            str(gate),
            "--emit-wsta198-ssh-adapter-packet",
        ]

    def live_args(self, root: Path, gate: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta198-live"),
            "--wsta197-transport-gate-json",
            str(gate),
            "--local-image",
            str(root / "debian.img"),
            "--local-image-sha256",
            "fake-sha",
            "--wsta153-seccomp-policy-json",
            str(root / "inputs" / "wsta153_seccomp_policy.json"),
            "--wsta156-filter-manifest-json",
            str(root / "inputs" / "wsta156_seccomp_filter_manifest.json"),
            "--wsta156-filter-object",
            str(root / "inputs" / "wsta156_seccomp_filters.o"),
            "--wsta161-loader-helper-manifest-json",
            str(root / "inputs" / "wsta161_seccomp_loader_helper_manifest.json"),
            "--wsta161-loader-helper",
            str(root / "inputs" / "a90-seccomp-loader-gated-apply"),
            *runner.ACK_FLAGS,
        ]

    def health_ok(self) -> dict:
        return {
            "checks": {
                "bridge_ready": True,
                "version_ok": True,
                "status_ok": True,
                "selftest_fail_zero": True,
            }
        }

    def bridge_record(self, text: str) -> dict:
        return {"rc": 0, "text": text}

    def test_source_gate_writes_default_off_adapter_packet(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            gate = self.write_transport_gate(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.source_args(root, gate)))
            adapter = json.loads((root / "wsta198" / runner.ADAPTER_JSON_NAME).read_text(encoding="utf-8"))
            script = (root / "wsta198" / runner.ADAPTER_SH_NAME).read_text(encoding="utf-8")
            markdown = (root / "wsta198" / runner.ADAPTER_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.SOURCE_PASS_DECISION)
        self.assertEqual(adapter["selected_transport"], runner.wsta197.SELECTED_TRANSPORT)
        self.assertEqual(adapter["token_transport"], "ssh-stdin-redacted-to-remote-env")
        self.assertTrue(adapter["ready_for_attended_live"])
        self.assertFalse(adapter["ready_for_unattended_live"])
        self.assertFalse(adapter["live_execution_requested"])
        self.assertIn("--execute-real-seccomp-load-canary-over-ssh", script)
        self.assertIn(runner.wsta193.PRIVATE_TOKEN_ENV, script)
        self.assertIn("WSTA198 does not run the live canary", markdown)
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])

    def test_default_run_is_fail_closed_without_explicit_source_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            gate = self.write_transport_gate(root)
            args = self.source_args(root, gate)
            args.remove("--emit-wsta198-ssh-adapter-packet")
            result = runner.run(runner.build_arg_parser().parse_args(args))

        self.assertEqual(result["decision"], "wsta198-blocked-explicit-source-gate-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])

    def test_blocks_invalid_or_nonprivate_transport_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            gate = self.write_transport_gate(root, mutate={"selected_transport": "host-subprocess"})
            result = runner.run(runner.build_arg_parser().parse_args(self.source_args(root, gate)))
        self.assertEqual(result["decision"], "wsta198-blocked-transport-gate-invalid")
        self.assertFalse(result["wsta197_transport_gate_checks"]["selected_transport_matches"])

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            gate = Path(outside) / runner.wsta197.TRANSPORT_JSON_NAME
            self.write_json(gate, {"schema": "a90-wsta197-seccomp-load-canary-transport-gate-v1"})
            result = runner.run(runner.build_arg_parser().parse_args(self.source_args(root, gate)))
        self.assertEqual(result["decision"], "wsta198-blocked-transport-gate-nonprivate")

    def test_live_gate_requires_private_token_before_device_path(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            gate = self.write_transport_gate(root)
            with mock.patch.object(runner.wsta196, "run_readonly_health_checks", side_effect=AssertionError("no health")):
                result = runner.run(runner.build_arg_parser().parse_args(self.live_args(root, gate)))

        self.assertEqual(result["decision"], "wsta198-blocked-private-token-env-missing")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_live_parser_exposes_helper_timeout_contract(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            gate = self.write_transport_gate(root)
            args = runner.build_arg_parser().parse_args(self.live_args(root, gate))

        self.assertEqual(args.bridge_timeout, 60.0)
        self.assertEqual(args.connect_timeout, 10.0)
        self.assertEqual(args.tcp_timeout, 30.0)
        self.assertEqual(args.transfer_timeout, 900.0)
        self.assertEqual(args.transfer_delay, 2.0)
        self.assertEqual(args.toybox, "/bin/toybox")
        self.assertEqual(args.wsta153_seccomp_policy_json, root / "inputs" / "wsta153_seccomp_policy.json")
        self.assertEqual(args.wsta161_loader_helper, root / "inputs" / "a90-seccomp-loader-gated-apply")

    def test_mocked_live_path_uses_ssh_stdin_token_and_redacts_output(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            gate = self.write_transport_gate(root)
            (root / "debian.img").write_text("fake", encoding="utf-8")
            for asset in (
                root / "inputs" / "wsta153_seccomp_policy.json",
                root / "inputs" / "wsta156_seccomp_filter_manifest.json",
                root / "inputs" / "wsta156_seccomp_filters.o",
                root / "inputs" / "wsta161_seccomp_loader_helper_manifest.json",
                root / "inputs" / "a90-seccomp-loader-gated-apply",
            ):
                asset.parent.mkdir(parents=True, exist_ok=True)
                asset.write_bytes(b"fake")
            mount_text = "A90D2_MOUNT_READY\nA90D2 mounted=1\n"
            start_text = "A90D2_DROPBEAR_STARTED\nA90D2 authorized_keys=1\nA90D2 shadow_temp_key_only=1\n"
            cleanup_text = "A90D2_CLEANUP_DONE\nA90D2 shadow_restored=1\n"
            postcheck_text = (
                "A90D2_POSTCHECK_DONE\n"
                "A90D2 post_mount_absent=1\n"
                "A90D2 post_loop_node_absent=1\n"
                "A90D2 post_dropbear_absent=1\n"
            )
            completed = SimpleNamespace(
                returncode=0,
                stdout=(
                    "A90WSTA198_REMOTE_CANARY_BEGIN\n"
                    "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1\n"
                    "a90_seccomp_loader_decision=loaded\n"
                    "A90WSTA163_SECCOMP_HELPER_APPLY_OK=1\n"
                    "A90WSTA154_SECCOMP_SERVICE=dpublic-hud\n"
                    "A90WSTA154_SECCOMP_POLICY_SERVICE=dpublic-hud-intent\n"
                    + runner.wsta161.LOAD_TOKEN
                    + "\n"
                ),
                stderr=runner.wsta161.LOAD_TOKEN,
            )
            with mock.patch.dict(runner.os.environ, {
                runner.wsta193.PRIVATE_TOKEN_ENV: runner.wsta161.LOAD_TOKEN
            }):
                with mock.patch.object(runner.wsta196, "run_readonly_health_checks", side_effect=[
                    self.health_ok(),
                    self.health_ok(),
                ]), mock.patch.object(runner.d2, "generate_ssh_key", return_value={"returncode": 0}), \
                    mock.patch.object(runner.d2, "read_public_key", return_value="ssh-ed25519 test"), \
                    mock.patch.object(runner.wsta94, "native_stale_cleanup", return_value={"cleaned": True}), \
                    mock.patch.object(runner.d1, "sha256_file", return_value="fake-sha"), \
                    mock.patch.object(runner.wsta42, "prepare_remote_work_image", return_value=True), \
                    mock.patch.object(runner, "stage_seccomp_canary_assets", return_value={
                        "staged": True,
                        "secret_values_logged": 0,
                    }), \
                    mock.patch.object(runner.wsta19, "bridge_shell", side_effect=[
                        self.bridge_record(mount_text),
                        self.bridge_record(start_text),
                        self.bridge_record(cleanup_text),
                        self.bridge_record(postcheck_text),
                    ]), mock.patch.object(runner.wsta19, "ssh_chroot_marker", return_value={
                        "marker": {"marker": True, "debian_version": "12.14"}
                    }), mock.patch.object(runner.subprocess, "run", return_value=completed) as subprocess_run, \
                    mock.patch.object(runner.wsta196, "run_canary_command", side_effect=AssertionError("host subprocess")):
                        result = runner.run(runner.build_arg_parser().parse_args(self.live_args(root, gate)))

        self.assertEqual(result["decision"], runner.LIVE_PASS_DECISION)
        self.assertTrue(result["safety"]["ssh_chroot_transport"])
        self.assertTrue(result["safety"]["token_passed_over_stdin_redacted"])
        self.assertTrue(result["safety"]["seccomp_assets_staged"])
        self.assertTrue(result["safety"]["seccomp_filter_loaded"])
        self.assertTrue(result["checks"]["canary_loaded"])
        self.assertIn("<redacted-wsta161-token>", result["execution"]["stdout"])
        self.assertIn("<redacted-wsta161-token>", result["execution"]["stderr"])
        self.assertNotIn(runner.wsta161.LOAD_TOKEN, json.dumps(result["execution"], sort_keys=True))
        ssh_command = result["execution"]["command"]
        self.assertEqual(ssh_command[-2:], ["root@192.168.7.2", "/bin/sh", "-s"][-2:])
        self.assertNotIn(runner.wsta161.LOAD_TOKEN, " ".join(ssh_command))
        self.assertTrue(subprocess_run.called)

    def test_print_template_and_public_surfaces_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            gate = self.write_transport_gate(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.source_args(root, gate)))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            adapter_text = (root / "wsta198" / runner.ADAPTER_JSON_NAME).read_text(encoding="utf-8")
            script_text = (root / "wsta198" / runner.ADAPTER_SH_NAME).read_text(encoding="utf-8")
            source_text = SOURCE.read_text(encoding="utf-8")

        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        for text in (summary_text, adapter_text, script_text, source_text, printed.call_args.args[0]):
            self.assertNotIn(TOKEN_LITERAL, text)
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("native_init_flash.py", text)
        self.assertIn("wsta198-seccomp-load-canary-ssh-adapter-source-pass", source_text)
        self.assertIn("READY_SSH_CHROOT_ADAPTER_DEFAULT_OFF_LIVE_BLOCKED_UNTIL_TOKEN_AND_HEALTH", source_text)
        self.assertIn('"boot_flash": False', source_text)
        self.assertIn('"correct_wsta161_token_in_artifact": False', source_text)


if __name__ == "__main__":
    unittest.main()
