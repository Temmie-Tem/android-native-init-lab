from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_p318_dwc3_event_latch_build.py"
MODULE_DIR = ROOT / "workspace/public/src/kernel-modules/s22plus_dwc3_event_latch"
MODULE = MODULE_DIR / "s22plus_dwc3_event_latch.c"
DECODER = MODULE_DIR / "s22plus_dwc3_event_decode.h"
FIXTURE = (
    ROOT
    / "workspace/public/src/native-init/"
    "s22plus_fyg8_p318_dwc3_event_decoder_fixture.c"
)
UDC_CORE = (
    ROOT
    / "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/drivers/usb/gadget/udc/core.c"
)
P260_RUNTIME = (
    ROOT / "workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c"
)


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("p318_latch_build", SCRIPT)
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load P3.18 latch build helper")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


P318 = load_module()


class P318Dwc3EventLatchTest(unittest.TestCase):
    def module_data(self) -> bytes:
        return MODULE.read_bytes()

    def decoder_data(self) -> bytes:
        return DECODER.read_bytes()

    def audit_source(
        self, module_data: bytes | None = None, decoder_data: bytes | None = None,
        udc_data: bytes | None = None, runtime_data: bytes | None = None,
    ):
        return P318.audit_latch_source(
            module_data if module_data is not None else self.module_data(),
            decoder_data if decoder_data is not None else self.decoder_data(),
            udc_data if udc_data is not None else UDC_CORE.read_bytes(),
            runtime_data if runtime_data is not None else P260_RUNTIME.read_bytes(),
        )

    def run_decoder_fixture(self, decoder_text: str | None = None):
        with tempfile.TemporaryDirectory(prefix="p318-dwc3-decode-") as name:
            temporary = Path(name)
            (temporary / "decode.h").write_text(
                decoder_text if decoder_text is not None else DECODER.read_text(),
                encoding="utf-8",
            )
            fixture = FIXTURE.read_text(encoding="utf-8").replace(
                '#include "../kernel-modules/s22plus_dwc3_event_latch/'
                's22plus_dwc3_event_decode.h"',
                '#include "decode.h"',
            )
            source = temporary / "fixture.c"
            source.write_text(fixture, encoding="utf-8")
            executable = temporary / "fixture"
            subprocess.run(
                [
                    "/usr/bin/cc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-O2",
                    str(source),
                    "-o",
                    str(executable),
                ],
                check=True,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return subprocess.run(
                [str(executable)],
                check=False,
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_sources_are_exact_and_actual_latch_contract_passes(self):
        receipts = P318._source_receipts(ROOT)  # noqa: SLF001
        self.assertEqual(
            set(receipts),
            {
                "Makefile", "s22plus_dwc3_event_decode.h",
                "s22plus_dwc3_event_latch.c", "decoder_fixture",
                "p260_runtime_udc_observation",
            },
        )
        audit = self.audit_source()
        self.assertTrue(audit["event_ready_is_first_callback_guard"])
        self.assertTrue(audit["qualifying_events_before_gate_are_counted"])
        self.assertTrue(audit["pre_gate_zero_cannot_race_a_gate_transition"])
        self.assertTrue(audit["gate_state_has_no_shadow_ready_flag"])
        self.assertTrue(audit["gate_state_consumers_use_one_acquire_authority"])
        self.assertTrue(audit["duplicate_gate_publication_warns_and_rejects"])
        self.assertTrue(audit["exact_a600000_dwc3_filter_precedes_decode"])
        self.assertEqual(
            audit["udc_name_authority"]["latch_exact_target"],
            "a600000.dwc3",
        )
        self.assertTrue(audit["first_event_claim_is_atomic"])
        self.assertTrue(audit["tracepoint_unregister_is_synchronized"])

    def test_real_shared_decoder_accepts_upper_fields_and_rejects_negatives(self):
        run = self.run_decoder_fixture()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(
            json.loads(run.stdout),
            {
                "schema": "s22plus_fyg8_p318_dwc3_decoder_fixture_v1",
                "positive": 6,
                "negative": 11,
                "verdict": "PASS",
            },
        )

    def test_decoder_rejects_whole_word_device_type_mutation(self):
        decoder = DECODER.read_text(encoding="utf-8")
        mutated = decoder.replace(
            "event_type = (raw & S22PLUS_DWC3_DEVICE_TYPE_MASK) >> 8;",
            "event_type = raw;",
            1,
        )
        self.assertNotEqual(mutated, decoder)
        self.assertNotEqual(self.run_decoder_fixture(mutated).returncode, 0)

    def test_decoder_rejects_dropped_event_class_mutation(self):
        decoder = DECODER.read_text(encoding="utf-8")
        mutated = decoder.replace(
            "event_class = (raw & S22PLUS_DWC3_EVENT_CLASS_MASK) >> 1;",
            "event_class = S22PLUS_DWC3_EVENT_CLASS_DEV;",
            1,
        )
        self.assertNotEqual(mutated, decoder)
        self.assertNotEqual(self.run_decoder_fixture(mutated).returncode, 0)

    def test_decoder_rejects_dropped_physical_ep0_mutation(self):
        decoder = DECODER.read_text(encoding="utf-8")
        mutated = decoder.replace(
            "if (((raw & S22PLUS_DWC3_ENDPOINT_MASK) >> 1) != 0U)",
            "if (0U != 0U)",
            1,
        )
        self.assertNotEqual(mutated, decoder)
        self.assertNotEqual(self.run_decoder_fixture(mutated).returncode, 0)

    def test_source_audit_rejects_hot_path_guard_reordering(self):
        source = MODULE.read_text(encoding="utf-8")
        original = "if (smp_load_acquire(&s22plus_latch.event_ready))"
        mutated = source.replace(
            original,
            "if (false)",
            1,
        )
        self.assertNotEqual(mutated, source)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(module_data=mutated.encode())

    def test_source_audit_rejects_non_atomic_event_claim(self):
        source = MODULE.read_text(encoding="utf-8")
        mutated = source.replace(
            "atomic_cmpxchg(&s22plus_latch.event_claimed, 0, 1)",
            "atomic_read(&s22plus_latch.event_claimed)",
            1,
        )
        self.assertNotEqual(mutated, source)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(module_data=mutated.encode())

    def test_source_audit_rejects_publish_before_event_fields(self):
        source = MODULE.read_text(encoding="utf-8")
        fields = (
            "s22plus_latch.first_event_raw = raw;\n"
            "\ts22plus_latch.first_event_kind = (u8)kind;\n"
            "\tsmp_store_release(&s22plus_latch.event_ready, 1);"
        )
        mutated = source.replace(
            fields,
            "smp_store_release(&s22plus_latch.event_ready, 1);\n"
            "\ts22plus_latch.first_event_raw = raw;\n"
            "\ts22plus_latch.first_event_kind = (u8)kind;",
            1,
        )
        self.assertNotEqual(mutated, source)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(module_data=mutated.encode())

    def test_source_audit_rejects_gate_replay(self):
        source = MODULE.read_text(encoding="utf-8")
        mutated = source.replace(
            "atomic_cmpxchg(&s22plus_latch.gate_claimed, 0, 1)",
            "atomic_read(&s22plus_latch.gate_claimed)",
            1,
        )
        self.assertNotEqual(mutated, source)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(module_data=mutated.encode())

    def test_source_audit_rejects_split_pre_gate_counter(self):
        source = MODULE.read_text(encoding="utf-8")
        mutated = source.replace(
            "&s22plus_latch.exposure_state, state_value, state_value + 1",
            "&s22plus_latch.exposure_state, state_value, state_value",
            1,
        )
        self.assertNotEqual(mutated, source)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(module_data=mutated.encode())

    def test_source_audit_rejects_non_acquire_gate_state_read(self):
        source = MODULE.read_text(encoding="utf-8")
        mutated = source.replace(
            "atomic_read_acquire(&s22plus_latch.exposure_state)",
            "atomic_read(&s22plus_latch.exposure_state)",
            1,
        )
        self.assertNotEqual(mutated, source)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(module_data=mutated.encode())

    def test_source_audit_rejects_shadow_gate_ready_state(self):
        source = MODULE.read_text(encoding="utf-8")
        mutated = source.replace(
            "\tint event_ready;",
            "\tint gate_ready;\n\tint event_ready;",
            1,
        )
        self.assertNotEqual(mutated, source)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(module_data=mutated.encode())

    def test_source_audit_rejects_silent_duplicate_gate_branch(self):
        source = MODULE.read_text(encoding="utf-8")
        mutated = source.replace("WARN_ON_ONCE(", "(", 1)
        self.assertNotEqual(mutated, source)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(module_data=mutated.encode())

    def test_udc_name_authority_rejects_kernel_or_observed_path_drift(self):
        udc = UDC_CORE.read_text(encoding="utf-8")
        mutated_udc = udc.replace(
            "kobject_name(&gadget->dev.parent->kobj)", '"fixed-udc"', 1
        )
        self.assertNotEqual(mutated_udc, udc)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(udc_data=mutated_udc.encode())

        runtime = P260_RUNTIME.read_text(encoding="utf-8")
        mutated_runtime = runtime.replace(
            "/sys/class/udc/a600000.dwc3/state",
            "/sys/class/udc/other.dwc3/state",
            1,
        )
        self.assertNotEqual(mutated_runtime, runtime)
        with self.assertRaises(P318.LatchBuildError):
            self.audit_source(runtime_data=mutated_runtime.encode())

    def test_current_ab_module_receipt_reaudits(self):
        build_dir = ROOT / P318.DEFAULT_OUTPUT_DIR
        result = P318.audit_build(ROOT, build_dir)
        self.assertEqual(result["verdict"], P318.VERDICT)
        self.assertTrue(result["a_b_byte_identical"])
        self.assertEqual(
            result["modules"]["a"]["sha256"],
            result["modules"]["b"]["sha256"],
        )
        self.assertEqual(
            result["modules"]["a"]["undefined_imports"],
            sorted(P318.EXPECTED_UNDEFINED),
        )


if __name__ == "__main__":
    unittest.main()
