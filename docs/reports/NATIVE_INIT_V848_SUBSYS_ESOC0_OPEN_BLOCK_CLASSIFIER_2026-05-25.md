# Native Init V848 subsys_esoc0 Open-Block Classifier Report

## Result

- decision: `v848-subsys-esoc0-open-block-boundary-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_subsys_esoc0_open_block_classifier_v848.py`
- evidence: `tmp/wifi/v848-subsys-esoc0-open-block-classifier/`

## Scope

V848 was host-only. It read V846/V847 manifests, V847 evidence files, and fixed
Samsung OSRC source files. It did not execute a device command, create a device
node, open any char device, open raw `/dev/esoc*`, write sysfs/GPIO/debugfs,
start daemons, start service-manager, start Wi-Fi HAL, scan/connect, use
credentials, run DHCP, change routes, ping externally, write boot images, write
partitions, or flash a custom kernel.

## Key Signals

| Signal | Value |
| --- | --- |
| V847 node materialization | `/dev/subsys_esoc0`, char-device path reached |
| V847 holder PID | present |
| V847 open completion | no `holder.opened=1`, no successful open rc |
| Kernel entry | `__subsystem_get: esoc0 count:0` |
| Firmware name update | `Changing subsys fw_name to esoc0` |
| mdm3/subsys9 state | `OFFLINING` |
| MHI/PCIe markers | absent |
| WLFW/BDF/`wlan0` markers | absent |
| Cleanup | V847 cleanup reboot restored native health |

## Source Boundary

`subsys_device_open()` calls `subsystem_get_with_fwname()`, which enters
`__subsystem_get()`. V847's dmesg proves execution reached that path and applied
the firmware-name update. The source then calls `subsys_start()`, which calls
the provider `powerup()` hook and later `wait_for_err_ready()`.

The block is now narrowed to two source-backed possibilities:

1. provider `powerup()` internal eSoC GPIO/IRQ handshake, likely the
   AP-to-MDM status assert and MDM-to-AP status wait implemented in the missing
   eSoC MDM provider; or
2. `wait_for_err_ready()`, where `powerup()` returns but SDX50M does not signal
   error-ready within the kernel completion path.

V847 did not capture task `wchan`, so V848 cannot honestly choose between those
two branches. It also did not show MHI/PCIe/WLFW progress or open completion,
so the remaining blocker is inside/under `subsys_start()`, before visible lower
Wi-Fi progression.

The staged OSRC tree enables `CONFIG_ESOC`, `CONFIG_ESOC_DEV`,
`CONFIG_ESOC_CLIENT`, `CONFIG_ESOC_MDM_4x`, and `CONFIG_ESOC_MDM_DRV`, but the
corresponding eSoC MDM provider source file is absent. That makes source-only
branch attribution insufficient; the next live run should observe the blocked
task's wait site instead.

## Candidate Decision

| Candidate | Decision | Reason |
| --- | --- | --- |
| Blind longer hold | reject | Extends opaque block risk without locating the wait site |
| Repeat V847 unchanged | reject | Would reproduce the same entry markers |
| Raw `/dev/esoc*` ioctl/sysfs/GPIO writes | reject | Provider behavior is opaque and broader than needed |
| MHI `power_up` write | defer | No V847 MHI/PCIe progression yet |
| Wi-Fi HAL/scan/connect | reject | WLFW/BDF/`wlan0` is still absent |
| Bounded wait-state sampler | select-next | Directly classifies provider `powerup()` vs `wait_for_err_ready()` |

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_subsys_esoc0_open_block_classifier_v848.py
python3 scripts/revalidation/native_wifi_subsys_esoc0_open_block_classifier_v848.py \
  --out-dir tmp/wifi/v848-plan-check \
  plan
python3 scripts/revalidation/native_wifi_subsys_esoc0_open_block_classifier_v848.py \
  --out-dir tmp/wifi/v848-subsys-esoc0-open-block-classifier \
  run
```

Result:

```text
decision: v848-subsys-esoc0-open-block-boundary-classified
pass: True
device_commands_executed: False
mknod_executed: False
subsys_char_open_executed: False
raw_esoc_open_executed: False
sysfs_write_executed: False
gpio_write_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V849 should run one bounded live `subsys_esoc0` char-open wait-state sampler:
materialize the node, start a single holder, capture holder process tree,
`/proc/<pid>/wchan`, `/proc/<pid>/stack` if readable, `/proc/<pid>/status`,
`/proc/<pid>/syscall`, read-only `/sys/module` eSoC/module surface, mdm3 state,
focused dmesg, then remove the node and cleanup reboot. Keep raw eSoC ioctls,
sysfs/GPIO writes, service-manager, Wi-Fi HAL, scan/connect, DHCP/routes,
external ping, and boot-image work blocked.
