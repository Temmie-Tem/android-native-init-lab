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
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2199_timer_xref_scorer.py`
      — format_signed_hex, clean_expr, timer_leaf, interval_class, interval_score,
      score_xref, score_candidate.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py`
      — as_int, extract_ts, flatten_json, event_group, parse_legacy_nonlog_key,
      split_group_event, group_to_surface, aggregate.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2198_jopp_ropp_classifier.py`
      — pure parse/scoring helpers (discover the deterministic ones).
- [x] `workspace/public/src/scripts/revalidation/a90_stock_kallsyms_extract.py`
      — token/offset decode + layout-validation helpers (pure parts only).
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_stack_symbolize.py`
      — slide / scoring helpers (pure parts only).
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_uprobe_trace_postprocess_v2221.py`
      — parse_stdout_json, load_json.
- [x] `workspace/public/src/harness/a90harness/schema.py` — result dataclass
      serialization and failure rollups.
- [x] `workspace/public/src/harness/a90harness/gate.py` — GateOptions,
      GateResult, evaluate_gate.
- [x] `workspace/public/src/harness/a90harness/evidence.py` — safe artifact
      labels/paths, bounded readers, private/public writers, EvidenceStore.
- [x] `workspace/public/src/harness/a90harness/failure.py` — workload/
      observer failure classification and mixed-soak summary.
- [x] `workspace/public/src/harness/a90harness/module.py` — StepResult,
      ModuleOutcome, TestModule metadata/defaults/artifacts, run_step.
- [x] `workspace/public/src/harness/a90harness/observer.py` —
      ObserverSample/Summary serialization, text_excerpt, observe_cycle,
      run_observer stop paths.
- [x] `workspace/public/src/harness/a90harness/runner.py` —
      ModuleRunner context wiring, step orchestration, observer result handling.
- [x] `workspace/public/src/harness/a90harness/bundle.py` —
      BundleFile serialization, bundle file inventory, README rendering,
      finalize_bundle manifest/index writes.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2203_timer_row_source_matcher.py`
      — timer row signature/scoring, source xref extraction, minimal analyze fixture.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_file_ops_anchor_v2204.py`
      — StepResult/sha256 helpers, probe/System.map parsing,
      file_operations slide analysis, residual/report rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2205_exact_slide_resymbolization_audit.py`
      — System.map parsing, runtime symbolization, V2195/V2202 mapping,
      legacy context loading, result classification, report rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2207_jopp_stub_mapper.py`
      — scalar/image helpers, instruction decoding, entry/static mapping,
      V2206/config/RKP inputs, analyze fixture, report rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2208_rela_fops_discriminator.py`
      — scalar/System.map/raw helpers, RELA discovery/scoring,
      rebuilt/source contrast, analyze fixture, report rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2209_fops_clone_semantic_mapper.py`
      — scalar/System.map/raw helpers, RELA/source initializer parsing,
      file_operations offset derivation, semantic map analysis, report rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2210_generic_fops_rela_inventory.py`
      — scalar/System.map/source/raw helpers, RELA discovery/clone-base scoring,
      generic fops inventory analysis, report rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2211_ropp_stack_recovery_audit.py`
      — scalar/System.map/raw helpers, BL/callsite decoding, stack slide rows,
      joint-key solving, source evidence, report rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_raw_frame_slots_v2212.py`
      — helper stdout parsing, address classification, probe analysis,
      live report rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_raw_frame_sample_ring_v2213.py`
      — sample-ring stdout parsing, address classification, convergence metrics,
      probe analysis, live report rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_perf_regs_frame_sample_ring_v2214.py`
      — perf-regs sample-ring stdout parsing, address classification,
      stock-map symbolization helpers, convergence metrics, report rendering.
- [ ] (append more as discovered: v2215+ analyzers.)

## Progress log

- 2026-06-12 — `a90harness/path_safety.py` — all 5 validators (require_safe_component,
  normalize_device_path, require_path_under, require_run_child, require_safe_raw_arg),
  accept + reject paths — 19 cases — green. Note: `normalize_device_path("/")` raises
  (bare root splits to an empty segment); pinned as current behavior, not a divergence.
