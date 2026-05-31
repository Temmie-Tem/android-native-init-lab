# V1243 SDX50M Power Prerequisite Response Sampler

- report: `docs/reports/NATIVE_INIT_V1243_SDX50M_POWER_PREREQ_RESPONSE_LIVE_2026-05-31.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper binary: `stage3/linux_init/helpers/a90_android_execns_probe_v259`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v259_deploy_preflight_v1243.py`
- live wrapper: `scripts/revalidation/native_wifi_sdx50m_power_prereq_response_live_v1243.py`
- shared sampler: `scripts/revalidation/native_wifi_late_per_proxy_response_sampler_live_v1242.py`
- deploy evidence: `tmp/wifi/v1243-execns-helper-v259-deploy/manifest.json`
- live evidence: `tmp/wifi/v1243-sdx50m-power-prereq-response-live/manifest.json`
- postflight evidence: `tmp/wifi/v1243-postflight-health/summary.md`

- helper version: `a90_android_execns_probe v259`
- helper sha256: `21085ecd7ddeb8132ae52d236f5d95d47d8cc899494eaa9646f0f196d8c035e5`
- deploy decision: `execns-helper-v259-deploy-pass`
- live decision: `v1243-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- pass: `True`

## Purpose

V1242 proved that the bounded late `per_proxy` path reaches
`pm-service -> /dev/subsys_esoc0`, but no GPIO142, PCIe, MHI, or `wlan0`
response appears. V1243 keeps the same action surface and improves the observer
so PMIC soft-reset GPIO evidence is not confused with TLMM GPIO9.

## Changes

| file | change |
| --- | --- |
| `stage3/linux_init/helpers/a90_android_execns_probe.c` | bumped helper to `v259`; added pinctrl source paths, PM8150L soft-reset line, and PCIe GDSC regulator lines to the response sampler |
| `scripts/revalidation/wifi_execns_helper_v259_deploy_preflight_v1243.py` | added fail-closed deploy/preflight wrapper for helper `v259` |
| `scripts/revalidation/native_wifi_sdx50m_power_prereq_response_live_v1243.py` | added V1243 wrapper around the V1242 bounded sampler |
| `scripts/revalidation/native_wifi_late_per_proxy_response_sampler_live_v1242.py` | generalized cycle labels and parsed the new v259 fields |

## Live Result

| field | value |
| --- | --- |
| sample count | `14` |
| `pm-service` `/dev/subsys_esoc0` attempt | `True` |
| late `per_proxy` started | `1` |
| GPIO142 `mdm status` IRQ count | `0` in every sample |
| `mdm3` state | `OFFLINING` in every sample |
| PCI device count | `0` in every sample |
| MHI bus count | `0` in every sample |
| MHI pipe seen | `False` |
| `wlan0` seen | `False` |
| AP2MDM GPIO135 pinctrl source | `/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins` |
| MDM2AP GPIO142 pinctrl source | `/sys/kernel/debug/pinctrl/3000000.pinctrl/pinmux-pins` |
| PMIC soft-reset source | `/sys/kernel/debug/pinctrl/c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000/pinmux-pins` |
| PMIC soft-reset line | `pin 7 (gpio9): (MUX UNCLAIMED) c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000:1270` |
| PCIe 1 GDSC line | `pcie_1_gdsc 0 2 0 0mV 0mA 0mV 0mV` |
| PCIe 0 GDSC line | `pcie_0_gdsc 0 1 0 0mV 0mA 0mV 0mV` |

All newly added power-prerequisite observer fields stayed unchanged from
`pre_late_per_proxy` through `late_per_proxy_poll_11` and
`post_late_per_proxy`.

## Interpretation

V1243 confirms that V1242's generic `pmic9_line` was not sufficient: it matched
TLMM GPIO9 first. The corrected PM8150L soft-reset observer sees the expected
PMIC pinctrl surface, but the line remains `MUX UNCLAIMED` across the full
bounded trigger window. The PCIe GDSC debug regulator lines also remain at
`0mV`, and no PCIe/MHI downstream device appears.

This does not prove a GPIO logic level. It does narrow the current blocker:
the Android-like userspace path reaches `mdm_subsys_powerup`, but the observable
PMIC soft-reset, PCIe GDSC, GPIO142, PCIe RC1, MHI, WLFW, and `wlan0` surfaces
do not move in native init.

Current next hypothesis:

```text
pm-service -> /dev/subsys_esoc0 -> mdm_subsys_powerup
  -> PM8150L soft-reset / PCIe GDSC observable state does not change
  -> no GPIO142 mdm status IRQ
  -> no PCIe RC1 / MHI / WLFW / wlan0
```

The next useful unit should compare the same PMIC soft-reset and PCIe GDSC
surfaces against Android-positive evidence, or use a still-bounded tracepoint
or userspace wrapper to prove whether the proprietary eSoC powerup path reaches
the PMIC/GDSC operations.

## Postflight

The live run returned `observer-reboot-required` because the actor process was
not proven stopped. A post-run reboot/health check returned the device to a
clean native init state:

- `boot: BOOT OK`
- `selftest: pass=11 warn=1 fail=0`
- `netservice: ncm0=absent tcpctl=stopped`

## Safety

V1243 did not start Wi-Fi HAL, perform scan/connect/link-up, use credentials,
run DHCP/routes, send external ping, send ESOC_NOTIFY, send ESOC_BOOT_DONE,
write boot/partitions, or flash. The only persistent device mutation was
deployment of helper `v259` to `/cache/bin/a90_android_execns_probe`.
