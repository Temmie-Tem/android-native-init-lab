"""Guard the methodology and error-taxonomy documents.

These tests follow the discipline the documents themselves recommend (M2):
they **recompute** every figure from the tree and compare it to the document,
rather than pinning the document's wording.  A test that asserts a string stays
green while the string is wrong, which is how a published census reached the
P3.19 report with the wrong population.

Monotonically growing corpora (reports, commits, ledger rows) are checked as
lower bounds, so the documents age honestly instead of rotting.  Defect counts
are checked exactly, in the direction that matters: they may fall, never rise.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODOLOGY = ROOT / "docs/operations/CAMPAIGN_METHODOLOGY_H0_2026-08-21.md"
TAXONOMY = ROOT / (
    "docs/reports/CAMPAIGN_ERROR_TAXONOMY_REVIEWER_AND_IMPLEMENTER_H0_2026-08-21.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
CHOREOGRAPHY_TEST = ROOT / "tests/test_s22plus_fyg8_p319_stock_choreography_docs.py"

CAUSE_HEADING = re.compile(
    r"^#+ *(root cause|cause|mechanism|what (went wrong|happened)|diagnosis"
    r"|failure|analysis)",
    re.IGNORECASE | re.MULTILINE,
)


def _incident_reports() -> list[Path]:
    reports = ROOT / "docs/reports"
    return sorted(
        p for p in reports.glob("*.md")
        if "INCIDENT" in p.name or "POSTMORTEM" in p.name
    )


def _dated_ledger_rows() -> list[list[str]]:
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if re.match(r"^20\d\d-", line):
            rows.append(line.split(" | "))
    return rows


class MethodologyDocsTest(unittest.TestCase):
    def setUp(self):
        self.methodology = METHODOLOGY.read_text(encoding="utf-8")
        self.taxonomy = TAXONOMY.read_text(encoding="utf-8")

    def _number(self, text: str, pattern: str) -> int:
        match = re.search(pattern, text)
        self.assertIsNotNone(match, f"figure not found: {pattern}")
        return int(match.group(1).replace(",", ""))

    # --- the documents must not claim authority -------------------------

    def test_neither_document_grants_authority(self):
        # An operations-directory document sitting beside the target contracts
        # must say plainly that it binds nothing, or it will eventually be
        # cited as permission.
        for name, text in (("methodology", self.methodology),
                           ("taxonomy", self.taxonomy)):
            with self.subTest(document=name):
                self.assertIn("Host-only", text)
                self.assertIn("no D0, D1, or F1 authority", text)
                self.assertIn("AGENTS.md", text)

    def test_documents_reference_each_other(self):
        self.assertIn("CAMPAIGN_METHODOLOGY_H0_2026-08-21.md", self.taxonomy)
        self.assertIn(
            "CAMPAIGN_ERROR_TAXONOMY_REVIEWER_AND_IMPLEMENTER_H0_2026-08-21.md",
            self.methodology,
        )

    # --- recomputed figures ---------------------------------------------

    def test_review_section_count_is_recomputed(self):
        source = CHOREOGRAPHY_TEST.read_text(encoding="utf-8")
        block = source.split("SECTION_ORDER = (", 1)[1].split("\n    )", 1)[0]
        actual = len(re.findall(r'^        "', block, re.MULTILINE))
        claimed = self._number(self.taxonomy, r"the (\d+) review sections pinned")
        self.assertEqual(claimed, actual)

    def test_incident_corpus_figures_are_recomputed(self):
        incidents = _incident_reports()
        with_heading = [p for p in incidents
                        if CAUSE_HEADING.search(p.read_text(encoding="utf-8"))]
        without = len(incidents) - len(with_heading)
        forms = {
            m.group(0).strip()
            for p in with_heading
            for m in CAUSE_HEADING.finditer(p.read_text(encoding="utf-8"))
        }
        self.assertEqual(
            self._number(self.methodology, r"Of the (\d+) incident reports"),
            len(incidents),
        )
        self.assertEqual(
            self._number(self.methodology,
                         r"\*\*(\d+) have no cause-section heading at"),
            without,
        )
        self.assertEqual(
            self._number(self.methodology, r"The (\d+) that do are split"),
            len(with_heading),
        )
        # Two metrics, because collapsing them is how the document first got
        # this wrong: "Root cause" and "Root cause and repair boundary" are one
        # keyword and two headings.
        full = {
            line.strip()
            for p in with_heading
            for line in p.read_text(encoding="utf-8").splitlines()
            if CAUSE_HEADING.match(line)
        }
        self.assertEqual(
            self._number(self.methodology, r"\*\*(\d+) distinct heading keywords"),
            len(forms), sorted(forms))
        self.assertEqual(
            self._number(self.methodology, r"\*\*(\d+)\ndistinct full headings"),
            len(full), sorted(full))

    def test_ledger_schema_figures_are_recomputed(self):
        rows = _dated_ledger_rows()
        nine = [r for r in rows if len(r) == 9]
        eight = [r for r in rows if len(r) == 8]
        claimed_total = self._number(self.taxonomy, r"Of (\d+) dated rows")
        claimed_nine = self._number(self.taxonomy, r"\*\*(\d+)\*\* carry the 9-field")
        # Total rows only grow; the document's figure is a lower bound.
        self.assertLessEqual(claimed_total, len(rows))
        self.assertLessEqual(claimed_nine, len(nine))
        # The malformed count is a defect count.  It may fall, never rise.
        claimed_eight = self._number(self.taxonomy, r"\*\*(\d+)\*\* carry 8")
        self.assertLessEqual(len(eight), claimed_eight, [r[:3] for r in eight])

    def test_corpus_scale_figures_are_lower_bounds(self):
        reports = len(list((ROOT / "docs/reports").glob("*.md")))
        tests = len(list((ROOT / "tests").glob("*.py")))
        s22 = len(_dated_ledger_rows())
        a90 = sum(
            1 for line in (ROOT / "docs/operations/CAMPAIGN_LEDGER_A90.md")
            .read_text(encoding="utf-8").splitlines() if re.match(r"^20\d\d-", line)
        )
        self.assertLessEqual(
            self._number(self.methodology, r"\*\*([\d,]+)\*\* reports"), reports)
        self.assertLessEqual(
            self._number(self.methodology, r"\*\*([\d,]+)\*\* test files"), tests)
        self.assertLessEqual(
            self._number(self.methodology, r"\*\*([\d,]+)\*\* ledger rows"), s22 + a90)

    def test_commit_count_is_a_lower_bound(self):
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertLessEqual(
            self._number(self.methodology, r"\*\*([\d,]+)\*\* commits since"),
            int(result.stdout.strip()),
        )

    # --- the load-bearing claims ----------------------------------------

    def test_taxonomy_keeps_the_two_error_profiles_separate(self):
        for token in (
            "# Part 1 — Reviewer errors (Claude)",
            "# Part 2 — Implementer errors (Codex / Luna MAX)",
            "# Part 3 — The comparison, which is the point",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.taxonomy)

    def test_taxonomy_states_the_central_split(self):
        # The one sentence this document exists to produce.  If it is ever
        # removed the rest is just a list of mistakes.
        flat = re.sub(r"\s+", " ", self.taxonomy)
        for token in (
            "Findings about *binding* and *proposition* are almost always accepted.",
            "Findings about *mechanism* are usually rejected.",
            "the reviewer should attack the binding and the proposition, and\nshould not attack the mechanism without opening the artifact first",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), flat)

    def test_methodology_marks_its_own_downgrades(self):
        # A recommendation list that only recommends is a wish list.  Two
        # imports are explicitly argued down, and that has to survive edits.
        flat = re.sub(r"\s+", " ", self.methodology)
        for token in (
            "*honest downgrade*",
            "**Do not do this now**",
            "Items 6 through 9 are free and unadopted. Start there.",
        ):
            with self.subTest(token=token):
                self.assertIn(re.sub(r"\s+", " ", token), flat)

    def test_methodology_ranks_every_import_it_introduces(self):
        # Every X-numbered import must appear in the ranked table or be
        # explicitly downgraded, so nothing is introduced and then dropped.
        introduced = set(re.findall(r"^### (X\d+)\.", self.methodology, re.MULTILINE))
        table = self.methodology.split("## Part 5", 1)[1]
        ranked = set(re.findall(r"\*\*(X\d+)", table))
        downgraded = {
            m for m in introduced
            if re.search(rf"### {m}\..*?\*honest downgrade\*", self.methodology)
            or re.search(rf"### {m}\.[^#]*?\*\*Do not do this now\*\*",
                         self.methodology, re.DOTALL)
        }
        self.assertEqual(introduced - ranked - downgraded, set())


if __name__ == "__main__":
    unittest.main()
