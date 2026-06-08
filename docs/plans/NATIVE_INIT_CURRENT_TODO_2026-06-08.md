# Native Init Current TODO

Date: `2026-06-08`

This is the active TODO map for the current native-init baseline hardening
cycle. It is intentionally higher-level than per-run reports and lower-level
than the long-term roadmap.

Current baseline:

- Device baseline: `A90 Linux init 0.9.247 (v2169-transport-contract)`.
- Active control path: USB ACM serial bridge managed by
  `workspace/public/src/scripts/revalidation/a90_bridge.py`.
- Active fast path: USB NCM link-local plus bounded FastUpload-style transfers.
- Standing boot/bridge/communication contract:
  `docs/operations/NATIVE_INIT_BOOT_TRANSPORT_CONTRACT.md`.
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

- Promote or rebase the next Wi-Fi test unit on V2174:
  - use `workspace/public/src/scripts/revalidation/native_wifi_connect_carrier_handoff_v2174.py` as the carrier-level safety baseline;
  - keep DHCP/routes/ping out of carrier validation;
  - preserve rollback to `v2169-transport-contract` until a new baseline is explicitly promoted.
- Finish remaining native Wi-Fi config/autoconnect design:
  - credential source under `workspace/private/secrets/`;
  - profile creation/listing operator commands;
  - no raw PSK or generated supplicant config in public git;
  - explicit boot-autoconnect gate.
- Add boot-time or operator-triggered autoconnect option.
- V2171 supplicant dependency probe completed:
  `supplicant-dependency-standalone-only-ctrl-ready`. Native `wifi connect`
  should keep the staged standalone `wpa_supplicant` route; vendor supplicant
  paths were absent in the native namespace.
- V2172 source build completed:
  `v2172-wifi-status-scan-source-build-pass`.
- Verify both target bands:
  - private 2.4 GHz test SSID from
    `workspace/private/secrets/a90-wifi-test.env`;
  - private 5 GHz test SSID from
    `workspace/private/secrets/a90-wifi-test.env`;
  - same password source, no duplicated secret storage.
- Run bounded stability checks:
  - connect;
  - DHCP;
  - one bounded ping target when explicitly in Wi-Fi connectivity scope;
  - hold/idle;
  - disconnect/reconnect.
- Add UI status surface:
  - Wi-Fi enabled/disabled;
  - SSID redacted or configured display mode;
  - RSSI/link quality;
  - MAC/IP redacted or local-only;
  - scan/connect state;
  - error label.
- Keep secondary interface noise out of the main gate:
  - `swlan0` MAC generation failure is not a primary `wlan0` blocker;
  - `set_features(-11)` remains non-blocking unless reproduced as persistent.

Exit criteria:

- N>=3 repeated connect cycles without cleanup-dependent success.
- `selftest fail=0` after the run.
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
- Current `v2169-transport-contract` baseline emits device-side
  `transport.contract=1`.

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
  - Wi-Fi lifecycle runner next;
  - baseline validation runner after that.
- Add phase timers to live runners:
  - `flash`;
  - `boot_wait`;
  - `helper_stage`;
  - `connect_window`;
  - `artifact_upload`;
  - `rollback`;
  - `selftest`.
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

- Generate an inventory for `workspace/public/src/scripts/revalidation/`.
- For each script, record:
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
  - historical scripts move to archive with references preserved;
  - delete-review items require a focused cleanup commit.

Exit criteria:

- A generated inventory report exists under `docs/reports/` or `workspace/public`
  as redacted metadata.
- Active entrypoints list in `workspace/public/src/scripts/revalidation/README.md`
  matches the actual current set.
- New scripts use shared modules instead of reimplementing bridge/NCM logic.

## Priority 4: Baseline And Versioning

Goal: avoid mixing run IDs, helper versions, and boot baseline tags.

Open tasks:

- Keep current baseline fixed as `v2169-transport-contract` until a newer boot
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
  - N>=3 for basic stability;
  - longer hold/idle only after cleanup is deterministic.
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

1. Decide whether to promote V2174 as the next Wi-Fi-capable test baseline.
2. Add the separate DHCP/route/ping-scoped command or runner only after
   carrier-level connect passes.
3. Migrate the Wi-Fi lifecycle runner to `a90_transport.py`.
4. Add phase timers to Wi-Fi live runners.
5. Generate a script inventory and classify active/module/archive/delete-review.
6. Run N>=3 Wi-Fi lifecycle stability checks.
7. Decide whether to promote the next boot/init baseline.
