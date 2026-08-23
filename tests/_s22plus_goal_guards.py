"""Shared semantic guards for the current S22+ P3.19 frontier wording."""

from __future__ import annotations


def assert_current_p319_qualification_boundary(testcase, goal: str) -> None:
    """Bind the authority tuple without pinning one prose serialization."""

    lines = goal.splitlines()

    def unique_line(anchor: str) -> str:
        matches = [line for line in lines if anchor in line]
        testcase.assertEqual(len(matches), 1)
        return matches[0]

    frontier = unique_line("The forward frontier has moved off")
    stage_a = unique_line("Historical Stage-A evidence retains")
    authority_lines = [line for line in lines if "`-48`/`-49`/`-08`" in line]
    testcase.assertEqual(authority_lines, [frontier, stage_a])
    current_lines = [line for line in lines if "`-52`/`-53`/`-10`" in line]
    testcase.assertEqual(current_lines, [frontier, stage_a])

    for line in (frontier, stage_a):
        testcase.assertIn("`-48`/`-49`/`-08`", line)
        testcase.assertIn("independently reviewed", line)
        testcase.assertIn("H0-only `PASS_GO`", line)
        testcase.assertIn("no ready/run manifest", line)
        testcase.assertIn("live authority", line)

    testcase.assertIn("reviewed stock-witness runtime/build closure", frontier)
    testcase.assertIn("binds all 437 current source keys", frontier)
    testcase.assertIn("`IMPLEMENTED_REVIEW_PENDING` under topic 34", frontier)
    testcase.assertIn("only on `FRESH_BASELINE_MISSING`", frontier)
    testcase.assertIn("runner-consumed global candidate registry", frontier)
    testcase.assertIn("typed module-plan binding", stage_a)
    testcase.assertIn("`IMPLEMENTED_REVIEW_PENDING`", stage_a)
    testcase.assertIn("is not PASS_GO", stage_a)
    testcase.assertIn("P3.19", stage_a)
    testcase.assertIn("`BLOCKED_P319_PROCESS_V2_INTEGRATION_H0`", stage_a)