- 2026-06-13 — `a90_kernel_v2199_timer_xref_scorer.py` — format_signed_hex,
  clean_expr, timer_leaf, interval_class, interval_score, score_xref,
  score_candidate — 9 cases — green. Also fixed `tests/_loader.py` to register
  standalone scripts in `sys.modules` before exec so dataclass-based analyzers
  import correctly.
- 2026-06-13 — `a90_kernel_v2220_helper_summary_trace_parser.py` — as_int,
  extract_ts, flatten_json, event_group, parse_legacy_nonlog_key,
  split_group_event, group_to_surface, aggregate — 7 cases — green.
- 2026-06-13 — `a90_kernel_v2198_jopp_ropp_classifier.py` — parse_int,
  format_signed_hex, nearest_symbol, build_symbol_index, read_u32,
  find_magic_addresses, is_bl/is_blr/decode_bl_target, classify_function_entry,
  parse_stack_logs, parse_timer_logs, extract_timer_callback_candidates,
  callback_confidence, timer_magic_candidate_slides, score_timer_slide,
  score_stack_slide — 9 cases — green.
- 2026-06-13 — `a90_stock_kallsyms_extract.py` — sha256_bytes, u16/u32/u64,
  unwrap_kernel, printable_token, parse_token_run, token_table_at,
  marker_candidate, parse_record_offsets, decode_names, find_num_syms_position,
  find_address_table, render_system_map — 12 cases — green.
- 2026-06-13 — `a90_kernel_stack_symbolize.py` — parse_int,
  parse_system_map, parse_stack_log, parse_timer_log, nearest_symbol,
  build_symbol_index, candidate_slides, score_slide — 7 cases — green.
- 2026-06-13 — `native_kernel_a90_uprobe_trace_postprocess_v2221.py` —
  parse_stdout_json, load_json — 8 cases — green.
- 2026-06-13 — `a90harness/schema.py` — CheckResult, CommandRecord,
  HarnessResult `to_dict` serialization and failure rollups — 5 cases — green.
- 2026-06-13 — `a90harness/gate.py` — GateOptions, GateResult,
  evaluate_gate allow/block decisions, required flags, metadata serialization —
  4 cases — green.
- 2026-06-13 — `a90harness/evidence.py` — safe_artifact_label, path
  builders, workspace private roots, private/public writers, bounded readers,
  EvidenceStore — 10 cases — green.
- 2026-06-13 — `a90harness/failure.py` — FailureClassification,
  classify_workload_event, classify_observer_sample, load_observer_samples,
  summarize_classifications, classify_mixed_soak — 13 cases — green.
- 2026-06-13 — `a90harness/module.py` — StepResult, ModuleOutcome,
  TestModule metadata/defaults/artifacts, run_step duration and exception
  paths — 9 cases — green.
- 2026-06-13 — `a90harness/observer.py` — ObserverSample, ObserverSummary,
  text_excerpt, observe_cycle default-command sampling, run_observer
  max-cycles/stop-event summaries — 7 cases — green.
- 2026-06-13 — `a90harness/runner.py` — ModuleRunner context wiring,
  module step orchestration, artifact/result writing, step failure capture,
  optional observer failure propagation — 3 cases — green.
- 2026-06-13 — `a90harness/bundle.py` — BundleFile, collect_bundle_files,
  render_bundle_readme, finalize_bundle manifest/summary/README/index writes,
  symlink rejection — 6 cases — green.
- 2026-06-13 — `a90_kernel_v2203_timer_row_source_matcher.py` — parse_int,
  row_signature, fast_extract_timer_xrefs, score_row_mapping,
  candidate_source_roots, render_markdown, analyze minimal source-backed
  fixture — 8 cases — green.
- 2026-06-13 — `native_kernel_file_ops_anchor_v2204.py` — StepResult,
  sha256_file, format_signed_hex, parse_key_values, parse_int,
  parse_probe_stdout, parse_system_map, analyze_fops, residual_state,
  render_report — 10 cases — green.
