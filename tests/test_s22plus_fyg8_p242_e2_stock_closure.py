import copy
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
MODULE_PATH = SCRIPT_DIR / "s22plus_fyg8_p242_e2_stock_closure.py"


def load_module():
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p242_e2_stock_closure_tested", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P242E2StockClosureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.private_ready = all(
            (ROOT / path).exists()
            for path in (
                cls.module.DEFAULT_VENDOR_RAMDISK,
                cls.module.DEFAULT_LZ4,
                cls.module.p241.DEFAULT_PLAN_HEADER,
                cls.module.planner.DEFAULT_METADATA_DIR,
            )
        )
        if cls.private_ready:
            cls.closure = cls.module.derive_module_closure(
                ROOT,
                ROOT / cls.module.DEFAULT_VENDOR_RAMDISK,
                ROOT / cls.module.DEFAULT_LZ4,
            )

    def require_private(self):
        if not self.private_ready:
            self.skipTest("exact FYG8 private inputs are unavailable")

    def generic_rootfs(self, init, child, init_elf, child_elf):
        return {
            "entry_count": self.module.EXPECTED_GENERIC_ENTRY_COUNT,
            "no_duplicate_or_alias": True,
            "init": {
                **init,
                "uid": 0,
                "gid": 0,
                "mode": 0o750,
                "nlink": 1,
                "elf": init_elf,
                "run_id_count": 1,
                "required_strings_complete": True,
                "forbidden_authority_absent": True,
            },
            "child": {
                **child,
                "uid": 0,
                "gid": 0,
                "mode": 0o750,
                "nlink": 1,
                "elf": child_elf,
                "token_count": 1,
            },
            "rdinit_override_absent": True,
            "verified": True,
        }

    def test_exact_stock_closure_matches_canonical_pin(self):
        self.require_private()
        self.assertEqual(self.closure["count"], 59)
        self.assertEqual(self.closure["constraint_count"], 210)
        self.assertEqual(self.closure["files"][0], "qcom_hwspinlock.ko")
        self.assertEqual(self.closure["files"][-1], "ucsi_glink.ko")
        self.assertEqual(
            self.module.closure_sha256(self.closure),
            self.module.EXPECTED_MODULE_CLOSURE_SHA256,
        )
        self.assertIs(
            self.module.validate_module_closure(self.closure), self.closure
        )

    def test_module_byte_or_order_mutation_is_rejected(self):
        self.require_private()
        cases = {
            "digest": lambda value: value["modules"][0].__setitem__(
                "sha256", "0" * 64
            ),
            "order": lambda value: value["modules"].__setitem__(
                slice(0, 2), list(reversed(value["modules"][:2]))
            ),
            "file_projection": lambda value: value["files"].__setitem__(
                0, "forged.ko"
            ),
            "verified_type": lambda value: value.__setitem__("verified", 1),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                forged = copy.deepcopy(self.closure)
                mutate(forged)
                with self.assertRaises(self.module.ClosureError):
                    self.module.validate_module_closure(forged)

    def test_effective_rootfs_validator_rejects_unbound_module_closure(self):
        self.require_private()
        init = {"size": 101, "sha256": "1" * 64}
        child = {"size": 102, "sha256": "2" * 64}
        init_elf = {
            "machine": "AArch64",
            "entrypoint": self.module.EXPECTED_ELF_ENTRYPOINTS["init"],
            "interpreter": False,
            "dynamic": False,
            "executable_stack": False,
            "entrypoint_mapped": True,
            "verified": True,
        }
        child_elf = {
            **init_elf,
            "entrypoint": self.module.EXPECTED_ELF_ENTRYPOINTS["child"],
        }
        value = {
            "composition_order": ["generic", "vendor[0]/"],
            "entry_count": 474,
            "generic_rootfs": self.generic_rootfs(
                init, child, init_elf, child_elf
            ),
            "no_duplicate_override_or_alias": True,
            "init": {**init, "elf": init_elf, "run_id_count": 1},
            "child": {**child, "elf": child_elf},
            "modules": [
                {
                    "file": row["file"],
                    "runtime": row["runtime_name"],
                    "layer": "vendor[0]/",
                }
                for row in self.closure["modules"]
            ],
            "module_count": 59,
            "module_closure_sha256": self.module.closure_sha256(self.closure),
            "rdinit_override_absent": True,
            "verified": True,
        }
        self.assertIs(
            self.module.validate_effective_rootfs(
                value,
                expected_init=init,
                expected_child=child,
                module_closure=self.closure,
            ),
            value,
        )
        value["module_closure_sha256"] = "0" * 64
        with self.assertRaises(self.module.ClosureError):
            self.module.validate_effective_rootfs(
                value,
                expected_init=init,
                expected_child=child,
                module_closure=self.closure,
            )

    def test_effective_rootfs_rejects_nested_shape_and_numeric_type_malleability(self):
        self.require_private()
        init = {"size": 101, "sha256": "1" * 64}
        child = {"size": 102, "sha256": "2" * 64}
        base_elf = {
            "machine": "AArch64",
            "entrypoint": self.module.EXPECTED_ELF_ENTRYPOINTS["init"],
            "interpreter": False,
            "dynamic": False,
            "executable_stack": False,
            "entrypoint_mapped": True,
            "verified": True,
        }
        value = {
            "composition_order": ["generic", "vendor[0]/"],
            "entry_count": 474,
            "generic_rootfs": self.generic_rootfs(
                init,
                child,
                base_elf,
                {
                    **base_elf,
                    "entrypoint": self.module.EXPECTED_ELF_ENTRYPOINTS["child"],
                },
            ),
            "no_duplicate_override_or_alias": True,
            "init": {**init, "elf": base_elf, "run_id_count": 1},
            "child": {
                **child,
                "elf": {
                    **base_elf,
                    "entrypoint": self.module.EXPECTED_ELF_ENTRYPOINTS["child"],
                },
            },
            "modules": [
                {
                    "file": row["file"],
                    "runtime": row["runtime_name"],
                    "layer": "vendor[0]/",
                }
                for row in self.closure["modules"]
            ],
            "module_count": 59,
            "module_closure_sha256": self.module.closure_sha256(self.closure),
            "rdinit_override_absent": True,
            "verified": True,
        }
        cases = {
            "extra_init_key": lambda item: item["init"].__setitem__("extra", 1),
            "extra_elf_key": lambda item: item["init"]["elf"].__setitem__(
                "extra", False
            ),
            "bool_run_id_count": lambda item: item["init"].__setitem__(
                "run_id_count", True
            ),
            "bool_entrypoint": lambda item: item["init"]["elf"].__setitem__(
                "entrypoint", True
            ),
            "float_module_count": lambda item: item.__setitem__(
                "module_count", 59.0
            ),
            "wrong_entrypoint": lambda item: item["init"]["elf"].__setitem__(
                "entrypoint", self.module.EXPECTED_ELF_ENTRYPOINTS["init"] + 4
            ),
            "generic_wrong_mode": lambda item: item["generic_rootfs"][
                "init"
            ].__setitem__("mode", 0o755),
            "generic_wrong_nlink": lambda item: item["generic_rootfs"][
                "child"
            ].__setitem__("nlink", 2),
            "generic_bool_uid": lambda item: item["generic_rootfs"][
                "init"
            ].__setitem__("uid", False),
            "generic_bool_nlink": lambda item: item["generic_rootfs"][
                "child"
            ].__setitem__("nlink", True),
            "generic_float_mode": lambda item: item["generic_rootfs"][
                "init"
            ].__setitem__("mode", float(0o750)),
            "generic_numeric_flag": lambda item: item["generic_rootfs"].__setitem__(
                "verified", 1
            ),
            "generic_forbidden_flag": lambda item: item["generic_rootfs"][
                "init"
            ].__setitem__("forbidden_authority_absent", False),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                forged = copy.deepcopy(value)
                mutate(forged)
                with self.assertRaises(self.module.ClosureError):
                    self.module.validate_effective_rootfs(
                        forged,
                        expected_init=init,
                        expected_child=child,
                        module_closure=self.closure,
                    )


if __name__ == "__main__":
    unittest.main()
