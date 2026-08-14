from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_cdc_acm_positive_control.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_positive_control", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 positive control")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318CdcAcmPositiveControlTest(unittest.TestCase):
    def inputs(self):
        return {
            "qemu_result_data": (ROOT / P318.DEFAULT_QEMU_RESULT).read_bytes(),
            "qemu_log_data": (ROOT / P318.DEFAULT_QEMU_LOG).read_bytes(),
            "runtime_data": (ROOT / P318.DEFAULT_RUNTIME).read_bytes(),
            "harness_data": (ROOT / P318.DEFAULT_HARNESS).read_bytes(),
            "observer_path": ROOT / P318.DEFAULT_OBSERVER,
            "selector_data": (ROOT / P318.DEFAULT_SELECTOR).read_bytes(),
            "extractor_data": SCRIPT.read_bytes(),
        }

    def test_current_two_seam_control_passes_without_overclaim(self):
        result = P318.build_contract(**self.inputs())
        self.assertEqual(result["verdict"], P318.VERDICT)
        self.assertEqual(result["qemu_dummy_hcd"]["banner_size"], 49)
        self.assertTrue(result["qemu_dummy_hcd"]["dummy_hcd_kernel_path_executed"])
        self.assertTrue(result["real_observer"]["accepted"])
        self.assertTrue(
            result["real_observer"][
                "real_python_open_raw_read_and_receipt_executed"
            ]
        )
        self.assertTrue(result["transitive_join"]["same_bytes_at_both_seams"])
        self.assertFalse(
            result["transitive_join"]["dummy_hcd_to_real_python_end_to_end"]
        )
        self.assertFalse(result["scope"]["actual_root_udev_guard"])

    def test_qemu_verdict_mutation_fails(self):
        values = self.inputs()
        result = json.loads(values["qemu_result_data"])
        result["verdict"] = "FAIL"
        values["qemu_result_data"] = json.dumps(result).encode()
        with self.assertRaisesRegex(P318.PositiveControlError, "authority"):
            P318.build_contract(**values)

    def test_qemu_console_stage_mutation_fails(self):
        values = self.inputs()
        result = json.loads(values["qemu_result_data"])
        mutated_log = values["qemu_log_data"].replace(
            b"name=pre-bind-banner", b"name=missing-banner"
        )
        result["qemu_output_sha256"] = __import__("hashlib").sha256(
            mutated_log.decode("utf-8").encode("utf-8")
        ).hexdigest()
        values["qemu_log_data"] = mutated_log
        values["qemu_result_data"] = json.dumps(result).encode()
        with self.assertRaisesRegex(P318.PositiveControlError, "console"):
            P318.build_contract(**values)

    def test_banner_source_mutation_fails(self):
        values = self.inputs()
        values["runtime_data"] = values["runtime_data"].replace(
            b'S22PLUS-FYG8-E3:', b'S22PLUS-FYG8-X3:', 1
        )
        with self.assertRaisesRegex(P318.PositiveControlError, "banner source"):
            P318.build_contract(**values)

    def test_real_observer_source_is_the_executed_file(self):
        result = P318.build_contract(**self.inputs())
        expected = P318.receipt((ROOT / P318.DEFAULT_OBSERVER).read_bytes())
        self.assertEqual(result["real_observer"]["observer_source"], expected)


if __name__ == "__main__":
    unittest.main()
