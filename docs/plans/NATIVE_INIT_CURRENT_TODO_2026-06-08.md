# Native Init Current TODO

Date: `2026-06-12`

This is the active TODO map for the current native-init baseline hardening
cycle. It is intentionally higher-level than per-run reports and lower-level
than the long-term roadmap.

Current baseline:

- Device baseline: `A90 Linux init 0.9.272 (v2254-wifi-detail-surface)`.
- Promotion run: `V2256`; boot SHA256
  `c668e9cd9a3621c955fa369c5d106271a96a949dcaec3774a5719d24b8ba19e9`.
- Immediate rollback image:
  `workspace/private/inputs/boot_images/boot_linux_v2254_wifi_detail_surface.img`.
- Previous verified rollback image:
  `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`.
- Emergency rollback image:
  `workspace/private/inputs/boot_images/boot_linux_v2169_transport_contract.img`.
- Active control path: USB ACM serial bridge managed by
  `workspace/public/src/scripts/revalidation/a90_bridge.py`.
- Active fast path: USB NCM link-local plus bounded FastUpload-style transfers.
- Standing boot/bridge/communication contract:
  `docs/operations/NATIVE_INIT_BOOT_TRANSPORT_CONTRACT.md`.
- Transport commonization design:
  `docs/plans/NATIVE_INIT_TRANSPORT_COMMONIZATION_DESIGN_2026-06-09.md`.
- Active source root: `workspace/public/src/native-init/`.
- Active script root: `workspace/public/src/scripts/revalidation/`.
- Private/generated payload root: `workspace/private/` and structured `tmp/`.

Latest promotion evidence:

- Source/build:
  `docs/reports/NATIVE_INIT_V2254_WIFI_DETAIL_SURFACE_SOURCE_BUILD_2026-06-12.md`.
- Rollbackable live WLAN surface validation:
  `docs/reports/NATIVE_INIT_V2255_WIFI_DETAIL_SURFACE_LIVE_2026-06-12.md`.
- Baseline promotion:
  `docs/reports/NATIVE_INIT_V2256_V2254_WIFI_DETAIL_SURFACE_BASELINE_PROMOTION_2026-06-12.md`.
- Status: promoted baseline preserves the V2237 native `wlan0` route and adds
  read-only route/default-DNS detail fields to `wifi status` and
  `screenapp wifi-status`. V2255 validated that surface rollbackably with no
  scan/connect/DHCP/ping or credentials. Long idle/hold data-path stability
  remains a separate follow-up.

## Priority 0: Commit Hygiene

Goal: keep the current workspace reviewable before more live tests.

Status: complete for the current `v2254-wifi-detail-surface` baseline.

Completed audit:

- Latest focused committed unit before this TODO cleanup:
  `532342ca Promote V2254 Wi-Fi detail baseline`.
- Post-commit workspace audit found no uncommitted tracked changes.
- `git diff --check` passed on the clean baseline.
- Generated logs, boot images, firmware, credentials, and raw captures remain out
  of git; tracked `workspace/private/` entries are README/skeleton files only.
- Audit report:
  `docs/reports/NATIVE_INIT_P0_COMMIT_HYGIENE_AUDIT_2026-06-10.md`.

Ongoing rule:

- Keep future changes in focused units:
  1. Wi-Fi config/autoconnect source changes.
  2. Bridge/transport wrapper and selector changes.
  3. TODO/workspace documentation.
  4. Script cleanup/migration changes.

Exit criteria:

- `git diff --check` passes.
- Changed Python files pass `py_compile`.
- No ignored private payload is staged.
- Each commit has one clear scope.

## Priority 1: Wi-Fi Lifecycle

Goal: keep the proven `wlan0` lifecycle as repeatable baseline behavior.

Status: complete for the current `v2254-wifi-detail-surface` baseline.

Completed baseline capabilities:

- Native commands are in place for:
  - `wifi config status`;
  - `wifi config prepare [profile]`;
  - `wifi status`;
  - `wifi scan [delay_ms]`;
  - `wifi connect [profile]`;
  - `wifi dhcp [profile]`;
  - `wifi ping [gateway|internet|all]`;
  - `wifi cleanup`;
  - `screenapp [network|wifi-status|wifi-profiles|wifi-scan|wifi-ping]`.
