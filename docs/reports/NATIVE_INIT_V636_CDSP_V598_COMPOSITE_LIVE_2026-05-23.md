# Native Init V636 CDSP + V598 Composite Live Report

- date: `2026-05-23 KST`
- status: `pass/classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_cdsp_v598_composite_v636.py`
- V401 evidence: `tmp/wifi/v636-v401-current-run-after-hide/`
- V490 evidence: `tmp/wifi/v636-v490-current-run-after-system/`
- preflight evidence: `tmp/wifi/v636-cdsp-v598-preflight-20260523-054527/`
- live evidence: `tmp/wifi/v636-cdsp-v598-live-20260523-054728/`
- decision: `v636-cdsp-v598-service180-only`

## Scope

V636 tested the intersection of two prior safe partial positives in one boot:

1. V635 firmware mount + CDSP-only bounded write;
2. V598/V625/V627 modem-holder companion + WLFW QRTR readback path.

It did not write ADSP/SLPI, `boot_wlan`, `qcwlanstate`, or `shutdown_wlan`,
start service-manager or Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, or ping externally.

## Setup

The current-state preflight before refresh blocked as expected:

```text
decision: v636-cdsp-v598-blocked
reason: blocked by v490-current-policy-load, cdsp-initial-not-online
```

The device was rebooted to a fresh native v319 baseline. Post-reboot health was
`BOOT OK` with `fail=0`. Then:

- V401 SELinuxfs mount passed after hiding the interactive menu;
- `mountsystem ro` mounted Android system read-only;
- V490 SELinux policy-load passed with no init reexec, daemon start, or Wi-Fi
  bring-up;
- V636 preflight passed with fresh V490 and `initial_cdsp_online=False`.

One V636 live attempt stopped before mount/CDSP mutation due to a runner-side
missing `proof_id` argument. The runner was fixed and the accepted live evidence
is `tmp/wifi/v636-cdsp-v598-live-20260523-054728/`.

## Result

```text
decision: v636-cdsp-v598-service180-only
pass: True
reason: post_cdsp_markers={'service_notifier_180': 1, 'service_notifier_74': 0, 'wlan_pd': 0, 'qmi_server_connected': 0, 'wlfw_start': 0, 'bdf_regdb': 0, 'bdf_bdwlan': 0, 'wlan_fw_ready': 0, 'wlan0': 0, 'kernel_warning': 0}
next: classify why CDSP-online still does not publish service 74
device_commands_executed: True
device_mutations: True
cdsp_write_executed: True
daemon_start_executed: True
wifi_bringup_executed: False
```

## Preflight Checks

| check | result | detail |
| --- | --- | --- |
| native clean | pass | v319, health `fail=0` |
| V490 current policy-load | pass | fresh for current boot |
| V525 companion identity | pass | required identities captured |
| helper v100 | pass | expected sha/marker active |
| firmware class path | pass | `/vendor/firmware_mnt/image` |
| firmware partitions | pass | `apnhlos=sda20`, `modem=sda21` |
| firmware mount targets | pass | not mounted before proof |
| subsystem modem cdev | pass | `236:0` visible |
| active target processes | pass | no residual holder/companion process |
| Wi-Fi link surface | pass | no `wlan0`/Wi-Fi link |
| initial CDSP | pass | not already `ONLINE` |

## Live Markers

| marker | delta |
| --- | ---: |
| `cdsp_pil` | 1 |
| `cdsp_power_clock` | 1 |
| `cdsp_brought_reset` | 1 |
| `sysmon_cdsp` | 0 |
| `service_notifier_180` | 1 |
| `service_notifier_74` | 0 |
| `wlan_pd` | 0 |
| `qmi_server_connected` | 0 |
| `wlfw_start` | 0 |
| `bdf_regdb` | 0 |
| `bdf_bdwlan` | 0 |
| `wlan_fw_ready` | 0 |
| `wlan0` | 0 |
| `kernel_warning` | 0 |

## Cleanup

The V598-class live path used reboot cleanup. Post-run `bootstatus` confirmed:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped
```

## Interpretation

CDSP-online does not regress the V598/V625/V627 safe partial positive: native
still reaches service-notifier `180`, and it does so without kernel warnings.

However, adding CDSP-online is still insufficient for Android's missing lower
Wi-Fi publication path. Service `74`, WLAN-PD, WLFW service `69`, BDF, firmware
ready, and `wlan0` remain absent. This keeps Wi-Fi HAL, scan/connect,
credentials, DHCP, routes, and external ping blocked.

## Next Gate

The next cycle should be host-only first: compare Android's service `180 -> 74`
transition against V636's post-CDSP-online service `180`-only evidence. The
likely target is the lower service `74` publisher dependency, not CDSP firmware
loading and not Wi-Fi credentials.
