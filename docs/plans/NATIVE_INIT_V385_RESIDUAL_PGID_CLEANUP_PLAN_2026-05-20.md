# Native Init v385 Residual PGID Cleanup Plan

## Summary

- Target: `a90_android_execns_probe v16` under the existing native init `A90 Linux init 0.9.61 (v319)` device baseline.
- Scope: repair the v384 service-manager start-only postflight proof gap by adding residual process-group scan, final SIGKILL, and recheck evidence.
- Non-goals: no Wi-Fi HAL start, no Wi-Fi scan/connect/link-up, no service-manager live run without exact v385 approval, and no native boot image version bump.

## Background

v384 deployed helper v15 and captured ptrace-lite service-manager evidence. The compact live rerun proved:

- `servicemanager`: exec reached, SIGABRT crash context captured, helper postflight safe.
- `hwservicemanager`: observable until timeout, direct child reaped, but process-group postflight proof failed.
- Device postflight was clean from host perspective: no service-manager processes, no Wi-Fi links, selftest PASS.

The v385 hypothesis is that the helper needs stronger in-helper residual process-group evidence after direct child reap. If a process group remains observable after the direct child exits, the helper should scan it, send bounded final SIGKILL, poll for ESRCH, scan again, and report explicit fields.

## Implementation Plan

1. Update `stage3/linux_init/helpers/a90_android_execns_probe.c`:
   - bump helper marker to `a90_android_execns_probe v16`.
   - add `/proc` process-group scanner for `pid/state/comm` evidence.
   - in `run_service_manager_start_only_guarded_ptrace()`, after child reap and pipe drain:
     - check `kill(-pgid, 0)` only when `pgid > 1`.
     - if the process group still exists, emit `pgid_scan.before_final_kill` entries.
     - send one final `SIGKILL` to the process group.
     - poll up to 1000 ms for `ESRCH`.
     - emit `pgid_scan.after_final_kill` entries.
     - report `residual_kill_sent`, `residual_cleared`, `residual_before_count`, `residual_after_count`, and final `postflight_safe`.
2. Build local static ARM64 helper:
   - output: `tmp/wifi/v385-a90_android_execns_probe-v16/a90_android_execns_probe`.
   - expected SHA256: `4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8`.
3. Add fail-closed host wrappers:
   - `scripts/revalidation/wifi_execns_helper_v16_deploy_preflight.py`
   - `scripts/revalidation/wifi_service_manager_start_only_v385_live_runner.py`
   - `scripts/revalidation/wifi_v385_deploy_live_executor.py`
4. Preserve v384 compact-argv behavior:
   - the underlying live runner may drop only `--data-wifi-mode private-empty` when needed to keep native shell command length within 30 args.
   - service-manager start-only path does not require `/data/vendor/wifi`.

## Approval Gates

Deploy approval phrase:

```text
approve v385 deploy execns helper v16 only; no daemon start and no Wi-Fi bring-up
```

Live approval phrase:

```text
approve v385 service-manager residual pgid cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Without these exact phrases plus `--apply --assume-yes`, v385 wrappers must not mutate the device or start service-manager processes.

## Test Plan

Local/static:

```bash
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra \
  -o tmp/wifi/v385-a90_android_execns_probe-v16/a90_android_execns_probe \
  stage3/linux_init/helpers/a90_android_execns_probe.c
sha256sum tmp/wifi/v385-a90_android_execns_probe-v16/a90_android_execns_probe
strings tmp/wifi/v385-a90_android_execns_probe-v16/a90_android_execns_probe | rg 'a90_android_execns_probe v16|residual|pgid_scan|ptrace-lite'
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v16_deploy_preflight.py scripts/revalidation/wifi_service_manager_start_only_v385_live_runner.py scripts/revalidation/wifi_v385_deploy_live_executor.py scripts/revalidation/wifi_service_manager_start_only_live_runner.py scripts/revalidation/a90ctl.py
git diff --check
```

No-approval behavior:

```bash
python3 scripts/revalidation/wifi_v385_deploy_live_executor.py --out-dir tmp/wifi/v385-plan-YYYYmmdd-HHMMSS plan
python3 scripts/revalidation/wifi_v385_deploy_live_executor.py --out-dir tmp/wifi/v385-noapproval-live-YYYYmmdd-HHMMSS live
python3 scripts/revalidation/wifi_execns_helper_v16_deploy_preflight.py --out-dir tmp/wifi/v385-noapproval-deploy-YYYYmmdd-HHMMSS run
python3 scripts/revalidation/wifi_service_manager_start_only_v385_live_runner.py --out-dir tmp/wifi/v385-live-preflight-YYYYmmdd-HHMMSS preflight
```

Approved live sequence, only after explicit approval:

```bash
python3 scripts/revalidation/wifi_v385_deploy_live_executor.py \
  --out-dir tmp/wifi/v385-approved-full-YYYYmmdd-HHMMSS \
  --deploy-approval-phrase 'approve v385 deploy execns helper v16 only; no daemon start and no Wi-Fi bring-up' \
  --live-approval-phrase 'approve v385 service-manager residual pgid cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up' \
  --apply --assume-yes full
```

## Acceptance Criteria

- Local helper builds and contains v16 marker plus residual PGID evidence strings.
- No-approval executor paths report no device mutation, no daemon start, and no Wi-Fi bring-up.
- Deploy preflight blocks until helper v16 is installed.
- Live preflight blocks until helper v16 is installed and exact approval is supplied.
- Approved v385 live evidence either proves `hwservicemanager` process-group cleanup or records bounded residual process evidence sufficient for the next classifier step.
