# Native Init V1058 First-Open Runtime Prerequisite Report

Date: `2026-05-27`

## Summary

V1058 followed the V1056 next route and performed a read-only current-boot prerequisite check before another PM first-open live retry.  The classifier did not open modem/eSoC device nodes and did not start Wi-Fi daemons, HAL, scan/connect, DHCP, routes, credentials, external ping, or any write path.

Decision: `v1058-global-firmware-mount-gap`

The current native v724 boot has the expected `firmware_class.path`, but the global firmware mounts are absent.  As a result, `modem.b00` and `modem.mdt` are not visible at `/vendor/firmware_mnt/image`, so another count-zero PM first-open retry would still lack the PIL firmware prerequisite.

## Evidence

Private evidence directory:

```text
tmp/wifi/v1058-first-open-runtime-prereq/
```

Manifest:

```text
tmp/wifi/v1058-first-open-runtime-prereq/manifest.json
```

Key results:

| Check | Result |
| --- | --- |
| native health | `version_ok=True`, `selftest_fail_zero=True`, `netservice_tcpctl_helper_ok=True` |
| `firmware_class.path` | `/vendor/firmware_mnt/image` |
| `/vendor/firmware_mnt` mount | `False` |
| `/vendor/firmware-modem` mount | `False` |
| `/firmware` mount | `False` |
| `/vendor/firmware_mnt/image/modem.b00` | `False` |
| `/vendor/firmware_mnt/image/modem.mdt` | `False` |
| modem/eSoC device-node stat | `/dev/subsys_modem=False`, `/dev/subsys_esoc0=False`, `/dev/esoc-0=False` |
| lower perturbation markers | `pil_boot=False`, `subsystem_get_modem=False`, `sysmon_qmi=False`, `wlfw=False` |

## Interpretation

V1058 confirms the next blocker is not an actor-order retry problem.  Current native boot is clean, but it is missing the firmware mount prerequisite needed before a useful PM first-open gate.

This matters because the kernel command line already points firmware loading at `/vendor/firmware_mnt/image`.  If that path is not mounted globally, the first opener can enter the lower PIL path without visible modem firmware blobs.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_first_open_runtime_prereq_v1058.py
python3 scripts/revalidation/native_wifi_first_open_runtime_prereq_v1058.py run
```

Result:

```text
decision=v1058-global-firmware-mount-gap
pass=True
next_step=run a bounded firmware-mount prerequisite refresh before any PM first-open live gate
```

## Guardrails

- No credentials used.
- No Wi-Fi scan/connect/link-up/external ping attempted.
- No service-manager, Wi-Fi HAL, daemon start, actor start, module load, eSoC ioctl, modem/eSoC device-node open, firmware mutation, sysfs/debugfs write, boot image write, partition write, or reboot.
- Evidence files are private (`0600`) under a private evidence directory.

## Next

V1059 should perform the smallest bounded firmware-mount prerequisite refresh:

1. mount the required firmware partitions read-only into the global namespace;
2. verify `/vendor/firmware_mnt/image/modem.b00` and `modem.mdt` visibility;
3. avoid PM actors, modem/eSoC opens, service-manager, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, external ping, and reboot;
4. leave the boot clean enough for the next PM first-open gate, or cleanly unmount if the mount refresh fails.
