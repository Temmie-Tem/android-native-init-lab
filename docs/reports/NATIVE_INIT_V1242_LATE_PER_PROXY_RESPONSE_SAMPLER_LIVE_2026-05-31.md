# V1242 Late per_proxy Response Sampler

- report: `docs/reports/NATIVE_INIT_V1242_LATE_PER_PROXY_RESPONSE_SAMPLER_LIVE_2026-05-31.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper binary: `stage3/linux_init/helpers/a90_android_execns_probe_v258`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v258_deploy_preflight_v1242.py`
- live classifier: `scripts/revalidation/native_wifi_late_per_proxy_response_sampler_live_v1242.py`
- deploy evidence: `tmp/wifi/v1242-execns-helper-v258-deploy/manifest.json`
- live evidence: `tmp/wifi/v1242-late-per-proxy-response-sampler-live/manifest.json`
- postflight evidence: `tmp/wifi/v1242-postflight-health/summary.md`

- helper version: `a90_android_execns_probe v258`
- helper sha256: `dd9bee9e2c0750c51be2151dd4b192d0612dd9269419c1641b9395d7336b6119`
- deploy decision: `execns-helper-v258-deploy-pass`
- live decision: `v1242-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- pass: `True`
- reason: `pm-service` reached `/dev/subsys_esoc0`, but the response sampler saw no GPIO142, MHI, or `wlan0` response. The observer process was not proven stopped, so the run required reboot/health-check.

## Changes

| file | change |
| --- | --- |
| `stage3/linux_init/helpers/a90_android_execns_probe.c` | bumped helper to `v258` and added `--pm-observer-late-per-proxy-response-sampler` |
| `scripts/revalidation/wifi_execns_helper_v258_deploy_preflight_v1242.py` | added fail-closed deploy/preflight wrapper for helper `v258` |
| `scripts/revalidation/native_wifi_late_per_proxy_response_sampler_live_v1242.py` | added V1238-derived live sampler with temporary debugfs mount and cleanup |

## Deploy

| field | value |
| --- | --- |
| transfer method | `ncm` through wrapper `auto` |
| device mutations | `True` (`/cache/bin/a90_android_execns_probe` update only) |
| daemon start | `False` |
| Wi-Fi bring-up | `False` |
| post-deploy preflight | `service-manager-start-only-smoke-approval-required`, `pass=True` |

NCM was enabled only to avoid slow serial transfer. No Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, flash, boot image write, or partition
write was performed.

## Live Result

| field | value |
| --- | --- |
| sample count | `14` |
| sampler mode | `late-per-proxy-pinctrl-irq-pcie` |
| `pm-service` `/dev/subsys_esoc0` attempt | `True` |
| late `per_proxy` started | `1` |
| GPIO142 `mdm status` IRQ count | `0` |
| PCI device count | `0` |
| MHI bus count | `0` |
| MHI pipe seen | `False` |
| `wlan0` seen | `False` |
| debugfs pinctrl seen | `True` |
| AP2MDM GPIO135 pinctrl | visible |
| MDM2AP GPIO142 pinctrl | visible |
| `mdm3` state during samples | `OFFLINING` |

The useful observation is now stable: even when the Android-like late
`per_proxy` path reaches `pm-service` and `pm-service` attempts
`/dev/subsys_esoc0`, native init still receives no MDM2AP GPIO142 response and
does not advance to PCIe RC1, MHI, WLFW, or `wlan0`.

## Interpretation

V1242 closes the "maybe the sampler missed the response" gap for the bounded
late `per_proxy` path. The blocker is lower than Binder/peripheral-manager
delivery and lower than `pm-service` entry into `mdm_subsys_powerup`.

Current narrowed blocker:

```text
per_proxy -> pm-service Binder -> /dev/subsys_esoc0 -> mdm_subsys_powerup
  -> no GPIO142 mdm status IRQ
  -> no PCIe RC1 device
  -> no MHI pipe
  -> no WLFW service
  -> no wlan0
```

The next useful work is SDX50M power/GPIO prerequisite classification, not
another blind retry of `per_proxy`, `mdm_helper`, CNSS, or Wi-Fi HAL start.

## Postflight

The live run returned `observer-reboot-required` because the actor process was
not proven stopped. A post-run reboot/health check returned the device to a
clean native init state:

- `boot: BOOT OK`
- `selftest: pass=11 warn=1 fail=0`
- `netservice: ncm0=absent tcpctl=stopped`

## Safety

V1242 remained a bounded observer gate. It did not start Wi-Fi HAL, perform
scan/connect/link-up, use credentials, run DHCP/routes, send external ping,
send ESOC_NOTIFY, send ESOC_BOOT_DONE, write boot/partitions, or flash. The
only persistent device mutation was deployment of the helper binary to
`/cache/bin/a90_android_execns_probe`.
