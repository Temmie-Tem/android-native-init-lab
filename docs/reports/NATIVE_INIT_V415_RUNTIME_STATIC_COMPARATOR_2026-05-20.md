# Native Init V415 Runtime Static Comparator

Date: 2026-05-20

## Scope

V415 compares V411 binderized runtime registration evidence with the V414 ranked
static Wi-Fi target set.

This pass is host-only.  It executed no bridge/device command, helper deploy,
daemon start, Wi-Fi HAL start, scan/connect/link-up, or Wi-Fi bring-up.

## Implementation

```text
scripts/revalidation/wifi_v415_runtime_static_comparator.py
```

Current input manifests:

```text
tmp/wifi/v411-current-query-preflight-20260520-114943/manifest.json
tmp/wifi/v414-static-runtime-target-classifier-20260520-121416/manifest.json
```

## Current Evidence

```text
tmp/wifi/v415-runtime-static-comparator-20260520-121831/
```

Result:

```text
decision: v415-runtime-static-comparator-waiting-for-v411-deploy
pass: True
reason: V411 is blocked before runtime registration query
next: execute exact-approved V411 helper v27 deploy before runtime/static comparison
primary_target: vendor.samsung.hardware.wifi@2.0-2::ISehWifi/default
runtime_registration_count: 0
primary_match_count: 0
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Evidence permissions:

```text
700 tmp/wifi/v415-runtime-static-comparator-20260520-121831
600 tmp/wifi/v415-runtime-static-comparator-20260520-121831/manifest.json
600 tmp/wifi/v415-runtime-static-comparator-20260520-121831/summary.md
```

## Primary Runtime Match Set

The comparator preserves the V414 primary runtime patterns:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default
vendor.samsung.hardware.wifi@2.1::ISehWifi/default
vendor.samsung.hardware.wifi@2.2::ISehWifi/default
```

## Branch Smoke

Synthetic primary-match fixture:

```text
tmp/wifi/v415-runtime-static-comparator-sample-primary-20260520-121847/
```

Result:

```text
decision: v415-runtime-static-primary-match
pass: True
runtime_registration_count: 2
primary_match_count: 1
primary_match: vendor.samsung.hardware.wifi@2.1::ISehWifi/default
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

This proves the comparator will route to a no-scan/no-link client-proof plan if
future V411 runtime output contains the Samsung Wi-Fi HAL service.

## Interpretation

V415 is ready, but the current real evidence still cannot compare runtime
registration because V411 is blocked before the live query.  The next live gate
therefore remains:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

After helper v27 deploy, rerun V411 preflight and the bounded V411 binderized
query.  Then rerun V415 against the live V411 manifest.