- 2026-06-13 — `a90_kernel_v2205_exact_slide_resymbolization_audit.py` —
  signed_hex, parse_system_map, nearest_symbol, symbolize_runtime,
  parse_stack_ips, load_exact_slide, map_v2195_stack, map_v2202_rows,
  load_legacy_context, classify_result, render_markdown — 11 cases — green.
- 2026-06-13 — `a90_kernel_v2207_jopp_stub_mapper.py` — parse_int,
  hex64, hex_signed, parse_system_map, build_symbol_index, nearest_symbol,
  load_kernel, load_synthetic_base, raw_offset, read_u32/read_u64,
  decode_branch_target, classify_insn, instruction_window, entry_profile,
  static_mapping, parse_v2206_members, parse_required_config,
  inspect_rkp_source, load_v2197_slide_context, analyze, render_table,
  render_markdown — 11 cases — green.
- 2026-06-13 — `a90_kernel_v2208_rela_fops_discriminator.py` —
  parse_int, hex64, hex_signed, parse_system_map, build_symbol_index,
  nearest_symbol, load_kernel_raw, load_synthetic_base, looks_like_kernel_va,
  is_stock_rela_record, discover_stock_rela, build_rela_addend_index,
  live_value, score_slides, parse_elf_rela_dyn, rebuilt_rela_comparison,
  source_initializer_evidence, analyze, render_table, render_markdown —
  14 cases — green.
- 2026-06-13 — `a90_kernel_v2209_fops_clone_semantic_mapper.py` —
  parse_int, hex64, hex_signed, parse_system_map, build_symbol_index,
  nearest_symbol, load_kernel_raw, load_synthetic_base, looks_like_kernel_va,
  is_stock_rela_record, discover_stock_rela, parse_config_symbols,
  strip_inactive_config_blocks, parse_file_operations_offsets, parse_macros,
  resolve_alias, parse_fops_initializers, parse_elf_rela_dyn, read_u32,
  landing_profile, live_value, object_bases_from_v2208, analyze, render_table,
  semantic_targets_for_runtime, render_markdown — 9 cases — green.
- 2026-06-13 — `a90_kernel_v2210_generic_fops_rela_inventory.py` —
  parse_int, hex64, hex_signed, parse_system_map, build_symbol_index,
  parse_config_symbols, strip_inactive_config_blocks, parse_macros,
  resolve_alias, parse_file_operations_offsets, parse_fops_initializers,
  load_kernel_raw, load_synthetic_base, looks_like_kernel_va,
  is_stock_rela_record, discover_stock_rela, parse_elf_rela_dyn,
  find_clone_base, analyze, render_table, render_markdown — 9 cases — green.
- 2026-06-13 — `a90_kernel_v2211_ropp_stack_recovery_audit.py` —
  parse_int, hex64, hex_signed, parse_system_map, build_symbol_index,
  nearest_symbol, load_kernel_raw, load_synthetic_base, parse_config_symbols,
  read_u32, is_bl, decode_bl_target, build_callsite_map, candidate_slides,
  stack_rows_for_slide, solve_joint_keys, source_evidence, analyze,
  render_table, render_markdown — 9 cases — green.
- 2026-06-13 — `native_kernel_raw_frame_slots_v2212.py` —
  parse_int, parse_helper_stdout, classify_addr, analyze_probe,
  render_report — 7 cases — green.
- 2026-06-13 — `native_kernel_raw_frame_sample_ring_v2213.py` —
  parse_int, parse_helper_stdout, classify_addr, analyze_probe,
  render_report — 7 cases — green.
- 2026-06-13 — `native_kernel_perf_regs_frame_sample_ring_v2214.py` —
  parse_int, parse_helper_stdout, classify_addr, load_text_symbols,
  nearest_symbol, symbolize_counter, analyze_probe, render_report —
  7 cases — green.
- (append: date — target — functions covered — test count — any `KNOWN-DIVERGENCE`.)
