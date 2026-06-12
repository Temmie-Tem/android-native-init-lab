"""Regression tests for native_kernel_a90_boot_window_preflight_v2222."""

import argparse
import unittest

from _loader import load_revalidation

v2222 = load_revalidation("native_kernel_a90_boot_window_preflight_v2222")


class PreflightParsers(unittest.TestCase):
    def test_parse_json_object_accepts_clean_and_wrapped_payloads(self):
        self.assertEqual(v2222.parse_json_object('{"ok": true, "count": 2}'), {"ok": True, "count": 2})

        wrapped = "noise before\n{\"decision\": \"ready\", \"pass\": true}\ntrailing prompt"

        self.assertEqual(v2222.parse_json_object(wrapped), {"decision": "ready", "pass": True})

    def test_parse_json_object_empty_text_returns_empty_dict(self):
        self.assertEqual(v2222.parse_json_object(" \n\t"), {})

    def test_parse_protocol_rc_extracts_signed_rc_from_a90p1_end(self):
        self.assertEqual(v2222.parse_protocol_rc("A90P1 BEGIN\nA90P1 END elapsed=0.1 rc=0\n"), 0)
        self.assertEqual(v2222.parse_protocol_rc("A90P1 END cmd=foo rc=-11 extra\n"), -11)
        self.assertIsNone(v2222.parse_protocol_rc("no protocol footer"))

    def test_grep_value_returns_first_group_or_default(self):
        text = "version: A90 Linux init 0.9.268\ninit: ok\n"

        self.assertEqual(v2222.grep_value(r"version: ([^\n]+)", text), "A90 Linux init 0.9.268")
        self.assertEqual(v2222.grep_value(r"missing: ([^\n]+)", text, default="fallback"), "fallback")

    def test_parse_helper_inventory_filters_shell_noise_and_groups_key_values(self):
        raw = (
            "a90:/# prompt\n"
            "A90P1 BEGIN\n"
            "cmdv1x something\n"
            "WARNING: linker: Warning: failed to find generated linker configuration\n"
            "HELPER /bin/a90_android_execns_probe\n"
            "exists=1\n"
            "executable=1\n"
            "sha256=abc123\n"
            "version_string=a90_android_execns_probe v427\n"
            "ignored-without-equals\n"
            "HELPER /cache/bin/a90_android_execns_probe\n"
            "exists=0\n"
            "[done]\n"
        )

        inventory = v2222.parse_helper_inventory(raw)

        self.assertEqual(
            inventory["/bin/a90_android_execns_probe"],
            {
                "exists": "1",
                "executable": "1",
                "sha256": "abc123",
                "version_string": "a90_android_execns_probe v427",
            },
        )
        self.assertEqual(inventory["/cache/bin/a90_android_execns_probe"], {"exists": "0"})


class ContractAndCommandHelpers(unittest.TestCase):
    def test_a90ctl_command_includes_transport_options_and_allow_error(self):
        args = argparse.Namespace(bridge_host="127.0.0.1", bridge_port=54321, timeout=12.5)

        command = v2222.a90ctl_command(args, ["selftest"], allow_error=True)

        self.assertEqual(command[0], v2222.sys.executable)
        self.assertIn(str(v2222.SCRIPT_DIR / "a90ctl.py"), command)
        self.assertIn("--allow-error", command)
        self.assertEqual(command[-1], "selftest")
        self.assertEqual(command[command.index("--host") + 1], "127.0.0.1")
        self.assertEqual(command[command.index("--port") + 1], "54321")
        self.assertEqual(command[command.index("--timeout") + 1], "12.5")

    def test_build_contract_carries_preflight_evidence_and_forbidden_gates(self):
        summary = {
            "summary_path": "workspace/private/runs/kernel/sample/summary.json",
            "pass": True,
            "bridge_ready": True,
            "selftest_fail0": True,
            "native_version": "A90 Linux init 0.9.268",
            "event_exists_count": 21,
            "event_enabled_count": 21,
            "helper_inventory": {"/bin/a90_android_execns_probe": {"version_string": "v427"}},
            "v2221_contract_pass": True,
        }

        contract = v2222.build_contract(summary)

        self.assertEqual(contract["contract_version"], 1)
        self.assertTrue(contract["requires_explicit_user_approval"])
        self.assertTrue(contract["preflight_only_runner"])
        self.assertTrue(contract["current_preflight_pass"])
        self.assertIn("a90cnss:wlfw_start", contract["expected_event_sequence"])
        forbidden = "\n".join(contract["forbidden_without_new_approval"])
        self.assertIn("probe_write_user", forbidden)
        self.assertIn("Wi-Fi scan/connect", forbidden)
        self.assertEqual(contract["preflight_evidence"]["event_exists_count"], 21)
        self.assertEqual(contract["preflight_evidence"]["helper_inventory"], summary["helper_inventory"])

    def test_residual_state_encodes_no_flash_no_bpf_and_selftest_risk(self):
        untouched = v2222.residual_state({"steps": [], "selftest_fail0": False})
        touched_ok = v2222.residual_state({"steps": [{"name": "post-selftest"}], "selftest_fail0": True})
        touched_bad = v2222.residual_state({"steps": [{"name": "post-selftest"}], "selftest_fail0": False})

        self.assertFalse(untouched["device_touched"])
        self.assertFalse(untouched["cleanup_required"])
        self.assertTrue(touched_ok["device_touched"])
        self.assertTrue(touched_ok["selftest_ok"])
        self.assertFalse(touched_ok["cleanup_required"])
        self.assertTrue(touched_bad["cleanup_required"])
        self.assertEqual(touched_bad["residual_risk"], "post-selftest-incomplete")
        self.assertFalse(touched_bad["flash_reboot"])
        self.assertFalse(touched_bad["tracefs_control_write"])
        self.assertFalse(touched_bad["bpf_attach"])
        self.assertFalse(touched_bad["partition_write"])

    def test_step_result_ok_property(self):
        ok = v2222.StepResult("ok", ["true"], 0, 0.01, "stdout", "stderr")
        bad = v2222.StepResult("bad", ["false"], 1, 0.01, "stdout", "stderr")

        self.assertTrue(ok.ok)
        self.assertFalse(bad.ok)


if __name__ == "__main__":
    unittest.main()