- Connectivity and stability evidence is complete for the promoted line:
  - V2174 fixed `/dev/urandom` and reached carrier;
  - V2176 passed connect, DHCP, bounded ping, cleanup, rollback, and N=3;
  - V2177 passed 180 second hold/idle, cleanup, reconnect, DHCP, ping, and
    rollback;
  - V2178 passed profile/autoconnect, private 2.4 GHz and 5 GHz checks, and
    boot autoconnect N=3;
  - V2184 passed network UI P0/P1, manual private 5 GHz connect, and 512MiB plus
    1GiB phone Wi-Fi transfer SHA checks;
  - V2185 passed bounded gateway plus fixed-IP ping and became a prior rollback
    baseline;
  - V2186 passed Wi-Fi status/RF UI polish and became a prior rollback baseline;
  - V2187 passed `screenapp` framebuffer validation and remains the previous
    conservative rollback baseline;
  - V2189 passed security P0 flash/staging hardening, carrier smoke, cleanup,
    and fresh local security scan; V2190 promoted it as a prior baseline;
  - V2232/V2233 crossed the service-object-visible post-BDF wall to real native
    `wlan0`; V2234 promoted it as the first native-`wlan0` baseline;
  - V2235 exposed that `wifi connect` could accept stale carrier while
    supplicant was `DISCONNECTED`;
  - V2236 fixed that validation gap, requires `wpa_state=COMPLETED`, and passed
    bounded 5 GHz plus direct 2.4 GHz switch/DHCP/ping validation;
  - V2237 replaced the blind post-`TERMINATE` delay with bounded
    `wpa_supplicant` exit polling plus SIGKILL escalation, and passed bounded
    5 GHz plus direct 2.4 GHz switch/DHCP/ping validation;
  - V2254 added read-only route/default-DNS fields to `wifi status` and
    `screenapp wifi-status`;
  - V2255 rollbackably validated that surface without scan/connect/DHCP/ping;
  - V2256 promoted V2254 as the current rollback/test baseline.
- Primary evidence reports:
  - `docs/reports/NATIVE_INIT_V2176_WIFI_DHCP_STABILITY_N3_2026-06-08.md`;
  - `docs/reports/NATIVE_INIT_V2177_WIFI_HOLD_RECONNECT_LIVE_VALIDATION_2026-06-09.md`;
  - `docs/reports/NATIVE_INIT_V2179_V2178_WIFI_PROFILE_AUTOCONNECT_BASELINE_PROMOTION_2026-06-09.md`;
  - `docs/reports/NATIVE_INIT_V2184_PHONE_WIFI_LARGE_TRANSFER_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2185_NETWORK_PING_BASELINE_PROMOTION_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2186_WIFI_UI_POLISH_BASELINE_PROMOTION_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2187_SCREENAPP_UI_VALIDATION_BASELINE_PROMOTION_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2189_SECURITY_P0_STAGE_FIX_LIVE_VALIDATION_2026-06-10.md`;
  - `docs/security/scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2190_V2189_SECURITY_P0_STAGE_FIX_BASELINE_PROMOTION_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2236_STRICT_WIFI_CONNECT_SOURCE_BUILD_2026-06-12.md`;
  - `docs/reports/NATIVE_INIT_V2236_STRICT_WIFI_CONNECT_LIVE_VALIDATION_2026-06-12.md`;
  - `docs/reports/NATIVE_INIT_V2237_SUPPLICANT_TERMINATE_POLL_SOURCE_BUILD_2026-06-12.md`;
  - `docs/reports/NATIVE_INIT_V2237_SUPPLICANT_TERMINATE_POLL_LIVE_VALIDATION_2026-06-12.md`;
  - `docs/reports/NATIVE_INIT_V2254_WIFI_DETAIL_SURFACE_SOURCE_BUILD_2026-06-12.md`;
  - `docs/reports/NATIVE_INIT_V2255_WIFI_DETAIL_SURFACE_LIVE_2026-06-12.md`;
  - `docs/reports/NATIVE_INIT_V2256_V2254_WIFI_DETAIL_SURFACE_BASELINE_PROMOTION_2026-06-12.md`.

