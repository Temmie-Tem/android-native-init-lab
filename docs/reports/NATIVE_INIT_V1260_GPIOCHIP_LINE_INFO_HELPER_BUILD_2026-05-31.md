# V1260 GPIOChip Line-info Helper Build

- report: `docs/reports/NATIVE_INIT_V1260_GPIOCHIP_LINE_INFO_HELPER_BUILD_2026-05-31.md`
- source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe_v263`
- result: `v1260-gpiochip-line-info-helper-build-pass`
- pass: `true`

## Scope

V1260 is source/build-only. It adds a fail-closed helper mode for the next
read-only PMIC GPIO9 line-info proof and builds a static aarch64 helper. It does
not deploy the helper, execute a device command, create a live device node,
request a GPIO line, write PMIC/GPIO/debugfs or regulator state, open
`/dev/subsys_esoc0`, start PM/CNSS/HAL actors, scan/connect, use credentials,
DHCP/routes, external ping, reboot, flash, boot image write, or partition write.

## Helper Changes

| Item | Value |
| --- | --- |
| helper marker | `a90_android_execns_probe v263` |
| new mode | `wifi-companion-pmic-gpiochip-line-info-preflight` |
| new flag | `--allow-pmic-gpiochip-line-info-preflight` |
| output prefix | `pmic_gpiochip_line_info_preflight.*` |
| build artifact | `stage3/linux_init/helpers/a90_android_execns_probe_v263` |
| SHA-256 | `32ac877a165a266d96589387d9974dfea38c81d0adb368bf17ff15de77a9f9fb` |

The new mode reuses the V1259 temporary devnode pattern, but adds only the
read-only `GPIO_GET_LINEINFO_IOCTL` for PMIC GPIO9 offset `7`. It prints line
flags, line name, and line consumer while preserving zero-action markers for GPIO
line request, PMIC write, eSoC ioctl, PM/CNSS/HAL actors, scan/connect,
credentials, DHCP/routes, and external ping.

## Expected Mapping

| Field | Value |
| --- | --- |
| expected device | `254:2` |
| expected chip | `gpiochip2` |
| expected class chip | `gpiochip1263` |
| expected global line | `1270` |
| expected chip offset | `7` |
| expected PMIC label fragment | `pm8150l@4:pinctrl@c000` |

## Validation

| Command | Result |
| --- | --- |
| `scripts/revalidation/build_android_execns_probe_helper.sh stage3/linux_init/helpers/a90_android_execns_probe_v263` | pass |
| `file stage3/linux_init/helpers/a90_android_execns_probe_v263` | static aarch64 executable |
| `readelf -d stage3/linux_init/helpers/a90_android_execns_probe_v263` | `There is no dynamic section in this file.` |
| `strings stage3/linux_init/helpers/a90_android_execns_probe_v263 \| rg 'v263|gpiochip-line-info|pmic_gpiochip_line_info_preflight'` | marker/mode/flag/output prefix present |

Build warnings are pre-existing `snprintf` truncation warnings in the older PM
observer sampling path; they are not introduced by the V1260 line-info preflight.

## Next

V1261 should deploy-only helper v263 and verify remote SHA, marker, mode, and
selftest. V1262 can then run the bounded live line-info proof. A GPIO line request
or PMIC GPIO9 hold remains a later explicit gate after the line flags and consumer
state are captured.

## Safety

- source/build-only; no deploy or device contact
- no live `mknod`, GPIO line request, PMIC/GPIO/debugfs/regulator write
- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, reboot, flash, boot image write, or partition write
