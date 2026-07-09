import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


HEADER_DIR = Path("workspace/public/src/native-init").resolve()
HEADER = HEADER_DIR / "s22plus_o2_loader_core.h"
HOST_TEST = Path("tests/s22plus_o2_loader_core_test.c").resolve()


class S22PlusO2LoaderCoreTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "host C compiler unavailable")
    def test_host_behavior_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "o2-loader-core-test"
            compiled = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    "-I",
                    str(HEADER_DIR),
                    str(HOST_TEST),
                    "-o",
                    str(binary),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            executed = subprocess.run([str(binary)], text=True, capture_output=True, check=False)
        self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
        self.assertEqual(executed.stdout.strip(), "s22plus_o2_loader_core_test=PASS")

    @unittest.skipUnless(shutil.which("aarch64-linux-gnu-gcc"), "arm64 cross compiler unavailable")
    def test_arm64_freestanding_compile(self):
        source = """
#include "s22plus_o2_loader_core.h"
int o2_compile_probe(struct s22plus_o2_reader *reader,
                     const char *const *names,
                     unsigned char *found,
                     struct s22plus_o2_proc_scan_result *result) {
    return s22plus_o2_scan_proc_modules(reader, names, 1, found, result);
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "probe.c"
            object_path = Path(tmp) / "probe.o"
            source_path.write_text(source, encoding="ascii")
            compiled = subprocess.run(
                [
                    "aarch64-linux-gnu-gcc",
                    "-std=c11",
                    "-ffreestanding",
                    "-fno-builtin",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(HEADER_DIR),
                    "-c",
                    str(source_path),
                    "-o",
                    str(object_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            self.assertTrue(object_path.is_file())

    def test_source_contract_streams_to_eof_and_stops_failures(self):
        text = HEADER.read_text(encoding="utf-8")
        self.assertIn("result->eof_seen = 1", text)
        self.assertIn("reader->read", text)
        self.assertIn("return S22PLUS_O2_ERR_FINIT", text)
        self.assertIn("return S22PLUS_O2_GATE_MISSING", text)
        self.assertNotIn("16384", text)


if __name__ == "__main__":
    unittest.main()