Standing rules:

- Keep V2254 as the current baseline and normal rollback/test image until a
  newer boot image is intentionally promoted.
- Keep V2237, V2187, V2186, V2185, V2178, and V2169 as older conservative
  fallbacks only.
- Keep Wi-Fi profiles, SSID, PSK, raw phone-transfer evidence, private IPs, and
  raw LAN identifiers under ignored private roots.
- Keep secondary-interface noise out of the main gate unless it becomes a
  persistent primary `wlan0` failure:
  - `swlan0` MAC generation failure is not a primary `wlan0` blocker;
  - `set_features(-11)` remains non-blocking unless persistent.

Deferred polish:

- Improve boot-autoconnect latency observability only when retesting boot
  autoconnect; runners must poll `autoconnect.decision=wifi-autoconnect-running`
  until a terminal result.
- Optional redacted SSID display toggle for scan results.
- Optional physical button/OCR validation for `NETWORK > PING TEST`; V2189
  preserves V2187 command-level framebuffer evidence for the same draw path.

## Priority 2: Bridge And Transport

Goal: keep every active runner on the shared bridge/NCM/tcpctl path.

Status: complete for the normal path; one opportunistic live edge remains.

Completed:

- `a90_bridge.py` manages bridge lifecycle:
  `preflight`, `status`, `ensure`, `start`, `stop`, `restart`, `doctor`, and
  `repair-dirs`.
- `a90_transport.py` is the shared selector/recovery/phase module.
- Active migrated runners record:
  - `selector_contract=1`;
  - `selected=serial|ncm|tcpctl`;
  - `fallback_reason=<label-or-null>`;
  - `phase_timer_contract=1`;
  - `serial_recovery_contract=1` where recovered serial commands are used.
- Transport selector has bounded host NCM link-local auto-repair for Samsung
  `04e8` + `cdc_ncm` present/no-`fe80::` state.
- V2180 live validation passed for NCM smoke plus current-baseline Wi-Fi
  autoconnect phase validation:
  `docs/reports/NATIVE_INIT_V2180_TRANSPORT_COMMONIZATION_LIVE_VALIDATION_2026-06-09.md`.
- Bridge artifacts land under `workspace/private/logs/bridge/`, and active
  runners should not directly start `serial_tcp_bridge.py` unless testing the
  bridge implementation itself.

Open edge:

- Live-validate serial `AT`/protocol-noise recovery only when it naturally fires:
  recovery metadata must appear, and unsafe commands must not replay unless
  explicitly scoped.
- Keep bridge warnings actionable:
  - `private_log_dir` and `private_run_dir` writable must pass;
  - `port_pid_resolution=cmdline-fallback` is acceptable when bridge is already
    running and process ownership blocks `/proc/*/fd` inspection.

## Priority 3: Test Script Inventory And Consolidation

Goal: prevent new one-off script sprawl.

Status: refreshed for the V2254 baseline; source-root has no `delete-review`
entries, and V2266 closed the last active live phase/residual metadata gap.
The active live runner phase/residual backlog is currently complete.

Completed:

- Current inventory report:
  `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md`.
- Current source-root state after V2272 inventory refresh:
  - `109 active`;
  - `6 module`;
  - `0 archive`;
  - `0 delete-review`.
- Active live metadata gaps:
  - phase timer markers missing: `0`;
  - residual-state metadata missing: `0`;
  - phase-timer-exempt live utilities: `2`;
  - residual-state-exempt live utilities/helpers: `3`.
- V2277 built the focused workqueue `execute_start` stack/callsite oracle as
  `boot_linux_v2277_workqueue_exec_stack.img` (`A90 Linux init 0.9.275`,
  helper `a90_android_execns_probe v433`, boot SHA256
  `313a39b603296810dc44d8132c2c7db6c8fc790eb168a9ef9d94b20225baa18f`).
  This was source/build-only; no device flash or live validation was performed.
  Next live unit is V2278: flash V2277 rollbackably, collect helper result plus
  `/cache/native-init-v2277-workqueue-exec-stack.log` and
  `/cache/native-init-v2277-tail-perf-regs-codeword.log`, rollback, verify
  selftest `fail=0`, then classify workqueue execute-start stacks/callsites
  with the V2276 bounded UAO-patch-aware same-boot slide rule.
