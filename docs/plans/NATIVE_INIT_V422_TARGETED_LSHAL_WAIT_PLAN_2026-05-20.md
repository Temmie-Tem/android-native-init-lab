# Native Init V422 Targeted lshal wait Plan

Date: 2026-05-20

## Scope

V422 turns the V421 micro-query direction into an executable fallback that can
run with the current static helper toolchain.  It does not replace the raw
`hwservicemanager listByInterface` design; it probes the same V414-ranked
fqinstances through targeted `/system/bin/lshal wait <fqinstance>` calls.

The live scope is limited to:

```text
servicemanager
hwservicemanager
vendor Wi-Fi HAL candidate
/system/bin/lshal wait <fqinstance>
```

It explicitly excludes scan/connect/link-up, credentials, DHCP, routing,
wificond, supplicant, hostapd, CNSS/diag, persistence, boot autostart, and
Wi-Fi bring-up.

## Implementation Targets

```text
stage3/linux_init/helpers/a90_android_execns_probe.c
scripts/revalidation/wifi_execns_helper_v28_deploy_preflight.py
scripts/revalidation/wifi_hal_micro_lshal_wait_v422_runner.py
```

Helper contract:

```text
version: a90_android_execns_probe v28
mode: wifi-hal-composite-lshal-wait-target
query: /system/bin/lshal wait <fqinstance>
per_target_timeout_ms: 2000
```

Target fqinstances:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default
vendor.samsung.hardware.wifi@2.1::ISehWifi/default
vendor.samsung.hardware.wifi@2.2::ISehWifi/default
```

## Approval Boundaries

Deploy approval:

```text
approve v422 deploy execns helper v28 only; no daemon start and no Wi-Fi bring-up
```

Live query approval:

```text
approve v422 targeted lshal wait micro proof only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Decision Labels

```text
execns-helper-v28-deploy-pass
v422-micro-lshal-wait-pass
v422-micro-lshal-wait-timeout
v422-micro-lshal-wait-no-registration
v422-micro-lshal-wait-runtime-gap
v422-micro-lshal-wait-review-required
```

## References

```text
https://android.googlesource.com/platform/frameworks/native/+/master/cmds/lshal/Lshal.cpp
https://android.googlesource.com/platform/frameworks/native/+/b3701625d91e62fdd41607378afa5803bc4491dc%5E2..b3701625d91e62fdd41607378afa5803bc4491dc/
```
