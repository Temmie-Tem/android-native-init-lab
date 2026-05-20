# Native Init V422 Targeted lshal wait Report

Date: 2026-05-20

## Scope

V422 implemented and ran the executable fallback for the V421 micro registration
question.  The helper starts only a bounded private namespace with
`servicemanager`, `hwservicemanager`, one vendor Wi-Fi HAL candidate, and
targeted `/system/bin/lshal wait <fqinstance>` probes.

This is not Wi-Fi bring-up.  No scan/connect/link-up, credentials, DHCP,
routing, wificond, supplicant, hostapd, CNSS/diag, persistence, or boot
autostart was approved or executed.

## Implementation

```text
stage3/linux_init/helpers/a90_android_execns_probe.c
scripts/revalidation/wifi_execns_helper_v28_deploy_preflight.py
scripts/revalidation/wifi_hal_micro_lshal_wait_v422_runner.py
docs/plans/NATIVE_INIT_V422_TARGETED_LSHAL_WAIT_PLAN_2026-05-20.md
```

Helper artifact:

```text
tmp/wifi/v422-a90_android_execns_probe-v28/a90_android_execns_probe
sha256: 17a21ba0258af7a575f707d5cad4c847ea67a22240dc3d51ec2f75b9fd8c0bb8
mode: wifi-hal-composite-lshal-wait-target
```

## Validation

Host checks:

```text
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v28_deploy_preflight.py scripts/revalidation/wifi_hal_micro_lshal_wait_v422_runner.py scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py scripts/revalidation/wifi_composite_hal_start_only_v405_runner.py
git diff --check
scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v422-a90_android_execns_probe-v28/a90_android_execns_probe
```

Plan/no-approval evidence:

```text
tmp/wifi/v422-helper-v28-deploy-plan-20260520-130711/
tmp/wifi/v422-micro-lshal-wait-plan-20260520-130711/
tmp/wifi/v422-micro-lshal-wait-noapproval-20260520-130711/
```

Live deploy evidence:

```text
tmp/wifi/v422-helper-v28-deploy-live-20260520-130722/
decision: execns-helper-v28-deploy-pass
pass: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Live targeted query evidence:

```text
tmp/wifi/v422-micro-lshal-wait-live-20260520-131322/
decision: v422-micro-lshal-wait-timeout
pass: True
helper_result: service-query-runtime-gap
helper_reason: lshal-wait-query-failed
micro_query_result: service-query-timeout
micro_query_reason: lshal-wait-timeout
postflight.clean: True
postflight.processes: 0
postflight.wifi_links: 0
wifi_bringup_executed: False
```

Target results:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default -> lshal-wait-timeout
vendor.samsung.hardware.wifi@2.1::ISehWifi/default -> lshal-wait-timeout
vendor.samsung.hardware.wifi@2.2::ISehWifi/default -> lshal-wait-timeout
```

## Interpretation

V422 proves that the current private runtime can launch the narrowed lshal wait
children and cleanly stop the service-manager/HAL process group afterward.
However, none of the three V414-ranked Samsung Wi-Fi HAL fqinstances became
observable through `lshal wait` within the bounded per-target window.

This result keeps the Wi-Fi bring-up gate closed.  The next useful branch is one
of:

1. build the raw `hwservicemanager listByInterface` client proposed by V421 with
   an Android/HIDL-capable toolchain; or
2. collect Android-side `lshal`/hwservice evidence in the full Android runtime
   and compare it against the private namespace result.

## References

```text
https://android.googlesource.com/platform/frameworks/native/+/master/cmds/lshal/Lshal.cpp
https://android.googlesource.com/platform/frameworks/native/+/b3701625d91e62fdd41607378afa5803bc4491dc%5E2..b3701625d91e62fdd41607378afa5803bc4491dc/
```
