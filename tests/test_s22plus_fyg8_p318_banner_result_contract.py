from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_banner_result_contract.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_banner_contract", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 banner-result contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318BannerResultContractTest(unittest.TestCase):
    def inputs(self):
        return {
            "materialized_data": (ROOT / P318.DEFAULT_MATERIALIZED).read_bytes(),
            "p260_data": (ROOT / P318.DEFAULT_P260_RUNTIME).read_bytes(),
            "envelope_data": (ROOT / P318.DEFAULT_P317_ENVELOPE).read_bytes(),
            "extractor_data": SCRIPT.read_bytes(),
        }

    def test_current_blind_spot_and_successor_design_are_exact(self):
        result = P318.build_contract(**self.inputs())
        self.assertEqual(result["verdict"], P318.VERDICT)
        self.assertTrue(result["current"]["terminal_before_banner"])
        self.assertTrue(result["current"]["banner_return_discarded"])
        self.assertFalse(result["current"]["terminal_can_retain_banner_result"])
        self.assertEqual(
            result["successor"]["status"], "DESIGN_ONLY_NOT_IMPLEMENTED"
        )
        self.assertTrue(
            result["successor"]["schema"]["new_envelope_version_required"]
        )
        self.assertFalse(result["scope"]["p318_candidate_ready"])

    def test_terminal_banner_order_mutation_fails(self):
        values = self.inputs()
        terminal = b"s22_max77705_checkpoint_payload_terminal_position("
        banner = b"if (tty_fd >= 0) (void)p260_write_banner(tty_fd);"
        start = values["materialized_data"].index(
            b"static __attribute__((noreturn)) void p317_publish("
        )
        terminal_at = values["materialized_data"].index(terminal, start)
        banner_at = values["materialized_data"].index(banner, terminal_at)
        mutated = bytearray(values["materialized_data"])
        mutated[terminal_at : terminal_at + len(terminal)] = b"X" * len(terminal)
        mutated[banner_at : banner_at + len(banner)] = b"Y" * len(banner)
        values["materialized_data"] = bytes(mutated)
        with self.assertRaisesRegex(P318.BannerContractError, "source seam"):
            P318.build_contract(**values)

    def test_discarded_return_mutation_fails(self):
        values = self.inputs()
        old = b"if (tty_fd >= 0) (void)p260_write_banner(tty_fd);"
        new = b"if (tty_fd >= 0) p260_write_banner(tty_fd);".ljust(
            len(old), b" "
        )
        values["materialized_data"] = values["materialized_data"].replace(
            old, new, 1
        )
        with self.assertRaisesRegex(P318.BannerContractError, "discarded banner"):
            P318.build_contract(**values)

    def test_eagain_deadline_mutation_fails(self):
        values = self.inputs()
        values["p260_data"] = values["p260_data"].replace(
            b"if (rc == -EAGAIN && retry_eagain)",
            b"if (rc == -EAGAIN)                ",
            1,
        )
        with self.assertRaisesRegex(P318.BannerContractError, "source seam"):
            P318.build_contract(**values)

    def test_short_write_accounting_mutation_fails(self):
        values = self.inputs()
        values["p260_data"] = values["p260_data"].replace(
            b"written += (size_t)rc;", b"written = (size_t)rc; ", 1
        )
        with self.assertRaisesRegex(P318.BannerContractError, "source seam"):
            P318.build_contract(**values)

    def test_all_four_outcomes_have_boundary_preimages(self):
        successor = P318.successor_contract()
        preimages = successor["arming"]["positive_preimages"]
        self.assertEqual({item["outcome"] for item in preimages}, set(P318.OUTCOMES))
        self.assertEqual(
            [item["bytes_written"] for item in preimages if item["outcome"] == "partial"],
            [1, 48],
        )
        self.assertEqual(successor["attempt"]["count"], 1)
        self.assertTrue(successor["attempt"]["retry_after_terminal_forbidden"])


if __name__ == "__main__":
    unittest.main()
