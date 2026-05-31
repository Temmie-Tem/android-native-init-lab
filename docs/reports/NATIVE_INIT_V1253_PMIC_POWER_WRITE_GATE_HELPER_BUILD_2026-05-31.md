# V1253 PMIC/Power-surface Write-gate Helper Build

- report: `docs/reports/NATIVE_INIT_V1253_PMIC_POWER_WRITE_GATE_HELPER_BUILD_2026-05-31.md`
- source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe_v261`
- evidence: `tmp/wifi/v1253-pmic-power-write-gate-helper-build/manifest.json`
- result: `v1253-pmic-power-write-gate-helper-build-pass`
- pass: `true`

## Scope

V1253 is source/build-only. It adds a fail-closed helper mode for the PMIC GPIO9
write-gate preflight and builds a static aarch64 helper. It does not deploy the
helper, execute a device command, request a GPIO line, write PMIC/GPIO/debugfs or
regulator state, open `/dev/subsys_esoc0`, start PM/CNSS/HAL actors, scan/connect,
use credentials, DHCP/routes, external ping, reboot, flash, boot image write, or
partition write.

## Helper Changes

| Item | Value |
| --- | --- |
| helper marker | `a90_android_execns_probe v261` |
| new mode | `wifi-companion-pmic-power-surface-write-gate-preflight` |
| new flag | `--allow-pmic-power-write-gate-preflight` |
| output prefix | `pmic_power_write_gate_preflight.*` |
| build artifact | `stage3/linux_init/helpers/a90_android_execns_probe_v261` |
| SHA-256 | `37947e378f4743a6661a03ee36dfc95ddf5ce9cd79acec0862a28a4564573a7c` |

The new mode verifies the V1251 read contract, scans `/dev/gpiochip*` via
`GPIO_GET_CHIPINFO_IOCTL`, cross-checks `/sys/kernel/debug/gpio` for the
expected PM8150L range, and prints the candidate PMIC GPIO9 mapping. It remains
read-only and prints `gpio_line_request_executed=0`, `esoc_ioctl_executed=0`,
and `pm_actor_executed=0`.

## Expected Mapping

| Field | Value |
| --- | --- |
| expected global line | `1270` |
| expected GPIO chip range | `1263-1273` |
| expected chip offset | `7` |
| expected DTS device | `qcom,ext-sdx50m` |

V1253 does not assume this mapping is valid on-device. The later deploy/live
preflight must derive it from live `gpiochip` and debugfs surfaces before any
line-hold proof is considered.

## Validation

| Command | Result |
| --- | --- |
| `scripts/revalidation/build_android_execns_probe_helper.sh stage3/linux_init/helpers/a90_android_execns_probe_v261` | pass |
| `file stage3/linux_init/helpers/a90_android_execns_probe_v261` | static aarch64 executable |
| `aarch64-linux-gnu-readelf -d stage3/linux_init/helpers/a90_android_execns_probe_v261` | `There is no dynamic section in this file.` |
| `strings stage3/linux_init/helpers/a90_android_execns_probe_v261 \| rg 'v261|write-gate'` | marker/mode/flag/output prefix present |

Build warnings are pre-existing `snprintf` truncation warnings in the older
PM observer sampling code path; they are not introduced by the V1253 PMIC
write-gate preflight.

## Next

V1254 should deploy-only helper v261 and verify remote SHA, marker, mode, and
selftest. V1255 can then run the temporary-debugfs read-only mapping preflight.
The first live write proof remains a separate later gate and must not combine
PMIC GPIO9 line hold with `/dev/subsys_esoc0` or PM actor start in the same
cycle.

## Safety

- source/build-only; no deploy or device contact
- no PMIC/GPIO/debugfs/regulator write
- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, reboot, flash, boot image write, or partition write
