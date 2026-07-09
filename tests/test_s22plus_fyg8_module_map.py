import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_module_map.py"
METADATA = ROOT / (
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location("s22plus_fyg8_module_map_tested", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


@unittest.skipUnless(METADATA.is_dir(), "private FYG8 module metadata unavailable")
class S22PlusFyg8ModuleMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.model = cls.module.build_model(METADATA)
        cls.artifacts = cls.module.build_artifacts(cls.model)

    def inventory_rows(self):
        lines = self.artifacts["inventory.tsv"].splitlines()
        header = lines[0].split("\t")
        return [dict(zip(header, line.split("\t"), strict=True)) for line in lines[1:]]

    def test_inventory_covers_all_exact_modules(self):
        rows = self.inventory_rows()
        self.assertEqual(len(rows), 441)
        self.assertEqual(len({row["filename"] for row in rows}), 441)
        self.assertTrue(all(len(row["sha256"]) == 64 for row in rows))
        self.assertTrue(all(row["vermagic"] == self.module.EXPECTED_VERMAGIC for row in rows))

    def test_retention_owner_and_debug_roles_are_separate(self):
        rows = {row["filename"]: row for row in self.inventory_rows()}
        logbuf = rows["sec_log_buf.ko"]
        debug = rows["sec_debug.ko"]
        self.assertEqual(logbuf["firststage_line_positions"], "2")
        self.assertEqual(logbuf["firststage_unique_position"], "2")
        self.assertEqual(debug["firststage_line_positions"], "105")
        self.assertEqual(debug["firststage_unique_position"], "100")
        self.assertEqual(logbuf["hard_deps"], "")
        self.assertEqual(debug["hard_deps"], "")
        self.assertEqual(logbuf["soft_pre"], "")
        self.assertEqual(debug["soft_pre"], "")
        self.assertIn("SOURCE_VERIFIED", logbuf["evidence_status"])
        self.assertIn("LIVE_BOUND", logbuf["evidence_status"])
        retention = self.artifacts["subsystem-retention.md"]
        self.assertIn("reserved-memory printk ring", retention)
        self.assertIn("panic notifier", retention)

    def test_dependency_edges_keep_hard_and_soft_semantics(self):
        edges = self.artifacts["dependency-edges.tsv"]
        self.assertIn("hard\tsec_debug.ko\tclk-rpmh.ko\tmodules.dep", edges)
        self.assertIn("soft_pre\tqcom_hwspinlock.ko\tsmem.ko\tmodules.softdep", edges)
        self.assertIn("soft_post\tdwc3-msm.ko\tucsi_glink.ko\tmodules.softdep", edges)

    def test_symbol_map_does_not_promote_kernel_or_unresolved_imports(self):
        manifest = self.module.json.loads(self.artifacts["manifest.json"])
        self.assertGreater(manifest["counts"]["declared_symbol_provider_overlaps"], 0)
        self.assertGreater(manifest["counts"]["candidate_only_symbol_overlaps"], 0)
        self.assertGreater(manifest["counts"]["kernel_or_unresolved_symbols"], 0)
        self.assertIn("kernel-or-unresolved", self.artifacts["README.md"])
        self.assertIn("CANDIDATE_ONLY", self.artifacts["symbol-overlap-edges.tsv"])

    def test_write_then_check_is_reproducible_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "map"
            self.module.write_artifacts(out, self.artifacts)
            self.module.check_artifacts(out, self.artifacts)
            (out / "README.md").write_text("drift\n", encoding="ascii")
            with self.assertRaisesRegex(self.module.MapError, "module map drifted"):
                self.module.check_artifacts(out, self.artifacts)

    def test_safety_manifest_is_host_only(self):
        manifest = self.module.json.loads(self.artifacts["manifest.json"])
        self.assertTrue(manifest["safety"]["host_only"])
        for key in (
            "adb",
            "module_insertion",
            "reboot",
            "image_build",
            "flash",
            "partition_write",
            "sysfs_write",
            "configfs_write",
        ):
            self.assertFalse(manifest["safety"][key])


if __name__ == "__main__":
    unittest.main()