- V2276 postprocessed the V2275 codeword log host-only. The three V2275 PC
  mismatches behind best slide `0xccef4` are all source-matched ARM64 UAO
  runtime alternatives (`str -> sttr`, `ldp -> ldtr`, `stp -> sttr`) while
  `lr_prev=709/709` and `lr=709/709` remain exact. Therefore the V2275 slide is
  acceptable only under a bounded UAO-patch-aware rule. Reclassifying V2275
  workqueue function pointers with that slide gives classifiable negative
  evidence: `target_hit_count=0` across `2048` stored samples. Do not rerun the
  combined workqueue/codeword capture for this question.
- V2275 ran the V2274 combined workqueue/codeword oracle rollbackably. The
  workqueue sampler completed and captured `12511` total events (`2048` stored).
  Final rollback to V2237 was manually completed after a host parser crash and
  ended with `version`/`status`/`selftest fail=0`.
- V2272 defined the underlying T1 oracle candidate:
  `t1-workqueue-fwclass-function-pointer-oracle`, stored in
  `docs/artifacts/native-init-frontier-candidates.json`.
- V2271 added `native_init_frontier_select.py`, a host-only selector/audit
  utility. At the time it returned `frontier-selector-no-automatic-safe-unit`
  because no new T1 oracle, no concrete V2254 live-validation/promotion
  criterion, and no active T3 cleanup backlog were present in public state.
- V2270 added direct `a90ctl.py` actionability gates to inventory
  `consolidation_signals`. Remaining direct references are now explicitly
  review-only:
  - `direct_a90ctl_reference_count=14`;
  - `direct_a90ctl_actionable_now_count=0`;
  - `direct_a90ctl_review_only_count=14`;
  - `direct_a90ctl_next_actionable_group={}`.
- V2269 migrated the current-baseline Wi-Fi detail surface runner
  `native_wifi_detail_surface_handoff_v2255.py` from direct `a90ctl.py`
  subprocess command lists to shared `a90_transport.run_serial_step`; direct
  `a90ctl.py` references are now `14` and the top remaining group is
  `flash_capable_kernel_handoff_runners`.
- V2268 grouped direct `a90ctl.py` references into machine-readable candidate
  groups; the top group was `current_baseline_wifi_surface` with
  `native_wifi_detail_surface_handoff_v2255.py` as its single member.
- V2267 added machine-readable `consolidation_signals` to the inventory JSON:
  - `active_live_phase_residual_backlog_closed=true`;
  - `direct_a90ctl_reference_count=15`;
  - `source_delete_review_count=0`.
- V2266 migrated `local_security_rescan.py` to shared `a90_transport` phase
  timing plus residual-state metadata while preserving host-only targeted-scan
  behavior.
- V2265 migrated the remaining kernel-observation gap entries to shared
  `a90_transport` phase timing plus residual-state metadata:
  `native_kernel_wlan_tracepoint_catalog_v2218.py`,
  `native_kernel_static_tracepoint_object_chain_audit_v2238.py`, and
  `native_kernel_fwclass_boundary_stack_handoff_v2253.py`.
- V2264 migrated the boot-window preflight/plan/handoff runner family to shared
  `a90_transport` phase timing plus residual-state metadata:
  `native_kernel_a90_boot_window_preflight_v2222.py`,
  `native_kernel_a90_boot_window_plan_v2223.py`,
  `native_kernel_a90_boot_window_handoff_v2225.py`, and
  `native_kernel_a90_boot_window_handoff_v2227.py`.
- V2263 migrated the service-object/post-BDF handoff runner family to shared
  `a90_transport` phase timing plus residual-state metadata:
  `native_kernel_a90_service_object_visible_handoff_v2229.py`,
  `native_kernel_a90_post_bdf_hold_handoff_v2231.py`, and
  `native_kernel_a90_service_object_fwclass_bridge_handoff_v2233.py`.
