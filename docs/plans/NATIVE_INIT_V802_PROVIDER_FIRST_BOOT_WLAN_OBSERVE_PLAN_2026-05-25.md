# Native Init V802 Provider-first Boot WLAN Observe Plan

## Goal

Run the V801-selected live gate: combine the strongest known provider-first
service context with the bounded `boot_wlan` trigger, then classify whether the
WLAN path advances past HDD init toward ICNSS-QMI, WLFW, BDF, wiphy, or
`wlan0`.

## Scope

- Target scripts:
  - `scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_v802.py`
  - `scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_orchestrator_v802.py`
- Target helper:
  - `/cache/bin/a90_android_execns_probe`
  - marker: `a90_android_execns_probe v124`
  - sha256: `d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6`
- Expected native image:
  - `A90 Linux init 0.9.68 (v724)`

## Live Gate

```text
V641 clean-DSP reboot
  -> V401 SELinuxfs mount surface
  -> V490 SELinux policy-load proof
  -> service74-gated provider-first service-manager / PeripheralManager context
  -> initial CNSS daemon suppressed until PeripheralManager query
  -> CNSS retry
  -> bounded a90_wlanbootctl boot-observe
  -> read-only ICNSS/WLAN/QRTR capture
  -> reboot cleanup
```

## Hard Gates

- No Wi-Fi HAL, `wificond`, supplicant, or hostapd start.
- No scan/connect/link-up, credential use, DHCP, route change, or external ping.
- No direct `qcwlanstate` write outside the fixed `a90_wlanbootctl` contract.
- No `esoc0` open/hold, bind/unbind, driver override, module load/unload,
  boot image write, partition write, or custom kernel flash.
- No Wi-Fi secret material in tracked output.

## Success Criteria

- Both V802 runners compile and plan-only manifests pass.
- Current-boot prep completes on recovered stock v724.
- Service `74` gate opens and PeripheralManager is visible before CNSS retry is
  interpreted.
- CNSS retry is observable and postflight safe.
- `boot_wlan` observe executes below Wi-Fi HAL/scan/connect.
- Any ICNSS-QMI/WLFW/BDF/wiphy/`wlan0` progression is classified; if absent,
  preserve the HDD/PLD boundary without widening to credentials or external
  networking.
- Reboot cleanup returns native v724 to healthy status.

## Validation

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
git diff --check
```
