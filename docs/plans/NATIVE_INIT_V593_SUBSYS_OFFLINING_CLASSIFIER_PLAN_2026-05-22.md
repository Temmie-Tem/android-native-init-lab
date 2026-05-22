# V593 Native Subsys OFFLINING Classifier Plan

- Date: 2026-05-22
- Scope: read-only classifier for native modem/esoc OFFLINING and PIL firmware request failures.
- Safety boundary: no mounts, no writes, no daemon start, no Wi-Fi HAL, no scan/connect/link-up, no DHCP, no routes, no external ping, no credentials.

## Inputs

- `/sys/bus/msm_subsys/devices/*/{name,state,restart_level,firmware_name,crash_count,uevent}`
- `/sys/devices/platform/soc/4080000.qcom,mss`
- `/sys/devices/platform/soc/soc:qcom,mdm3`
- `/sys/bus/rpmsg/devices`
- `/sys/kernel/debug/service_notifier`
- `/proc/net/qrtr`
- `/sys/module/firmware_class/parameters/path`
- Native global firmware candidate paths
- Focused `dmesg` lines for PIL, modem, mss, esoc, subsys, firmware, QRTR, QMI, CNSS, ICNSS, WLFW, BDF, WLAN readiness.

## Classifications

- `v593-subsys-pil-firmware-load-failed`: subsystem get reached PIL firmware loading, but firmware blobs timed out or were not visible.
- `v593-subsys-offlining-crash-suspected`: OFFLINING plus crash/restart evidence without a clearer firmware path failure.
- `v593-subsys-transition-observed`: ONLINE/readiness markers appeared.
- `v593-subsys-offlining-no-crash-marker`: OFFLINING persists without crash/readiness markers.
- `v593-subsys-offlining-captured-reboot-required`: read-only evidence is contaminated by a stuck helper residual.

## Decision Use

V593 gates the next native Wi-Fi step. If firmware visibility is missing, do not retry subsystem cdev open, qcwlanstate, CNSS daemon, HAL, scan, or connect.