- V2262 migrated the uprobe trace kernel-observation runner pair to shared
  `a90_transport` phase timing plus residual-state metadata:
  `native_kernel_a90_uprobe_trace_buffer_collector_v2219.py` and
  `native_kernel_a90_uprobe_trace_postprocess_v2221.py`.
- V2261 migrated the raw/perf sample-ring kernel-observation runner family to
  shared `a90_transport` phase timing plus residual-state metadata:
  `native_kernel_raw_frame_slots_v2212.py`,
  `native_kernel_raw_frame_sample_ring_v2213.py`,
  `native_kernel_perf_regs_frame_sample_ring_v2214.py`, and
  `native_kernel_perf_regs_codeword_sample_ring_v2216.py`.
- V2260 migrated the file-ops anchor kernel-observation runner pair to shared
  `a90_transport` phase timing plus residual-state metadata:
  `native_kernel_file_ops_anchor_v2204.py` and
  `native_kernel_fops_member_anchor_v2206.py`.
- V2259 migrated the timer kernel-observation runner family to shared
  `a90_transport` phase timing plus residual-state metadata:
  `native_kernel_timer_start_context_v2200.py`,
  `native_kernel_timer_object_context_v2201.py`, and
  `native_kernel_timer_object_histogram_v2202.py`.
- V2258 migrated `native_wifi_detail_surface_handoff_v2255.py` to shared
  `a90_transport` phase timing plus residual-state metadata; it is no longer in
  the active live gap list.
- V2167 historical runner is archived under
  `workspace/public/archive/scripts/revalidation/native_wifi_connect_dhcp_google_ping_handoff_v2167.py`.
- `workspace/public/archive/scripts/revalidation/` is provenance-only and must
  not be used as the start point for new active work.

Standing rules:

- Refresh inventory after each active entrypoint migration.
- Keep classifying scripts by purpose, last run, deps, docs references,
  live-device requirement, and secret/log handling.
- Migrate/delete only after classification; archive-wide dedupe remains a
  separate provenance cleanup task.

## Priority 4: Baseline And Versioning

Goal: avoid mixing run IDs, helper versions, and boot baseline tags.

Status: standing rule.

When promoting a new boot image:

- Use the next global run/build identity, not helper numbering.
- Record:
  - run ID;
  - native init semantic version;
  - build tag;
  - helper version;
  - boot image path;
  - boot SHA256;
  - host commit.
- Update rollback image path and SHA in the runbook.
- Keep V2254 fixed as current baseline until the next explicit promotion.

## Priority 5: Workspace Structure

Goal: keep a fresh clone usable while private/generated payloads stay out of git.

Status: ongoing workspace discipline.

Standing rules:

- Keep public source, scripts, redacted reports, templates, and inventories in
  `workspace/public/` and `docs/`.
- Keep private/generated artifacts under:
  - `workspace/private/inputs/`;
  - `workspace/private/builds/`;
  - `workspace/private/logs/`;
  - `workspace/private/secrets/`.
- Keep `tmp/` structured:
  - `tmp/wifi/runs/` for live Wi-Fi evidence;
  - `tmp/wifi/bench/` for transport smoke;
  - `tmp/logs/` for cross-run logs.
- Avoid new root-level payload folders.

Deferred cleanup:

- Decide later whether old `tmp/` evidence should be archived, compressed, or
  deleted. Do not mix that cleanup into Wi-Fi, transport, or baseline commits.

## Priority 6: QA And Stability

Goal: define when behavior is strong enough to become baseline.

Status: current baseline QA is sufficient; future promotions must follow the QA
policy.

Completed:

- QA/stability policy exists:
  `docs/operations/NATIVE_INIT_QA_STABILITY_POLICY.md`.
- V2176 route has N>=3 basic stability evidence.
- V2177 route has 180 second hold/idle plus cleanup/reconnect evidence.
- Active live runner metadata now records phase timers and residual-state where
  applicable.

Before the next baseline promotion:

- Reuse or run the relevant smoke checks for:
  - bridge;
  - NCM;
  - transport selector;
  - Wi-Fi connect;
  - cleanup;
  - rollback selftest.
