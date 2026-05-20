# Native Init V411 Current Preflight

Date: 2026-05-20

## Scope

This report records a current read-only V411 preflight refresh after committing
the guarded V411 deploy/query executor.

No helper deploy, daemon start, Wi-Fi HAL start, scan/connect/link-up, or Wi-Fi
bring-up was approved or executed in this pass.

## Evidence

Deploy preflight:

```text
tmp/wifi/v411-current-deploy-preflight-20260520-114943/
```

Binderized query preflight:

```text
tmp/wifi/v411-current-query-preflight-20260520-114943/
```

## Deploy Preflight Result

```text
decision: execns-helper-v27-deploy-preflight-ready-needs-deploy
pass: True
reason: preflight complete; helper v27 deploy still requires exact approval
next: operator may approve V411 deploy
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Notable checks:

```text
local-helper-v27: pass
native-version: pass
native-clean: pass
ncm-host-reachable: warn
service-manager-processes-clean: pass
wifi-link-surface-clean: pass
remote-helper-v27: needs-deploy
approval-gate: needs-operator
local-helper-v27-query-guard: pass
remote-helper-v27-query-guard: needs-deploy
```

The NCM reachability warning does not block the next step because the deploy
wrapper can use the existing serial fallback path.  It should be cleared before
preferring NCM transfer.

## Binderized Query Preflight Result

```text
decision: v411-hal-registration-query-blocked
pass: False
reason: blocked before live run by helper-v27
next: resolve blockers before approval
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Notable checks:

```text
v408-registration-surface-pass: pass
native-version: pass
native-clean: pass
helper-v27: blocked
lshal-binary: pass
runtime-materials: pass
system-ext-vndk-v30: pass
service-manager-binaries: pass
process-surface-clean: pass
wifi-link-clean: pass
approval-gate: needs-operator
```

## Interpretation

The device is still on helper v26:

```text
remote sha: daf1b59e2475c0db28fb99eb83f8be02a46f695d8c4e435c47e68f45370a7caa
remote marker: a90_android_execns_probe v26
```

The local V411 helper v27 artifact is ready:

```text
local sha: 0519b557482f347d47962e9da76ee7afcce270bf12df860d37678e9a26bf2c74
```

The next required action remains the exact-approved V411 helper v27 deploy only.
After deploy, rerun the V411 binderized query preflight before considering the
bounded live query gate.

## Next Gate

Required deploy phrase:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

This deploy gate only replaces `/cache/bin/a90_android_execns_probe`.  It does
not approve daemon start, Wi-Fi HAL start, scan/connect/link-up, or Wi-Fi
bring-up.
