# Native Init Current TODO

Date: `2026-06-09`

This is the active TODO map for the current native-init baseline hardening
cycle. It is intentionally higher-level than per-run reports and lower-level
than the long-term roadmap.

Current baseline:

- Device baseline: `A90 Linux init 0.9.253 (v2178-wifi-profile-autoconnect)`.
- Promotion run: `V2179`; boot SHA256
  `8ea6f468f997446e9fa3e80606db107ca27d067f3ee023ff45c2ecf159341047`.
- Immediate rollback image:
  `workspace/private/inputs/boot_images/boot_linux_v2174_wifi_urandom_connect.img`.
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

## Priority 0: Commit Hygiene

Goal: keep the current workspace reviewable before more live tests.

- Review uncommitted Wi-Fi config changes separately from bridge/transport
  changes.
- Keep generated logs, boot images, firmware, credentials, and raw captures out
  of git.
- Commit in focused units:
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

Goal: turn "wlan0 can scan/connect" into a repeatable baseline feature.

Completed first units:

- `wifi config status` exists as a read-only config/secret validator.
- `wifi config prepare [profile]` exists as an explicit, non-boot supplicant
  config generator.
- `wifi status` exists as a read-only native-init status/UI primitive.
- `wifi scan [delay_ms]` exists as a bounded credential-free nl80211 scan
  primitive.
- `wifi connect [profile]` exists at source level as a bounded
  association/carrier primitive.
- `wifi dhcp [profile]` exists at source level as a bounded DHCP/temporary
  route-DNS primitive that requires carrier first.
- `wifi cleanup` exists at source level for repeated connectivity tests.
- V2176 source/build and live validation entrypoints exist:
  - `workspace/public/src/scripts/revalidation/build_native_init_boot_v2176_wifi_dhcp.py`;
  - `workspace/public/src/scripts/revalidation/native_wifi_dhcp_ping_handoff_v2176.py`.
- `v2176-wifi-dhcp` live validation passed:
  - flashed V2176 test boot on top of V2174 baseline;
  - ran carrier connect, DHCP, one bounded external ping, cleanup, and rollback;
  - reached `wifi-connect-carrier-up`, `wifi-dhcp-pass`, and ping rc `0`;
  - verified cleanup removed test DHCP/DNS residue;
  - rolled back to `v2174-wifi-urandom-connect`;
  - final rollback `selftest fail=0`.
- `v2176-wifi-dhcp` final-code N=3 stability validation passed:
  - all three runs selected `tcpctl`;
  - all three reached carrier, DHCP, bounded ping rc `0`, cleanup success, and
    rollback selftest success;
  - aggregate report:
    `docs/reports/NATIVE_INIT_V2176_WIFI_DHCP_STABILITY_N3_2026-06-08.md`.
- `v2177-wifi-hold-reconnect` live validation passed:
  - flashed V2176 test boot on top of the V2174 baseline;
  - ran carrier connect, DHCP, 180 second hold/idle sampling, one bounded
    external ping, cleanup, reconnect, DHCP, one bounded external ping, final
    cleanup, and rollback;
  - held carrier/route/resolv through all six hold samples and final ping rc
    `0`;
  - reconnected after cleanup with `wpa_state=COMPLETED`, carrier `1`, DHCP
    pass, and ping rc `0`;
  - rolled back to `v2174-wifi-urandom-connect`;
  - final rollback `selftest fail=0`;
  - report:
    `docs/reports/NATIVE_INIT_V2177_WIFI_HOLD_RECONNECT_LIVE_VALIDATION_2026-06-09.md`.
- `v2174-wifi-urandom-connect` live validation passed:
  - prior V2173 no-carrier evidence isolated the connect blocker to missing
    `/dev/urandom` during WPA SNonce generation;
  - native `/dev` bootstrap now creates `/dev/random` and `/dev/urandom`;
  - flashed V2174 test boot;
  - reached `wpa_state=COMPLETED` and `carrier=1`;
  - preserved `credentials_logged=0`, `secret_values_logged=0`,
    `dhcp_routing=0`, and `external_ping=0`;
  - rolled back to `v2169-transport-contract`;
  - final rollback `selftest fail=0`.
- `v2174-wifi-urandom-connect` was promoted as the current baseline by V2175:
  - flashed the same V2174 boot image as the persistent baseline;
  - verified device-visible version
    `A90 Linux init 0.9.251 (v2174-wifi-urandom-connect)`;
  - verified boot partition readback SHA
    `cda957e4302d66e407fc97a95932501f0ef2ac655ee264c94519111fece0b3ba`;
  - verified `transport.contract=1`, NCM/tcpctl readiness, and
    `selftest fail=0`.
