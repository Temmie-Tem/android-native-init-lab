# V1299 Compact Dense Response Sampler Live

- date: 2026-05-31
- scope: bounded live no-write response sampler
- helper: `a90_android_execns_probe v272`
- live runner: `scripts/revalidation/native_wifi_compact_dense_response_sampler_live_v1299.py`
- evidence: `tmp/wifi/v1299-compact-dense-response-sampler-live/manifest.json`
- result: `v1299-compact-dense-full-window-response-sampled-no-esoc0-trigger`
- pass: `true`

## Purpose

V1296 showed V1295's dense sampler stopped at `14/40` because helper stdout was
truncated at `1048576` bytes. V1297/V1298 added and deployed the compact dense
sampler. V1299 reruns the same bounded late-`per_proxy` response window using
compact output.

## Result

The compact dense sampler completed the full intended response window:

| field | value |
|---|---|
| mode | `late-per-proxy-dense-compact-pinctrl-irq-pcie` |
| sample count | `42` |
| phases | `pre_late_per_proxy`, `late_per_proxy_poll_00..39`, `post_late_per_proxy` |
| `response_sampler.end` | `present` |
| helper stdout truncated | `false` |
| helper stdout bytes | `778235` |

The output cap blocker is closed. The new observed blocker is that this compact
run did not observe `pm-service` opening `/dev/subsys_esoc0`.

## Observations

| field | value |
|---|---|
| late `per_proxy` started | `1` |
| late `per_proxy` poll count | `40` |
| `per_mgr` `/dev/subsys_modem` seen | `1` |
| `pm_proxy_helper` `/dev/subsys_modem` seen | `1` |
| `per_mgr` `/dev/subsys_esoc0` seen | `0` |
| GPIO142 IRQ total | `0` |
| PCI devices | `0` |
| MHI bus devices | `0` |
| MHI pipe | `absent` |
| `ks` process | `0` |
| `wlan0` | `absent` |
| `mdm3` | `OFFLINING` |

Read-only surface details stayed consistent with prior no-response runs:

- TLMM GPIO135 target line: `gpio135 : out 0 16mA no pull`
- TLMM GPIO142 target line: `gpio142 : in  0 8mA no pull`
- PMIC soft reset line is visible as `MUX UNCLAIMED`
- `gpiochip` lineinfo sees `AP2MDM_SOFT_RESET`, kernel-owned output
- zero-action guard passed: no GPIO line request, PMIC write, or eSoC ioctl

## Cleanup

- debugfs mounted for read-only observation and was absent after cleanup
- the PM observer reported `observer-reboot-required` because all actors were
  not proven safely stopped
- postflight device state was healthy after reboot:
  - `A90 Linux init 0.9.68 (v724)`
  - selftest `pass=11 warn=1 fail=0`
  - netservice disabled/stopped

## Safety Audit

- Wi-Fi HAL start: `false`
- scan/connect/link-up: `false`
- credential use: `false`
- DHCP/route: `false`
- external ping: `false`
- PMIC write: `false`
- userspace GPIO line request/hold: `false`
- direct eSoC ioctl: `false`
- flash / boot image write / partition write: `false`

## Interpretation

V1299 proves the compact sampler can capture the full dense window below the
helper stdout cap. It does not reproduce the V1295 `pm-service`
`/dev/subsys_esoc0` attempt. The next blocker is therefore no longer output
budget; it is the late-`per_proxy` to PM-service Binder/request delivery path in
the compact dense run.

## Next

V1300 should be host-only: compare V1295 and V1299 transcripts/manifests around
late `per_proxy`, `pm_proxy_helper`, `per_mgr`, Binder delivery, child exits,
and compact-vs-verbose side effects. Do not run another live trigger until the
missing `/dev/subsys_esoc0` attempt is explained.
