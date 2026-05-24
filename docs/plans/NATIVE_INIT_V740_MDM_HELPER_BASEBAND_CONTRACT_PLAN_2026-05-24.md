# Native Init V740 MDM Helper/Baseband Contract Plan

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_mdm_helper_baseband_contract_v740.py`
- evidence target: `tmp/wifi/v740-mdm-helper-baseband-contract/`

## Goal

Reconcile the older V621/V622 `mdm_helper` evidence with the current V739
blocker:

```text
Android: service-notifier 180 -> mdm_helper -> WLAN-PD/WLFW/BDF/wlan0
Native:  mss ONLINE, mdm3 OFFLINING, no MHI/WLFW/BDF/wlan0
```

V740 decides whether `mdm_helper` is a blind live target, a post-notifier
candidate, or still blocked by evidence gaps.

## Scope

V740 is host-only.

It does not contact the device, open `subsys_modem`, open `esoc0`, write sysfs,
write DSP boot nodes, start daemons, start service-manager, start Wi-Fi HAL,
scan/connect, use credentials, run DHCP, change routes, external ping, write a
boot image, or write a partition.

## Inputs

| input | purpose |
| --- | --- |
| V739 | current Android/native `mdm3` delta and active blocker |
| V621 | prior `mdm_helper`/`mdm_launcher` static contract classification |
| V622 | same-boot Android `mdm_helper` timing and lower Wi-Fi markers |
| V614 snapshot | vendor init `mdm_helper`, `mdm_launcher`, `init.mdm.sh` contract |
| V735 | native CNSS-only window that once produced service publication |
| V738 | latest native modem/WLAN/MHI observer |

## Expected Classification

V740 should pass if it proves:

1. V739 remains the active blocker: Android `mdm3=ONLINE`, native
   `mdm3=OFFLINING`;
2. Android static init has `vendor.mdm_helper` as the real disabled service and
   `vendor.mdm_launcher` as the `ro.baseband` wrapper;
3. V622 same-boot timing places `mdm_helper` after service-notifier `180` but
   before WLAN-PD;
4. therefore `mdm_helper` is not a first-trigger target and must not be blindly
   started;
5. a future live proof, if selected, must be gated on a native lower
   service-publication window and remain below HAL/connect.

## Validation Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_baseband_contract_v740.py

python3 scripts/revalidation/native_wifi_mdm_helper_baseband_contract_v740.py \
  --out-dir tmp/wifi/v740-mdm-helper-baseband-contract-plan plan

python3 scripts/revalidation/native_wifi_mdm_helper_baseband_contract_v740.py \
  --out-dir tmp/wifi/v740-mdm-helper-baseband-contract run
```
