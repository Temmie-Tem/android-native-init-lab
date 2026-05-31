# Native Init V1304 AP2MDM/MDM2AP Response Classifier

## Summary

- Cycle: `V1304`
- Type: host-only classifier
- Decision: `v1304-ap2mdm-assertion-visibility-gap-classified`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1304-ap2mdm-mdm2ap-response-classifier/manifest.json`
  - `tmp/wifi/v1304-ap2mdm-mdm2ap-response-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_ap2mdm_mdm2ap_response_classifier_v1304.py`

V1304 compares the V1303 compact powerup-marker live evidence against Android-positive and eSoC research references. It performs no device command and does not mutate device state.

## Key Results

| field | value |
| --- | --- |
| V1303 powerup reached | `true` |
| V1303 sample/phase count | `42 / 42` |
| first path | `/dev/subsys_esoc0` |
| first wchan | `mdm_subsys_powerup` |
| GPIO135 powerup line | `gpio135 : out 0 16mA no pull` |
| GPIO142 powerup line | `gpio142 : in  0 8mA no pull` |
| GPIO135 high seen | `false` |
| GPIO142 high seen | `false` |
| MDM status count max | `0` |
| MHI bus count max | `0` |
| MHI pipe / wlan0 | `false / false` |

## Reference Check

| reference | result |
| --- | --- |
| ext-sdx50m powerup contract expects AP2MDM GPIO135 high | `true` |
| MDM2AP GPIO142 status path documented | `true` |
| Android-positive PCIe RC1 reference exists | `true` |
| Android-positive WLAN-PD/WLFW/BDF/`wlan0` reference exists | `true` |
| Android post-boot low GPIO caution exists | `true` |
| V1290 native static GPIO corroboration exists | `true` |

## Interpretation

V1303 closed the trigger-delivery question: `pm-service` reaches `openat("/dev/subsys_esoc0")` and blocks in `mdm_subsys_powerup`. V1304 classifies the remaining gap below that trigger.

During the observed powerup window, AP2MDM GPIO135 stayed low and MDM2AP GPIO142 stayed low. No MDM status IRQ, PCIe/MHI, WLFW, or `wlan0` progress appeared. The ext-sdx50m contract says AP2MDM GPIO135 should assert before MDM2AP/PCIe progress, so the current blocker is best described as an AP2MDM assertion/visibility gap.

This is not a standalone proof that GPIO135 can never pulse high. Android post-boot snapshots can also show low GPIO lines after successful lower progress. The next unit should therefore tighten timing/visibility before any lower mutating retry.

## Next

V1305 should either:

1. add a tighter read-only AP2MDM/MDM2AP transition sampler around the first `mdm_subsys_powerup` marker, or
2. classify the ext-mdm PMIC/pinctrl branch that prevents GPIO135 assertion.

Do not run another blind eSoC/PM/CNSS retry until this boundary is closed.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_ap2mdm_mdm2ap_response_classifier_v1304.py
python3 scripts/revalidation/native_wifi_ap2mdm_mdm2ap_response_classifier_v1304.py run
```

Both passed.

## Safety

- Host-only classifier; no bridge/device command.
- No PMIC write, userspace GPIO request/hold, direct eSoC ioctl, PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
