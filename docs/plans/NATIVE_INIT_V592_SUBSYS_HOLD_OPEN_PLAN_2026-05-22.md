# V592 Native Subsystem Hold-Open Plan

- Date: 2026-05-22
- Scope: test whether temporary `subsys_modem` / `subsys_esoc0` char-device open is the smallest safe native trigger for lower modem readiness.
- Safety boundary: no daemon start, no service-manager, no Wi-Fi HAL, no scan/connect/link-up, no DHCP, no routes, no external ping, no credentials.

## Preconditions

- Native baseline is healthy: `A90 Linux init 0.9.61 (v319)`, `status/selftest fail=0`.
- `/mnt/system/system` is mounted read-only through `mountsystem ro`.
- `/cache/bin/a90_android_execns_probe` is helper `v100`.
- No active `a90_android_execns_probe`, CNSS, companion, or Wi-Fi user-space process is present.

## Method

1. Build static helper `a90_android_execns_probe v100`.
2. Add `subsys-hold-open-proof` mode.
3. Inside the helper private namespace, mount vendor and firmware partitions read-only as before.
4. Create temporary private `/dev/subsys_modem` and `/dev/subsys_esoc0` nodes from `/sys/class/subsys/*/dev`.
5. Open the char devices from a chrooted child for a bounded window.
6. Capture subsystem state, rpmsg, QRTR, service-notifier, and dmesg before/after.

## Expected Outcomes

- `subsys-hold-readiness-delta`: modem/esoc moves `ONLINE`, rpmsg IPCRTR appears, or QRTR/QMI/WLFW markers appear.
- `subsys-hold-no-readiness-delta`: char devices open and cleanly exit but no lower readiness changes.
- `subsys-hold-reboot-required`: open path blocks beyond the bounded cleanup window and further live tests must stop.

## Follow-Up Gate

- If cdev open does not create readiness, do not retry qcwlanstate/HAL.
- Classify modem/esoc OFFLINING and firmware request path before any broader Wi-Fi action.
