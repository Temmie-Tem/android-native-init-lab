import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3431_pid1_keystone_design.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3431_pid1_keystone_design", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3431Pid1KeystoneDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.design = cls.module.build_design(cls.module.repo_root())

    def setUp(self):
        self.expectation = self.module.make_expectation(
            "0123456789abcdef0123456789abcdef",
            "1" * 64,
        )
        self.marker = self.module.encode_marker(self.expectation)

    def classify(self, stage, blob):
        return self.module.classify_snapshot(stage, blob, self.expectation)

    def test_static_design_inputs_pass(self):
        self.assertEqual(
            self.design["verdict"], "HOST_DESIGN_PASS_NO_LIVE"
        )
        proofs = self.design["static_evidence"]["source_proofs"]
        self.assertEqual(
            proofs["kernel_executes_initramfs_init_as_pid1"], "VERIFIED"
        )
        self.assertEqual(
            proofs["finit_module_success_is_after_module_init_live"], "VERIFIED"
        )
        self.assertEqual(
            proofs["sec_log_buf_required_observer_builders_are_synchronous"],
            "VERIFIED",
        )

    def test_kernel_config_closes_sec_debug_builtin_assumption(self):
        config = self.design["static_evidence"]["kernel_config"]
        self.assertEqual(config["gki_modules"], "y")
        self.assertEqual(config["gki_pstore"], "y")
        self.assertEqual(config["gki_pstore_ram"], "y")
        self.assertEqual(config["gki_magic_sysrq"], "y")
        self.assertEqual(config["waipio_gki_sec_debug"], "m")
        self.assertEqual(config["waipio_sec_debug"], "m")

    def test_contract_pin_and_committed_json_are_current(self):
        self.assertEqual(
            self.module.CONTRACT_SHA256,
            self.module.PINNED_CONTRACT_SHA256,
        )
        committed = Path(
            "docs/plans/s22plus-v3431-pid1-keystone-contract.json"
        ).read_text(encoding="utf-8")
        expected = json.dumps(self.design, indent=2, sort_keys=True) + "\n"
        self.assertEqual(committed, expected)

    def test_marker_roundtrip(self):
        scan = self.module.scan_markers(b"prefix" + self.marker + b"suffix")
        self.assertEqual(len(scan.markers), 1)
        marker = scan.markers[0]
        self.assertEqual(marker.run_id, self.expectation.run_id)
        self.assertEqual(marker.phase, self.module.PHASE)
        self.assertEqual(marker.sequence, 1)
        self.assertEqual(marker.pid, 1)
        self.assertFalse(scan.issues)

    def test_baseline_requires_current_run_absence(self):
        self.assertTrue(self.classify("baseline", b"historical text")["pass"])
        result = self.classify("baseline", self.marker)
        self.assertFalse(result["pass"])
        self.assertEqual(result["classification"], "FAIL_STOP")
        self.assertIn(
            "current-run-marker-present-before-candidate", result["errors"]
        )

    def test_foreign_marker_is_permitted_but_cannot_satisfy_run(self):
        foreign = self.module.make_expectation("f" * 32, "2" * 64)
        frame = self.module.encode_marker(foreign)
        baseline = self.classify("baseline", frame)
        self.assertTrue(baseline["pass"])
        retained = self.classify("retention", frame)
        self.assertEqual(
            retained["classification"],
            "NO_PROOF_PID1_VS_OBSERVER_UNRESOLVED_STOP",
        )
        self.assertEqual(retained["foreign_run_marker_count"], 1)

    def test_exact_retained_marker_is_positive(self):
        result = self.classify("retention", self.marker)
        self.assertTrue(result["pass"])
        self.assertEqual(
            result["classification"],
            "PASS_PID1_EXECUTION_AND_OBSERVER_LOAD",
        )

    def test_absence_is_no_proof_not_fail(self):
        result = self.classify("retention", b"unrelated retained kernel log")
        self.assertFalse(result["pass"])
        self.assertFalse(result["errors"])
        self.assertEqual(
            result["classification"],
            "NO_PROOF_PID1_VS_OBSERVER_UNRESOLVED_STOP",
        )

    def test_duplicate_current_marker_is_fail(self):
        result = self.classify("retention", self.marker + self.marker)
        self.assertEqual(result["classification"], "FAIL_STOP")
        self.assertIn("pid1-enter-count:2", result["errors"])

    def test_wrong_pid_is_fail(self):
        result = self.classify(
            "retention", self.module.encode_marker(self.expectation, pid=2)
        )
        self.assertEqual(result["classification"], "FAIL_STOP")
        self.assertIn("pid-is-not-one", result["errors"])

    def test_wrong_sequence_is_fail(self):
        result = self.classify(
            "retention", self.module.encode_marker(self.expectation, sequence=2)
        )
        self.assertEqual(result["classification"], "FAIL_STOP")
        self.assertIn("sequence-mismatch", result["errors"])

    def test_wrong_module_is_fail(self):
        other = self.module.make_expectation(
            self.expectation.run_id,
            self.expectation.context_sha256,
            module_sha256="a" * 64,
        )
        result = self.classify("retention", self.module.encode_marker(other))
        self.assertIn("module-identity-mismatch", result["errors"])

    def test_wrong_contract_is_fail(self):
        other = self.module.make_expectation(
            self.expectation.run_id,
            self.expectation.context_sha256,
            contract_sha256="b" * 64,
        )
        result = self.classify("retention", self.module.encode_marker(other))
        self.assertIn("contract-identity-mismatch", result["errors"])

    def test_wrong_context_is_fail(self):
        other = self.module.make_expectation(
            self.expectation.run_id,
            "c" * 64,
        )
        result = self.classify("retention", self.module.encode_marker(other))
        self.assertIn("context-identity-mismatch", result["errors"])

    def test_crc_corruption_is_fail(self):
        corrupt = bytearray(self.marker)
        offset = corrupt.find(b"phase=PID1_ENTER")
        corrupt[offset] = ord("x")
        result = self.classify("retention", bytes(corrupt))
        self.assertEqual(result["classification"], "FAIL_STOP")
        self.assertTrue(
            any(error.startswith("current-run-malformed:") for error in result["errors"])
        )

    def test_truncated_frame_is_fail(self):
        result = self.classify("retention", self.marker[:-6])
        self.assertEqual(result["classification"], "FAIL_STOP")
        self.assertIn("current-run-malformed:truncated-frame", result["errors"])

    def test_truncated_without_start_uses_raw_token_backstop(self):
        truncated = self.marker[len(self.module.FRAME_START) + 5 :]
        result = self.classify("retention", truncated)
        self.assertEqual(result["classification"], "FAIL_STOP")
        self.assertIn("current-run-unframed-or-malformed", result["errors"])

    def test_report_pins_are_checked(self):
        pins = self.design["static_evidence"]["report_pins"]
        self.assertEqual(set(pins), set(self.module.REPORT_PINS))
        for pin in pins.values():
            self.assertRegex(pin["sha256"], r"^[0-9a-f]{64}$")

    def test_contract_is_conjunctive_and_not_module_free(self):
        contract = self.module.CONTRACT_CORE
        self.assertEqual(
            contract["claim_kind"],
            "conjunctive_pid1_execution_and_observer_load",
        )
        self.assertTrue(self.design["proof_boundary"]["not_pure_module_free"])
        self.assertEqual(
            contract["observer"]["embedded_path"],
            "/observer/sec_log_buf.ko",
        )

    def test_candidate_gate_order_keeps_pid_and_observer_before_marker(self):
        gates = self.module.CANDIDATE_GATE_ORDER
        self.assertLess(
            gates.index("raw_getpid_returned_one"),
            gates.index("finit_module_returned_zero"),
        )
        self.assertLess(
            gates.index("finit_module_returned_zero"),
            gates.index("pid1_enter_marker_full_write_returned"),
        )
        self.assertLess(
            gates.index("last_kmsg_and_ap_klog_nodes_present"),
            gates.index("pid1_enter_marker_full_write_returned"),
        )

    def test_ambiguous_channels_are_explicitly_rejected(self):
        rejected = self.module.FORBIDDEN_PROOF_CHANNELS
        self.assertIn("intentional_panic", rejected)
        self.assertIn("pmsg", rejected)
        self.assertIn("ramoops", rejected)
        self.assertIn("usb", rejected)
        self.assertIn("timed_reboot_or_download", rejected)
        self.assertIn("persistent_partition_marker", rejected)

    def test_live_and_build_remain_disabled(self):
        contract = self.module.CONTRACT_CORE
        self.assertFalse(contract["live_authorized"])
        self.assertFalse(contract["candidate_source_authorized"])
        self.assertFalse(contract["image_build_authorized"])
        self.assertFalse(contract["flash_authorized"])
        self.assertFalse(self.design["safety"]["device_contact"])

    def test_run_id_is_fresh_128_bit_hex(self):
        first = self.module.generate_run_id()
        second = self.module.generate_run_id()
        self.assertRegex(first, r"^[0-9a-f]{32}$")
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
