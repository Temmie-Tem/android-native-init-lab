# Native Init V1064 PM Service Trigger Observer Helper Report

Date: `2026-05-27`

## Summary

V1064 added source/build-only helper support for a PM-service trigger observer. The new observer is intended to answer the V1063 blocker directly: whether Android-like service-manager and Peripheral Manager ordering causes `pm-service` or `pm_proxy_helper` to open `/dev/subsys_modem`, or whether the PM stack remains idle without an additional runtime input.

## Change

- Bumped `a90_android_execns_probe` from `v180` to `v181`.
- Added mode `wifi-companion-pm-service-trigger-observer` and flag `--allow-pm-service-trigger-observer`.
- Added validation that rejects unrelated CNSS/HAL/scan/connect/eSoC proof flags for the observer mode.
- Added observer output namespace `pm_service_trigger_observer.*` with explicit guardrail markers.
- Added bounded PM stack observation for `servicemanager`, `hwservicemanager`, `vndservicemanager`, `pm_proxy_helper`, `pm-service`, and `pm-proxy` only.

## Guardrails

```text
mdm_helper_start_executed=0
cnss_daemon_start_executed=0
wifi_hal_start_executed=0
scan_connect_linkup=0
external_ping=0
subsys_esoc0_open_attempted=0
```

The helper support does not start Wi-Fi bring-up and does not perform live deployment in this cycle.

## Build Evidence

Command:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v1064-pm-service-trigger-observer-helper/a90_android_execns_probe
```

Result:

```text
artifact=tmp/wifi/v1064-pm-service-trigger-observer-helper/a90_android_execns_probe
size=1188336
sha256=74eaa88bf8221715ed2afae654e53eb7571037655dd6b8e0df0966ab454ef9ce
file=ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
readelf=There is no dynamic section in this file.
```

Marker check:

```text
a90_android_execns_probe v181
wifi-companion-pm-service-trigger-observer
--allow-pm-service-trigger-observer
pm_service_trigger_observer.result=pm-service-subsys-modem-observed
pm_service_trigger_observer.result=pm-service-idle-input-gap-observed
```

## Outcome

- PASS: helper source/build support exists for the PM-service trigger observer.
- PASS: static aarch64 build completed.
- PASS: marker strings for version, mode, flag, and result labels are present.
- PASS: live Wi-Fi bring-up was not attempted in this cycle.

## Next Step

V1065 should be deploy-only for helper `v181` over the now-working NCM/TCP path, proving remote sha/usage parity and native health without daemon start or Wi-Fi bring-up. V1066 should run the bounded PM-service trigger observer live, still without `mdm_helper`, CNSS, Wi-Fi HAL, scan/connect, DHCP, or external ping.