- `v2178-wifi-profile-autoconnect` was promoted as the current baseline by V2179:
  - fixed stale autoconnect result/log state, profile-list duplicate display,
    and Wi-Fi status/HUD decision surfacing;
  - flashed patched V2178 boot image SHA
    `8ea6f468f997446e9fa3e80606db107ca27d067f3ee023ff45c2ecf159341047`;
  - verified disabled boot reports `wifi-autoconnect-disabled` without stale
    `wifi-autoconnect-pass`;
  - verified boot autoconnect N=3, all `wifi-autoconnect-pass`, carrier `1`,
    DHCP final rc `0`, no external ping;
  - verified private 2.4 GHz and 5 GHz profiles with `wifi autoconnect once`,
    carrier plus DHCP pass, and `secret_values_logged=0`;
  - rolled back to V2174 during validation and verified rollback
    `selftest fail=0`;
  - flashed V2178 again as the current baseline with autoconnect disabled and
    final `selftest fail=0`;
  - promotion report:
    `docs/reports/NATIVE_INIT_V2179_V2178_WIFI_PROFILE_AUTOCONNECT_BASELINE_PROMOTION_2026-06-09.md`.
- `v2172-wifi-status-scan` live validation passed:
  - corrected the test boot to reuse verified V726 private-property snapshot;
  - flashed test boot;
  - verified `wlan0_present=1`;
  - ran bounded direct nl80211 scan with `scan_result_count=12`;
  - preserved `credentials=0`, `connect=0`, `dhcp_routing=0`,
    `external_ping=0`;
  - rolled back to `v2169-transport-contract`;
  - final rollback `selftest fail=0`.
- `v2170-wifi-config-prepare` source build passed on top of
  `v2169-transport-contract`.
- `v2170-wifi-config-prepare` live validation passed:
  - flashed test boot;
  - generated a synthetic redacted supplicant config;
  - preserved `secret_values_logged=0`;
  - cleaned up runtime config residue;
  - rolled back to `v2169-transport-contract`;
  - final rollback `selftest fail=0`.

Open tasks:

- Keep V2178 as the profile/autoconnect baseline and V2174 as immediate
  rollback until a newer boot image is intentionally promoted.
- Keep private Wi-Fi profile/secret files out of public git; use
  `workspace/public/src/scripts/revalidation/a90_wifi_profile_stage.py` for
  staging and keep raw SSID/PSK under ignored private roots.
- Improve boot-autoconnect latency observability:
  - firmware/helper window dominates and can take roughly three minutes;
  - status runners must poll `autoconnect.decision=wifi-autoconnect-running`
    until a terminal result.
- Harden serial bridge retry behavior against intermittent `AT` noise:
  - V2179 proved bridge restart/retry is sufficient for live validation;
  - shared runner helpers should keep this behavior instead of failing the full
    run on one malformed cmdv1 exchange.
- Continue UI polish beyond the P3 minimum:
  - optional redacted SSID display mode;
  - RSSI/link quality when available from supplicant status;
  - clearer disabled/running/pass/fail labels on the HUD.
- Keep secondary interface noise out of the main gate:
  - `swlan0` MAC generation failure is not a primary `wlan0` blocker;
  - `set_features(-11)` remains non-blocking unless reproduced as persistent.

Exit criteria:

- V2178 profile/autoconnect baseline promotion is complete by V2179.
- Boot autoconnect N=3 passed with carrier and DHCP, no external ping.
- Private 2.4 GHz and 5 GHz profile checks passed with redacted evidence.
- `selftest fail=0` after rollback/promotion validation.
- Secret scan reports no leaked PSK.
- Public report contains redacted Wi-Fi evidence only.

## Priority 2: Bridge And Transport

Goal: make every runner use the same bridge/NCM/tcpctl decision path.

Completed first units:

- `a90_bridge.py` wrapper exists for bridge lifecycle:
  - `preflight`;
  - `status`;
  - `ensure`;
  - `start`;
  - `stop`;
  - `restart`;
  - `doctor`;
  - `repair-dirs`.
- `a90_transport.py` exists as the first shared selector module.
- `a90_ncm_transport_smoke.py` records transport selection into its manifest.
- Selector manifest includes `selector_contract=1`.
- Bridge status includes `wrapper_contract=1`.
- Boot/bridge/communication contract is documented in
  `docs/operations/NATIVE_INIT_BOOT_TRANSPORT_CONTRACT.md`.
- Transport selector has bounded host NCM link-local auto-repair for the
  Samsung `04e8` + `cdc_ncm` present/no-`fe80::` state.
- Current `v2178-wifi-profile-autoconnect` baseline preserves the device-side
  `transport.contract=1` contract from V2174/V2169.
