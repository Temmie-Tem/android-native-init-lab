import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_max77705_attribute_stage_a.py"
)
REVALIDATION = SCRIPT.parent


def load_module():
    sys.path.insert(0, str(REVALIDATION))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_p319_max77705_attribute_stage_a_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(REVALIDATION))


VALID = (
    b"adapter\ti2c-57\n"
    b"client\t57-0066\n"
    b"entry\tdriver\tsymlink\n"
    b"entry\tregmap\tregular\n"
    b"entry_count\t2\n"
    b"regmap_count\t1\n"
    b"regmap_kind\tregular\n"
)


class S22PlusFyg8P319StageATest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def handle(self, root: Path, payload: bytes, name: str = "stage-a"):
        capture = self.module.raw_capture.prepare_capture_dir(root)
        return self.module.raw_capture.publish_captured_bytes(
            capture, name, stdout=payload
        )

    def test_exact_inventory_yields_one_bounded_stage_b_attribute(self):
        with tempfile.TemporaryDirectory() as temporary:
            handle = self.handle(Path(temporary), VALID)
            value = self.module.parse_stage_a(handle)
        self.assertEqual(value["adapter_name"], "i2c-57")
        self.assertEqual(value["client_name"], "57-0066")
        self.assertEqual(value["regmap_exact_entry_count"], 1)
        self.assertEqual(value["regmap_exact_entry_kind"], "regular")
        self.assertEqual(value["raw_stdout"]["sha256"], hashlib.sha256(VALID).hexdigest())

    def test_specific_shape_predicates_fail_after_raw_publication(self):
        mutations = (
            (VALID.replace(b"adapter\ti2c-57\n", b""), "adapter row cardinality"),
            (VALID.replace(b"client\t57-0066", b"client\tbad"), "client name"),
            (VALID.replace(b"entry_count\t2", b"entry_count\t3"), "entry_count differs"),
            (VALID.replace(b"regmap_count\t1", b"regmap_count\t0"), "regmap_count differs"),
            (VALID.rstrip(b"\n"), "final line delimiter"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, (payload, message) in enumerate(mutations):
                with self.subTest(message=message):
                    handle = self.handle(root, payload, f"mutation-{index}")
                    with self.assertRaisesRegex(self.module.StageAError, message):
                        self.module.parse_stage_a(handle)
                    self.assertEqual(handle.stdout_path.read_bytes(), payload)

    def test_parser_rejects_live_bytes_and_command_contract_is_zero_io(self):
        with self.assertRaises(self.module.StageAError):
            self.module.parse_stage_a(b"adapter\ti2c-57\n")
        safety = self.module.stage_a_safety_contract()
        self.assertEqual(safety["result"], "pass")
        for key in (
            "attribute_body_open_count",
            "attribute_body_read_count",
            "i2c_device_access_count",
            "debugfs_access_count",
            "sysfs_write_count",
            "reboot_count",
            "module_action_count",
        ):
            self.assertEqual(safety[key], 0)

    def test_offline_validation_has_no_device_authority(self):
        self.assertEqual(self.module.main(["--validate"]), 0)
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("--retry", source)
        self.assertNotIn("--reboot", source)
        self.assertNotIn("--flash", source)


if __name__ == "__main__":
    unittest.main()
