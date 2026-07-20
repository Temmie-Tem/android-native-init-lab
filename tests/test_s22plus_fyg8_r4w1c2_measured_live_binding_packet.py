import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c2_measured_live_binding_packet.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("r4w1c2_measured_live_binding_packet_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1C2MeasuredLiveBindingPacketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def copy_source_root(self, temporary: str) -> Path:
        module = self.module
        root = Path(temporary)
        for relative in (
            module.live.SCRIPT_RELATIVE,
            module.live.TEST_RELATIVE,
            module.live.POLICY_DRAFT,
            module.connected.SCRIPT_RELATIVE,
            module.connected.TEST_RELATIVE,
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((Path.cwd() / relative).read_bytes())
        (root / module.live.CONSUMED_STATE.parent).mkdir(parents=True, exist_ok=True)
        (root / module.OUTPUT_ROOT).mkdir(parents=True, exist_ok=True)
        return root

    def binding(self, module):
        return {
            "pass_path": str(module.connected.PASS_STATE),
            "created_at_utc": "2026-07-20T00:00:00.000000Z",
            "pass_size": 123,
            "pass_sha256": "a" * 64,
            "result_path": "workspace/private/runs/connected/result.json",
            "result_size": 456,
            "result_sha256": "b" * 64,
        }

    def test_parser_exposes_only_host_modes(self):
        options = {action.dest for action in self.module.build_parser()._actions}
        self.assertIn("source_check", options)
        self.assertIn("emit_binding", options)
        self.assertNotIn("live", options)
        self.assertNotIn("rollback_from_download", options)

    def test_pinned_live_source_matches_current_files(self):
        module = self.module
        self.assertEqual(
            module.core.hash_stable_file(Path.cwd() / module.live.SCRIPT_RELATIVE),
            {
                "size": module.EXPECTED_LIVE_HELPER_SIZE,
                "sha256": module.EXPECTED_LIVE_HELPER_SHA256,
            },
        )
        self.assertEqual(
            module.core.hash_stable_file(Path.cwd() / module.live.TEST_RELATIVE),
            {
                "size": module.EXPECTED_LIVE_TEST_SIZE,
                "sha256": module.EXPECTED_LIVE_TEST_SHA256,
            },
        )

    def test_source_gate_requires_connected_active_and_live_inactive(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_source_root(temporary)
            with mock.patch.object(module.connected, "policy_active", return_value=True), mock.patch.object(
                module.live, "policy_active", return_value=False
            ):
                identities = module.source_gate(root)
            self.assertEqual(identities["live_helper"]["sha256"], module.EXPECTED_LIVE_HELPER_SHA256)
            with mock.patch.object(module.connected, "policy_active", return_value=True), mock.patch.object(
                module.live, "policy_active", return_value=True
            ):
                with self.assertRaises(module.GateError):
                    module.source_gate(root)

    def test_connected_binding_reopens_pass_and_result_identities(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pass_path = root / module.connected.PASS_STATE
            result_path = root / "workspace/private/runs/connected/result.json"
            pass_path.parent.mkdir(parents=True)
            result_path.parent.mkdir(parents=True)
            pass_path.write_text("pass")
            result_path.write_text('{"artifacts":{}}')
            record = {
                "created_at_utc": "2026-07-20T00:00:00.000000Z",
                "result_path": str(result_path.relative_to(root)),
                "helper_sha256": module.live.CONNECTED_HELPER_SHA256,
                "test_sha256": module.live.CONNECTED_TEST_SHA256,
                "policy_clause_sha256": module.live.CONNECTED_CLAUSE_SHA256,
            }
            with mock.patch.object(
                module.connected, "validate_connected_pass", return_value=record
            ):
                binding = module.connected_binding(root, {})
            self.assertEqual(binding["pass_size"], 4)
            self.assertEqual(binding["result_size"], len('{"artifacts":{}}'))

    def test_emit_packet_creates_exact_clause_without_editing_agents(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_source_root(temporary)
            output = root / module.OUTPUT_ROOT / "packet"
            output.mkdir()
            agents = root / "AGENTS.md"
            agents.write_text("unchanged\n")
            before = agents.read_bytes()
            result = module.emit_packet(
                root,
                output,
                identities={"ok": True},
                artifacts={"target": module.live.TARGET},
                binding=self.binding(module),
            )
            self.assertEqual(agents.read_bytes(), before)
            self.assertFalse(result["device_contact"])
            self.assertFalse(result["policy_edited"])
            clause = (
                output / "AGENTS_R4W1C2_MEASURED_LIVE_CLAUSE.md"
            ).read_text().strip()
            self.assertEqual(module.live.parse_connected_binding(clause), self.binding(module))

    def test_allocate_output_rejects_escape_and_existing_path(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = self.copy_source_root(temporary)
            with self.assertRaises(module.GateError):
                module.allocate_output(root, Path("../escape"))
            existing = root / module.OUTPUT_ROOT / "existing"
            existing.mkdir()
            with self.assertRaises(module.GateError):
                module.allocate_output(root, existing)

    def test_main_source_check_has_zero_device_actions(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(module, "repo_root", return_value=root), mock.patch.object(
                module, "source_gate", return_value={"source": True}
            ), mock.patch.object(
                module.live, "verify_artifacts", return_value={"target": module.live.TARGET}
            ), mock.patch.object(
                module, "connected_binding", return_value=self.binding(module)
            ):
                rc = module.main(["--source-check"])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
