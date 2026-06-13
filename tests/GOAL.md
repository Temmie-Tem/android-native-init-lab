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
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2215_perf_regs_ropp_jopp_classifier.py`
      — scalar/System.map/raw helpers, function ranges, slide intervals,
      BL callsite maps, slide/no-slide classifiers, ROPP decode audit,
      report rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_perf_regs_codeword_sample_ring_v2216.py`
      — perf-regs codeword stdout parsing, address/symbol helpers,
      stock raw/meta reads, generated slide discovery, codeword match
      analysis, probe metrics, report rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2217_exact_slide_resymbolization_audit.py`
      — exact slide extraction, System.map/raw helpers, instruction
      classification, function ranges, callsite maps, live register
      resymbolization, ROPP decode audit, report rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_wlan_tracepoint_catalog_v2218.py`
      — cmdv1 output cleanup, trace event parsing/categorization,
      tracepoint format field parsing, System.map symbolization,
      trace extract output parsing, residual state, StepResult.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_uprobe_trace_buffer_collector_v2219.py`
      — cmdv1 output cleanup, event-state parsing, event-name mapping,
      trace-argument parsing, trace-line parsing/group inference, hit summary,
      residual state, StepResult.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_preflight_v2222.py`
      — JSON extraction, protocol rc parsing, regex value extraction,
      helper inventory parsing, a90ctl command construction, contract
      rendering, residual state, StepResult.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_plan_v2223.py`
      — SHA/JSON helpers, latest preflight discovery, helper source marker
      audit, boot image inventory, contract loading, capture-plan rendering,
      residual state.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2224_a90_boot_window_observer.py`
      — V2189 wrapper argument rewrites, report rendering, manifest version-axis
      normalization.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_handoff_v2225.py`
      — SHA/build-manifest helpers, a90ctl/flash command rendering, dry-run plan,
      artifact diagnosis, result classification, report rendering, residual state.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2226_a90_boot_window_property_root.py`
      — V2189 wrapper argument rewrites, v726 property-root route, report rendering,
      manifest version-axis normalization.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_boot_window_handoff_v2227.py`
      — SHA/build-manifest helpers, command rendering, artifact diagnosis,
      current-window preflight classifiers, result classification, report rendering,
      residual state.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2228_service_object_visible_observer.py`
      — V2189 wrapper argument rewrites, service-object-visible helper route,
      report rendering, manifest version-axis normalization.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_service_object_visible_handoff_v2229.py`
      — SHA/build-manifest helpers, command rendering, artifact diagnosis,
      service-object snapshot extraction, current-window preflight classifiers,
      result classification, report rendering, residual state.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2230_service_object_visible_post_bdf_hold.py`
      — V2189 wrapper argument rewrites, long post-BDF hold window,
      report rendering, manifest version-axis normalization.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_post_bdf_hold_handoff_v2231.py`
      — SHA/build-manifest helpers, command rendering, artifact diagnosis,
      current-window preflight classifiers, result classification, report rendering,
      residual state.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2232_service_object_fwclass_bridge.py`
      — helper bridge flag deduplication/propagation, V2230 wrapper argument
      rewrites, report rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_a90_service_object_fwclass_bridge_handoff_v2233.py`
      — SHA/build-manifest helpers, command rendering, artifact diagnosis including
      post-FW_READY boot_wlan / firmware_class / ICNSS snapshots, current-window
      preflight classifiers, result classification, report rendering, residual state.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2236_strict_wifi_connect.py`
      — helper bridge flag deduplication/propagation, V2230 wrapper argument
      rewrites, strict-connect report rendering.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2237_supplicant_terminate_poll.py`
      — helper bridge flag deduplication/propagation, V2230 wrapper argument
      rewrites, supplicant terminate-poll report rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_static_tracepoint_object_chain_audit_v2238.py`
      — cmdv1 cleanup, macro argument parsing, trace block extraction, pointer
      parameter/source/live format parsing, object-chain feasibility classification,
      residual state.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2239_scalar_uprobe_timeline.py`
      — key edge extraction, delta computation, parser-summary loading,
      outcome inference, delta statistics, scalar/uprobe contract rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2240_codepath_identity_boundary.py`
      — address-domain classification, a90 uprobe sample extraction, low12 and
      relative-offset signatures, kernel/user identity-boundary summary rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2241_user_uprobe_offset_base_map.py`
      — helper-source uprobe spec parsing, runtime probe extraction,
      load-bias observation/missing/alias classification, ELF metadata fallback,
      offset/base-map summary rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2242_user_elf_offset_context.py`
      — LOAD segment modeling, observed spec filtering, offset context issue
      classification, private context writer metadata, user-ELF context summary.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2243_user_uprobe_semantic_classifier.py`
      — disassembly line parsing, target/neighbor lookup, instruction/event-role
      classes, role alignment, context classification, semantic summary rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2244_semantic_timeline_merger.py`
      — semantic key-event lookup, evidence-strength bucketing, edge merge,
      per-run strength summary, cross-run outcome comparison, merged summary output.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2245_post_fwready_tail_inventory.py`
      — helper key-value parsing, tail-key counts, target-stack extraction,
      post-FWREADY stage classification, run comparison, inventory summary output.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2246_post_fwready_tail_symbol_source_map.py`
      — hex/System.map/source helpers, target-stack extraction, row mapping,
      pass/review summary output.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2247_tail_pc_lr_scorer.py`
      — exact-slide extraction, target range loading, sample address extraction,
      PC/LR hit scoring, pass/no-slide/no-target summary output.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2248_tail_capture_insertion_audit.py`
      — source-line matching, helper/build/sampler anchor extraction,
      tail-capture contract rendering, pass/fail summary output.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2249_tail_perf_sampler_hook.py`
      — tail sampler flag deduplication/propagation, V2237 wrapper argument
      rewrites, ramdisk helper injection, report rendering, manifest metadata.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2250_tail_perf_sampler_full_print.py`
      — full-print tail sampler flag propagation, V2237 wrapper argument
      rewrites, ramdisk helper injection, report rendering, manifest metadata.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_v2251_tail_target_evidence_classifier.py`
      — helper stack/feeder parsing, scorer summary normalization,
      deterministic tail evidence classification, evidence metadata output.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2252_fwclass_boundary_stack.py`
      — boundary-stack flag propagation, V2237 wrapper argument rewrites,
      report contract, manifest/promotion metadata.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_fwclass_boundary_stack_handoff_v2253.py`
      — key-value parsing, phase/boundary classification, dry-run command
      rendering, manifest classification, report/residual-state rendering.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2254_wifi_detail_surface.py`
      — V2237 wrapper argument rewrites, T2/read-only surface report contract,
      manifest/promotion metadata.
