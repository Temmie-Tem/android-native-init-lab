from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
DESIGN = (
    ROOT
    / "docs/reports/S22PLUS_FYG8_P336_LONG_IDLE_RESYNC_DESIGN_H0_2026-09-04.md"
)


def compact(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class P336ResyncContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.target = compact(TARGET)
        cls.design = compact(DESIGN)

    def test_one_open_bounded_preamble_contract(self) -> None:
        for phrase in (
            "P336 long-idle resident resynchronization",
            "Before a later P336 action reads a candidate preamble",
            "only complete exact P336 banner plus stage-zero diagnostic preambles",
            "only one OPEN, AUTH and command tuple",
            "finite byte-bounded series",
        ):
            self.assertIn(phrase, self.target + " " + self.design)

    def test_partial_failure_evidence_is_mandatory(self) -> None:
        for phrase in (
            "bounded partial TX/RX",
            "exact audit stage",
            "An uncertain result immediately selects the existing rollback owner",
            "failure before AUTH proving zero EXEC",
        ):
            self.assertIn(phrase, self.target + " " + self.design)

    def test_scope_does_not_expand(self) -> None:
        for phrase in (
            "P335 is consumed and grants no P336 session or replay authority",
            "adds no command, caller-selected shell, interactive PTY, file transfer",
            "no D0, D1, F1, device, recovery, replay or live authority",
        ):
            self.assertIn(phrase, self.target + " " + self.design)

    def test_closure_row_requirement_includes_p336(self) -> None:
        self.assertIn("`s22plus-fyg8-p335`, or `s22plus-fyg8-p336` F1 closure row", self.target)


if __name__ == "__main__":
    unittest.main()
