import importlib.util
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1b_patch_check.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r4w1b_checked", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1BPatchCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.source = ROOT / cls.module.DEFAULT_SOURCE
        cls.patch = ROOT / cls.module.DEFAULT_PATCH

    def test_integrated_contract_passes(self):
        result = self.module.run_check(self.source, self.patch)
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertEqual(len(result["dt_contract"]["revisions"]), 11)
        self.assertEqual(result["patched_contract"]["marker_size"], 99)
        self.assertEqual(result["patched_contract"]["exec_success_edge_count"], 1)

    def test_base_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for relative in self.module.BASE_FILES:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((self.source / relative).read_bytes())
            path = root / "kernel_platform/common/init/main.c"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(self.module.CheckError, "base SHA256 mismatch"):
                self.module.check_base_files(root)

    def test_patch_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as name:
            mutated = Path(name) / "mutated.patch"
            mutated.write_bytes(self.patch.read_bytes() + b"\n")
            with self.assertRaisesRegex(self.module.CheckError, "patch SHA256 mismatch"):
                self.module.check_patch_policy(mutated)

    def test_added_security_config_is_rejected(self):
        text = self.patch.read_text(encoding="ascii")
        added = self.module.added_patch_lines(text + "+CONFIG_RKP=n\n")
        symbols = {
            symbol
            for line in added
            for symbol in self.module.re.findall(r"CONFIG_[A-Z0-9_]+", line)
        }
        self.assertNotEqual(symbols, {"CONFIG_S22PLUS_FYG8_RETAINED_WITNESS"})

    def test_vendor_header_shape_is_pinned(self):
        result = self.module.check_vendor_abi(self.source)
        self.assertTrue(result["verified"])
        self.assertEqual(result["missing"], {})

    def test_dt_node_contract_rejects_no_map_and_wrong_phandle(self):
        carveout = (
            '\ncompatible = "samsung,carve-out";\n'
            'reg = <0x08 0x1ff000 0x00 0x901000>;\n'
            'phandle = <0x9f>;\n'
        )
        log_buf = (
            '\ncompatible = "samsung,kernel_log_buf";\nstatus = "okay";\n'
            'memory-region = <0x9f>;\nsec,use-partial_reserved_mem;\n'
            'reg = <0x08 0x200000 0x00 0x200000>;\nsec,strategy = <0x03>;\n'
        )
        self.assertEqual(self.module.validate_dt_nodes(carveout, log_buf), "0x9f")
        with self.assertRaisesRegex(self.module.CheckError, "no-map"):
            self.module.validate_dt_nodes(carveout + "no-map;\n", log_buf)
        with self.assertRaisesRegex(self.module.CheckError, "does not reference"):
            self.module.validate_dt_nodes(carveout, log_buf.replace("0x9f", "0xa0"))

    def test_marker_is_build_bound_and_ascii(self):
        encoded = self.module.MARKER.encode("ascii")
        self.assertIn(self.module.MARKER_ID.encode("ascii"), encoded)
        self.assertTrue(encoded.startswith(b"\n[[S22R4W1B|"))
        self.assertTrue(encoded.endswith(b"]]\n"))
        self.assertEqual(len(encoded), 99)
        self.assertEqual(
            self.module.hashlib.sha256(
                self.module.MARKER_PREIMAGE.encode("ascii")
            ).hexdigest(),
            self.module.MARKER_PREIMAGE_SHA256,
        )
        self.assertEqual(self.module.MARKER_PREIMAGE_SHA256[:32], self.module.MARKER_ID)
        self.assertLess(len(encoded), self.module.LOG_SIZE - 16)

    def check_mutated_patch_rejected(self, text, message):
        with tempfile.TemporaryDirectory() as name:
            mutated = Path(name) / "mutated.patch"
            mutated.write_text(text, encoding="ascii")
            with mock.patch.object(
                self.module,
                "PATCH_SHA256",
                self.module.sha256_file(mutated),
            ):
                with self.assertRaisesRegex(self.module.CheckError, message):
                    self.module.check_patch_policy(mutated)

    def test_historical_marker_is_rejected(self):
        text = self.patch.read_text(encoding="ascii")
        self.check_mutated_patch_rejected(
            text.replace("S22R4W1B|", "S22R4W1|"),
            "historical",
        )

    def test_wrong_marker_phase_is_rejected(self):
        text = self.patch.read_text(encoding="ascii")
        self.check_mutated_patch_rejected(
            text.replace(self.module.MARKER_PHASE, "RAMDISK_EXEC_ACCEPTED"),
            "marker phase missing",
        )


if __name__ == "__main__":
    unittest.main()
