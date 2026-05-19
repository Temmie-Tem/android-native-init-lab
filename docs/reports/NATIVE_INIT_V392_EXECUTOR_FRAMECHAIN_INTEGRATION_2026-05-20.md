# Native Init v392 Executor Framechain Integration

## Summary

V392 one-shot executor now automatically runs the host-only frame-chain analyzer after an approved service-manager start-only live run returns `service-manager-start-only-live-runtime-gap`.

This keeps the operator loop continuous after V392 live evidence: deploy helper v21, run bounded service-manager start-only capture, classify the runtime gap, parse frame-chain evidence, and route the next action from one executor manifest.

This update does not deploy helper v21, does not start service-manager daemons, and does not attempt Wi-Fi bring-up.

## Changed Tooling

- executor: `scripts/revalidation/wifi_v392_deploy_live_executor.py`
- analyzer: `scripts/revalidation/wifi_service_manager_framechain_analyze.py`

New executor behavior:

- adds `planned_framechain_command`
- records the frame-chain analyzer command in `summary.md`
- after approved V392 live runtime-gap:
  - runs `wifi_service_manager_runtime_gap_classifier.py`
  - runs `wifi_service_manager_framechain_analyze.py`
  - returns the frame-chain decision as the top-level V392 executor route when available

Expected top-level post-live routes:

- `v392-deploy-live-executor-full-service-manager-framechain-symbolization-pass`
- `v392-deploy-live-executor-full-service-manager-framechain-maprow-ready`
- `v392-deploy-live-executor-full-service-manager-framechain-no-maprow`
- `v392-deploy-live-executor-full-service-manager-framechain-needs-v392-live`

## Validation

Static validation:

```text
python3 -m py_compile scripts/revalidation/wifi_v392_deploy_live_executor.py scripts/revalidation/wifi_service_manager_framechain_analyze.py
git diff --check
```

Result: PASS.

No-approval executor validation:

```text
python3 scripts/revalidation/wifi_v392_deploy_live_executor.py \
  --out-dir tmp/wifi/v392-executor-framechain-noapproval \
  full
```

Result:

```text
decision: v392-deploy-live-executor-approval-required
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Plan validation:

```text
python3 scripts/revalidation/wifi_v392_deploy_live_executor.py \
  --out-dir tmp/wifi/v392-executor-framechain-plan \
  plan
```

Result:

```text
decision: v392-deploy-live-executor-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
planned_framechain_command: present
```

Host-only integration smoke using V390 runtime-gap evidence:

- evidence: `tmp/wifi/v392-executor-framechain-classify-smoke/`
- final evidence: `tmp/wifi/v392-executor-framechain-classify-smoke-final/`
- classifier decision: `service-manager-runtime-gap-servicemanager-sigabrt-captured`
- framechain decision: `service-manager-framechain-needs-v392-live`
- returned route: `service-manager-framechain-needs-v392-live`
- device commands/mutations/daemon/Wi-Fi actions: none

Read-only device health after the integration change:

- evidence: `tmp/wifi/v392-post-integration-readonly-20260520-071002/`
- `version`: `A90 Linux init 0.9.61 (v319)`
- `status`: PASS, `selftest: pass=11 warn=1 fail=0`
- `selftest`: PASS, `pass=11 warn=1 fail=0`

## Current Blocker

V392 live execution still requires exact approval phrases:

```text
approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up
```

```text
approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

Until those are provided, the executor remains fail-closed and Wi-Fi HAL/start/scan/connect remains blocked.
