# Native Init v411 Binderized lshal Query Prep

Date: 2026-05-20
Scope: helper/runner prep only; no helper deploy, daemon start, HAL start, `lshal`, or Wi-Fi bring-up live query was executed.

## Summary

V411 is implemented and fail-closed.  It prepares a narrower follow-up to the
V410 `lshal-timeout` result by changing the helper-owned query child to:

```text
/system/bin/lshal list --types=binderized --neat
```

The target is to prove `hwservicemanager` binderized service publication without
using the broader default `lshal` path that timed out in V410.

## Build Evidence

Helper v27:

```text
artifact: tmp/wifi/v411-a90_android_execns_probe-v27/a90_android_execns_probe
sha256: 0519b557482f347d47962e9da76ee7afcce270bf12df860d37678e9a26bf2c74
file: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
dynamic section: none
```

Required strings:

```text
a90_android_execns_probe v27
wifi-hal-composite-lshal-binderized-list
--types=binderized
--neat
--allow-hal-service-query
```

## Contract Linter

V411 binderized-lshal contract linter:

```text
script: scripts/revalidation/wifi_v411_binderized_lshal_linter.py
evidence: tmp/wifi/v411-binderized-lshal-linter-20260520-113507/
decision: v411-binderized-lshal-contract-pass
pass: True
reason: all V411 binderized-lshal contract checks passed
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

The linter proves the helper source, runner, deploy wrapper, and generated
approval manifests agree on:

```text
helper-v27-version: pass
helper-binderized-mode-allowlisted: pass
helper-implicit-data-wifi-default: pass
helper-binderized-lshal-argv: pass
runner-v27-sha-mode-approval: pass
runner-records-implicit-contract: pass
runner-checks-binderized-helper-strings: pass
deploy-v27-sha-mode-and-guard: pass
deploy-checks-binderized-helper-strings: pass
approved-command-arg-budget: pass
approved-command-mode: pass
approved-command-query-guard: pass
approved-command-uses-implicit-data-wifi: pass
approved-plan-host-only: pass
noapproval-no-device-command: pass
deploy-plan-local-helper-pass: pass
query-preflight-expected-helper-blocker: pass
```

Linter evidence permissions:

```text
700 tmp/wifi/v411-binderized-lshal-linter-20260520-113507
600 tmp/wifi/v411-binderized-lshal-linter-20260520-113507/manifest.json
600 tmp/wifi/v411-binderized-lshal-linter-20260520-113507/README.md
```

## Prepared Gates

```text
scripts/revalidation/wifi_execns_helper_v27_deploy_preflight.py
scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py
```

Deploy approval phrase:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

Live query approval phrase:

```text
approve v411 bounded binderized lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Evidence

Approved query plan, host-only:

```text
evidence: tmp/wifi/v411-binderized-query-approved-plan-20260520-112814/
decision: v411-hal-registration-query-plan-ready
pass: True
command_len: 29
mode: wifi-hal-composite-lshal-binderized-list
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Query no-approval run:

```text
evidence: tmp/wifi/v411-binderized-query-noapproval-20260520-112815/
decision: v411-hal-registration-query-approval-required
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Helper deploy plan:

```text
evidence: tmp/wifi/v411-helper-v27-deploy-plan-20260520-112815/
decision: execns-helper-v27-deploy-plan-ready
pass: True
local-helper-v27: pass
local-helper-v27-query-guard: pass
binderized_query: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Helper deploy no-approval run:

```text
evidence: tmp/wifi/v411-helper-v27-deploy-noapproval-20260520-112915/
decision: execns-helper-v27-deploy-approval-required
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Helper deploy read-only preflight:

```text
evidence: tmp/wifi/v411-helper-v27-deploy-readonly-preflight-20260520-112857/
decision: execns-helper-v27-deploy-preflight-ready-needs-deploy
pass: True
remote-helper-v27: needs-deploy
remote-helper-v27-query-guard: needs-deploy
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Query read-only preflight:

```text
evidence: tmp/wifi/v411-binderized-query-readonly-preflight-20260520-112815/
decision: v411-hal-registration-query-blocked
pass: False
reason: blocked before live run by helper-v27
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Passing read-only query checks before the expected helper blocker:

```text
v408-registration-surface-pass: pass
native-version: pass
native-clean: pass
lshal-binary: pass
runtime-materials: pass
system-ext-vndk-v30: pass
service-manager-binaries: pass
process-surface-clean: pass
wifi-link-clean: pass
```

## Fail-Closed Executor

V411 deploy/query executor:

```text
script: scripts/revalidation/wifi_v411_deploy_query_executor.py
```

No-approval executor evidence:

```text
evidence: tmp/wifi/v411-executor-plan-noapproval-20260520-114711/
decision: v411-deploy-query-executor-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

```text
evidence: tmp/wifi/v411-executor-deploy-noapproval-20260520-114711/
decision: v411-deploy-query-executor-approval-required
remaining_blockers: exact-v411-deploy-approval-phrase
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

```text
evidence: tmp/wifi/v411-executor-live-noapproval-20260520-114711/
decision: v411-deploy-query-executor-approval-required
remaining_blockers: exact-v411-binderized-lshal-live-approval-phrase
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

```text
evidence: tmp/wifi/v411-executor-full-noapproval-20260520-114711/
decision: v411-deploy-query-executor-approval-required
remaining_blockers: exact-v411-deploy-approval-phrase, exact-v411-binderized-lshal-live-approval-phrase
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Partial full-approval refusal evidence:

```text
evidence: tmp/wifi/v411-executor-full-deployonly-refusal-20260520-114711/
remaining_blockers: exact-v411-binderized-lshal-live-approval-phrase
device_commands_executed: False
device_mutations: False
```

```text
evidence: tmp/wifi/v411-executor-full-liveonly-refusal-20260520-114711/
remaining_blockers: exact-v411-deploy-approval-phrase
device_commands_executed: False
device_mutations: False
```

Executor evidence permissions:

```text
700 tmp/wifi/v411-executor-plan-noapproval-20260520-114711
600 tmp/wifi/v411-executor-plan-noapproval-20260520-114711/manifest.json
600 tmp/wifi/v411-executor-plan-noapproval-20260520-114711/summary.md
```

## Interpretation

V411 is ready for the next operator-approved deploy gate.  The only expected
blocker is that the device still has helper v26 deployed.  No V411 helper deploy,
composite daemon start, Wi-Fi HAL start, binderized `lshal` query, scan/connect,
or Wi-Fi bring-up has been executed in this prep step.

## Next Target

First live gate:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

After deploy and post-deploy read-only preflight, the separate query gate is:

```text
approve v411 bounded binderized lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```
