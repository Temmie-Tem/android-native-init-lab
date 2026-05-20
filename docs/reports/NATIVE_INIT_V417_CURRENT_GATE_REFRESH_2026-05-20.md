# Native Init V417 Current Gate Refresh

Date: 2026-05-20

## Scope

V417 refreshes the current Wi-Fi gate packet after the V411 through V416
host-side tooling was committed.

This pass did not deploy helper v27.  It did not start service-manager, start a
Wi-Fi HAL, scan, connect, link up, or bring up Wi-Fi.

## Evidence

```text
tmp/wifi/v417-current-deploy-preflight-20260520-122621/
tmp/wifi/v417-current-query-preflight-20260520-122621/
tmp/wifi/v417-registration-router-20260520-122621/
tmp/wifi/v417-runtime-static-comparator-20260520-122621/
tmp/wifi/v417-current-gate-packet-20260520-122621/
```

## Result

```text
v411_deploy: execns-helper-v27-deploy-preflight-ready-needs-deploy pass=True
v411_query: v411-hal-registration-query-blocked pass=False
v412_router: v412-registration-router-waiting-for-v411-deploy pass=True
v415_comparator: v415-runtime-static-comparator-waiting-for-v411-deploy pass=True
v416_gate_packet: v416-current-gate-waiting-for-v411-deploy pass=True
next_gate: v411-helper-v27-deploy-only
primary_target: vendor.samsung.hardware.wifi@2.0-2::ISehWifi/default
```

The refreshed V416 gate packet reports:

```text
reason: all host-side follow-up tools are ready; live path is blocked only by helper v27 deploy gate
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

The V411 query preflight touched the device read-only, then stopped before the
live registration query because helper v27 is not deployed:

```text
decision: v411-hal-registration-query-blocked
reason: blocked before live run by helper-v27
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

## Evidence Permissions

```text
700 tmp/wifi/v417-current-deploy-preflight-20260520-122621
600 tmp/wifi/v417-current-deploy-preflight-20260520-122621/manifest.json
600 tmp/wifi/v417-current-deploy-preflight-20260520-122621/summary.md
700 tmp/wifi/v417-current-query-preflight-20260520-122621
600 tmp/wifi/v417-current-query-preflight-20260520-122621/manifest.json
600 tmp/wifi/v417-current-query-preflight-20260520-122621/summary.md
700 tmp/wifi/v417-registration-router-20260520-122621
600 tmp/wifi/v417-registration-router-20260520-122621/manifest.json
600 tmp/wifi/v417-registration-router-20260520-122621/summary.md
700 tmp/wifi/v417-runtime-static-comparator-20260520-122621
600 tmp/wifi/v417-runtime-static-comparator-20260520-122621/manifest.json
600 tmp/wifi/v417-runtime-static-comparator-20260520-122621/summary.md
700 tmp/wifi/v417-current-gate-packet-20260520-122621
600 tmp/wifi/v417-current-gate-packet-20260520-122621/manifest.json
600 tmp/wifi/v417-current-gate-packet-20260520-122621/summary.md
```

## Interpretation

V417 confirms the current blocker has not changed: the host-side routing,
static/runtime comparison, and gate-packet layers are ready, but runtime
registration evidence still depends on deploying helper v27 first.

The next bounded live step is only:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

That step permits only replacing `/cache/bin/a90_android_execns_probe` with the
helper v27 binary whose SHA-256 is:

```text
0519b557482f347d47962e9da76ee7afcce270bf12df860d37678e9a26bf2c74
```

It still does not approve service-manager start, Wi-Fi HAL start,
scan/connect/link-up, credentials, DHCP, routing, or Wi-Fi bring-up.
