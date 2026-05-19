# V382 Approved Deploy + Service-Manager Start-Only Result

## Summary

- Executed the guarded V382 full handoff with both exact approval phrases.
- Remote `/cache/bin/a90_android_execns_probe` was updated to `a90_android_execns_probe v14`.
- Bounded service-manager start-only smoke ran with private Binder nodes, private property root, and private-empty `/data` tree.
- Wi-Fi HAL, CNSS/diag, wificond, supplicant, hostapd, scan/connect/link-up, DHCP, routing, firmware mutation, and Android partition writes were not executed.

## Evidence

- Executor evidence: `tmp/wifi/v382-executor-full-approved-20260520-035119`
- Top-level decision: `v382-deploy-live-executor-full-pass`
- Route decision: `service-manager-start-only-router-runtime-gap`
- Classifier decision: `service-manager-runtime-gap-manual-review`
- Remote helper SHA256: `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`
- Native build on device: `A90 Linux init 0.9.61 (v319)`

## Deploy Result

- Deploy decision: `execns-helper-v14-deploy-pass`
- Transfer method: `serial appendfile + uudecode`
- Serial chunks: `910`
- Encoded bytes: `1273904`
- Device mutation: helper replacement under `/cache/bin/a90_android_execns_probe` only
- Daemon start during deploy: `false`
- Wi-Fi bring-up during deploy: `false`

## Live Result

- Live decision: `service-manager-start-only-live-runtime-gap`
- `system-servicemanager`:
  - result: `start-only-runtime-gap`
  - reason: `child-exited-before-observe-window`
  - signal: `6` / `SIGABRT`
  - postflight_safe: `true`
- `system-hwservicemanager`:
  - result: `start-only-pass`
  - reason: `observed-until-timeout-clean-stop`
  - signal: `15` from bounded timeout stop
  - postflight_safe: `true`
- Postflight:
  - `manager_processes=[]`
  - `wifi_links=[]`
  - `clean=true`

## Manual Review Clues

`system-servicemanager` reached pre-exec and attempted exec, then aborted immediately:

- private `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` existed in the helper namespace
- private `/dev/__properties__` was visible
- private `/data/vendor/wifi` and `/data/vendor/wifi/sockets` existed
- real `/linkerconfig/ld.config.txt` and `apex.libraries.config.txt` were materialized
- stderr only exposed `libc: Fatal signal 6 (SIGABRT)` before observation window

`system-hwservicemanager` survived until bounded timeout and logged:

- `SELinux: Loaded service_contexts from:`
  - `/system/etc/selinux/plat_hwservice_contexts`
  - `/vendor/etc/selinux/vendor_hwservice_contexts`
- `libc: Using old property service protocol ("ro.property_service.version" is not set)`

## Interpretation

- The previous helper-version blocker is closed: v14 is deployed and verified on device.
- Binder devnode provisioning and private property root are no longer the first blocker for `hwservicemanager`.
- The remaining blocker is specifically `servicemanager` aborting with `SIGABRT` before it becomes observable.
- Because the classifier does not yet recognize this class, the next cycle should improve runtime-gap evidence capture before any HAL start-only or Wi-Fi bring-up.

## Next Candidate

V383 should focus on `servicemanager` abort classification:

- capture `servicemanager` stderr/stdout with a larger early buffer if needed
- capture available tombstone/debuggerd/log paths if native environment exposes them
- probe service context files used by `/system/bin/servicemanager`
- compare `servicemanager` vs `hwservicemanager` runtime dependencies and SELinux context loading
- keep Wi-Fi HAL/start/scan/connect blocked
