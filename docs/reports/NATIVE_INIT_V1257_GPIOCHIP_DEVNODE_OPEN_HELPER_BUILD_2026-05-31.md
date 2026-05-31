# V1257 GPIOChip Devnode-open Helper Build

- report: `docs/reports/NATIVE_INIT_V1257_GPIOCHIP_DEVNODE_OPEN_HELPER_BUILD_2026-05-31.md`
- source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe_v262`
- result: `v1257-gpiochip-devnode-open-helper-build-pass`
- pass: `true`

## Scope

V1257 is source/build-only. It adds a fail-closed helper mode for a later bounded
temporary gpiochip devnode-open proof and builds a static aarch64 helper. It does
not deploy the helper, execute a device command, create a live device node, request
a GPIO line, write PMIC/GPIO/debugfs or regulator state, open `/dev/subsys_esoc0`,
start PM/CNSS/HAL actors, scan/connect, use credentials, DHCP/routes, external
ping, reboot, flash, boot image write, or partition write.

## Helper Changes

| Item | Value |
| --- | --- |
| helper marker | `a90_android_execns_probe v262` |
| new mode | `wifi-companion-pmic-gpiochip-devnode-open-preflight` |
| new flag | `--allow-pmic-gpiochip-devnode-open-preflight` |
| output prefix | `pmic_gpiochip_devnode_open_preflight.*` |
| build artifact | `stage3/linux_init/helpers/a90_android_execns_probe_v262` |
| SHA-256 | `17773e5bcdec090c061a962833d27a783439e1b718c96b47a504f625d79cc36d` |

The new mode validates the V1256 sysfs contract for PM8150L before any devnode
action: `/sys/bus/gpio/devices/gpiochip2/dev=254:2`,
`/sys/class/gpio/gpiochip1263/label` containing `pm8150l@4:pinctrl@c000`,
base `1263`, and `ngpio=11`. Only after those checks pass, the future live gate
may create a private temporary char node for `254:2`, open it read-only, run
`GPIO_GET_CHIPINFO_IOCTL`, close it, and unlink it.

The helper still prints hard zero-action markers:
`gpio_line_request_executed=0`, `pmic_write_executed=0`,
`esoc_ioctl_executed=0`, `pm_actor_executed=0`,
`cnss_daemon_start_executed=0`, `wifi_hal_start_executed=0`,
`scan_connect_linkup=0`, `credentials=0`, `dhcp_routing=0`, and
`external_ping=0`.

## Expected Mapping

| Field | Value |
| --- | --- |
| expected device | `254:2` |
| expected chip | `gpiochip2` |
| expected class chip | `gpiochip1263` |
| expected global line | `1270` |
| expected chip offset | `7` |
| expected PMIC label fragment | `pm8150l@4:pinctrl@c000` |

V1257 does not execute the mknod/open path on the device. That path is staged for
V1259 after a separate deploy-only cycle.

## Validation

| Command | Result |
| --- | --- |
| `scripts/revalidation/build_android_execns_probe_helper.sh stage3/linux_init/helpers/a90_android_execns_probe_v262` | pass |
| `file stage3/linux_init/helpers/a90_android_execns_probe_v262` | static aarch64 executable |
| `readelf -d stage3/linux_init/helpers/a90_android_execns_probe_v262` | `There is no dynamic section in this file.` |
| `strings stage3/linux_init/helpers/a90_android_execns_probe_v262 \| rg 'v262|gpiochip-devnode-open|pmic_gpiochip_devnode_open_preflight'` | marker/mode/flag/output prefix present |

Build warnings are pre-existing `snprintf` truncation warnings in the older PM
observer sampling path; they are not introduced by the V1257 gpiochip devnode-open
preflight.

## Next

V1258 should deploy-only helper v262 and verify remote SHA, marker, mode, and
selftest. V1259 can then run a bounded live temporary-devnode-open proof. The
first GPIO line request or PMIC GPIO9 line-hold remains a later explicit gate and
must not be combined with `/dev/subsys_esoc0`, PM/CNSS/HAL actors, Wi-Fi bring-up,
credentials, DHCP/routes, or external ping.

## Safety

- source/build-only; no deploy or device contact
- no live `mknod`, GPIO line request, PMIC/GPIO/debugfs/regulator write
- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, reboot, flash, boot image write, or partition write
