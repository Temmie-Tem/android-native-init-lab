# V1262 GPIOChip Line-info Live

- report: `docs/reports/NATIVE_INIT_V1262_GPIOCHIP_LINE_INFO_LIVE_2026-05-31.md`
- runner: `scripts/revalidation/native_wifi_gpiochip_line_info_live_v1262.py`
- evidence: `tmp/wifi/v1262-gpiochip-line-info-live/manifest.json`
- result: `v1262-gpiochip-line-info-pass`
- pass: `true`

## Scope

V1262 executes only the bounded temporary gpiochip devnode plus read-only line-info
proof from helper v263. It creates a temporary private char node for gpiochip
`254:2`, opens it read-only, runs `GPIO_GET_CHIPINFO_IOCTL` and
`GPIO_GET_LINEINFO_IOCTL` for offset `7`, closes it, and unlinks it. It does not
request a GPIO line, write PMIC/GPIO/debugfs or regulator state, open
`/dev/subsys_esoc0`, start PM/CNSS/HAL actors, scan/connect, use credentials,
DHCP/routes, external ping, reboot, flash, boot image write, or partition write.

## Result

| Field | Value |
| --- | --- |
| helper | `a90_android_execns_probe v263` |
| helper SHA | `32ac877a165a266d96589387d9974dfea38c81d0adb368bf17ff15de77a9f9fb` |
| mode | `wifi-companion-pmic-gpiochip-line-info-preflight` |
| sysfs contract | matched |
| temporary `mknod` | `true` |
| read-only open | `true` |
| `GPIO_GET_CHIPINFO_IOCTL` | `true` |
| `GPIO_GET_LINEINFO_IOCTL` | `true` |
| cleanup unlink | `true` |
| chip name | `gpiochip2` |
| chip lines | `11` |
| line offset | `7` |
| global line | `1270` |
| line flags | `0x1` |
| line kernel flag | `1` |
| line is output | `0` |
| line consumer | `AP2MDM_SOFT_RESET` |
| postflight selftest | `fail=0` |

## Interpretation

V1262 proves the PMIC GPIO9 cdev line-info path is readable without requesting the
line. It also changes the next decision: line offset `7` is already kernel-owned
(`GPIOLINE_FLAG_KERNEL`) with consumer `AP2MDM_SOFT_RESET`. A userspace GPIO line
request or line-hold should be treated as unsafe and not used as the next live
repair path.

This does not invalidate the PMIC/pinctrl blocker. It means the next useful work
should classify the kernel-owned `AP2MDM_SOFT_RESET` contract and the ext-mdm
power-up sequence rather than attempting to claim the line from userspace.

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

## Next

V1263 should be host-only or source/build-only: classify the implication of
`AP2MDM_SOFT_RESET` being kernel-owned and select a safer next Wi-Fi blocker. The
current evidence rejects direct userspace PMIC GPIO9 line request/hold as the next
step. Candidate next directions are kernel-owned line state correlation, ext-mdm
power-up sequencing, or a bounded observer around the existing PM service path.

## Safety

- temporary devnode plus read-only line-info proof only
- no GPIO line request or PMIC write
- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, reboot, flash, boot image write, or partition write
