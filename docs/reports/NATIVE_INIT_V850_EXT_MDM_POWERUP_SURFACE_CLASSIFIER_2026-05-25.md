# Native Init V850 ext-mdm Powerup Surface Classifier Report

## Result

- decision: `v850-ext-mdm-powerup-surface-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_ext_mdm_powerup_surface_classifier_v850.py`
- evidence: `tmp/wifi/v850-ext-mdm-powerup-surface-classifier/`

## Scope

V850 was host-only. It read V845/V849 evidence, existing Android reference
evidence, and Samsung OSRC source/DTS files. It did not execute device commands,
create nodes, open char devices, open raw `/dev/esoc*`, write GPIO/sysfs/debugfs,
start daemons, start service-manager, start Wi-Fi HAL, scan/connect, use
credentials, run DHCP, change routes, ping externally, write boot images, write
partitions, or flash a custom kernel.

## Classification

| Signal | Value |
| --- | --- |
| V849 holder `wchan` | `mdm_subsys_powerup` |
| V849 holder state | `D (disk sleep)` |
| V849 stack | `mdm_subsys_powerup -> __subsystem_get -> subsys_device_open` |
| `wait_for_err_ready` | not reached |
| MHI hook evidence | not reached |
| Native mdm3 | `OFFLINING` |
| Android reference mdm3 | `ONLINE` |
| Android reference WLAN-PD | present |
| DTS compatible | `qcom,ext-sdx50m` |
| AP2MDM status GPIO | `0x87` |
| MDM2AP status GPIO | `0x8e` |
| Provider source | absent despite ESOC MDM configs |

## Interpretation

The blocker is below the subsystem char-device entry point but before
`wait_for_err_ready`, MHI, WLFW, BDF, or `wlan0`. The current native path is
waiting inside the proprietary ext-mdm provider `powerup()` implementation.
Android proves the hardware path can reach mdm3 `ONLINE` and WLAN-PD presence,
so the missing piece is native ext-mdm provider readiness or its prerequisite
surface, not Wi-Fi credentials or upper Wi-Fi orchestration.

V849 dmesg also preserves two provider hints:

- `Cannot config MDM_PMIC_PWR_STATUS gpio`
- `mdm_configure_ipc set AP2MDM_ERRFATAL2 as a AP2MDM_ERRFATAL`

These are not sufficient to justify writes, but they are important targets for
the next read-only live surface.

## Rejected Candidates

| Candidate | Decision | Reason |
| --- | --- | --- |
| Blind longer `subsys_esoc0` open | reject | Already blocks in `mdm_subsys_powerup` D-state |
| Raw eSoC ioctl or GPIO/sysfs write | reject | Provider source is absent and store semantics are unproven |
| MHI `power_up` write | reject now | V849 did not reach MHI hook context |
| Wi-Fi HAL/scan/connect | reject | mdm3/WLFW/BDF/`wlan0` are still absent |

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_ext_mdm_powerup_surface_classifier_v850.py
python3 scripts/revalidation/native_wifi_ext_mdm_powerup_surface_classifier_v850.py \
  --out-dir tmp/wifi/v850-plan-check \
  plan
python3 scripts/revalidation/native_wifi_ext_mdm_powerup_surface_classifier_v850.py \
  --out-dir tmp/wifi/v850-ext-mdm-powerup-surface-classifier \
  run
```

Result:

```text
decision: v850-ext-mdm-powerup-surface-selected
pass: True
device_commands_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V851 should run a live read-only ext-mdm provider surface snapshot: filtered
`/proc/kallsyms`, `/proc/interrupts`, platform driver/sysfs/of_node/power state,
eSoC sysfs, msm_subsys state, readable GPIO/debug/pinctrl if available, and
focused dmesg. It should not open raw eSoC devices, write GPIO/sysfs, start Wi-Fi
HAL, scan/connect, run DHCP/routes, ping externally, or change boot images.