- Active Wi-Fi lifecycle runners use the shared transport selector/serial step:
  - `native_wifi_connect_carrier_handoff_v2174.py` uses
    `a90_transport.select_transport()` for preflight and
    `a90_transport.run_serial_step()` for cmdv1 commands;
  - `native_wifi_dhcp_ping_handoff_v2176.py` inherits the V2174 command path
    and already records `transport_selection`.
- Baseline validation runner transport migration is complete:
  - `a90_v725_fasttransport_baseline_validation.py` now uses
    `a90_transport.select_transport()` and recovered serial cmdv1 probes.
- Transport commonization implementation is in place:
  - `a90_transport.phase()` records `phase_timer_contract=1` and
    `phase_timers[]` using a monotonic elapsed clock;
  - `a90_transport.run_serial_command_recovered()` records
    `serial_recovery_contract=1` and structured recovery evidence;
  - protocol-noise recovery can restart the managed bridge once and retry safe
    commands once;
  - V2174 carrier, V2176 DHCP/ping, V2177 hold/reconnect, and V725 transport
    baseline runners now use the shared phase timer contract.
- Transport commonization live validation passed by V2180:
  - `a90_ncm_transport_smoke.py` recorded `phase_timer_contract=1`, selected
    `ncm`, and passed 1 MiB download plus upload;
  - `native_wifi_v2178_autoconnect_phase_validation.py` recorded
    `phase_timer_contract=1`, ran current-baseline `wifi autoconnect once`,
    cleaned up, restored autoconnect disabled, and ended with `selftest fail=0`;
  - report:
    `docs/reports/NATIVE_INIT_V2180_TRANSPORT_COMMONIZATION_LIVE_VALIDATION_2026-06-09.md`.

Open tasks:

- Stabilize `a90_transport.py` as the import target for active runners:
  - bridge ensure/status;
  - `cmdv1` version/status;
  - host NCM snapshot;
  - optional host NCM link-local repair;
  - selection manifest.
- Treat selector fields as the stable contract for migrated runners:
  - `selector_contract=1`;
  - `selected=serial|ncm|tcpctl`;
  - `fallback_reason=<label-or-null>`.
- Migrate one runner at a time:
  - NCM smoke first;
  - Wi-Fi lifecycle runner done;
  - baseline validation runner done.
- Live-validate serial `AT` noise recovery when it naturally fires:
  - recovery must appear in the relevant step metadata;
  - unsafe commands must still not replay unless explicitly scoped.
- Keep bridge warnings actionable:
  - `private_log_dir` / `private_run_dir` writable must be pass;
  - `port_pid_resolution=cmdline-fallback` is acceptable when bridge is already
    running and process ownership blocks `/proc/*/fd` inspection.

Exit criteria:

- Active smoke runner works with NCM ready.
- Same runner records explicit serial fallback when NCM is absent.
- No runner directly starts `serial_tcp_bridge.py` unless testing the bridge
  implementation itself.
- Bridge artifacts land under `workspace/private/logs/bridge/`.

## Priority 3: Test Script Inventory And Consolidation

Goal: stop accumulating one-off scripts that duplicate transport and artifact
logic.

Inventory labels:

| Label | Meaning | Action |
| --- | --- | --- |
| `active` | Current entrypoint used by baseline/live work | Keep in `workspace/public/src/scripts/revalidation/` |
| `module` | Shared import-only helper | Keep in current script tree or move to harness |
| `archive` | Historical/provenance script still referenced by docs/reports | Move or keep under `workspace/public/archive/scripts/` |
| `delete-review` | Generated, broken, duplicate, or unreferenced one-off | Review before deleting |

Open tasks:

- Keep the inventory current when active entrypoints move.
- For each script, continue to record:
  - purpose;
  - last known baseline/run;
  - import dependencies;
  - docs/reports references;
  - live-device requirement;
  - secret/log handling.
- Identify duplicated logic:
  - bridge command construction;
  - `a90ctl.py` subprocess wrappers;
  - NCM readiness;
  - FastUpload/archive handling;
  - phase timing;
  - manifest writing;
  - redaction/secret scan.
- Move only after classification:
  - active scripts stay stable;
  - V2167 historical runner moved to
    `workspace/public/archive/scripts/revalidation/native_wifi_connect_dhcp_google_ping_handoff_v2167.py`;
  - delete-review items require a focused cleanup commit.

Exit criteria:

- A generated inventory report exists under `docs/reports/` or `workspace/public`
  as redacted metadata.
- Current inventory report:
  `docs/reports/REVALIDATION_SCRIPT_INVENTORY_2026-06-08.md`.
- V2167 is no longer a current entrypoint; it is archived under
  `workspace/public/archive/scripts/revalidation/`.
- Active entrypoints list in `workspace/public/src/scripts/revalidation/README.md`
  matches the actual current set.
- New scripts use shared modules instead of reimplementing bridge/NCM logic.

## Priority 4: Baseline And Versioning

