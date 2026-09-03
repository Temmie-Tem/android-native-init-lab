from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
PROCESS = ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
DESIGN = (
    ROOT
    / "docs/reports/"
    "S22PLUS_FYG8_P335_ATTENDED_RESIDENT_SESSION_DESIGN_H0_2026-09-04.md"
)


def compact(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class P335ResidentLeaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.target = compact(TARGET)
        cls.process = compact(PROCESS)
        cls.design = compact(DESIGN)

    def test_lease_is_nonterminal_and_rollback_owned(self) -> None:
        for phrase in (
            "ordinary F1 journal at `OBSERVED`",
            "intermediate nonterminal observation state",
            "not `RESIDENT_HEALTHY`",
            "Candidate replay and a replacement artifact remain forbidden",
            "only after exact rollback and final healthy rooted FYG8 Android return",
        ):
            self.assertIn(phrase, self.target)
        for phrase in (
            "ordinary journal pauses at `OBSERVED`",
            "`RECOVERY_DOWNLOAD` remains the sole next ordinary state",
            "exact preapproved rollback remains the sole later partition effect",
        ):
            self.assertIn(phrase, self.process)

    def test_lease_is_finite_attended_and_same_boot(self) -> None:
        for phrase in (
            "at most one attended hour and 16 named read-only actions",
            "unchanged nonzero per-boot identity",
            "an uncertain intent or dispatch is never replayed",
            "unexpected reboot",
            "attendance loss",
        ):
            self.assertIn(phrase, self.target)

    def test_catalog_does_not_claim_general_shell(self) -> None:
        for phrase in (
            "host runner never accepts a caller command, shell fragment, path, executable or environment",
            "three named commands",
            "adds no persistent file, Android service, interactive PTY, file transfer, generic shell authority",
            "grants no D0, D1, F1, device, Odin, or live authority",
        ):
            self.assertIn(phrase, self.target + " " + self.design)

    def test_durable_publication_precedes_guard_release(self) -> None:
        self.assertIn(
            "no-clobber lease and guard are durably published and directory-fsynced",
            self.target,
        )
        self.assertIn(
            "No named action can start before the complete lease exists",
            self.design,
        )

    def test_lease_has_one_timer_and_one_session_per_action(self) -> None:
        for phrase in (
            "`OBSERVED -> candidate_boot_ready -> lease/guard`",
            "`s22plus_fyg8_p335_resident_lease_v1`",
            "owns its monotonic one-hour deadline",
            "separate append-only action intent/result journal",
            "at most one authenticated session for each of the 16 lease actions",
            "not independent D1 or standing authority",
        ):
            self.assertIn(phrase, self.target)

    def test_campaign_ledger_accounting_includes_p335(self) -> None:
        self.assertIn("s22plus-fyg8-p335", self.target)
        self.assertIn(
            "no campaign-ledger closure row is written while the lease remains active",
            self.design,
        )


if __name__ == "__main__":
    unittest.main()
