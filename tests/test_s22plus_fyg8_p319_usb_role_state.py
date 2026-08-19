import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_usb_role_state_d0.py"
)


def load():
    spec = importlib.util.spec_from_file_location("p319_usb_role_state", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["p319_usb_role_state"] = module
    spec.loader.exec_module(module)
    return module


def block(key, value, rc="0", present="yes"):
    if present != "yes":
        return f"attr\tbegin\t{key}\npresent\tno\nattr\tend\t{key}"
    return (
        f"attr\tbegin\t{key}\npresent\tyes\nbody\tbegin\n{value}\n"
        f"body\tend\nbody_rc\t{rc}\nattr\tend\t{key}"
    )


def transcript(blocks, udc=("a600000.dwc3",)):
    head = "role_state\tbegin\nudc_class\tbegin\n" + "\n".join(udc) + "\nudc_class\tend"
    return "\n".join([head, *blocks, "role_state\tend"])


class SafetyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_contract_passes_on_the_shipped_script(self):
        contract = self.m.role_state_safety_contract()
        self.assertEqual(contract["result"], "pass")
        self.assertTrue(contract["script_equals_rendered_table"])
        self.assertEqual(contract["cat_target_count"], len(self.m.READ_TARGETS))

    def test_contract_rejects_a_script_that_reads_one_extra_path(self):
        # The failure this is guarding is a widened read that still looks
        # harmless line by line.
        extra = self.m.ROLE_STATE_SCRIPT + "cat /sys/class/mxim/debug0/reg\n"
        contract = self.m.role_state_safety_contract(extra)
        self.assertEqual(contract["result"], "fail")
        self.assertFalse(contract["script_equals_rendered_table"])
        self.assertIn("mxim", contract["forbidden_token_hits"])

    def test_contract_rejects_a_redirect(self):
        written = self.m.ROLE_STATE_SCRIPT.replace(
            "cat /sys/class/udc/a600000.dwc3/state",
            "cat /sys/class/udc/a600000.dwc3/state > /data/local/tmp/x",
        )
        contract = self.m.role_state_safety_contract(written)
        self.assertEqual(contract["result"], "fail")
        self.assertGreater(contract["redirect_count"], 0)

    def test_contract_rejects_the_pull_up_primitive(self):
        for token in ("soft_connect", "srp", "echo", "tee"):
            with self.subTest(token=token):
                contract = self.m.role_state_safety_contract(
                    self.m.ROLE_STATE_SCRIPT + f"{token} 1\n"
                )
                self.assertEqual(contract["result"], "fail")
                self.assertIn(token, contract["forbidden_token_hits"])

    def test_contract_rejects_a_reordered_table(self):
        # Equality with the rendering is the load-bearing property, so a script
        # that reads the same paths in another order is still refused.
        reordered = self.m.render_script(tuple(reversed(self.m.READ_TARGETS)))
        contract = self.m.role_state_safety_contract(reordered)
        self.assertEqual(contract["result"], "fail")

    def test_default_script_resolves_at_call_time(self):
        # A default argument bound at definition time would let the contract
        # clear one script while a different one was sent to the device.
        original = self.m.ROLE_STATE_SCRIPT
        self.m.ROLE_STATE_SCRIPT = original + "cat /dev/mxim_dev\n"
        try:
            self.assertEqual(self.m.role_state_safety_contract()["result"], "fail")
        finally:
            self.m.ROLE_STATE_SCRIPT = original
        self.assertEqual(self.m.role_state_safety_contract()["result"], "pass")

    def test_declared_paths_carry_no_write_primitive(self):
        for _key, path, _why in self.m.READ_TARGETS:
            with self.subTest(path=path):
                self.assertNotIn("soft_connect", path)
                self.assertNotIn("srp", path)


class ParseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_parses_values_and_statuses(self):
        text = transcript([block("role_mode", "peripheral"),
                           block("udc_state", "configured", rc="0")])
        observation = self.m.parse_role_state(text)
        self.assertTrue(observation["reached_end"])
        self.assertTrue(observation["controller_present"])
        self.assertEqual(observation["values"]["role_mode"], "peripheral")
        self.assertEqual(observation["values"]["udc_state"], "configured")
        self.assertEqual(observation["body_rc"]["udc_state"], "0")

    def test_a_value_shaped_like_a_marker_does_not_end_its_own_section(self):
        # The first version emitted body_rc inside the body block, which made
        # an attribute value and a status line ambiguous.
        text = transcript([block("role_mode", "body_rc\t9"),
                           block("udc_state", "configured")])
        observation = self.m.parse_role_state(text)
        self.assertEqual(observation["values"]["role_mode"], "body_rc\t9")
        self.assertEqual(observation["body_rc"]["role_mode"], "0")
        self.assertEqual(observation["values"]["udc_state"], "configured")

    def test_absent_target_is_reported_not_guessed(self):
        text = transcript([block("configfs_udc", "", present="no")])
        observation = self.m.parse_role_state(text)
        self.assertIn("configfs_udc", observation["absent_targets"])
        self.assertNotIn("configfs_udc", observation["values"])

    def test_failed_read_is_reported(self):
        text = transcript([block("udc_state", "", rc="1")])
        observation = self.m.parse_role_state(text)
        self.assertEqual(observation["failed_reads"], ["udc_state"])

    def test_missing_controller_is_visible(self):
        text = transcript([block("role_mode", "none")], udc=("dummy_udc.0",))
        observation = self.m.parse_role_state(text)
        self.assertFalse(observation["controller_present"])
        self.assertEqual(observation["udc_class_entries"], ["dummy_udc.0"])

    def test_truncated_transcript_does_not_reach_end(self):
        text = "role_state\tbegin\nudc_class\tbegin\na600000.dwc3\nudc_class\tend"
        self.assertFalse(self.m.parse_role_state(text)["reached_end"])


class ClassifyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def frontier(self, blocks):
        return self.m.classify(self.m.parse_role_state(transcript(blocks)))

    def test_role_none_stops_before_everything_else(self):
        result = self.frontier([block("role_mode", "none"),
                                block("udc_state", "not attached"),
                                block("configfs_udc", "")])
        self.assertEqual(result["stage"], "role_not_peripheral")

    def test_peripheral_without_a_bound_gadget(self):
        result = self.frontier([block("role_mode", "peripheral"),
                                block("udc_state", "not attached"),
                                block("configfs_udc", "")])
        self.assertEqual(result["stage"], "role_only")

    def test_bound_but_no_host_driving_the_bus(self):
        result = self.frontier([block("role_mode", "peripheral"),
                                block("udc_state", "not attached"),
                                block("configfs_udc", "a600000.dwc3")])
        self.assertEqual(result["stage"], "bound_not_attached")

    def test_enumeration_stopped_partway(self):
        result = self.frontier([block("role_mode", "peripheral"),
                                block("udc_state", "powered"),
                                block("configfs_udc", "a600000.dwc3")])
        self.assertEqual(result["stage"], "attached_not_configured")

    def test_configured_is_the_only_success(self):
        result = self.frontier([block("role_mode", "peripheral"),
                                block("udc_state", "configured"),
                                block("udc_function", "configfs-gadget"),
                                block("configfs_udc", "a600000.dwc3")])
        self.assertEqual(result["stage"], "configured")
        self.assertTrue(result["state_is_known"])

    def test_unreadable_mode_is_unknown_rather_than_a_stage(self):
        result = self.frontier([block("udc_state", "configured")])
        self.assertEqual(result["stage"], "unknown")

    def test_unrecognised_state_string_is_flagged(self):
        result = self.frontier([block("role_mode", "peripheral"),
                                block("udc_state", "brand new state"),
                                block("configfs_udc", "a600000.dwc3")])
        self.assertEqual(result["stage"], "attached_not_configured")
        self.assertFalse(result["state_is_known"])


class ValidateModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_validate_reports_no_device_contact_and_emits_the_script(self):
        import contextlib
        import io

        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = self.m.main(["--validate"])
        self.assertEqual(code, 0)
        value = json.loads(stream.getvalue())
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])
        self.assertEqual(value["safety"]["result"], "pass")
        self.assertEqual(value["script"], self.m.ROLE_STATE_SCRIPT)
        self.assertEqual(len(value["read_targets"]), len(self.m.READ_TARGETS))

    def test_collect_refuses_before_contact_when_the_contract_fails(self):
        # A run directory is created inside collect(), so a contract failure
        # must leave no directory behind at all.
        import tempfile

        original = self.m.ROLE_STATE_SCRIPT
        self.m.ROLE_STATE_SCRIPT = original + "cat /dev/mxim_dev\n"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "AGENTS.md").write_text("stub", encoding="utf-8")
                with self.assertRaises(self.m.RoleStateError):
                    self.m.collect(root)
                self.assertFalse((root / self.m.DEFAULT_RUN_ROOT).exists())
        finally:
            self.m.ROLE_STATE_SCRIPT = original


if __name__ == "__main__":
    unittest.main()
