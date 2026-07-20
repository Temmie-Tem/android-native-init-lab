import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c3_regular_ap_live_gate.py"
)
MODULE_DIR = SCRIPT.parent


def load_module():
    sys.path.insert(0, str(MODULE_DIR.resolve()))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_r4w1c3_regular_ap_live_gate", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class S22PlusFyg8R4W1C3RegularApLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_policy_is_inactive(self):
        self.assertFalse(self.module.policy_active(self.module.repo_root()))

    def test_policy_draft_pins_current_sources_and_stays_inactive(self):
        policy = self.module.verify_policy_draft(self.module.repo_root())
        self.assertFalse(policy["active"])

    def test_policy_requires_one_co_located_active_clause(self):
        module = self.module
        required = (
            module.POLICY_BEGIN,
            module.POLICY_END,
            module.POLICY_MARKER,
            module.ACTIVE_SENTINEL,
            "PIN",
        )
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            module, "required_policy_values", return_value=required
        ):
            root = Path(temporary)
            clause = "\n".join(
                (
                    module.POLICY_BEGIN,
                    module.POLICY_MARKER,
                    module.ACTIVE_SENTINEL,
                    "PIN",
                    module.POLICY_END,
                )
            )
            (root / "AGENTS.md").write_text(clause, encoding="utf-8")
            self.assertTrue(module.policy_active(root))
            scattered = clause.replace("PIN", "") + "\nPIN\n"
            (root / "AGENTS.md").write_text(scattered, encoding="utf-8")
            self.assertFalse(module.policy_active(root))

    def test_live_stops_before_device_contact_when_policy_inactive(self):
        module = self.module
        args = module.build_parser().parse_args(
            ["--live", "--ack", module.LIVE_ACK_TOKEN]
        )
        with mock.patch.object(module, "verify_artifacts", return_value={}), mock.patch.object(
            module, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(module.connected, "current_android_exact") as android:
            self.assertEqual(module.main(["--live", "--ack", module.LIVE_ACK_TOKEN]), 2)
        android.assert_not_called()

    def test_verdict_requires_candidate_transfer_marker_and_magisk(self):
        module = self.module
        self.assertEqual(
            module.classify_verdict(0, "magisk", {"acceptance_present": True}),
            (module.PASS_VERDICT, 0),
        )
        self.assertEqual(
            module.classify_verdict(1, "magisk", {"acceptance_present": True})[1],
            31,
        )
        self.assertEqual(module.classify_verdict(0, "magisk", None)[1], 32)
        self.assertEqual(module.classify_verdict(0, "stock", None)[1], 30)

    def test_render_plan_is_host_only_and_regular_path(self):
        module = self.module
        artifacts = {"regular_path_inputs": {}}
        policy = {"active": False}
        with mock.patch.object(module, "verify_artifacts", return_value=artifacts), mock.patch.object(
            module, "verify_policy_draft", return_value=policy
        ), mock.patch("builtins.print") as output:
            self.assertEqual(module.main(["--render-live-plan"]), 0)
        rendered = json.loads(output.call_args.args[0])
        self.assertFalse(rendered["device_contact"])
        self.assertFalse(rendered["odin_transfer"])
        self.assertFalse(rendered["anonymous_proc_fd_inputs"])
        self.assertTrue(rendered["transfer_command_shape"][3].endswith(".tar.md5"))

    def test_source_does_not_call_sealed_transport(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("flash_sealed_exact", source)
        self.assertNotIn("sealed_memfd", source)
        self.assertIn("f1.execute_odin_boot_only", source)


if __name__ == "__main__":
    unittest.main()
