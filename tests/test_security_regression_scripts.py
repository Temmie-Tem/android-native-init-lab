from __future__ import annotations

import contextlib
import io
import unittest

from _loader import load_revalidation


def run_embedded_suite(module_name: str) -> unittest.result.TestResult:
    module = load_revalidation(module_name)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    stream = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)


class SecurityRegressionScriptSuites(unittest.TestCase):
    def test_unit_a_embedded_regressions_run_cleanly(self) -> None:
        result = run_embedded_suite("security_unit_a_regression")

        self.assertEqual(result.testsRun, 6)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])

    def test_unit_b_embedded_regressions_run_cleanly(self) -> None:
        result = run_embedded_suite("security_unit_b_regression")

        self.assertEqual(result.testsRun, 4)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])

    def test_tier2_embedded_regressions_run_cleanly(self) -> None:
        result = run_embedded_suite("security_tier2_regression")

        self.assertEqual(result.testsRun, 3)
        self.assertEqual(result.failures, [])
        self.assertEqual(result.errors, [])

    def test_unit_b_minimal_manifest_preserves_secret_hygiene_defaults(self) -> None:
        unit_b = load_revalidation("security_unit_b_regression")

        manifest = unit_b.minimal_v2178_manifest()

        self.assertEqual(manifest["autoconnect_status"]["secret_values_logged"], "0")
        self.assertEqual(manifest["connect"]["secret_values_logged"], "0")
        self.assertEqual(manifest["connect"]["credentials_logged"], "0")
        self.assertEqual(manifest["scope"]["credentials_logged"], 0)
        self.assertEqual(manifest["cleanup"]["decision"], "wifi-cleanup-done")
        self.assertEqual(manifest["autoconnect_disable_restore"]["decision"], "wifi-autoconnect-disabled")


if __name__ == "__main__":
    unittest.main()
