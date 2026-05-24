# Native Init V802 Provider-first Boot WLAN Observe Report

## Result

- decision: `v802-provider-first-boot-wlan-hdd-boundary-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_orchestrator_v802.py`
- evidence: `tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed/`
- helper: `a90_android_execns_probe v124`
- native image: `A90 Linux init 0.9.68 (v724)`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_v802.py \
  scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_orchestrator_v802.py

python3 scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_v802.py \
  --out-dir tmp/wifi/v802-provider-first-boot-wlan-observe-plan-check-after-parse-fix \
  plan

python3 scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_orchestrator_v802.py \
  --out-dir tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-plan-check-after-parse-fix \
  plan

python3 scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_orchestrator_v802.py \
  --out-dir tmp/wifi/v802-provider-first-boot-wlan-observe-orchestrated-live-fixed \
  --cnss-runtime-sec 30 \
  --boot-observe-sec 25 \
  --apply \
  --assume-yes \
  run

python3 scripts/revalidation/a90ctl.py selftest
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| cleanup native version | v724 observed |
| cleanup selftest | `pass=11 warn=1 fail=0` |
| current-boot prep | pass |
| service `74` gate | open |
| PeripheralManager exact query | yes |
| initial CNSS daemon | suppressed |
| CNSS retry | observable, start order `11`, signal `9`, postflight safe |
| `boot_wlan` observe | executed |
| `wlan: Loading driver` | `1` |
| HDD state major marker | `1` |
| `qcwlanstate` markers | `30` |
| `wlan: driver loaded` | `0` |
| ICNSS-QMI / FW-ready | `0 / 0` |
| service `69` / WLFW / BDF | `0 / 0 / 0` |
| wiphy / `wlan0` | `0 / 0` |
| `mss` after boot | `ONLINE` |
| `mdm3` after boot | `OFFLINING` |
| known ASoC `pm_qos` warning | finding, not first blocker |
| Wi-Fi HAL / scan / connect / credentials / DHCP / external ping | not executed |

## Interpretation

V802 proves that simply combining the best provider-first service context with a
bounded `boot_wlan` trigger does not move the device beyond the known HDD init
boundary.

```text
service74 gate open
  -> PeripheralManager exact query
  -> CNSS retry observable
  -> boot_wlan observe executed
  -> wlan: Loading driver / qcwlanstate activity
  -> no driver-loaded, ICNSS-QMI, WLFW, BDF, wiphy, or wlan0
```

The immediate blocker is therefore inside the HDD/PLD-to-ICNSS transition in
this exact provider-first `boot_wlan` window, not Wi-Fi HAL, `wificond`,
credentials, DHCP, or routing. The repeated `pm_qos_add_request()` warning is
kept as a finding because V792 already classified this exact ASoC warning path
as not the first WLFW blocker.

## Safety

- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credential use,
  DHCP, route change, or external ping.
- No `esoc0` open/hold, bind/unbind, driver override, module load/unload, boot
  image write, partition write, or custom kernel flash.
- Runtime cleanup reboot returned native v724 to healthy status.
- No Wi-Fi secret material was written to tracked output.

## Next

V803 should be a narrow HDD/PLD prerequisite classifier for the provider-first
`boot_wlan` window. It should use V802 evidence plus Samsung OSRC symbols to
identify which prerequisite prevents `wlan_hdd_probe()` / `hdd_wlan_startup()`
from reaching `wlan: driver loaded`. Do not repeat blind `boot_wlan`, and do
not move to Wi-Fi HAL, scan/connect, credentials, DHCP, routes, or external
ping until ICNSS-QMI/WLFW/BDF/wiphy/`wlan0` appears.
