from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_p318_poll_budget_measurement.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("p318_poll_measurement", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 poll measurement")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318PollBudgetMeasurementTest(unittest.TestCase):
    def inputs(self):
        return (
            (ROOT / P318.DEFAULT_LIVE_STATE).read_bytes(),
            (ROOT / P318.DEFAULT_TELEMETRY_SOURCE).read_bytes(),
            SCRIPT.read_bytes(),
        )

    def test_actual_p317_records_fit_measured_47_byte_budget(self):
        result = P318.measure(*self.inputs())
        measurement = result["measurement"]
        self.assertEqual(result["verdict"], P318.VERDICT)
        self.assertEqual(measurement["p317_record_count"], 2)
        self.assertEqual(measurement["maximum_observed_packbits_size"], 9)
        self.assertEqual(measurement["proposed_v4_lossless_capacity"], 47)
        self.assertEqual(measurement["minimum_observed_margin"], 38)
        self.assertEqual(measurement["required_boundary_preimages"], [47, 48])
        self.assertTrue(measurement["actual_packbits_function_executed"])
        self.assertTrue(
            measurement[
                "packbits_execution_and_receipt_use_identical_source_bytes"
            ]
        )
        self.assertTrue(
            measurement["future_poll_payloads_not_proven_by_this_incident_measurement"]
        )
        for row in measurement["records"]:
            self.assertEqual(row["poll_counts"], [2, 2, 2, 2])
            self.assertEqual(row["raw_size"], 8)
            self.assertEqual(row["packbits_size"], 9)
            self.assertTrue(row["roundtrip"])

    def test_capacity_below_observed_payload_fails_closed(self):
        with self.assertRaisesRegex(P318.MeasurementError, "exceeds"):
            P318.measure(*self.inputs(), proposed_capacity=8)

    def test_recorded_encoded_size_mutation_fails_closed(self):
        live_state, telemetry_source, extractor = self.inputs()
        mutated = live_state.replace(
            b'"poll_encoded_size": 9', b'"poll_encoded_size": 8', 1
        )
        self.assertNotEqual(mutated, live_state)
        with self.assertRaisesRegex(P318.MeasurementError, "authority"):
            P318.measure(mutated, telemetry_source, extractor)

    def test_packbits_function_body_mutation_fails_closed(self):
        live_state, telemetry_source, extractor = self.inputs()
        mutated = telemetry_source.replace(
            b"output.append(len(literal) - 1)",
            b"output.append(len(literal) - 2)",
            1,
        )
        self.assertNotEqual(mutated, telemetry_source)
        with self.assertRaises(P318.MeasurementError):
            P318.measure(live_state, mutated, extractor)


if __name__ == "__main__":
    unittest.main()
