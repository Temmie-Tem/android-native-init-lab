"""Pin the recovered WSTA18/WSTA19 evidence for native Wi-Fi ownership.

The isolated-Debian architecture rests on native PID 1 surviving the handoff.
Read only through the current documents, that looks like the residue of an
experiment retired on cost, which invites the architecture to be reopened on
false grounds. It was in fact settled live on 2026-07-04 for a structural
reason. These tests keep the recovered citation, its mechanism, and its exact
limits attached to the record.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest


def flatten(text: str) -> str:
    """Collapse wrapping and blockquote markers.

    The report quotes its sources verbatim, and those quotes wrap across lines
    with a leading `> `. Asserting on the raw text would make the tests fail on
    reflowing rather than on the claim changing.
    """
    return " ".join(text.replace("> ", " ").split())


REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "docs/reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md"
WSTA18 = REPO / (
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md"
)
WSTA19 = REPO / (
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS"
    "_2026-07-04.md"
)
WSTA14 = REPO / (
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA14_LINKSTATE_SCAN_BLOCKED_2026-07-04.md"
)
GOAL = REPO / "GOAL_A90.md"


class RecoveredEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = flatten(REPORT.read_text(encoding="utf-8"))

    def test_the_cited_sources_still_exist(self) -> None:
        for path in (WSTA14, WSTA18, WSTA19):
            self.assertTrue(path.is_file(), str(path))

    def test_the_quoted_root_cause_is_still_in_wsta18(self) -> None:
        """The quote is the whole point; a paraphrase would not survive audit."""
        source = flatten(WSTA18.read_text(encoding="utf-8"))
        for fragment in (
            "firmware down indication",
            "Root PD shutdown",
            "WMI stop in progress",
            "cnss-daemon",
            "cnss_diag",
        ):
            self.assertIn(fragment, source, fragment)
            self.assertIn(fragment, self.report, fragment)

    def test_the_wsta19_conclusion_is_quoted_exactly(self) -> None:
        source = flatten(WSTA19.read_text(encoding="utf-8"))
        self.assertIn("WCNSS/WMI", source)
        self.assertIn("WCNSS/WMI", self.report)
        self.assertIn("wsta19-native-owned-chroot-wifi-boundary-pass", source)
        self.assertIn("wsta19-native-owned-chroot-wifi-boundary-pass", self.report)

    def test_the_failure_is_recorded_as_post_switch_root(self) -> None:
        """The tempting wrong reading is that native still held the interface."""
        self.assertIn("wifi-sta-assoc-failed", flatten(WSTA14.read_text(encoding="utf-8")))
        self.assertIn("with native userspace gone", self.report)
        self.assertIn("is false", self.report)

    def test_the_report_states_its_own_limits(self) -> None:
        self.assertIn("## What this does not settle", self.report)
        self.assertIn("re-materialize", self.report)

    def test_the_report_does_not_reopen_the_selected_closure(self) -> None:
        self.assertIn("NESTED_PID_NAMESPACE_ISOLATION", self.report)
        self.assertIn("does not reopen it", self.report)

    def test_no_authority_is_created(self) -> None:
        self.assertIn("Device or live effect: none", self.report)
        for token in ("D0", "D1", "F1"):
            self.assertIn(token, self.report)
        self.assertIn("authority is granted or implied", self.report)

    def test_the_goal_points_at_the_recovered_evidence(self) -> None:
        self.assertIn(REPORT.name, flatten(GOAL.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
