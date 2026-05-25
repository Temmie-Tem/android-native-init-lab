# Native Init V851 ext-mdm Provider Surface Snapshot Report

## Result

- decision: `v851-ext-mdm-provider-surface-limited`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_ext_mdm_provider_surface_snapshot_v851.py`
- evidence: `tmp/wifi/v851-ext-mdm-provider-surface-snapshot/`

## Scope

V851 was a live read-only run. It executed bounded serial read commands and
postflight health checks only. It did not open raw `/dev/esoc*` or
`/dev/subsys*`, write GPIO/sysfs/debugfs, export GPIOs, write subsystem state,
bind/unbind drivers, load/unload modules, start daemons, start service-manager,
start Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, ping
externally, write boot images, write partitions, or flash a custom kernel.

## Key Signals

| Signal | Value |
| --- | --- |
| Runtime | stock native `0.9.68 (v724)` |
| Pre/post health | `BOOT OK`, selftest `fail=0` |
| mdm3 state | `OFFLINING` |
| `mdm_subsys_powerup` in `/proc/kallsyms` | not exposed |
| `__subsystem_get` in `/proc/kallsyms` | present |
| `subsys_device_open` in `/proc/kallsyms` | present |
| `mhi_arch_esoc_ops_power_on` in `/proc/kallsyms` | present |
| `mhi_pci_probe` in `/proc/kallsyms` | present |
| mdm3/eSoC/sysfs | present |
| live devicetree mdm3 | present |
| AP2MDM status property | present |
| MDM2AP status property | present |
| PMIC power-status property | not present in live mdm3 node |
| `/sys/kernel/debug/gpio` | not readable |
| `/sys/kernel/debug/pinctrl` | not present/readable |
| raw `/dev/esoc*` node | absent |
| MHI/WLFW/BDF/`wlan0` runtime progress | absent |

## Interpretation

The V849 stack still proves the blocked holder was waiting in
`mdm_subsys_powerup`, but a normal idle read of `/proc/kallsyms` does not expose
that symbol. This limits source cross-reference from the idle native state.
The surrounding public symbols are visible, including `__subsystem_get`,
`subsys_device_open`, `mhi_arch_esoc_ops_power_on`, and `mhi_pci_probe`.

The provider surface remains below upper Wi-Fi: mdm3 is still `OFFLINING`, and
there is no MHI/WLFW/BDF/`wlan0` progress. GPIO/pinctrl readback is still
limited in native because debugfs GPIO is unreadable and pinctrl debug is not
present. The next useful discriminator is an Android matched snapshot of the
same provider surface, especially GPIO/IRQ/PMIC/pinctrl and mdm3 state while
Android has already proven mdm3 can reach `ONLINE`.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_ext_mdm_provider_surface_snapshot_v851.py
python3 scripts/revalidation/native_wifi_ext_mdm_provider_surface_snapshot_v851.py \
  --out-dir tmp/wifi/v851-plan-check \
  plan
python3 scripts/revalidation/native_wifi_ext_mdm_provider_surface_snapshot_v851.py \
  --out-dir tmp/wifi/v851-ext-mdm-provider-surface-snapshot \
  --allow-live-readonly \
  --assume-yes \
  run
```

Result:

```text
decision: v851-ext-mdm-provider-surface-limited
pass: True
device_commands_executed: True
device_mutations: False
raw_esoc_open_executed: False
subsys_char_open_executed: False
gpio_write_executed: False
sysfs_write_executed: False
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V852 should capture the same provider surface from Android as a matched
positive-control snapshot. The goal is to compare mdm3 state, AP2MDM/MDM2AP IRQ
counts, PMIC/pinctrl visibility, and any GPIO/debug signal that native cannot
see before considering any GPIO/eSoC write or upper Wi-Fi action.