Goal: avoid mixing run IDs, helper versions, and boot baseline tags.

Open tasks:

- Keep current baseline fixed as `v2178-wifi-profile-autoconnect` until a newer boot
  image is intentionally promoted.
- If a new boot/init image is promoted, use the next global run/build identity,
  not helper numbering.
- Record all axes in reports:
  - run ID;
  - native init semantic version;
  - build tag;
  - helper version;
  - boot image path;
  - boot SHA256;
  - host commit.
- Keep rollback image path and SHA current in the runbook.

Exit criteria:

- New baseline report names the exact artifact and SHA.
- Rollback to the prior baseline is verified with `selftest fail=0`.
- README and runbook agree on latest verified baseline.

## Priority 5: Workspace Structure

Goal: make a fresh clone usable while keeping private/generated payloads out of
git.

Open tasks:

- Keep public source, scripts, redacted reports, templates, and inventories in
  `workspace/public/` and `docs/`.
- Keep private/generated artifacts in:
  - `workspace/private/inputs/`;
  - `workspace/private/builds/`;
  - `workspace/private/logs/`;
  - `workspace/private/secrets/`.
- Keep `tmp/` structured:
  - `tmp/wifi/runs/` for live Wi-Fi evidence;
  - `tmp/wifi/bench/` for transport smoke;
  - `tmp/logs/` for cross-run logs.
- Avoid new root-level payload folders.
- Decide later whether old `tmp/` evidence should be archived, compressed, or
  deleted; do not mix that cleanup into Wi-Fi or transport commits.

Exit criteria:

- New runner outputs use structured paths.
- A fresh clone plus private inputs can rebuild/test the current workflow.
- No new unstructured root payload directories appear.

## Priority 6: QA And Stability

Goal: define when a feature is strong enough to become baseline behavior.

Open tasks:

- Add or reuse smoke checks for:
  - bridge;
  - NCM;
  - transport selector;
  - Wi-Fi connect;
  - cleanup;
  - rollback selftest.
- Add repeated-run evidence:
  - N>=3 for basic stability is complete for the V2176 route;
  - 180 second hold/idle plus cleanup/reconnect is complete for the V2176
    route.
- Capture residual state:
  - bridge process;
  - NCM interface;
  - supplicant process;
  - generated configs;
  - runtime logs.
- Treat cleanup failure as a real baseline risk if it affects the next run.

Exit criteria:

- Repeated runs do not rely on stale state.
- Cleanup is either successful or explicitly harmless.
- Phase timers identify where wall time is spent.

## Priority 7: Security And Safety Scope

Goal: keep the lab workflow powerful but bounded.

Open tasks:

- Keep bridge bound to localhost.
- Do not add authentication bypasses or external exposure for convenience.
- Keep Wi-Fi credentials private and environment/file based.
- Keep raw captures private unless redacted.
- Preserve blocked operations unless explicitly scoped:
  - PMIC/GPIO/GDSC/regulator writes;
  - eSoC notify/BOOT_DONE;
  - PCI rescan;
  - platform bind/unbind;
  - unbounded external network tests.
- Avoid automatic retry of unsafe root commands.

Exit criteria:

- Public docs do not contain secrets or raw private identifiers.
- Runners fail closed on secret leakage.
- Safety scope is stated in live reports.

## Suggested Next Sequence

1. If serial `AT` noise fires, confirm the shared recovery evidence is present;
   otherwise keep it as a ready-but-not-live-fired path.
2. Polish Wi-Fi status/HUD output on top of the promoted V2178 baseline:
   redacted SSID display, RSSI/link quality, and clearer
   disabled/running/pass/fail labels.
3. Refresh the script inventory after each active runner migration and continue
   deleting or archiving only classified one-off scripts.
4. Run a longer Wi-Fi soak only after runner timing/retry instrumentation is in
   place, or when a new baseline promotion needs additional stability evidence.

## Current Risk Register

| Risk | Current impact | Handling |
| --- | --- | --- |
| Boot autoconnect latency | Wi-Fi success can take roughly three minutes. | Poll `autoconnect.decision` until a terminal result; shared phase timers are live-validated for bounded current-baseline runners, but boot/reboot latency still needs separate timing if retested. |
| Serial `AT` noise | A single cmdv1 exchange can be malformed. | Shared recovery is implemented for safe commands; V2180 did not naturally fire the path, so live-fired evidence remains opportunistic. |
| UI completeness | Baseline works, but operator-facing status is still sparse. | Add redacted SSID, RSSI/link quality, and clearer state labels. |
| Script sprawl | Older one-off runners still duplicate transport/artifact logic. | Keep inventory current; migrate one active runner at a time. |
| Private data leakage | Wi-Fi profiles and raw run artifacts are intentionally private. | Keep secrets under ignored private roots; public reports stay redacted. |
