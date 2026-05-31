# V1259 GPIOChip Devnode-open Live

- report: `docs/reports/NATIVE_INIT_V1259_GPIOCHIP_DEVNODE_OPEN_LIVE_2026-05-31.md`
- runner: `scripts/revalidation/native_wifi_gpiochip_devnode_open_live_v1259.py`
- evidence: `tmp/wifi/v1259-gpiochip-devnode-open-live/manifest.json`
- result: `v1259-gpiochip-devnode-open-pass`
- pass: `true`

## Scope

V1259 executes only the bounded temporary gpiochip devnode-open proof from helper
v262. It creates a temporary private char node for gpiochip `254:2`, opens it
read-only, runs `GPIO_GET_CHIPINFO_IOCTL`, closes it, and unlinks it. It does not
request a GPIO line, write PMIC/GPIO/debugfs or regulator state, open
`/dev/subsys_esoc0`, start PM/CNSS/HAL actors, scan/connect, use credentials,
DHCP/routes, external ping, reboot, flash, boot image write, or partition write.

## Result

| Field | Value |
| --- | --- |
| helper | `a90_android_execns_probe v262` |
| helper SHA | `17773e5bcdec090c061a962833d27a783439e1b718c96b47a504f625d79cc36d` |
| mode | `wifi-companion-pmic-gpiochip-devnode-open-preflight` |
| sysfs dev match | `true` |
| sysfs label match | `true` |
| sysfs base match | `true` |
| sysfs ngpio match | `true` |
| temporary `mknod` | `true` |
| read-only open | `true` |
| `GPIO_GET_CHIPINFO_IOCTL` | `true` |
| cleanup unlink | `true` |
| chip name | `gpiochip2` |
| chip label | `c440000.qcom,spmi:qcom,pm8150l@` |
| chip lines | `11` |
| postflight selftest | `fail=0` |

The truncated chip label is the kernel cdev `GPIO_MAX_NAME_SIZE` output. The
identity remains sufficient because the sysfs label match had already confirmed
`pm8150l@4:pinctrl@c000` before the temporary devnode was created.

## Zero-action Markers

All forbidden-action markers stayed zero:

| Marker | Value |
| --- | --- |
| `gpio_line_request_executed` | `0` |
| `pmic_write_executed` | `0` |
| `esoc_ioctl_executed` | `0` |
| `pm_actor_executed` | `0` |
| `cnss_daemon_start_executed` | `0` |
| `wifi_hal_start_executed` | `0` |
| `scan_connect_linkup` | `0` |
| `credentials` | `0` |
| `dhcp_routing` | `0` |
| `external_ping` | `0` |

## Interpretation

V1259 closes the devnode-open uncertainty. Native init can safely materialize the
missing gpiochip cdev node from sysfs metadata, open PM8150L's gpiochip read-only,
query chip metadata, and remove the node afterward. This does not yet prove that
requesting or holding PMIC GPIO9 is safe; it only proves the cdev access path and
cleanup behavior.

## Next

V1260 should be a source/build-only or host-only plan for the next smallest PMIC
GPIO9 gate. The preferred next live proof is still read-only if possible:
`GPIO_GET_LINEINFO_IOCTL` for offset `7` on gpiochip `254:2`, with no line request
and no output value change. A GPIO line request or PMIC GPIO9 hold should remain a
separate later gate after line-info flags and current consumer state are captured.

## Safety

- temporary devnode-open proof only
- no GPIO line request or PMIC write
- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, reboot, flash, boot image write, or partition write