- [x] `workspace/public/src/scripts/revalidation/native_wifi_detail_surface_handoff_v2255.py`
      — Wi-Fi status/screenapp parsing, read-only action detection,
      dry-run command rendering, manifest classification, report/residual-state
      rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_workqueue_fwclass_oracle_plan_v2272.py`
      — workqueue/firmware source evidence checks, firmware tracepoint absence
      detection, candidate readiness classification, text rendering.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2273_workqueue_fwclass_func_sampler.py`
      — workqueue sampler flag propagation, V2237 wrapper argument rewrites,
      ramdisk helper injection, report rendering, manifest/live-candidate
      metadata.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2274_workqueue_codeword_combined.py`
      — combined workqueue/codeword sampler flag propagation, V2237 wrapper
      argument rewrites, dual ramdisk helper injection, report rendering,
      manifest/live-candidate metadata.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_workqueue_codeword_handoff_v2275.py`
      — workqueue log parsing, same-boot codeword slide classification,
      dry-run command rendering, manifest decisions, report/residual-state
      rendering.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_v2276_codeword_mismatch_postprocess.py`
      — UAO runtime-patch instruction classification, codeword mismatch row
      analysis, workqueue classification with a fixed slide, patch-aware
      decision branches.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2277_workqueue_exec_stack.py`
      — execute-start stack sampler flag propagation, V2237 wrapper argument
      rewrites, dual ramdisk helper injection, report rendering, manifest/
      live-candidate metadata.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_workqueue_exec_stack_handoff_v2278.py`
      — execute-start stack log parsing, same-boot codeword slide classification,
      dry-run command rendering, manifest decisions, report/residual-state
      rendering.
- [x] `workspace/public/src/scripts/revalidation/build_native_init_boot_v2279_workqueue_exec_wide.py`
      — wide execute-start sampler flag propagation, V2237 wrapper argument
      rewrites, dual ramdisk helper injection, report rendering, manifest/
      live-candidate metadata.
- [x] `workspace/public/src/scripts/revalidation/native_kernel_workqueue_exec_wide_handoff_v2280.py`
      — wide execute-start log parsing, same-boot codeword slide classification,
      dry-run command rendering, manifest decisions, report/residual-state
      rendering.
- [x] `workspace/public/src/scripts/revalidation/native_wifi_v2254_hold_reconnect_handoff_v2282.py`
      — credential-gated V2254 hold/reconnect preflight, dry-run command
      rendering, manifest decisions, secret redaction, report rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_transport.py`
      — phase timers, residual state, bridge command rendering, serial recovery
      classification, NCM readiness/repair compaction, transport selection.
- [x] `workspace/public/src/scripts/revalidation/a90_ncm_transport.py`
      — key/value parsing, host NCM candidate selection/snapshot parsing,
      NetworkManager link-local repair decisions, secret scanning, upload archive
      validation.
- [x] `workspace/public/src/scripts/revalidation/a90ctl.py`
      — cmdv1/cmdv1x argument encoding, wire-input modes, A90P1 protocol
      parsing/validation, retry policy, JSON result rendering.
- [x] `workspace/public/src/harness/a90harness/scheduler.py`
      — resource-lock derivation, default workload selection, seeded schedule
      construction, document/result serialization, mixed-soak event accounting.
- [x] `workspace/public/src/harness/a90harness/device.py`
      — direct/broker backend validation, metadata, command record generation,
      broker payload construction, exception capture, exclusive lock reentrancy.
- [x] `workspace/public/src/scripts/revalidation/a90_serial_lock.py`
      — explicit/default lock path selection, env timeout parsing, metadata
      write/clear behavior, busy timeout handling, exit no-op safety.
