# Native Init v410 Helper v26 Deploy Live

Date: 2026-05-20
Scope: exact-approved helper deploy only

## Result

```text
decision: execns-helper-v26-deploy-pass
pass: True
reason: helper v26 deployed or already current; V410 query preflight was rerun
next: next requires separate V410 registration-query approval
```

The live run deployed `a90_android_execns_probe v26` to:

```text
/cache/bin/a90_android_execns_probe
```

This run did not start `servicemanager`, `hwservicemanager`, `vndservicemanager`, the Wi-Fi HAL, scan/connect/link-up, or Wi-Fi bring-up.

## Approval Boundary

Approved phrase:

```text
approve v410 deploy execns helper v26 only; no daemon start and no Wi-Fi bring-up
```

Explicitly not approved:

```text
service-manager, hwservicemanager, vndservicemanager start
Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start
Wi-Fi scan/connect/link-up/credential/DHCP/routing
Android partition write, firmware mutation, rfkill write, driver bind/unbind
```

## Evidence

Deploy evidence:

```text
tmp/wifi/v410-execns-helper-v26-deploy-live-20260520-110409/
```

Deploy manifest:

```text
decision: execns-helper-v26-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
helper_expected_sha256: daf1b59e2475c0db28fb99eb83f8be02a46f695d8c4e435c47e68f45370a7caa
remote_helper: /cache/bin/a90_android_execns_probe
transfer_method: serial
chunks_written: 783
encoded_bytes: 1094836
```

The pre-deploy probe saw the previous remote helper as `v24`; deployment then completed through serial fallback.

Post-deploy registration-query preflight evidence:

```text
tmp/wifi/v410-registration-query-post-deploy-preflight-20260520-111017/
```

Post-deploy preflight manifest:

```text
decision: v410-hal-registration-query-preflight-ready
pass: True
reason: read-only preflight is ready; live query still needs approval
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Passing checks after deploy:

```text
v408-registration-surface-pass: pass
native-version: pass
native-clean: pass
helper-v26: pass
lshal-binary: pass
runtime-materials: pass
system-ext-vndk-v30: pass
service-manager-binaries: pass
process-surface-clean: pass
wifi-link-clean: pass
```

## Next Gate

The next live step is the bounded registration query. It remains separate and still requires this exact approval phrase:

```text
approve v410 bounded lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```
