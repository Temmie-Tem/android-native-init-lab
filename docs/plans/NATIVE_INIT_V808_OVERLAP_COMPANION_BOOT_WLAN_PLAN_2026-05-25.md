# Native Init V808 Overlap Companion Boot WLAN Plan

## Goal

Run the V807-selected live gate: keep the provider-first companion context alive
while `boot_wlan` is triggered, then classify whether WLFW service `69`,
`FW_READY`, BDF, wiphy, or `wlan0` appears before any Wi-Fi HAL or
scan/connect widening.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_overlap_companion_boot_wlan_v808.py`
- Inputs:
  - V807 overlap-route manifest.
  - Current v724 native boot.
  - V401 SELinuxfs surface and V490 policy-load prep.
  - V752 firmware mount/modem-holder/QRTR wait helpers.
  - V802 provider-first companion command and helper parser.
- Evidence output:
  - `tmp/wifi/v808-overlap-companion-boot-wlan/`

## Hard Gates

- Bounded live device gate with runner-owned reboot cleanup.
- No custom kernel flash, boot image write, partition write, Wi-Fi HAL,
  `wificond`, supplicant, hostapd, scan/connect/link-up, credential use, DHCP,
  route change, external ping, `esoc0` open, bind/unbind, driver override, or
  module load/unload.
- `boot_wlan` is allowed only through `a90_wlanbootctl boot-observe`.
- Provider-first companion is allowed only as start-only/readback below HAL.
- No Wi-Fi secret material in tracked output.

## Success Criteria

- V808 compiles and plan-only manifest passes.
- V807 route input is present and passed.
- V641/V401/V490 current-boot prep is ready.
- Firmware partitions are mounted read-only and `subsys_modem` holder reaches
  QRTR RX before overlap.
- Provider-first helper is alive when `boot_wlan` begins and final helper output
  proves service74 gate, provider query, and CNSS retry contract.
- Forbidden Wi-Fi HAL/scan/connect/network actions remain false.
- The result classifies whether overlap advances WLFW/service69/driver/netdev
  markers or leaves service69 absent.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_overlap_companion_boot_wlan_v808.py

python3 scripts/revalidation/native_wifi_overlap_companion_boot_wlan_v808.py \
  --out-dir tmp/wifi/v808-overlap-companion-boot-wlan-plan-check \
  plan

python3 scripts/revalidation/native_wifi_overlap_companion_boot_wlan_v808.py run

python3 scripts/revalidation/a90ctl.py --hide-on-busy --json selftest

git diff --check
```