- Treat cleanup failure as a baseline risk unless residual-state evidence proves
  the leftover state is harmless for the next run.

## Priority 7: Security And Safety Scope

Goal: keep the lab workflow powerful but bounded.

Status: standing rule.

Keep:

- bridge bound to localhost;
- no authentication bypasses or external exposure for convenience;
- Wi-Fi credentials private and environment/file based;
- raw captures private unless redacted;
- blocked operations blocked unless explicitly scoped:
  - PMIC/GPIO/GDSC/regulator writes;
  - eSoC notify/BOOT_DONE;
  - PCI rescan;
  - platform bind/unbind;
  - unbounded external network tests;
- no automatic retry of unsafe root commands.

## Suggested Next Sequence

1. Run `native_init_frontier_select.py --json` after the normal state read.
   Current expected result is `frontier-selector-actionable-unit-present` with
   `selected_track=T1` when the V2278 live-validation contract is encoded in
   `docs/artifacts/native-init-frontier-candidates.json`.
2. Run V2278 live validation for the already-built V2277 workqueue
   `execute_start` stack/callsite oracle. This is the substantive T1 next step;
   it should flash only the V2277 boot artifact through the checked helper,
   collect both sampler logs, rollback, and selftest.
3. Do not rerun generic CPU-clock sampling or the same combined
   workqueue/codeword capture for this question.
4. Start new WLAN live validation from V2254 only when a concrete criterion
   exists, unless a test explicitly validates an older rollback image.
5. Defer architecture source cleanup unless a cleanup patch is kept separate and
   validation-neutral.
6. If serial `AT` noise naturally fires, confirm shared recovery evidence.
7. Run longer Wi-Fi/data-path soak only when new promotion criteria require it.

## Current Risk Register

| Risk | Current impact | Handling |
| --- | --- | --- |
| Boot autoconnect latency | Wi-Fi success can take roughly three minutes. | Poll `autoconnect.decision` until a terminal result; shared phase timers are live-validated for bounded current-baseline runners, but boot/reboot latency still needs separate timing if retested. |
| Serial `AT` noise | A single cmdv1 exchange can be malformed. | Shared recovery is implemented for safe commands; V2180 did not naturally fire the path, so live-fired evidence remains opportunistic. |
| Physical network-menu ping selection | V2189 inherits V2187 command-level framebuffer presentation evidence for `WIFI STATUS` and `WIFI PING RESULTS`, but not button-driven physical capture. | Treat as UI polish, not a baseline blocker; validate physically or with OCR only if visual-navigation evidence is required. |
| Large-transfer soak depth | V2184 passed 512MiB and 1GiB single-run bidirectional SHA checks, but not repeated N-run or multi-hour soak. | Treat as strong data-path evidence; run `cleanup -> reconnect -> 512MiB` or N-run soak only if promotion criteria require it. |
| UI completeness | V2254 is the current baseline and preserves V2237 native `wlan0` bring-up/strict connect cleanup while adding the read-only Wi-Fi detail surface. | Keep V2254 as baseline; physical button/OCR validation remains optional. |
| T1 oracle execution | V2277 built the focused workqueue `execute_start` stack/callsite oracle image after V2276 made the V2275 `work->func` classification target-negative under the bounded UAO-patch-aware same-boot slide rule. | Do not rerun the same combined capture. Next T1 is V2278 live validation of the V2277 boot image, followed by rollback and selftest before classifying stack/callsite evidence. |
| Script sprawl | Current source-root inventory has no delete-review rows and no active live phase/residual gaps. Remaining direct `a90ctl.py` references are review-only: `direct_a90ctl_reference_count=14`, `direct_a90ctl_actionable_now_count=0`, `direct_a90ctl_review_only_count=14`, top group `flash_capable_kernel_handoff_runners`. | Do not select direct-ref migration solely from historical references; use `consolidation_signals.direct_a90ctl_next_actionable_group` and migrate a runner only if it is revived or changed for a bounded run. |
| Private data leakage | Wi-Fi profiles and raw run artifacts are intentionally private. | Keep secrets under ignored private roots; public reports stay redacted. |
