import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_consumed_suite_expected_failures.py"
)

SYNTHETIC = """\
import unittest


class SyntheticTest(unittest.TestCase):
    def test_passes(self):
        self.assertTrue(True)

    def test_fails(self):
        self.assertTrue(False)

    def test_subtest_fails(self):
        for name in ("alpha", "beta"):
            with self.subTest(name=name):
                self.assertTrue(False)
"""


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_consumed_suite_expected_failures_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ConsumedSuiteExpectedFailuresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def synthetic_tests(self, directory: str):
        # A distinct module name per temporary directory: unittest refuses to
        # re-import the same name from a new location.
        name = "synthetic_suite_" + Path(directory).name.replace("-", "_")
        path = Path(directory)
        (path / (name + ".py")).write_text(SYNTHETIC, encoding="utf-8")
        self.addCleanup(sys.modules.pop, name, None)
        self.addCleanup(sys.path.remove, str(path))
        return path, name + ".py", {
            "failing": name + ".SyntheticTest.test_fails",
            "subtest": name + ".SyntheticTest.test_subtest_fails",
            "passing": name + ".SyntheticTest.test_passes",
        }

    def run_with_manifest(self, manifest, directory, pattern):
        original = self.module.EXPECTED_FAILURES
        self.module.EXPECTED_FAILURES = manifest
        try:
            return self.module.audit(pattern, directory)
        finally:
            self.module.EXPECTED_FAILURES = original

    def test_unaccounted_failure_is_reported_as_a_regression(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory, pattern, ids = self.synthetic_tests(temporary)
            with self.assertRaisesRegex(
                self.module.ExpectedFailureError,
                "unaccounted test failure is a regression",
            ):
                self.run_with_manifest(
                    {ids["subtest"]: "known"}, directory, pattern
                )

    def test_expected_failure_that_now_passes_must_leave_the_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory, pattern, ids = self.synthetic_tests(temporary)
            with self.assertRaisesRegex(
                self.module.ExpectedFailureError,
                "expected failure now passes and must leave the manifest",
            ):
                self.run_with_manifest(
                    {
                        ids["failing"]: "known",
                        ids["subtest"]: "known",
                        ids["passing"]: "stale entry",
                    },
                    directory,
                    pattern,
                )

    def test_exactly_accounted_synthetic_suite_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory, pattern, ids = self.synthetic_tests(temporary)
            value = self.run_with_manifest(
                {ids["failing"]: "known", ids["subtest"]: "known"},
                directory,
                pattern,
            )
            self.assertEqual(value["verdict"], self.module.VERDICT)
            self.assertEqual(value["tests_run"], 3)
            self.assertEqual(value["expected_failures"], 2)
            self.assertEqual(value["unaccounted_failures"], 0)
            self.assertEqual(value["stale_manifest_entries"], 0)
            self.assertFalse(value["device_contact"])
            self.assertFalse(value["live_authorized"])

    def test_subtest_failures_collapse_to_the_owning_test_method(self):
        # Two subTest parameters fail; the manifest must need only one entry,
        # otherwise every new parameter would silently look unaccounted.
        with tempfile.TemporaryDirectory() as temporary:
            directory, pattern, ids = self.synthetic_tests(temporary)
            run = self.module.discover_failures(pattern, directory)
            self.assertEqual(
                sorted(run["observed"]),
                sorted((ids["failing"], ids["subtest"])),
            )

    def test_receipt_is_deterministic_mode0400_and_no_clobber(self):
        value = {
            "schema": self.module.SCHEMA,
            "verdict": self.module.VERDICT,
        }
        payload = self.module.encode_receipt(value)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            self.module.write_receipt(path, payload)
            self.module.write_receipt(path, payload)
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            self.assertEqual(path.stat().st_nlink, 1)
            with self.assertRaisesRegex(
                self.module.ExpectedFailureError,
                "receipt would change existing bytes",
            ):
                self.module.write_receipt(path, payload + b"\n")

    def test_manifest_reasons_are_stated_for_every_entry(self):
        self.assertTrue(self.module.EXPECTED_FAILURES)
        for identity, reason in self.module.EXPECTED_FAILURES.items():
            with self.subTest(identity=identity):
                self.assertIsInstance(reason, str)
                self.assertGreater(len(reason), 40)


if __name__ == "__main__":
    unittest.main()
