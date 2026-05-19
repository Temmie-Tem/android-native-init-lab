# Native Init v386 Compact Ptrace Capture Plan

## Summary

v386 keeps the current `A90 Linux init 0.9.61 (v319)` device baseline and updates only the Android exec namespace helper/tooling. The target helper is `a90_android_execns_probe v17`.

The v385 approved run showed that residual cleanup is proven for `servicemanager`, but `hwservicemanager` emits enough ptrace-lite snapshot output over USB ACM serial that host tooling misses `A90P1 END` and never receives the machine-readable `service_manager_start.*` summary. v386 fixes the capture path before any Wi-Fi HAL/start/scan/connect step.

## Scope

- Add compact service-manager ptrace capture in `stage3/linux_init/helpers/a90_android_execns_probe.c`.
- Keep `--capture-mode ptrace-lite` as the public mode to avoid increasing native shell argv count.
- Preserve verbose ptrace behavior for non-service-manager paths unless explicitly touched later.
- Add v386 deploy/live wrappers that require new exact approval phrases.
- No Wi-Fi HAL start, no scan/connect/link-up, no credentials, no DHCP/routing, no rfkill writes, no firmware mutation.

## Design

### Compact Service-Manager Snapshot

For service-manager start-only mode, `ptrace-lite` should print only bounded summary fields while the child is stopped:

- target pid/pgid and `exe`/`cwd` symlink values.
- signal info for crash stops.
- `NT_PRSTATUS` byte count only, not full register words.
- `auxv`, `status`, `maps`, and `mountinfo` byte/line/truncation summaries only, not raw file contents.
- existing `service_manager_start.*` lifecycle fields and residual process-group cleanup fields.

Raw `/proc/<pid>/maps` and `/proc/<pid>/mountinfo` contents are the main serial bottleneck, so v386 must not emit them on the service-manager live path.

### Approval Boundary

New exact phrases are required:

```text
approve v386 deploy execns helper v17 only; no daemon start and no Wi-Fi bring-up
approve v386 service-manager compact ptrace capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

The deploy phrase may only install `/cache/bin/a90_android_execns_probe`. The live phrase may only run bounded service-manager start-only probes for `servicemanager` and `hwservicemanager`.

## Validation

Static/local:

```bash
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v386-a90_android_execns_probe-v17/a90_android_execns_probe
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v17_deploy_preflight.py \
  scripts/revalidation/wifi_service_manager_start_only_v386_live_runner.py \
  scripts/revalidation/wifi_v386_deploy_live_executor.py
git diff --check
```

No-approval gates:

```bash
python3 scripts/revalidation/wifi_execns_helper_v17_deploy_preflight.py plan
python3 scripts/revalidation/wifi_service_manager_start_only_v386_live_runner.py plan
python3 scripts/revalidation/wifi_v386_deploy_live_executor.py plan
```

Approved live validation, only after explicit user approval:

```bash
python3 scripts/revalidation/wifi_v386_deploy_live_executor.py \
  --deploy-approval-phrase 'approve v386 deploy execns helper v17 only; no daemon start and no Wi-Fi bring-up' \
  --live-approval-phrase 'approve v386 service-manager compact ptrace capture only; no Wi-Fi HAL start and no Wi-Fi bring-up' \
  --apply --assume-yes full
```

Acceptance:

- helper marker is `a90_android_execns_probe v17`.
- `hwservicemanager` capture returns `A90P1 END` within host timeout.
- both targets include machine-readable `service_manager_start.*` summary fields.
- postflight has no manager residual process and no Wi-Fi link.
- result can be classified without bridge-tail manual recovery.

## Next Step

If v386 live proof passes or reaches a clearly classified runtime gap, continue with the next service-manager runtime blocker. If compact output still times out, the next fix is host/device timeout alignment or writing verbose capture to a private file rather than serial stdout.
