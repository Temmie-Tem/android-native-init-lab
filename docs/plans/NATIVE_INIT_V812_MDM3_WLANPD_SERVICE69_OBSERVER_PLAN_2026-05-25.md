# Native Init V812 mdm3/WLAN-PD/service69 Observer Plan

## Goal

Run the smallest current-stock-v724 live observer for the mdm3/WLAN-PD/WLFW
publication blocker selected by V811, while staying below Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, and external ping.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_mdm3_wlanpd_service69_observer_v812.py`
- Inputs:
  - V811 WLFW publication precondition classifier.
  - Current native build `A90 Linux init 0.9.68 (v724)`.
  - Current helper v124 at `/cache/bin/a90_android_execns_probe`.
  - V401 SELinuxfs mount proof and V490 native policy-load proof.
  - Existing V735 current CNSS-only observer, reused as the live arm.

## Hard Gates

- No custom kernel flash, boot image write, partition write, or bootloader
  handoff.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect/link-up, or
  credential use.
- No DHCP, route change, or external ping.
- No `esoc0` open/hold, subsystem state write, bind/unbind, driver override, or
  module load/unload.
- Firmware mounts and the `subsys_modem` holder are allowed only inside the
  bounded lower observer window.
- Cleanup must return to healthy stock v724 native init.

## Success Criteria

- V812 compiles and plan-only manifest passes.
- V401 and V490 refresh pass on the current boot before the lower observer.
- The live arm starts only the lower companion/CNSS diagnostic stack and does
  not cross into service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP,
  routes, or external ping.
- The result classifies whether mdm3/WLAN-PD/WLFW service69 publication
  advanced beyond the V811 blocker.
- Postflight verifies healthy v724 native init after cleanup.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_wlanpd_service69_observer_v812.py

python3 scripts/revalidation/native_wifi_mdm3_wlanpd_service69_observer_v812.py \
  --out-dir tmp/wifi/v812-mdm3-wlanpd-service69-observer-plan-check \
  plan

python3 scripts/revalidation/native_wifi_mdm3_wlanpd_service69_observer_v812.py \
  --out-dir tmp/wifi/v812-mdm3-wlanpd-service69-observer-rerun \
  run

git diff --check
```
