import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_order_authority.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_max77705_order_authority_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8Max77705OrderAuthorityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_unique_selected_order_uses_first_occurrence(self):
        result = self.module.unique_selected_order(
            ["a.ko", "b.ko", "a.ko", "c.ko"], {"a.ko", "c.ko"}
        )
        self.assertEqual(result, ["a.ko", "c.ko"])

    def test_dependency_violation_requires_dependency_before_consumer(self):
        dependencies = {"base.ko": (), "consumer.ko": ("base.ko",)}
        self.assertEqual(
            self.module.dependency_violations(["base.ko", "consumer.ko"], dependencies), []
        )
        violation = self.module.dependency_violations(
            ["consumer.ko", "base.ko"], dependencies
        )
        self.assertEqual(len(violation), 1)
        self.assertEqual(violation[0]["dependency"], "base.ko")

    def test_proposed_additions_are_dependency_ordered(self):
        self.assertEqual(
            self.module.PROPOSED_ADDITIONS,
            (
                "msm-geni-se.ko",
                "gpi.ko",
                "i2c-msm-geni.ko",
                "spu_verify.ko",
                "mfd_max77705.ko",
                "pdic_max77705.ko",
            ),
        )

    def test_plan_parser_rejects_non_61_shape(self):
        with self.assertRaises(self.module.OrderError):
            self.module.parse_plan('{"one.ko", "one", ""},\n')


if __name__ == "__main__":
    unittest.main()
