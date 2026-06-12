# Sub-goal: host-only regression test harness for the analysis tooling

A **host-only, no-device sub-goal** referenced by the root `GOAL.md` autonomous loop —
safe filler between device iterations. This file is the source of truth + progress
ledger: the objective, the runner contract, and a coverage checklist the agent checks
off one target at a time. See root `AGENTS.md` for the hard rules. When working this
sub-goal, commit scope is `git add tests/` only, one target per commit.

## Objective

Build a Python `unittest` regression suite under `tests/` that pins the behavior
of the repository's **host-only** analyzers and shared harness library, so future
refactors are protected. Pure/deterministic functions only — no device, no live
data required.

## Definition of done

Every target in the checklist below is `[x]`, each covered by a green
`tests/test_*.py`, and `python3 -m unittest discover -s tests -p 'test_*.py'`
passes with `fail=0`. When all targets are checked, mark the goal achieved.

## Runner

- Run all: `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- Import helper: `tests/_loader.py`
  - `load_harness("path_safety")` → import `a90harness.<name>` (shared library).
  - `load_revalidation("a90_kernel_v2199_timer_xref_scorer")` → load a standalone
    revalidation analyzer script by file name (importlib, not an installed pkg).
  - `load_script("workspace/.../foo.py")` → load any repo script by relative path.
- New test modules `import` from `_loader` directly (unittest discover puts the
  `tests/` dir on `sys.path`).

## Working agreement (one unit per commit)

For each iteration: pick the first unchecked target → read its source to
characterize **actual** behavior → write `tests/test_<name>.py` (stdlib
`unittest`) covering its pure functions incl. edge/reject cases → run it green →
flip the checkbox to `[x]` and add a Progress-log line → **commit only `tests/`
and this file**. One target per commit, so any unit is easy to revert.

## Coverage checklist  (first unchecked = next unit)

Priority: safety-critical shared library first, then analyzers with clear pure
functions.

- [x] `workspace/public/src/harness/a90harness/path_safety.py` — require_safe_component,
      normalize_device_path, require_path_under, require_run_child, require_safe_raw_arg.
      Cover accepted inputs AND reject cases (traversal `..`, relative, `//`, trailing
      `/`, whitespace, shell metachars, control/NUL) that must raise RuntimeError.
- [ ] `workspace/public/src/scripts/revalidation/a90_kernel_v2199_timer_xref_scorer.py`
      — format_signed_hex, clean_expr, timer_leaf, interval_class, interval_score,
      score_xref, score_candidate.
- [ ] `workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py`
      — as_int, extract_ts, flatten_json, event_group, parse_legacy_nonlog_key,
      split_group_event, group_to_surface, aggregate.
- [ ] `workspace/public/src/scripts/revalidation/a90_kernel_v2198_jopp_ropp_classifier.py`
      — pure parse/scoring helpers (discover the deterministic ones).
- [ ] `workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py`
      — token/offset decode + layout-validation helpers (pure parts only).
- [ ] `workspace/public/src/scripts/revalidation/a90_kernel_stack_symbolize.py`
      — slide / scoring helpers (pure parts only).
- [ ] `workspace/public/src/scripts/revalidation/native_kernel_a90_uprobe_trace_postprocess_v2221.py`
      — parse_stdout_json, load_json.
- [ ] `workspace/public/src/harness/a90harness/schema.py` — pure validators (discover).
- [ ] (append more as discovered: a90harness gate.py / evidence.py / failure.py,
      and v2203 / v2204 / v2205 / v2207 / v2208 / v2209 / v2210 analyzers.)

## Progress log

- 2026-06-12 — `a90harness/path_safety.py` — all 5 validators (require_safe_component,
  normalize_device_path, require_path_under, require_run_child, require_safe_raw_arg),
  accept + reject paths — 19 cases — green. Note: `normalize_device_path("/")` raises
  (bare root splits to an empty segment); pinned as current behavior, not a divergence.
- (append: date — target — functions covered — test count — any `KNOWN-DIVERGENCE`.)