- [x] `workspace/public/src/scripts/revalidation/native_init_frontier_select.py`
      — read_text/read_json, marker helpers, T1 readiness filtering,
      track evaluation branches, select_frontier path/decision handling.
- [x] `workspace/public/src/scripts/revalidation/inventory_revalidation_scripts.py`
      — classification, live-device detection, import detection,
      direct-a90ctl grouping, consolidation signals, inventory generation,
      markdown rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_kernel_tools.py`
      — repo path resolution, host metadata capture, cmdv1 capture wrapping,
      manifest truncation, cmdv1 text cleanup, kernel config parsing,
      markdown rendering, config fetch glue.
- [x] `workspace/public/src/scripts/revalidation/a90_ncm_host_preflight.py`
      — IPv4 validation, command/service wrappers, IPv4 parsing,
      interface classification, template rendering/writing, decision branches,
      summary/manifest rendering.
- [x] `workspace/public/src/scripts/revalidation/a90_ncm_transport_smoke.py`
      — size parsing, deterministic pattern-file generation, PATH lookup,
      bounded NetworkManager repair recording, raw upload stream success/fail
      classification.
- [ ] (append more as discovered: v2231+ analyzers.)

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
- 2026-06-13 — `a90_kernel_v2215_perf_regs_ropp_jopp_classifier.py` —
  parse_int, hex64, hex_signed, parse_system_map, build_symbol_index,
  nearest_symbol, load_kernel_raw, load_synthetic_base, read_u32, is_bl,
  decode_bl_target, build_function_ranges, function_lookup, union_intervals,
  top_slide_intervals, build_callsite_map, candidate_slides_from_intervals,
  score_slide, classify_no_slide, classify_under_slide, ropp_decode_audit,
  render_report — 7 cases — green.
- 2026-06-13 — `native_kernel_perf_regs_codeword_sample_ring_v2216.py` —
  parse_int, parse_helper_stdout, classify_addr, load_text_symbols,
  load_symbol_index, nearest_symbol, symbolize_counter, load_kernel_raw,
  load_synthetic_base, read_stock_u32, candidate_slides,
  codeword_generated_slides, codeword_match_analysis, analyze_probe,
  render_report — 8 cases — green.
- 2026-06-13 — `a90_kernel_v2217_exact_slide_resymbolization_audit.py` —
  parse_int, hex64, hex_signed, extract_exact_slide, parse_system_map,
  build_symbol_index, nearest_symbol, load_kernel_raw, load_synthetic_base,
  read_u32, is_bl, decode_bl_target, decode_insn_kind,
  build_function_ranges, function_lookup, build_callsite_map,
  resymbolize_live_regs, ropp_decode_attempt, render_report —
  7 cases — green.
- 2026-06-13 — `native_kernel_wlan_tracepoint_catalog_v2218.py` —
  clean_cmdv1_text, parse_events, category_for, parse_format,
  load_system_map, symbolize, parse_extract_output, residual_state,
  StepResult.ok — 9 cases — green. Also extended `tests/_loader.py`
  to expose each standalone script's directory on `sys.path`, matching
  CLI sibling-import behavior for scripts that import `a90_transport`.
- 2026-06-13 — `native_kernel_a90_uprobe_trace_buffer_collector_v2219.py` —
  clean_cmdv1_text, parse_event_state, event_name_map, parse_args_text,
  parse_trace_lines, summarize_hits, residual_state, StepResult.ok,
  is_kernel_va — 10 cases — green. Also fixed `KV_RE` to parse unquoted
  trace args such as `svc=69` and `rc=-11`, matching tracefs output.
- 2026-06-13 — `native_kernel_a90_boot_window_preflight_v2222.py` —
  parse_json_object, parse_protocol_rc, grep_value, parse_helper_inventory,
  a90ctl_command, build_contract, residual_state, StepResult.ok —
  9 cases — green.
- 2026-06-13 — `native_kernel_a90_boot_window_plan_v2223.py` —
  sha256_file, load_json, latest_v2222_summary, source_marker_audit,
  boot_image_inventory, contract_summary, build_capture_plan,
  residual_state — 8 cases — green.
- 2026-06-13 — `build_native_init_boot_v2224_a90_boot_window_observer.py` —
  configure_base, render_report, normalize_manifest_axes — 3 cases —
  green.
- 2026-06-13 — `native_kernel_a90_boot_window_handoff_v2225.py` —
  sha256, load_build_manifest, a90ctl_command, flash_command,
  dry_run_commands, diagnose_artifacts, classify, render_report,
  residual_state — 11 cases — green. Also extended `tests/_loader.py`
  so `load_revalidation()` exposes `a90harness` for standalone scripts
  that import shared harness modules.
- 2026-06-13 — `build_native_init_boot_v2226_a90_boot_window_property_root.py` —
  configure_base, render_report, normalize_manifest_axes — 3 cases —
  green.
- 2026-06-13 — `native_kernel_a90_boot_window_handoff_v2227.py` —
  sha256, load_build_manifest, a90ctl_command, flash_command,
  dry_run_commands, extract_summary_value, diagnose_artifacts,
  is_current_window_a90_absent_preflight,
  is_current_window_collector_busy_preflight, classify, render_report,
  residual_state — 10 cases — green.
- 2026-06-13 — `build_native_init_boot_v2228_service_object_visible_observer.py` —
  configure_base, render_report, normalize_manifest_axes — 3 cases —
  green.
- 2026-06-13 — `native_kernel_a90_service_object_visible_handoff_v2229.py` —
  sha256, load_build_manifest, a90ctl_command, flash_command,
  dry_run_commands, diagnose_artifacts,
  is_current_window_a90_absent_preflight,
  is_current_window_collector_busy_preflight, classify, render_report,
  residual_state — 9 cases — green.
- 2026-06-13 — `build_native_init_boot_v2230_service_object_visible_post_bdf_hold.py` —
  configure_base, render_report, normalize_manifest_axes — 3 cases —
  green.
- 2026-06-13 — `native_kernel_a90_post_bdf_hold_handoff_v2231.py` —
  sha256, load_build_manifest, a90ctl_command, flash_command,
  dry_run_commands, extract_summary_value, diagnose_artifacts,
  is_current_window_a90_absent_preflight,
  is_current_window_collector_busy_preflight, classify, render_report,
  residual_state — 9 cases — green.
- 2026-06-13 — `build_native_init_boot_v2232_service_object_fwclass_bridge.py` —
  with_bridge_flag, configure_helper_flags via configure_base,
  configure_base, render_report — 3 cases — green.
- 2026-06-13 — `native_kernel_a90_service_object_fwclass_bridge_handoff_v2233.py` —
  sha256, load_build_manifest, a90ctl_command, flash_command,
  dry_run_commands, extract_summary_value, diagnose_artifacts including
  post-FW_READY boot_wlan / firmware_class / ICNSS snapshots,
  is_current_window_a90_absent_preflight,
  is_current_window_collector_busy_preflight, classify, render_report,
  residual_state — 9 cases — green.
- 2026-06-13 — `build_native_init_boot_v2236_strict_wifi_connect.py` —
  with_bridge_flag, configure_helper_flags via configure_base,
  configure_base, render_report — 3 cases — green.
- 2026-06-13 — `build_native_init_boot_v2237_supplicant_terminate_poll.py` —
  with_bridge_flag, configure_helper_flags via configure_base,
  configure_base, render_report — 3 cases — green.
- 2026-06-13 — `native_kernel_static_tracepoint_object_chain_audit_v2238.py` —
  clean_cmdv1_text, split_top_level_args, extract_macro_call,
  pointer_params, source_fields, parse_live_format, event_source_summary,
  classify_event, residual_state — 8 cases — green.
- 2026-06-13 — `a90_kernel_v2239_scalar_uprobe_timeline.py` —
  first_edges, compute_deltas, build_run_summary, infer_outcome,
  summarize_delta_stats, build_contract — 8 cases — green.
- 2026-06-13 — `a90_kernel_v2240_codepath_identity_boundary.py` —
  classify_domain, extract_samples, build_a90cnss_relative_signature,
  summarize_low12_by_event, build_summary — 8 cases — green.
- 2026-06-13 — `a90_kernel_v2241_user_uprobe_offset_base_map.py` —
  parse_uprobe_specs, extract_runtime_probes, build_bias_observations,
  summarize_biases, elf_metadata, build_summary — 8 cases — green.
- 2026-06-13 — `a90_kernel_v2242_user_elf_offset_context.py` —
  LoadSegment helpers, parse_load_segments missing-file path, object_for_spec,
  observed_spec_keys, build_offset_contexts, write_private_context,
  build_summary — 9 cases — green.
- 2026-06-13 — `a90_kernel_v2243_user_uprobe_semantic_classifier.py` —
  parse_instructions, find_target, instruction_class, event_role,
  role_alignment, classify_context, counter_dict, build_summary — 8 cases — green.
- 2026-06-13 — `a90_kernel_v2244_semantic_timeline_merger.py` —
  semantic_by_event, evidence_strength, merge_edge, summarize_run,
  compare_outcomes, build_summary — 8 cases — green.
- 2026-06-13 — `a90_kernel_v2245_post_fwready_tail_inventory.py` —
  read_key_values, as_int, count_tail_keys, collect_target_stacks,
  classify_stage, summarize_run, compare_runs, build_summary — 10 cases — green.
- 2026-06-13 — `a90_kernel_v2246_post_fwready_tail_symbol_source_map.py` —
  parse_int_hex, load_text_symbols, symbol_index, extract_observed_stack,
  find_source_definition, build_rows, build_summary — 9 cases — green.
- 2026-06-13 — `a90_kernel_v2247_tail_pc_lr_scorer.py` —
  parse_int, load_exact_slide, load_targets, target_for_static,
  sample_addresses, score_samples, build_summary — 10 cases — green.
- 2026-06-13 — `a90_kernel_v2248_tail_capture_insertion_audit.py` —
  line_matches, require_matches, first_line, helper_tail_anchors,
  build_anchors, v2216_sampler_anchors, build_summary — 8 cases — green.
- 2026-06-13 — `build_native_init_boot_v2249_tail_perf_sampler_hook.py` —
  sha256, with_tail_flags, configure_base, patch_ramdisk_helpers,
  render_report, main manifest/promotion metadata — 6 cases — green.
- 2026-06-13 — `build_native_init_boot_v2250_tail_perf_sampler_full_print.py` —
  sha256, with_tail_flags, configure_base, patch_ramdisk_helpers,
  render_report, main manifest/promotion metadata — 6 cases — green.
- 2026-06-13 — `a90_kernel_v2251_tail_target_evidence_classifier.py` —
  parse_int, extract_stack_symbol, read_json, parse_helper, summarize_feeder,
  summarize_scorer, build_summary decision/evidence branches — 9 cases — green.
- 2026-06-13 — `build_native_init_boot_v2252_fwclass_boundary_stack.py` —
  with_boundary_stack_flag, configure_base, render_report, main
  manifest/promotion metadata — 4 cases — green.
- 2026-06-13 — `native_kernel_fwclass_boundary_stack_handoff_v2253.py` —
  parse_key_values, summarize_phase, classify_boundary_artifacts,
  dry_run_commands, classify_manifest, render_report, residual_state —
  8 cases — green.
- 2026-06-13 — `build_native_init_boot_v2254_wifi_detail_surface.py` —
  configure_base, render_report, main manifest/promotion metadata —
  3 cases — green.
- 2026-06-13 — `native_wifi_detail_surface_handoff_v2255.py` —
  parse_key_values, last_value, sanitize_field_value, classify_wifi_status,
  classify_screenapp, flash_command, dry_run_commands, classify_test_health,
  classify_manifest, render_report, residual_state — 13 cases — green.
- 2026-06-13 — `native_kernel_workqueue_fwclass_oracle_plan_v2272.py` —
  read_text, rel, regex_present, firmware_tracepoint_source_absent,
  build_plan ready/block branches, render_text — 5 cases — green.
- 2026-06-13 — `build_native_init_boot_v2273_workqueue_fwclass_func_sampler.py` —
  sha256, with_workqueue_flags, configure_base, patch_ramdisk_helpers,
  render_report, main manifest/live-candidate metadata — 6 cases — green.
- 2026-06-13 — `build_native_init_boot_v2274_workqueue_codeword_combined.py` —
  sha256, with_workqueue_flags, configure_base, build_bpf_helpers,
  patch_ramdisk_helpers, render_report, main manifest/live-candidate metadata —
  7 cases — green.
- 2026-06-13 — `native_kernel_workqueue_codeword_handoff_v2275.py` —
  parse_key_values, parse_workqueue_log, resolve_symbol,
  classify_combined_artifacts, dry_run_commands, classify_manifest,
  render_report, residual_state — 9 cases — green.
- 2026-06-13 — `native_kernel_v2276_codeword_mismatch_postprocess.py` —
  as_int/hex helpers, ARM64 post-index/unprivileged instruction classifiers,
  classify_uao_runtime_patch, symbol_resolver, mismatch_rows,
  classify_workqueue_with_slide, analyze decision branches — 10 cases — green.
- 2026-06-13 — `build_native_init_boot_v2277_workqueue_exec_stack.py` —
  sha256, with_workqueue_flags, configure_base, build_bpf_helpers,
  patch_ramdisk_helpers, render_report, main manifest/live-candidate metadata —
  7 cases — green.
- 2026-06-13 — `native_kernel_workqueue_exec_stack_handoff_v2278.py` —
  parse_scalar_fields, parse_key_values, parse_workqueue_stack_log,
  symbol_resolver, analyze_codeword, classify_artifacts, dry_run_commands,
  classify_manifest, render_report, residual_state — 11 cases — green.
- 2026-06-13 — `build_native_init_boot_v2279_workqueue_exec_wide.py` —
  sha256, with_workqueue_flags, configure_base, build_bpf_helpers,
  patch_ramdisk_helpers, render_report, main manifest/live-candidate metadata —
  7 cases — green.
- 2026-06-13 — `native_kernel_workqueue_exec_wide_handoff_v2280.py` —
  parse_scalar_fields, parse_key_values, parse_workqueue_wide_log,
  symbol_resolver, analyze_codeword, classify_artifacts, dry_run_commands,
  classify_manifest, render_report, residual_state — 11 cases — green.
- 2026-06-13 — `native_wifi_v2254_hold_reconnect_handoff_v2282.py` —
  preflight, dry_run_commands, classify, redacted_secret_status,
  redacted_env_load, render_report — 8 cases — green.
- 2026-06-13 — `a90_transport.py` — phase, add_total_phase,
  set_residual_state, parse_json_stdout, bridge_command,
  protocol_result_to_command_result, serial recovery helpers, parse_key_values,
  summarize_host_ncm, auto_repair_enabled, maybe_repair_host_ncm,
  compact_ncm_repair, select_transport — 13 cases — green.
- 2026-06-13 — `a90_ncm_transport.py` — parse_key_values, sha256_file,
  env_flag, scoped_ipv6_bind_tuple, write_compact_step,
  is_a90_ncm_netdev, host_ncm_candidates, safe_host_ifname,
  host_netdev_snapshot, nmcli_connection_for_device,
  host_linklocal_repair_nmcli, scan_secret_*,
  validate_uploaded_archive — 11 cases — green.
- 2026-06-13 — `a90ctl.py` — parse_fields, shell_command_to_argv,
  can_use_legacy_cmdv1_arg, encode_cmdv1x_arg, encode_cmdv1_line,
  double_input_line, encode_wire_line, has_prompt_after_last_end,
  parse_protocol_output, validate_protocol_command, command_allows_retry,
  should_retry_cmdv1_exchange, result_to_json, run_cmdv1_command — 14 cases — green.
- 2026-06-13 — `a90harness/scheduler.py` — locks_for_module,
  default_workloads, build_schedule, schedule_document, WorkloadEvent.to_dict,
  MixedSoakResult.to_dict, run_mixed_soak_schedule pass/blocked/external-client
  paths — 9 cases — green.
- 2026-06-13 — `a90harness/device.py` — DeviceClient init validation,
  metadata, direct backend delegation, broker payload/response handling,
  exception-to-CommandRecord capture, exclusive context reentrancy — 8 cases — green.
- 2026-06-13 — `a90_serial_lock.py` — lock_path, default_timeout,
  SerialBridgeLock metadata write/clear, busy timeout close behavior,
  never-entered __exit__ no-op — 5 cases — green.
- 2026-06-13 — `native_init_frontier_select.py` — read_text/read_json,
  marker_present, all_markers_present, ready_t1_candidates, track_evaluations,
  select_frontier missing/present frontier candidate branches — 7 cases — green.
- 2026-06-13 — `inventory_revalidation_scripts.py` — classify,
  requires_live_device, imports_module, direct_a90ctl_candidate_groups,
  consolidation_signals, inventory, render_markdown — 7 cases — green.
- 2026-06-13 — `a90_kernel_tools.py` — repo_path,
  collect_host_metadata, run_capture, capture_to_manifest, strip_cmdv1_text,
  parse_kernel_config, config_state/config_enabled, summarize_options,
  markdown_table, fetch_kernel_config — 10 cases — green.
- 2026-06-13 — `a90_ncm_host_preflight.py` — valid_ipv4,
  run_text, read_text, service_state, ipv4_addrs, classify_interface,
  render_templates, write_templates, decide, render_summary, build_manifest —
  9 cases — green.
- 2026-06-13 — `a90_ncm_transport_smoke.py` — parse_sizes,
  write_pattern_file, shutil_which, maybe_force_nm_repair,
  stream_remote_to_host unreachable/success/failure branches — 8 cases — green.
- 2026-06-13 — `ncm_host_setup.py` — parse_status,
  prefix_to_netmask, cmdv1_unavailable, sudo_prefix,
  validate_host_interface_name, select_host_interface,
  device_command cmdv1/raw/busy branches, configure_host_interface_nmcli,
  configure_host_interface fallback/manual paths, command_setup orchestration —
  13 cases — green.
- 2026-06-13 — `a90_wifi_profile_stage.py` — root_paths,
  write_private_file, build_stage_files valid/invalid secret-status paths,
  compact_stage, finalize_manifest residual-state wiring, run preflight-fail
  and successful tcpctl transfer/verify branches with secret transfer flags —
  8 cases — green.
- 2026-06-13 — `a90_v725_fasttransport_baseline_validation.py` —
  run_command, status_summary, candidate_brief, write_step,
  run_json_subprocess, run_transport_smoke, run_idempotent_netservice,
  run_nm_repair_probe, wait_for_status — 9 cases — green.
- 2026-06-13 — `native_wifi_supplicant_dependency_probe.py` —
  sha256_file, remote_probe_script contract markers, parse_candidate_results,
  pick_decision precondition/connect/no-connect branches, transfer_ok —
  7 cases — green.
- 2026-06-13 — `tcpctl_host.py` — sha256_file, validate_install_target,
  parse_tcpctl_token, tcpctl_command_requires_auth, get_tcpctl_token,
  tcpctl_run_line, tcpctl_listen_command, tcpctl_request,
  tcpctl_expect_ok, tcpctl_install_command, wait_for_tcpctl,
  cmdv1_unavailable, device_command, command_run — 15 cases — green.
- 2026-06-13 — `a90_bridge.py` — validate_private_repair_path,
  ensure_private_repair_dir, cmdline_port_match, parse_proc_tcp_line,
  listen_sockets, selected_device_info, collect_status, print_status_text,
  build_bridge_command, effective_expect_realpath, write_metadata,
  path_detail, stat_info — 13 cases — green.
- 2026-06-13 — `serial_tcp_bridge.py` — Bridge.resolve_device,
  serial_realpath_allowed, accept_client, close_client, forward_client,
  forward_serial, flush_serial_tx — 11 cases — green.
- 2026-06-13 — `a90harness/modules/cpu_memory_profiles.py` —
  CpuMemoryProfile.to_dict, zero_sha256, parse_status, profile selection,
  safe temp/path builders, _run_cmd, _run_profile success/failure branches,
  run report writing, verify pass/mismatch/missing-report branches — 9 cases —
  green.
- 2026-06-13 — `a90harness/modules/ncm_tcp_preflight.py` —
  prepare ping-skip/helper-present/helper-missing branches, run tcpctl smoke
  command and marker validation, cleanup skip/no-op, verify authenticated marker
  and auth=none rejection branches — 7 cases — green.
- 2026-06-13 — `a90harness/modules/storage_io.py` — prepare ping
  skip/success branches, run skip/smoke/quick command construction, cleanup
  skip/clean command, verify skip/missing/pass/empty-result branches — 7 cases
  — green.
- 2026-06-13 — `a90harness/modules/kselftest_feasibility.py` — run command
  contract, timeout floor/scale and nonzero rc branches, verify missing/pass
  and mutation/safe-candidate/blocked reject branches — 5 cases — green.
- 2026-06-13 — `a90harness/modules/cpu_mem_thermal.py` — smoke/quick run
  command construction and nonzero rc branches, verify missing/pass and
  failed/missing controlled-zombie check branches — 5 cases — green.
- 2026-06-13 — `a90harness/modules/usb_recovery.py` — metadata USB rebind
  and operator gate contract, smoke/quick run command and nonzero rc branches,
  verify missing/pass and failed/missing final-health check branches — 6 cases
  — green.
- 2026-06-13 — `cpu_mem_thermal_stability.py` — parse_size,
  parse_status_text, zero_sha256/parse_sha256, sample_extreme,
  process_snapshot zombie/fd counting and fd-failure tolerance,
  maybe_host_ping disabled/success/error branches — 6 cases — green.
- 2026-06-13 — `kselftest_feasibility.py` — private output path/mode and
  symlink rejects, safe_filename, run_capture success/error evidence writes,
  classify tracefs/toybox marker branches, render_markdown summary/capture
  output — 5 cases — green.
- 2026-06-13 — `storage_iotest.py` — parse_sizes,
  deterministic_bytes/sha256, device root/path/port validation, mkdir_chain,
  run_one_file mocked transfer/hash/rename/sync/unlink flow, command_run
  report/residual state, command_clean safe run-child removal — 7 cases —
  green.
- 2026-06-13 — `netservice_reconnect_soak.py` — USB/NCM status parsing,
  host-interface selection gates, tcpctl token cache/auth rules, start/stop
  ready-marker checks, verify_ncm_and_tcp orchestration, once/soak failure
  cleanup paths, host config/sudo/cmdv1 fallback branches — 10 cases — green.
- 2026-06-13 — `usb_recovery_validate.py` — private evidence mode/symlink
  rejection, raw cmdv1 success/disconnect evidence writes, recovery polling
  success, cmdv1 exception capture, recovery_times filtering, main report
  checks/residual-state failure path — 5 cases — green.
- 2026-06-13 — `native_ui_screenapp_validation_v2187.py` —
  screenapp_pass field contract, classify flash/status/ping/rollback/pass
  decisions, render_report evidence/safety text, rel path handling,
  fields_for key-value parsing — 5 cases — green.
- 2026-06-13 — `native_wifi_v2178_autoconnect_phase_validation.py` —
  classify pass and baseline/connect/secret/cleanup/disable/selftest failure
  branches, step_text/find_step output handling, zero_flag strictness,
  rel path handling — 5 cases — green.
- 2026-06-13 — `native_wifi_dhcp_ping_handoff_v2176.py` —
  classify preflight/flash/rollback/pass/safety branches, render_report
  metadata-only public scope, run_ping_step command quoting, run_dhcp_window
  DHCP-fail skip-ping and DHCP-pass ping/cleanup paths, rel/flash delegation —
  7 cases — green.
- 2026-06-13 — `native_wifi_connect_carrier_handoff_v2174.py` —
  profile/env file validation, Wi-Fi secret length-only status, evidence
  redaction, key-value/step helpers, classify preflight/flash/rollback/pass
  and safety branches, render_report connect-scope text — 8 cases — green.
- 2026-06-13 — `native_wifi_hold_reconnect_handoff_v2177.py` —
  classify preflight/flash/rollback/pass/safety branches, ping command
  quoting/parsing, DHCP-fail skip-ping and DHCP-pass ping paths, cleanup residue
  gates, hold sampling loop, render_report redacted hold scope — 8 cases —
  green.
- 2026-06-13 — `build_native_init_boot_v2184_network_ui_p0_p1.py` —
  configure_base V2184 axis rewrites, network UI P0/P1 render_report safety
  scope, normalize_manifest_axes version metadata — 3 cases — green.
- 2026-06-13 — `build_native_init_boot_v2185_network_ping_test.py` —
  configure_base V2185 axis rewrites, network ping render_report safety scope,
  normalize_manifest_axes promoted-baseline metadata — 3 cases — green.
- 2026-06-13 — `build_native_init_boot_v2186_wifi_ui_polish.py` —
  configure_base V2186 axis rewrites, Wi-Fi UI polish render_report safety
  scope, normalize_manifest_axes promoted-baseline metadata — 3 cases — green.
- 2026-06-13 — `build_native_init_boot_v2187_screenapp_ui_validation.py` —
  configure_base V2187 axis rewrites, screenapp UI validation render_report
  safety scope, normalize_manifest_axes promoted-baseline metadata — 3 cases —
  green.
- 2026-06-13 — `build_native_init_boot_v2188_security_p0_hardening.py` —
  configure_base V2188 axis rewrites, security P0 hardening render_report
  no-runtime-Wi-Fi safety scope, normalize_manifest_axes unpromoted-candidate
  metadata — 3 cases — green.
- 2026-06-13 — `build_native_init_boot_v2189_security_p0_stage_fix.py` —
  configure_base V2189 axis rewrites, helper marker/SHA pinning before patch,
  security stage-fix render_report no-runtime-Wi-Fi safety scope,
  normalize_manifest_axes parent-candidate metadata — 4 cases — green.
- 2026-06-13 — `build_native_init_boot_v2169_transport_contract.py` —
  configure_base V2169 axis rewrites and transport flag propagation,
  legacy mkbootimg symlink shim, transport-contract render_report safety scope,
  normalize_manifest_axes promoted-baseline metadata — 4 cases — green.
- 2026-06-13 — `build_native_init_boot_v2170_wifi_config_prepare.py` —
  configure_base V2170 axis rewrites, helper patch plus temporary legacy-link
  cleanup, config-prepare render_report negative Wi-Fi scope,
  normalize_manifest_axes test-candidate metadata — 4 cases — green.
- 2026-06-13 — `build_native_init_boot_v2172_wifi_status_scan.py` —
  configure_base V2172 axis rewrites, helper patch plus temporary legacy-link
  cleanup, status/scan render_report credential-free scope,
  normalize_manifest_axes test-candidate metadata — 4 cases — green.
- 2026-06-13 — `build_native_init_boot_v2174_wifi_urandom_connect.py` —
  configure_base V2174 axis rewrites, helper patch plus temporary legacy-link
  cleanup, connect/urandom render_report redacted-scope contract,
  normalize_manifest_axes test-candidate metadata — 4 cases — green.
- 2026-06-13 — `build_native_init_boot_v2176_wifi_dhcp.py` —
  configure_base V2176 axis rewrites, helper patch plus temporary legacy-link
  cleanup, DHCP/cleanup render_report ping-boundary safety scope,
  normalize_manifest_axes test-candidate metadata — 4 cases — green.
- 2026-06-13 — `build_native_init_boot_v2178_wifi_profile_autoconnect.py` —
  configure_base V2178 axis rewrites, helper patch plus temporary legacy-link
  cleanup, profile/autoconnect render_report disabled-by-default safety scope,
  normalize_manifest_axes test-candidate metadata — 4 cases — green.
- 2026-06-13 — `build_native_init_boot_v2182_hud_menu_cleanup.py` —
  configure_base V2182 axis rewrites, helper patch plus temporary legacy-link
  cleanup, HUD/menu cleanup render_report no-active-Wi-Fi safety scope,
  normalize_manifest_axes promoted-baseline metadata — 4 cases — green.
- 2026-06-13 — `build_native_init_boot_v724.py` — PID1 source
  selection excluding standalone `a90_*.c` programs, static init build command,
  ramdisk helper copy/mode/reproducible cpio contract, base boot ramdisk
  replacement error path, marker verification pass/fail branches — 5 cases —
  green.
- 2026-06-13 — `build_native_init_boot_v725_fasttransport.py` —
  arg-driven PID1 source selection, fasttransport `EXTRA_CFLAGS` injection,
  ramdisk-local transport helper materialization and modes, base boot ramdisk
  replacement error path, fasttransport marker verification pass/fail branches
  — 5 cases — green.
- 2026-06-13 — `build_native_init_boot_v726_wifi_lifecycle.py` —
  V2168 wrapper axis rewrites and lifecycle modem-owner flag propagation,
  lifecycle route/safety render_report text, manifest cycle/baseline axis
  normalization including non-V726 preservation, main helper patch and success
  only normalization orchestration — 5 cases — green.
- 2026-06-13 — `native_init_flash.py` — ADB device list parsing,
  SHA256/path validation, chunk-boundary marker search, local boot image
  regular/aligned/marker/hash safety checks, sealed local image copy
  mutation checks, cmdv1 result rejection branches — 8 cases — green.
- 2026-06-13 — `_workspace_bootstrap.py` — repo root discovery success/failure,
  harness/archive path injection defaults, env-controlled archive inclusion,
  explicit archive override, duplicate prevention — 6 cases — green.
- 2026-06-13 — `build_native_init_wifi_test_boot_v2168.py` — V2137 axis
  rewrites, helper marker/SHA propagation, fasttransport ramdisk helper
  wrapping, QCACLD firmware_class render_report safety scope, main
  patch/report/return orchestration — 3 cases — green.
- 2026-06-13 — `cleanup_tmp_wifi_artifacts.py` — structured threshold removal
  planning, legacy-flat protection/explicit deletion gate, build-product-only
  pruning, symlink escape refusal in execute_plan, text rendering — 5 cases —
  green.
- (append: date — target — functions covered — test count — any `KNOWN-DIVERGENCE`.)
