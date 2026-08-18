import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
RUNNER = REVALIDATION / "s22plus_fyg8_p319_usbc_log_harvest_d0.py"
AUDIT = REVALIDATION / "s22plus_fyg8_raw_first_observer_audit.py"


def load(path: Path, name: str):
    if str(REVALIDATION) not in sys.path:
        sys.path.insert(0, str(REVALIDATION))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class P319LogHarvestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load(RUNNER, "p319_log_harvest_runner")

    # --- the reader must not clear what it reads -------------------------

    def test_contract_passes_and_no_dmesg_carries_a_flag(self):
        contract = self.runner.harvest_safety_contract()
        self.assertEqual(contract["result"], "pass")
        self.assertTrue(contract["read_only_and_non_clearing"])
        self.assertEqual(contract["ring_clearing_hits"], [])
        self.assertEqual(contract["flagged_dmesg_count"], 0)
        self.assertEqual(contract["forbidden_token_hits"], [])
        self.assertEqual(contract["redirect_count"], 0)
        self.assertEqual(contract["dmesg_invocations"], 5)

    def test_contract_rejects_every_ring_clearing_and_write_shape(self):
        base = self.runner.HARVEST_SCRIPT
        mutations = {
            "dmesg -c": base.replace("dmesg | wc -l", "dmesg -c | wc -l"),
            # A bare token list would miss this one; the regex must not.
            "dmesg  -C two spaces": base.replace(
                "dmesg | wc -l", "dmesg  -C | wc -l"
            ),
            "--read-clear": base.replace(
                "dmesg | wc -l", "dmesg --read-clear | wc -l"
            ),
            "--clear": base.replace("dmesg | wc -l", "dmesg --clear | wc -l"),
            "sysfs write": base + "echo hi > /sys/class/typec/port0/data_role\n",
            "opcode read": base + "cat /sys/class/mxim/debug0/opcode\n",
            "fw_update": base + "cat /sys/.../fw_update\n",
            "module action": base + "insmod /data/x.ko\n",
        }
        for label, script in mutations.items():
            with self.subTest(mutation=label):
                contract = self.runner.harvest_safety_contract(script)
                self.assertEqual(contract["result"], "fail")

    def test_typec_attributes_are_pinned_not_globbed(self):
        # "exactly what we read" is what makes a body read reviewable.
        script = self.runner.HARVEST_SCRIPT
        self.assertNotIn("/sys/class/typec/port0/*", script)
        for name in self.runner.TYPEC_ATTRIBUTES:
            with self.subTest(name=name):
                self.assertIn(f"/sys/class/typec/port0/{name}", script)

    # --- redaction --------------------------------------------------------

    def test_redaction_removes_identifiers_and_counts_them(self):
        text = (
            "wlan0 mac aa:bb:cc:dd:ee:ff addr 192.168.0.11\n"
            "uuid 12345678-1234-1234-1234-123456789abc\n"
            "ptr ffffff8012345678 imei 123456789012345\n"
            "max77705_switch_path value(0x01)\n"
        )
        redacted, counts = self.runner.redact(text)
        for leak in (
            "aa:bb:cc:dd:ee:ff",
            "192.168.0.11",
            "12345678-1234-1234-1234-123456789abc",
            "ffffff8012345678",
            "123456789012345",
        ):
            with self.subTest(leak=leak):
                self.assertNotIn(leak, redacted)
        self.assertEqual(
            counts,
            {"mac": 1, "ipv4": 1, "uuid": 1, "kernel_pointer": 1, "long_digits": 1},
        )
        # Redaction must not eat the evidence it exists to protect.
        self.assertIn("max77705_switch_path value(0x01)", redacted)

    def test_redaction_reports_nothing_when_there_is_nothing_to_redact(self):
        redacted, counts = self.runner.redact("com_to_usb_ap\n")
        self.assertEqual(counts, {})
        self.assertEqual(redacted, "com_to_usb_ap\n")

    # --- parsing ----------------------------------------------------------

    def harvest(self, driver_lines, **scalars):
        rows = ["harvest\tbegin"]
        base = {"kmsg_lines": "900", "kmsg_bytes": "120000",
                "kmsg_first": "[    1.000000] boot",
                "kmsg_last": "[ 3601.000000] now",
                "usblog_present": "yes", "typec_port_present": "yes"}
        base.update(scalars)
        rows += [f"{key}\t{value}" for key, value in base.items()]
        rows += ["driver_log\tbegin", *driver_lines, "driver_log\tend"]
        rows += ["driver_log_rc\t0" if driver_lines else "driver_log_rc\t1"]
        rows += ["usblog\tbegin", "usblog\tend"]
        rows += ["typec\tbegin", "data_role\t[device] host", "typec\tend"]
        rows += ["harvest\tend"]
        return "\n".join(rows) + "\n"

    def test_parser_extracts_the_mux_commands(self):
        lines = [
            "[  12.3] max77705_switch_path value(0x1)",
            "[  12.3] com_to_usb_ap",
            "[  12.4] max77705: opcode_write: 00000000: 06 01",
            "[  12.4] opcode 0x6, write_length 2",
            "[  99.0] max77705_switch_path value(0x0)",
            "[  99.0] com_to_open",
        ]
        observation = self.runner.parse_harvest(self.harvest(lines))
        self.assertTrue(observation["reached_end"])
        self.assertEqual(observation["switch_path_count"], 2)
        self.assertEqual(observation["switch_path_values"], ["0x1", "0x0"])
        self.assertEqual(
            observation["com_to_calls"], ["com_to_open", "com_to_usb_ap"]
        )
        self.assertEqual(observation["opcode_write_dumps"], 1)
        self.assertEqual(observation["opcode_messages"], 1)
        self.assertTrue(observation["driver_log_matched"])
        self.assertEqual(observation["typec"]["data_role"], "[device] host")

    def test_an_empty_grep_is_a_result_and_not_an_error(self):
        # This is the outcome that would refute the campaign hypothesis, so it
        # must parse cleanly rather than look like a broken run.
        observation = self.runner.parse_harvest(self.harvest([]))
        self.assertTrue(observation["reached_end"])
        self.assertEqual(observation["driver_log_rc"], "1")
        self.assertFalse(observation["driver_log_matched"])
        self.assertEqual(observation["switch_path_count"], 0)
        self.assertEqual(observation["com_to_calls"], [])

    def test_missing_end_sentinel_is_not_complete(self):
        text = self.harvest(["x"]).replace("harvest\tend\n", "")
        self.assertFalse(self.runner.parse_harvest(text)["reached_end"])

    # --- boundary ---------------------------------------------------------

    def test_runner_is_declared_to_the_raw_first_boundary(self):
        audit = load(AUDIT, "p319_log_harvest_audit_doc")
        self.assertIsNotNone(audit.OBSERVER_FILE_RE.fullmatch(RUNNER.name))


    def test_ring_span_is_measured_so_a_negative_can_be_interpreted(self):
        observation = self.runner.parse_harvest(self.harvest(["x"]))
        self.assertEqual(observation["ring_span_seconds"], 3600.0)
        self.assertEqual(observation["kmsg_first"], "[    1.000000] boot")

    def test_absent_switch_path_is_inconclusive_without_an_attach(self):
        # The defect this catches: a ring too short to reach the attach makes
        # switch_path_count 0 look like proof the driver never commanded it.
        quiet = self.runner.parse_harvest(
            self.harvest(["[ 100.0] max77705_fg_read_avg_current: avg_current=0mA"])
        )
        self.assertEqual(quiet["switch_path_count"], 0)
        self.assertEqual(quiet["attach_markers_in_window"], 0)
        self.assertFalse(quiet["mux_evidence_conclusive"])

        attached = self.runner.parse_harvest(
            self.harvest(["[ 100.0] max77705_ccstat_irq: attached"])
        )
        self.assertEqual(attached["switch_path_count"], 0)
        self.assertGreater(attached["attach_markers_in_window"], 0)
        self.assertTrue(attached["mux_evidence_conclusive"])

        commanded = self.runner.parse_harvest(
            self.harvest(["[ 100.0] max77705_switch_path value(0x1)"])
        )
        self.assertTrue(commanded["mux_evidence_conclusive"])


if __name__ == "__main__":
    unittest.main()
