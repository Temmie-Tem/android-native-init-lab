from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p318_generator as generator  # noqa: E402
import s22plus_fyg8_p318_runtime_qualification as qualification  # noqa: E402


class P318RuntimeQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = qualification.audit(ROOT)

    def test_actual_runtime_and_gate_fixture_pass(self) -> None:
        self.assertEqual(cls_value := self.value["verdict"], qualification.VERDICT)
        self.assertTrue(self.value["gate_fixture"]["actual_gate_helper_executed"])
        self.assertEqual(self.value["gate_fixture"]["result"]["negative"], 5)
        self.assertTrue(self.value["userspace_a_b"]["byte_identical"])
        self.assertTrue(cls_value.startswith("PASS_P318_"))

    def test_module_counts_are_not_ambiguous(self) -> None:
        facts = self.value["generator"]
        self.assertEqual(facts["early_module_count"], 70)
        self.assertEqual(facts["late_diagnostic_payload_count"], 1)
        self.assertEqual(facts["effective_module_count"], 71)

    def test_gate_order_mutation_fails(self) -> None:
        source = (ROOT / generator.P317_RUNTIME).read_bytes()
        mutated = source.replace(
            b"    rc = p260_bind_udc();\n",
            b"    rc = p260_bind_udc(); /* moved */\n",
            1,
        )
        with self.assertRaises(generator.GeneratorError):
            generator._transform_p317_runtime(ROOT, mutated)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
