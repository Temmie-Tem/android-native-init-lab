# V593 Native Subsys OFFLINING Classifier Report

- Date: 2026-05-22
- Evidence: `tmp/wifi/v593-subsys-offlining-classifier`
- Decision: `v593-subsys-pil-firmware-load-failed`
- Pass: `true`
- Wi-Fi bring-up: not executed
- Daemon/HAL start: not executed
- Device mutations: `false`

## State Summary

| Key | Value |
| --- | --- |
| `mss_state` | `OFFLINING` |
| `any_offlining` | `true` |
| `rpmsg_ipcrtr_present` | `false` |
| `service_notifier_present` | `false` |
| `proc_qrtr_present` | `false` |
| `crash_count_positive` | `false` |
| `firmware_class_path` | `/vendor/firmware_mnt/image` |
| `global_modem_blobs_visible` | `false` |
| `firmware_load_failure_count` | `80` |
| `helper_residual_d_state` | `false` |

## Key Evidence

- Native global firmware candidates were absent:
  - `/vendor/firmware_mnt/image`
  - `/vendor/firmware-modem/image`
  - `/firmware/image`
  - `/mnt/system/vendor/firmware`
  - `/mnt/system/system/vendor/firmware`
- `dmesg` shows V592 cdev open entered `subsys-restart` / PIL modem load.
- Firmware loader then timed out or failed to locate `modem.bXX` blobs.
- No QRTR/QMI/WLFW/BDF/WLAN-ready marker appeared.

## Interpretation

The current blocker is no longer simply "companion services missing". The native kernel path can be forced into modem PIL loading, but `firmware_class` points at `/vendor/firmware_mnt/image` while that global path is absent. The helper's private firmware mounts do not satisfy this global firmware request path.

## Next Gate

V594 should be a read-only or tightly bounded firmware visibility parity proof:

1. Compare Android `/sys/module/firmware_class/parameters/path`, `/proc/mounts`, and `/vendor/firmware_mnt/image` contents.
2. Recreate only the required global read-only firmware mount path in native init.
3. Verify modem blobs are visible before any further subsystem cdev open, qcwlanstate, CNSS daemon, HAL, scan, or connect.
