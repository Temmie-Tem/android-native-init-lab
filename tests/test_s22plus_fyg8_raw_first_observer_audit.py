import importlib.util
import hashlib
import os
from pathlib import Path
import sys
import unittest
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_raw_first_observer_audit.py"
)
REVALIDATION = SCRIPT.parent


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_raw_first_observer_audit_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusRawFirstObserverAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def source(self, name: str) -> str:
        return (REVALIDATION / name).read_text(encoding="utf-8")

    def test_current_tree_scans_full_directory_and_passes_d0_f1(self):
        value = self.module.audit_sources(REVALIDATION)
        self.assertEqual(value["verdict"], self.module.VERDICT)
        self.assertGreater(value["all_revalidation_python_files_scanned"], 1700)
        self.assertGreater(value["subprocess_modules_scanned"], 390)
        self.assertEqual(
            value["legacy_unmigrated_observer_sources"],
            self.module.LEGACY_UNMIGRATED_OBSERVER_COUNT,
        )
        self.assertEqual(
            value["legacy_unmigrated_observer_inventory_sha256"],
            self.module.LEGACY_UNMIGRATED_OBSERVER_SHA256,
        )
        self.assertTrue(
            value["legacy_unmigrated_observers_are_inactive_and_byte_frozen"]
        )
        # Derived, not restated: the auditor already fails closed when the
        # real population differs from its constant, so a second literal
        # here only drifts.  Registering the Stage A probe moved it to 122.
        self.assertEqual(
            value["closed_observer_source_count"],
            self.module.CLOSED_OBSERVER_SOURCE_COUNT,
        )
        self.assertEqual(
            value["closed_observer_source_inventory_sha256"],
            self.module.CLOSED_OBSERVER_SOURCE_SHA256,
        )
        self.assertTrue(value["closed_observer_sources_are_byte_frozen"])
        self.assertTrue(
            value["new_or_changed_observer_source_requires_review"]
        )
        self.assertTrue(value["d0_covered"])
        self.assertTrue(value["f1_covered"])
        self.assertFalse(value["device_observation_parser_accepts_live_stream"])
        self.assertTrue(
            value[
                "guard_readiness_marker_is_acquisition_control_not_result_classification"
            ]
        )
        self.assertTrue(
            value["guard_arm_marker_parsed_only_from_finalized_handle"]
        )
        self.assertTrue(value["p300_sidecar_nested_raw_receipts_reopened"])
        self.assertTrue(value["f1_final_observer_phase_capture_bound"])
        self.assertTrue(value["auditor_bound_source_execution"])
        self.assertTrue(value["permanent"])
        self.assertIsNone(value["expiry"])

    def test_d0_direct_stdout_and_nonhandle_parser_mutations_reject(self):
        raw_name = "device_action_raw_capture_v1.py"
        raw_source = self.source(raw_name).replace(
            "                os.fsync(descriptor)\n                metadata =",
            "                metadata =",
            1,
        )
        with self.assertRaises(self.module.RawFirstAuditError):
            self.module.audit_sources(REVALIDATION, {raw_name: raw_source})

        d0_name = "device_action_d0_v2.py"
        d0_source = self.source(d0_name).replace(
            "return raw_capture.acquire_command(",
            "return forbidden_direct_command(",
            1,
        )
        with self.assertRaises(self.module.RawFirstAuditError):
            self.module.audit_sources(REVALIDATION, {d0_name: d0_source})

        stage_name = "s22plus_fyg8_p319_max77705_attribute_stage_a.py"
        stage_source = self.source(stage_name).replace(
            "handle: raw_capture.RawCaptureHandle",
            "payload: bytes",
            1,
        )
        with self.assertRaises(self.module.RawFirstAuditError):
            self.module.audit_sources(REVALIDATION, {stage_name: stage_source})

    def test_f1_enumeration_and_cdc_preparse_mutations_reject(self):
        odin_name = "s22plus_odin_transition_core.py"
        odin_source = self.source(odin_name).replace(
            "effective_runner, raw_handles = _raw_first_runner(run_dir, sequence)",
            "effective_runner = runner",
            1,
        )
        with self.assertRaises(self.module.RawFirstAuditError):
            self.module.audit_sources(REVALIDATION, {odin_name: odin_source})

        cdc_name = "device_action_cdc_acm_observer_v1.py"
        cdc_source = self.source(cdc_name).replace(
            "writer.write_stdout(chunk)", "pass  # lost raw", 1
        )
        with self.assertRaises(self.module.RawFirstAuditError):
            self.module.audit_sources(REVALIDATION, {cdc_name: cdc_source})
        prefinalize_marker = self.source(cdc_name).replace(
            "                    writer.write_stdout(chunk)\n",
            "                    writer.write_stdout(chunk)\n"
            "                    if expected in chunk:\n"
            "                        break\n",
            1,
        )
        with self.assertRaises(self.module.RawFirstAuditError):
            self.module.audit_sources(
                REVALIDATION, {cdc_name: prefinalize_marker}
            )

        live_name = "device_action_f1_live_v2.py"
        stale_client = self.source(live_name).replace(
            "capture = final_client.capture(",
            "capture = self.client.capture(",
            1,
        )
        with self.assertRaises(self.module.RawFirstAuditError):
            self.module.audit_sources(REVALIDATION, {live_name: stale_client})

        binding_name = "s22plus_fyg8_p300_usb_trace_binding.py"
        bypassed_nested_receipt = self.source(binding_name).replace(
            "handle = raw_capture.load_handle(path)",
            "handle = foreign_unbound_handle(path)",
            1,
        )
        with self.assertRaises(self.module.RawFirstAuditError):
            self.module.audit_sources(
                REVALIDATION,
                {binding_name: bypassed_nested_receipt},
            )

    def test_new_s22_d0_subprocess_parser_without_helper_rejects(self):
        unsafe_sources = (
            """\
import subprocess
def collect():
    result = subprocess.run(['adb'], stdout=subprocess.PIPE)
    return result.stdout.decode()
""",
            """\
from subprocess import run
def collect():
    result = run(['adb', 'shell', 'id'], capture_output=True)
    return result.stdout.decode()
""",
            """\
import subprocess as sp
def collect():
    result = sp.run(['adb', 'shell', 'id'], capture_output=True)
    return result.stdout.decode()
""",
            """\
from os import popen as pp
def collect():
    return pp('adb shell id').read()
""",
            """\
from device_action_d0_v2 import bounded_command as bc
def collect():
    return bc(['adb', 'shell', 'id'], timeout=1).stdout
""",
            """\
def collect():
    sp = __import__('subprocess')
    return sp.run(['adb', 'shell', 'id'], capture_output=True).stdout
""",
        )
        for unsafe in unsafe_sources:
            with self.subTest(sha256=hashlib.sha256(unsafe.encode()).hexdigest()):
                with self.assertRaisesRegex(
                    self.module.RawFirstAuditError,
                    "bypasses common raw capture"
                    "|bypasses the raw-first boundary"
                    "|closed observer source inventory differs",
                ):
                    self.module.audit_sources(
                        REVALIDATION,
                        {"s22plus_fyg8_future_d0.py": unsafe},
                    )
                with self.assertRaisesRegex(
                    self.module.RawFirstAuditError,
                    "bypasses the raw-first boundary"
                    "|legacy observer inventory differs"
                    "|closed observer source inventory differs",
                ):
                    self.module.audit_sources(
                        REVALIDATION,
                        {"s22plus_fyg8_future_f1_observer.py": unsafe},
                    )
        with self.assertRaisesRegex(
            self.module.RawFirstAuditError,
            "closed observer source inventory differs",
        ):
            self.module.audit_sources(
                REVALIDATION,
                {
                    "s22plus_fyg8_future_observer.py": (
                        "def parse(handle):\n    return handle\n"
                    )
                },
            )
        for existing in (
            "device_action_f1_v2.py",
            "s22plus_m10a1_stat_dev_reboot_live_gate.py",
        ):
            for unsafe in unsafe_sources[-3:]:
                with self.subTest(existing=existing):
                    with self.assertRaisesRegex(
                        self.module.RawFirstAuditError,
                        "bypasses the raw-first boundary"
                        "|pre-boundary device source inventory differs"
                        "|closed observer source inventory differs"
                        "|legacy observer inventory differs",
                    ):
                        self.module.audit_sources(
                            REVALIDATION, {existing: unsafe}
                        )

    def test_inactive_legacy_observer_inventory_is_exactly_byte_frozen(self):
        name = "s22plus_reset_reason_readonly_probe.py"
        mutation = self.source(name) + "\n# changed legacy observer\n"
        with self.assertRaisesRegex(
            self.module.RawFirstAuditError, "legacy observer inventory differs"
        ):
            self.module.audit_sources(REVALIDATION, {name: mutation})

    def test_loaded_auditor_cannot_receipt_different_source_bytes(self):
        name = SCRIPT.name
        source = self.source(name)
        mutations = (
            source + "\n# post-import replacement\n",
            source.replace(
                self.module.AUDITOR_NORMALIZED_SHA256,
                "0" * 64,
                1,
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation_sha256=hashlib.sha256(mutation.encode()).hexdigest()):
                with self.assertRaises(self.module.RawFirstAuditError):
                    self.module.audit_sources(REVALIDATION, {name: mutation})

    def test_stale_bytecode_constants_are_refused_not_audited(self):
        """A .pyc can outlive its source when an edit keeps the file size.

        Swapping one pinned 64-hex digest for another leaves the file exactly as
        long, and when both edits land inside one mtime second the invalidation
        check does not trip.  The module then audits with one set of constants
        while compiling the bound source from another.
        """
        original = self.module.AUDITOR_NORMALIZED_SHA256
        self.module.AUDITOR_NORMALIZED_SHA256 = "0" * 64
        try:
            with self.assertRaisesRegex(
                self.module.RawFirstAuditError,
                "executing auditor constants differ from its source",
            ):
                self.module.audit_sources(REVALIDATION)
        finally:
            self.module.AUDITOR_NORMALIZED_SHA256 = original
        # And the unmutated module still audits.
        self.assertIn("verdict", self.module.audit_sources(REVALIDATION))

    def test_preimport_semantic_mutation_is_replaced_by_bound_source(self):
        source = self.source(SCRIPT.name)
        mutation = source.replace(
            'raise RawFirstAuditError(f"active raw-first source changed: {name}")',
            "continue  # malicious pre-import bypass",
            1,
        )
        self.assertNotEqual(source, mutation)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / SCRIPT.name
            path.write_text(mutation, encoding="utf-8")
            spec = importlib.util.spec_from_file_location(
                "raw_first_preimport_mutation", path
            )
            loaded = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            sys.modules[spec.name] = loaded
            spec.loader.exec_module(loaded)
            path.write_text(source, encoding="utf-8")
            value = loaded.audit_sources(REVALIDATION)
        self.assertEqual(value["verdict"], self.module.VERDICT)

    def test_private_receipt_is_deterministic_mode0400_and_no_clobber(self):
        value = self.module.audit_sources(REVALIDATION)
        payload = self.module.encode_receipt(value)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            self.module.write_receipt(path, payload)
            self.module.write_receipt(path, payload)
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            self.assertEqual(path.stat().st_nlink, 1)
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                hashlib.sha256(payload).hexdigest(),
            )
            alias = Path(temporary) / "receipt-alias.json"
            alias.hardlink_to(path)
            with self.assertRaises(self.module.RawFirstAuditError):
                self.module.write_receipt(path, payload)
            alias.unlink()
            path.chmod(0o600)
            with self.assertRaises(self.module.RawFirstAuditError):
                self.module.write_receipt(path, payload)

    # The P3.19 Stage A observer carried no `d0` in its name, so the filename
    # rules never covered the source whose loss motivated this boundary.  These
    # cases pin detection to behavior instead: a successor cannot escape by
    # being named outside a pattern.
    UNMIGRATED_DEVICE_OBSERVER = """\
import subprocess
def read_control1(adb, serial):
    result = subprocess.run(
        [adb, '-s', serial, 'shell', 'cat', '/sys/x/control1'],
        capture_output=True, text=True, timeout=30,
    )
    return int(result.stdout.strip(), 16)
"""

    def test_new_device_acquiring_source_rejects_under_any_filename(self):
        for name in (
            "s22plus_fyg8_p319_max77705_control1_stage_b.py",
            "max77705_stage_b_probe.py",
            "totally_unrelated_name.py",
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    self.module.RawFirstAuditError,
                    "device-acquiring source bypasses the raw-first boundary",
                ):
                    self.module.audit_sources(
                        REVALIDATION,
                        {name: self.UNMIGRATED_DEVICE_OBSERVER},
                    )

    def test_host_only_build_source_is_not_a_device_observer(self):
        value = self.module.audit_sources(
            REVALIDATION,
            {
                "build_something_new_v9999.py": (
                    "import subprocess\n"
                    "def build():\n"
                    "    result = subprocess.run(['gcc', 'x.c'], capture_output=True)\n"
                    "    return result.stdout\n"
                )
            },
        )
        self.assertEqual(value["verdict"], self.module.VERDICT)

    def test_s22_pre_boundary_device_source_is_byte_frozen(self):
        name = "s22plus_p0_recon_collect.py"
        self.assertIn(name, self.module.PRE_BOUNDARY_DEVICE_SOURCES)
        with self.assertRaisesRegex(
            self.module.RawFirstAuditError,
            "pre-boundary device source inventory differs",
        ):
            self.module.audit_sources(
                REVALIDATION,
                {name: self.source(name) + "\n# changed device source\n"},
            )

    def test_other_target_edit_does_not_break_the_s22_boundary(self):
        # Target isolation: A90 and S20+ own those bytes.  Membership still
        # blocks a new unmigrated source, but an ordinary edit must not fail
        # this S22+ contract and stall the parallel targets.
        for name in (
            "a90_repl_resident_session.py",
            "s20plus_g986n_d0_inventory.py",
            "s20plus_g986n_autonomous_research_coordinator_h0.py",
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.module.PRE_BOUNDARY_DEVICE_SOURCES)
                value = self.module.audit_sources(
                    REVALIDATION,
                    {name: self.source(name) + "\n# harmless edit\n"},
                )
                self.assertEqual(value["verdict"], self.module.VERDICT)

    def test_other_target_source_bytes_copied_under_new_name_are_rejected(self):
        source = self.source(
            "s20plus_g986n_autonomous_research_coordinator_h0.py"
        )
        for name in (
            "copied_coordinator.py",
            "s22plus_fyg8_copied_coordinator.py",
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    self.module.RawFirstAuditError,
                    "device-acquiring source bypasses the raw-first boundary",
                ):
                    self.module.audit_sources(REVALIDATION, {name: source})

    def test_registered_host_only_source_is_typed_and_byte_frozen(self):
        name = "s22plus_fyg8_p319_candidate_qualification.py"
        self.assertNotIn(name, self.module.PRE_BOUNDARY_DEVICE_SOURCES)
        spec = self.module.S22_HOST_ONLY_NON_ACQUIRING_SOURCE_SPECS[name]
        source = self.source(name)
        value = self.module._audit_host_only_non_acquiring_source(name, source)
        self.assertEqual(value["owner"], "s22plus-fyg8-p319")
        self.assertEqual(value["classification"], "host-only-non-acquiring")
        self.assertEqual(value["profile"], "H0-candidate-qualification")
        self.assertEqual(value["size"], 46610)
        self.assertEqual(value["sha256"], spec["sha256"])
        self.assertEqual(value["exec_lines"], [238, 252])
        self.assertEqual(value["getattr_line"], 152)

        mutations = (
            source + "\n# changed host-only source\n",
            source.replace(
                'exec(compile(source, str(STOCK_SOURCE), "exec"), module.__dict__)',
                "exec(SRC)",
                1,
            ),
            source.replace(
                "os.fsync(fd)", 'os.system("adb shell id")', 1
            ),
            source.replace("import struct", "import ctypes", 1),
            source.replace(
                'getattr(os, "O_DIRECTORY", 0)',
                'getattr(os, "system")',
                1,
            ),
            source.replace('"device_contact": False', '"device_contact": True', 1),
        )
        for mutation in mutations:
            with self.subTest(sha256=hashlib.sha256(mutation.encode()).hexdigest()):
                with self.assertRaisesRegex(
                    self.module.RawFirstAuditError,
                    "host-only source",
                ):
                    self.module._audit_host_only_non_acquiring_source(name, mutation)
        with self.assertRaisesRegex(
            self.module.RawFirstAuditError,
            "host-only source is not registered",
        ):
            self.module._audit_host_only_non_acquiring_source(
                "s22plus_fyg8_p319_candidate_qualification_copy.py", source
            )

    def test_device_transport_detection_ignores_incidental_substrings(self):
        self.assertFalse(
            self.module._touches_device_transport("readback = 1\n")
        )
        for text in ("adb", "adb_path = 1", "ADB", "/platform-tools/adb", "'adb'"):
            with self.subTest(text=text):
                self.assertTrue(self.module._touches_device_transport(text))

    def test_process_spawn_bypasses_are_all_rejected(self):
        """The corpus that refuted the previous rule. Each must now be rejected."""
        cases = {
            "os_system": 'import os\nA="/usr/bin/adb"\ndef r(s):\n    os.system(f"{A} -s {s} shell cat /sys/x")\n',
            "posix_spawn": 'import os\ndef r(s):\n    os.posix_spawn("/usr/bin/adb",["adb","-s",s,"shell"],{})\n',
            "pty_spawn": 'import pty\ndef r(s):\n    pty.spawn(["adb","-s",s,"shell"])\n',
            "asyncio": 'import asyncio\nasync def r(s):\n    await asyncio.create_subprocess_exec("adb","-s",s,"shell")\n',
            "importlib": 'import importlib\ndef r(s):\n    return importlib.import_module("sub"+"process").check_output(["adb"])\n',
            "getattr_indirect": 'import device_action_d0_v2 as d0\ndef r(s):\n    return getattr(d0,"bounded_command")(["adb","-s",s]).stdout\n',
            "exec_embedded": 'SRC="import subprocess\\nsubprocess.run([\'adb\'])"\ndef r():\n    exec(SRC)\n',
            "ctypes": 'import ctypes\ndef r(s):\n    ctypes.CDLL("libc.so.6").system(b"adb shell cat /sys/x")\n',
            "split_literal": 'import subprocess\nT="a" "d" "b"\ndef r(s):\n    return subprocess.run([T,"-s",s],capture_output=True).stdout\n',
        }
        for label, source in cases.items():
            for name in (
                "s22plus_fyg8_p320_mux_reader.py",
                "totally_unrelated_name.py",
            ):
                with self.subTest(bypass=label, name=name):
                    with self.assertRaises(self.module.RawFirstAuditError):
                        self.module.audit_sources(
                            REVALIDATION, overrides={name: source}
                        )

    def test_receipt_records_the_behavioral_device_boundary(self):
        value = self.module.audit_sources(REVALIDATION)
        self.assertEqual(
            value["pre_boundary_device_source_count"],
            self.module.PRE_BOUNDARY_DEVICE_SOURCE_COUNT,
        )
        self.assertEqual(
            value["pre_boundary_device_source_inventory_sha256"],
            self.module.PRE_BOUNDARY_DEVICE_SOURCE_SHA256,
        )
        self.assertEqual(value["pre_boundary_device_source_count"], 127)
        self.assertEqual(
            value["pre_boundary_device_source_inventory_sha256"],
            "c7029746710d2f83d710a3abbecbba5a6bbc3367c7a5f20a559b63a92f1677db",
        )
        # These two fields used to be hardcoded True in the receipt and were
        # published as evidence; an adversarial review refuted the second with
        # ten working bypasses. The receipt now names the rule instead of
        # certifying itself, and the bypass corpus below does the proving.
        self.assertNotIn(
            "new_device_acquiring_source_rejected_under_any_filename", value
        )
        self.assertNotIn(
            "device_acquisition_detected_by_behavior_not_filename", value
        )
        self.assertEqual(value["acquisition_rule"], "process_spawn_capability_v2")
        self.assertEqual(value["host_only_non_acquiring_source_count"], 1)
        self.assertEqual(
            value["host_only_non_acquiring_source_inventory_sha256"],
            "a85944d3066909bbb54fd5e00fdf265900708f0ca9a4af2245e46fff25de9933",
        )
        self.assertTrue(value["host_only_non_acquiring_sources_are_byte_frozen"])
        self.assertEqual(
            value["host_only_non_acquiring_sources"][0]["name"],
            "s22plus_fyg8_p319_candidate_qualification.py",
        )
        self.assertEqual(value["pre_boundary_cross_target_membership_count"], 51)


if __name__ == "__main__":
    unittest.main()
