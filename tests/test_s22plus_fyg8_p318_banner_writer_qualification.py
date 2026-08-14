from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_banner_writer_qualification.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_banner_qualification", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 banner qualification")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318BannerWriterQualificationTest(unittest.TestCase):
    def inputs(self):
        return {
            "writer_data": (ROOT / P318.WRITER).read_bytes(),
            "fixture_data": (ROOT / P318.FIXTURE).read_bytes(),
            "runtime_fixture_data": (ROOT / P318.RUNTIME_FIXTURE).read_bytes(),
            "p260_data": (ROOT / P318.P260_RUNTIME).read_bytes(),
            "extractor_data": SCRIPT.read_bytes(),
            "root": ROOT,
        }

    def run_mutated_fixture(self, writer_text: str):
        with tempfile.TemporaryDirectory(prefix="p318-banner-mutation-") as name:
            temporary = Path(name)
            (temporary / "s22plus_fyg8_p318_banner_writer.inc.c").write_text(
                writer_text, encoding="utf-8"
            )
            fixture = temporary / "fixture.c"
            fixture.write_bytes((ROOT / P318.FIXTURE).read_bytes())
            executable = temporary / "fixture"
            compile_result = subprocess.run(
                [
                    "/usr/bin/cc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-O2",
                    str(fixture),
                    "-o",
                    str(executable),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if compile_result.returncode != 0:
                return compile_result
            return subprocess.run(
                [str(executable)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_actual_c_writer_and_runtime_wrapper_pass(self):
        result = P318.build_contract(**self.inputs())
        self.assertEqual(result["verdict"], P318.VERDICT)
        self.assertEqual(
            result["actual_c_fixtures"]["scripted_terminal_paths"]["result"],
            {
                "schema": "s22plus_fyg8_p318_banner_writer_fixture_v1",
                "cases": 15,
                "verdict": "PASS",
            },
        )
        self.assertEqual(
            result["actual_c_fixtures"]["runtime_wrapper"]["result"]["bytes"],
            49,
        )
        self.assertTrue(result["source_audit"]["deadline_checked_before_every_write"])
        self.assertTrue(result["source_audit"]["eagain_epipe_enodev_distinct"])

    def test_private_receipt_is_exact_current_output(self):
        expected = P318.encode_contract(P318.build_contract(**self.inputs()))
        actual = (ROOT / P318.DEFAULT_OUTPUT).read_bytes()
        self.assertEqual(actual, expected)

    def test_eintr_retry_reason_mutation_fails_actual_fixture(self):
        writer = (ROOT / P318.WRITER).read_text(encoding="utf-8")
        mutated = writer.replace(
            "retry_reason = S22PLUS_P318_BANNER_RETRY_EINTR;",
            "retry_reason = S22PLUS_P318_BANNER_RETRY_NONE;",
            1,
        )
        self.assertNotEqual(mutated, writer)
        self.assertNotEqual(self.run_mutated_fixture(mutated).returncode, 0)

    def test_enodev_error_collapse_mutation_fails_actual_fixture(self):
        writer = (ROOT / P318.WRITER).read_text(encoding="utf-8")
        mutated = writer.replace(
            "return S22PLUS_P318_BANNER_ERROR_ENODEV;",
            "return S22PLUS_P318_BANNER_ERROR_EPIPE;",
            1,
        )
        self.assertNotEqual(mutated, writer)
        self.assertNotEqual(self.run_mutated_fixture(mutated).returncode, 0)

    def test_uncapped_eagain_sleep_mutation_fails_actual_fixture(self):
        writer = (ROOT / P318.WRITER).read_text(encoding="utf-8")
        mutated = writer.replace(
            "? remaining : S22PLUS_P318_BANNER_POLL_NS;",
            "? remaining : S22PLUS_P318_BANNER_POLL_NS * 2;",
            1,
        )
        self.assertNotEqual(mutated, writer)
        self.assertNotEqual(self.run_mutated_fixture(mutated).returncode, 0)

    def test_zero_write_reclassification_mutation_fails_actual_fixture(self):
        writer = (ROOT / P318.WRITER).read_text(encoding="utf-8")
        mutated = writer.replace(
            "written, S22PLUS_P318_BANNER_ERROR_ZERO_WRITE);",
            "written, S22PLUS_P318_BANNER_ERROR_OTHER);",
            1,
        )
        self.assertNotEqual(mutated, writer)
        self.assertNotEqual(self.run_mutated_fixture(mutated).returncode, 0)

    def test_source_audit_rejects_deadline_reinitialization(self):
        inputs = self.inputs()
        writer = inputs["writer_data"].decode()
        mutated = writer.replace(
            "while (written < size) {",
            "while (written < size) {\n"
            "        deadline.tv_sec += S22PLUS_P318_BANNER_DEADLINE_SEC;",
            1,
        )
        with self.assertRaises(P318.BannerQualificationError):
            P318.audit_source(mutated.encode(), inputs["p260_data"])

    def test_source_audit_rejects_write_before_loop_clock_check(self):
        inputs = self.inputs()
        writer = inputs["writer_data"].decode()
        mutated = writer.replace(
            "if (ops->clock_gettime(ops->context, &now) != 0 ||",
            "if (0 ||",
            1,
        )
        with self.assertRaises(P318.BannerQualificationError):
            P318.audit_source(mutated.encode(), inputs["p260_data"])


if __name__ == "__main__":
    unittest.main()
