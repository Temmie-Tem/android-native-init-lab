import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1b_live_binding_packet.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_r4w1b_live_binding_packet", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1BLiveBindingPacketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def values(self):
        return {
            "CONNECTED_PASS_CREATED_AT_UTC": "2026-07-18T21:30:00.000000Z",
            "CONNECTED_PASS_RECORD_SIZE": "1234",
            "CONNECTED_PASS_RECORD_SHA256": "a" * 64,
            "CONNECTED_RESULT_PATH": "workspace/private/runs/run/result.json",
            "CONNECTED_RESULT_SIZE": "5678",
            "CONNECTED_RESULT_SHA256": "b" * 64,
        }

    def test_exact_source_and_template_pins(self):
        module = self.module
        self.assertEqual(module.EXPECTED_HELPER_SHA256, module.gate.helper_sha256(module.gate.repo_root()))
        self.assertEqual(module.EXPECTED_TEST_SHA256, module.gate.test_sha256(module.gate.repo_root()))
        self.assertEqual(module.EXPECTED_CORE_SHA256, module.gate.core_sha256(module.gate.repo_root()))
        self.assertEqual(module.EXPECTED_CORE_TEST_SHA256, module.gate.core_test_sha256(module.gate.repo_root()))
        _, identity = module.read_template(module.gate.repo_root())
        self.assertEqual(identity["sha256"], module.EXPECTED_TEMPLATE_SHA256)

    def test_template_renders_every_placeholder_once(self):
        module = self.module
        template, _ = module.read_template(module.gate.repo_root())
        rendered = module.render_template(template, self.values())
        for name in module.PLACEHOLDERS:
            self.assertNotIn("{{" + name + "}}", rendered)
        clause = module.extract_exact_clause(rendered)
        self.assertEqual(clause.count(module.gate.LIVE_ACTIVE_SENTINEL), 1)
        self.assertIn("a" * 64, clause)
        self.assertIn("b" * 64, clause)

    def test_render_rejects_missing_duplicate_and_unsafe_values(self):
        module = self.module
        template, _ = module.read_template(module.gate.repo_root())
        values = self.values()
        values.pop("CONNECTED_RESULT_SIZE")
        with self.assertRaises(module.PacketError):
            module.render_template(template, values)
        duplicate = template.replace(
            "{{CONNECTED_RESULT_SIZE}}",
            "{{CONNECTED_RESULT_SIZE}}{{CONNECTED_RESULT_SIZE}}",
        )
        with self.assertRaises(module.PacketError):
            module.render_template(duplicate, self.values())
        unsafe = self.values()
        unsafe["CONNECTED_RESULT_SIZE"] = "{{BAD}}"
        with self.assertRaises(module.PacketError):
            module.render_template(template, unsafe)
        for name, value in (
            ("CONNECTED_PASS_CREATED_AT_UTC", "bad-time"),
            ("CONNECTED_PASS_RECORD_SIZE", "0"),
            ("CONNECTED_RESULT_SHA256", "z" * 64),
            ("CONNECTED_RESULT_PATH", "workspace/private/runs/../escape/result.json"),
            ("CONNECTED_RESULT_PATH", "workspace/private/runs/run/result.json`\nBAD"),
        ):
            with self.subTest(name=name, value=value):
                malformed = self.values()
                malformed[name] = value
                with self.assertRaises(module.PacketError):
                    module.render_template(template, malformed)

    def test_promotion_state_requires_connected_only_and_unconsumed(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(
                module.gate, "policy_active", side_effect=lambda _root, connected: connected
            ):
                state = module.ensure_promotion_state(
                    root, require_connected_pass=False
                )
            self.assertTrue(state["connected_policy_active"])
            self.assertFalse(state["live_policy_active"])
            with mock.patch.object(module.gate, "policy_active", return_value=True), self.assertRaises(
                module.PacketError
            ):
                module.ensure_promotion_state(root, require_connected_pass=False)
            consumed = root / module.gate.CONSUMED_STATE
            consumed.parent.mkdir(parents=True)
            consumed.write_text("{}", encoding="ascii")
            with mock.patch.object(
                module.gate, "policy_active", side_effect=lambda _root, connected: connected
            ), self.assertRaises(module.PacketError):
                module.ensure_promotion_state(root, require_connected_pass=False)

    def test_emit_refuses_without_connected_pass_before_allocating_run_dir(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(module, "source_pins", return_value={}), mock.patch.object(
                module, "read_template", return_value=("template", {"size": 1, "sha256": "a" * 64})
            ), mock.patch.object(
                module.gate, "policy_active", side_effect=lambda _root, connected: connected
            ), mock.patch.object(module.core, "allocate_run_dir") as allocate, self.assertRaises(
                module.PacketError
            ):
                module.emit_after_connected(root, None)
            allocate.assert_not_called()

    def test_emit_reopens_connected_evidence_and_writes_inert_review_packet(self):
        module = self.module
        pins = {
            "helper_sha256": module.EXPECTED_HELPER_SHA256,
            "test_sha256": module.EXPECTED_TEST_SHA256,
            "core_sha256": module.EXPECTED_CORE_SHA256,
            "core_test_sha256": module.EXPECTED_CORE_TEST_SHA256,
        }
        receipt = {
            "read_to_eof": True,
            "stderr_bytes": 0,
            "bytes": 64,
        }
        marker = {"baseline_absent": True, "integrity_issue": False}
        result = {
            "schema": module.gate.SCHEMA,
            "mode": "connected-read-only-dry-run",
            "target": module.gate.TARGET,
            "device_contact": True,
            "device_writes": False,
            "reboot": False,
            "download_transition": False,
            "odin_transfer": False,
            "flash": False,
            "verdict": "PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY",
            "baseline": {
                "target": module.gate.TARGET,
                "device_writes": False,
                "one_shot_consumed": False,
                "no_odin_endpoint": True,
                "sec_log_buf_live": True,
                "bind": module.gate.EXPECTED_BIND,
                "pstore_console_absent": {
                    path: True for path in module.gate.PSTORE_PATHS
                },
                "observers": {
                    "ap_klog": {
                        **receipt,
                        "marker": marker,
                        "read_count": 1,
                        "byte_identical": True,
                        "reads": [receipt],
                    },
                    "last_kmsg": {
                        **receipt,
                        "marker": marker,
                        "read_count": 2,
                        "byte_identical": True,
                        "reads": [receipt, receipt],
                    },
                },
            },
        }
        template_data = module.read_template(module.gate.repo_root())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / module.gate.RUN_ROOT / "connected"
            run_dir.mkdir(parents=True)
            result_path = run_dir / "result.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            result_identity = module.core.hash_stable_file(result_path)
            pass_path = root / module.gate.CONNECTED_PASS_STATE
            pass_path.parent.mkdir(parents=True)
            record = {
                "schema": "s22plus_fyg8_r4w1b_connected_pass_v1",
                "target": module.gate.TARGET,
                "created_at_utc": "2026-07-18T21:30:00.000000Z",
                **pins,
                "result_path": str(result_path.relative_to(root)),
                "result_sha256": result_identity["sha256"],
                "verdict": "PASS_R4W1B_CONNECTED_BASELINE_READ_ONLY",
                "device_writes": False,
            }
            pass_path.write_text(json.dumps(record), encoding="utf-8")
            requested = module.gate.RUN_ROOT / "binding"
            with mock.patch.object(module, "source_pins", return_value=pins), mock.patch.object(
                module, "read_template", return_value=template_data
            ), mock.patch.object(
                module.gate, "policy_active", side_effect=lambda _root, connected: connected
            ), mock.patch.object(
                module.gate, "validate_connected_result_contract"
            ) as contract, mock.patch.object(
                module.gate, "validate_connected_pass", return_value=record
            ):
                packet = module.emit_after_connected(root, requested)
            self.assertEqual(
                packet["verdict"],
                "PASS_R4W1B_LIVE_BINDING_REVIEW_PACKET_EMITTED_HOST_ONLY",
            )
            self.assertFalse(packet["device_contact"])
            self.assertEqual(packet["exact_agents_clause"]["live_active_sentinel_count"], 1)
            self.assertTrue((root / requested / "packet.json").is_file())
            self.assertFalse((root / module.gate.CONSUMED_STATE).exists())
            self.assertEqual(contract.call_count, 2)

    def test_source_has_no_device_or_transfer_calls(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "adb devices",
            "odin_devices(",
            "flash_exact(",
            "connected_preflight(",
            "subprocess.run(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
