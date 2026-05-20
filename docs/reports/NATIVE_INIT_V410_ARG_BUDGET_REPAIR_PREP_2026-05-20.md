# Native Init v410 Registration Query Arg-Budget Repair Prep

## Summary

V410 supersedes V409 before live deploy.

The V409 approved query command stayed under the native shell argument limit by
dropping `--data-wifi-mode private-empty`.  V410 repairs this by moving the
private-empty Wi-Fi data boundary into helper v26 defaults for
`wifi-hal-composite-lshal-list`.

No helper deploy, daemon start, HAL start, `lshal` execution, or Wi-Fi bring-up
was executed in V410 prep.

## Build Evidence

Helper v26:

```text
artifact: tmp/wifi/v410-a90_android_execns_probe-v26/a90_android_execns_probe
sha256: daf1b59e2475c0db28fb99eb83f8be02a46f695d8c4e435c47e68f45370a7caa
file: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
dynamic section: none
```

Required strings:

```text
a90_android_execns_probe v26
wifi-hal-composite-lshal-list
private-empty
--allow-hal-service-query
```

## Arg-Budget Evidence

V409 approved plan argcheck:

```text
evidence: tmp/wifi/v409-registration-query-approved-plan-argcheck-20260520-104659/
decision: v409-hal-registration-query-plan-ready
command_len: 29
has_data_wifi: False
has_query_guard: True
```

Interpretation: V409 would have relied on omitting `--data-wifi-mode
private-empty`.  It is therefore superseded before live deploy.

V410 approved plan argcheck:

```text
evidence: tmp/wifi/v410-registration-query-approved-plan-argcheck-20260520-104923/
decision: v410-hal-registration-query-plan-ready
command_len: 29
has_data_wifi_arg: False
implicit_data_wifi: private-empty
has_query_guard: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

The approved command remains under the 30-argument limit while helper v26 keeps
the private Wi-Fi data boundary.

V410 arg-budget contract linter:

```text
script: scripts/revalidation/wifi_v410_arg_budget_linter.py
evidence: tmp/wifi/v410-arg-budget-linter-privatewrite-20260520-110025/
decision: v410-arg-budget-contract-pass
pass: True
reason: all V410 arg-budget contract checks passed
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

The linter checks the helper source, V410 runner, V410 deploy wrapper, and the
approved-plan manifest together.  It proves:

```text
helper-v26-version: pass
helper-implicit-data-wifi-default: pass
helper-data-wifi-allowlist: pass
runner-v26-sha: pass
runner-records-implicit-contract: pass
deploy-v26-sha-and-guard: pass
approved-command-arg-budget: pass
approved-command-query-guard: pass
approved-command-uses-implicit-data-wifi: pass
approved-plan-no-device-command: pass
```

The linter writes evidence with private output handling:

```text
700 tmp/wifi/v410-arg-budget-linter-privatewrite-20260520-110025
600 tmp/wifi/v410-arg-budget-linter-privatewrite-20260520-110025/manifest.json
600 tmp/wifi/v410-arg-budget-linter-privatewrite-20260520-110025/README.md
```

V409 superseded fail-closed wrappers:

```text
script: scripts/revalidation/wifi_execns_helper_v25_deploy_preflight.py
evidence: tmp/wifi/v409-helper-v25-deploy-superseded-20260520-111400/
decision: v409-superseded-by-v410
device_commands_executed: False
device_mutations: False
```

```text
script: scripts/revalidation/wifi_hal_registration_query_v409_runner.py
evidence: tmp/wifi/v409-registration-query-superseded-20260520-111400/
decision: v409-superseded-by-v410
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

## Fail-Closed Evidence

V410 helper deploy plan:

```text
evidence: tmp/wifi/v410-helper-v26-deploy-plan-20260520-104934/
decision: execns-helper-v26-deploy-plan-ready
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

V410 helper deploy read-only preflight:

```text
evidence: tmp/wifi/v410-helper-v26-deploy-readonly-preflight-20260520-104934/
decision: execns-helper-v26-deploy-preflight-ready-needs-deploy
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

V410 helper deploy no-approval run:

```text
evidence: tmp/wifi/v410-helper-v26-deploy-noapproval-20260520-104934/
decision: execns-helper-v26-deploy-approval-required
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

V410 registration query no-approval run:

```text
evidence: tmp/wifi/v410-registration-query-noapproval-20260520-105350/
decision: v410-hal-registration-query-approval-required
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

V410 registration query read-only preflight:

```text
evidence: tmp/wifi/v410-registration-query-readonly-preflight-20260520-104934/
decision: v410-hal-registration-query-blocked
pass: False
reason: blocked before live run by helper-v26
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

The registration preflight still confirms:

```text
lshal-binary: pass
runtime-materials: pass
system-ext-vndk-v30: pass
service-manager-binaries: pass
process-surface-clean: pass
wifi-link-clean: pass
```

Remaining blocker:

```text
helper-v26
```

## Live Deploy Update

V410 helper v26 deploy completed after exact approval.

```text
evidence: tmp/wifi/v410-execns-helper-v26-deploy-live-20260520-110409/
decision: execns-helper-v26-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

The deployment used serial fallback and installed the expected helper SHA:

```text
daf1b59e2475c0db28fb99eb83f8be02a46f695d8c4e435c47e68f45370a7caa
```

Post-deploy read-only preflight also passed.

```text
evidence: tmp/wifi/v410-registration-query-post-deploy-preflight-20260520-111017/
decision: v410-hal-registration-query-preflight-ready
pass: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Detailed live report:

```text
docs/reports/NATIVE_INIT_V410_HELPER_V26_DEPLOY_LIVE_2026-05-20.md
```

## Next Target

Next live gate, only after this deploy and post-deploy preflight:

```text
approve v410 bounded lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```
