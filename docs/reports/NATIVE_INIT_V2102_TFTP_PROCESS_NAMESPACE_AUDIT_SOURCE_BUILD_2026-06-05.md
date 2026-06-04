# Native Init V2102 TFTP Process Namespace Audit Source Build

## Summary

- Cycle: `V2102`
- Type: source/build-only follow-up to V2101, adding a read-only `/proc/<tftp_server>/root` and `mountinfo` audit for the stock `tftp_server` process.
- Decision: `v2102-tftp-process-namespace-audit-source-build-pass`
- Result: PASS
- Reason: helper v412 keeps the V2100 light internal-modem route and adds no ptrace, no QMI send, and no extra service actors. It only records whether the running stock `tftp_server` process actually sees the namespace-local `/mnt/vendor/persist/rfs` auto-dir targets.
- Manifest: `tmp/wifi/v2102-tftp-process-namespace-audit-test-boot/manifest.json`
- Boot image: `tmp/wifi/v2102-tftp-process-namespace-audit-test-boot/boot_linux_v2102_tftp_process_namespace_audit.img`
- Boot SHA256: `324909509cd46eb2d8f1386f77c03df0919788ea1635adb595a690f586476d34`
- Init: `A90 Linux init 0.9.228 (v2102-tftp-process-namespace-audit)`
- Helper marker: `a90_android_execns_probe v412`
- Helper SHA256: `3e59a0b0de541afb2b604d3d3f23f1e0b7b18a51c659804674d20d88234d8473`

## Route

- Helper runtime mode: `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only`
- Helper timeout: `75`
- Property root: `/mnt/sdext/a90/private-property-v317/v2102/dev/__properties__`
- Light firmware trace: `True`
- Kept: V2100 route, readonly/readwrite RFS bridges, vendor-owned tombstone dirs, persist-RFS auto-dir targets, `tftp_server` logdw sink, focused PerMgr/WLFW summaries, post-BDF surface summary, and long lower-window hold.
- Added: read-only process-root/mountinfo audit for the already-running stock `tftp_server` process.
- Excluded: `tftp_server` ptrace, AP QMI send, DIAG, QRTR matrix, RIL/cnss/pm-service strace, macloader retry, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and off-path SDX50M/eSoC/PCIe/GDSC/PMIC/GPIO actions.

## Property Runtime

- `persist.vendor.cnss-daemon.kmsg_logging`: `1` in `u:object_r:vendor_default_prop:s0`
- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`

## Safety Scope

This build script performed host-side source/build work only. The live handoff should decide whether `tftp_server` is in the same filesystem view as the helper-created persist-RFS auto-dir targets.
