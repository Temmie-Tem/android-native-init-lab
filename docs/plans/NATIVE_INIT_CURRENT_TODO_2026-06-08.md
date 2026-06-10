# Native Init Current TODO

Date: `2026-06-10`

This is the active TODO map for the current native-init baseline hardening
cycle. It is intentionally higher-level than per-run reports and lower-level
than the long-term roadmap.

Current baseline:

- Device baseline: `A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)`.
- Promotion run: `V2187`; boot SHA256
  `0422f854b3e78d36e225012fd89a53016067155e200291d067ff7d71f32091ca`.
- Immediate rollback image:
  `workspace/private/inputs/boot_images/boot_linux_v2187_screenapp_ui_validation.img`.
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

Pre-promotion candidate:

- Candidate: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`.
- Boot SHA256:
  `a7332612199cfd275f2dfc6fdb25843af401a1ecef2fa54ac0f52afe705f1ffe`.
- Live validation:
  `docs/reports/NATIVE_INIT_V2189_SECURITY_P0_STAGE_FIX_LIVE_VALIDATION_2026-06-10.md`.
- Fresh local security scan:
  `docs/security/scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md`
  (`PASS=10`, `WARN=1`, `FAIL=0`).
- Promotion precheck:
  `docs/reports/NATIVE_INIT_V2189_PROMOTION_PRECHECK_2026-06-10.md`.
- Status: eligible for explicit baseline promotion; current promoted baseline
  remains V2187 until the promotion report and baseline pointer updates land.

## Priority 0: Commit Hygiene

Goal: keep the current workspace reviewable before more live tests.

Status: complete for the current `v2187-screenapp-ui-validation` baseline.

Completed audit:

- Latest focused committed unit before this TODO cleanup:
  `53ee87ca Add QA metadata contracts to active runners`.
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

Status: complete for the current `v2187-screenapp-ui-validation` baseline.

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
  - V2187 passed `screenapp` framebuffer validation and is now the promoted
    rollback baseline.
- Primary evidence reports:
  - `docs/reports/NATIVE_INIT_V2176_WIFI_DHCP_STABILITY_N3_2026-06-08.md`;
  - `docs/reports/NATIVE_INIT_V2177_WIFI_HOLD_RECONNECT_LIVE_VALIDATION_2026-06-09.md`;
  - `docs/reports/NATIVE_INIT_V2179_V2178_WIFI_PROFILE_AUTOCONNECT_BASELINE_PROMOTION_2026-06-09.md`;
  - `docs/reports/NATIVE_INIT_V2184_PHONE_WIFI_LARGE_TRANSFER_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2185_NETWORK_PING_BASELINE_PROMOTION_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2186_WIFI_UI_POLISH_BASELINE_PROMOTION_2026-06-10.md`;
  - `docs/reports/NATIVE_INIT_V2187_SCREENAPP_UI_VALIDATION_BASELINE_PROMOTION_2026-06-10.md`.

Standing rules:

- Keep V2187 as the current baseline and rollback image until a newer boot image
  is intentionally promoted.
- Keep V2186, V2185, V2178, and V2169 as older conservative fallbacks only.
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
- Optional physical button/OCR validation for `NETWORK > PING TEST`; V2187
  already has command-level framebuffer evidence for the same draw path.

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

Status: current source-root is clean.

Completed:

- Current inventory report:
  `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-10.md`.
- Current source-root state:
  - `43 active`;
  - `6 module`;
  - `0 archive`;
  - `0 delete-review`.
- Active live metadata gaps are closed:
  - phase timer markers: `0`;
  - residual-state metadata: `0`;
  - phase-timer-exempt live utilities: `2`;
  - residual-state-exempt live utilities/helpers: `3`.
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
- Keep V2187 fixed as current baseline until that promotion happens.

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

1. Promote V2189 only through an explicit promotion report and baseline pointer
   updates; do not silently replace V2187.
2. Defer architecture source cleanup until after the security baseline
   promotion, unless a cleanup patch is kept separate and validation-neutral.
3. If serial `AT` noise naturally fires, confirm shared recovery evidence.
4. Run longer Wi-Fi/data-path soak only when new promotion criteria require it.

## Current Risk Register

| Risk | Current impact | Handling |
| --- | --- | --- |
| Boot autoconnect latency | Wi-Fi success can take roughly three minutes. | Poll `autoconnect.decision` until a terminal result; shared phase timers are live-validated for bounded current-baseline runners, but boot/reboot latency still needs separate timing if retested. |
| Serial `AT` noise | A single cmdv1 exchange can be malformed. | Shared recovery is implemented for safe commands; V2180 did not naturally fire the path, so live-fired evidence remains opportunistic. |
| Physical network-menu ping selection | V2187 has command-level framebuffer presentation evidence for `WIFI STATUS` and `WIFI PING RESULTS`, but not button-driven physical capture. | Treat as UI polish, not a baseline blocker; validate physically or with OCR only if visual-navigation evidence is required. |
| Large-transfer soak depth | V2184 passed 512MiB and 1GiB single-run bidirectional SHA checks, but not repeated N-run or multi-hour soak. | Treat as strong data-path evidence; run `cleanup -> reconnect -> 512MiB` or N-run soak only if promotion criteria require it. |
| UI completeness | V2187 is the current baseline and adds `screenapp` proof for the same network app draw paths while preserving V2186 Wi-Fi status/ping behavior. | Keep V2187 as baseline; physical button/OCR validation remains optional. |
| Script sprawl | Current source-root inventory is clean, but archive provenance remains large and older utility scripts still duplicate some transport/artifact logic. | Keep inventory current; migrate one active runner at a time; do not run archive scripts without focused migration/review. |
| Private data leakage | Wi-Fi profiles and raw run artifacts are intentionally private. | Keep secrets under ignored private roots; public reports stay redacted. |
