# Native Init V1305 AP2MDM Transition Window Classifier

## Summary

- Cycle: `V1305`
- Type: host-only classifier
- Decision: `v1305-ap2mdm-low-through-extended-powerup-window`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1305-ap2mdm-transition-window-classifier/manifest.json`
  - `tmp/wifi/v1305-ap2mdm-transition-window-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_ap2mdm_transition_window_classifier_v1305.py`

V1305 extracts the actual V1303 response-sample timeline to determine whether the V1304 AP2MDM assertion/visibility gap could be explained by a too-short sampling window.

## Key Results

| field | value |
| --- | --- |
| V1303 powerup samples | `42` |
| first / last phase | `pre_late_per_proxy / post_late_per_proxy` |
| first / last monotonic ms | `1911643 / 1916656` |
| powerup window | `5013ms` |
| sample delta min / avg / max | `67ms / 122.268ms / 133ms` |
| GPIO135 values | `gpio135 : out 0 16mA no pull` |
| GPIO142 values | `gpio142 : in  0 8mA no pull` |
| GPIO135 high seen | `false` |
| GPIO142 high seen | `false` |
| MDM status count max | `0` |
| MHI bus count max | `0` |
| MHI pipe / ks / wlan0 | `false / false / false` |

## Reference Check

| reference | result |
| --- | --- |
| V1304 AP2MDM assertion/visibility gap | `true` |
| ext-sdx50m contract: 150ms then GPIO135 high | `true` |
| ext-sdx50m contract: 200ms after GPIO135 high | `true` |
| GPIO142 handled through async IRQ path | `true` |
| Android-positive PCIe/WLAN reference | `true` |
| prior PMIC pinctrl delta | `true` |

## Interpretation

The V1303 observation window covers about five seconds while `pm-service` remains blocked in `mdm_subsys_powerup`. GPIO135 remains low across that entire window, and no MDM2AP/PCIe/MHI/WLFW/`wlan0` progress appears.

That closes the simple “sampler missed a short GPIO pulse” explanation for V1304. The remaining gap is lower: the proprietary ext-mdm powerup branch either does not reach the visible AP2MDM assertion point, cannot drive it because a prerequisite is missing, or the required PMIC/pinctrl/GDSC state is not reproduced in native init.

## Next

V1306 should classify why visible AP2MDM assertion is absent:

1. PM8150L soft-reset pinctrl state mismatch,
2. PCIe GDSC/runtime power prerequisite mismatch,
3. branch-before-`mdm_do_first_power_on` inside proprietary `mdm_subsys_powerup`.

No blind lower eSoC/PM/CNSS retry should run before that classification.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_ap2mdm_transition_window_classifier_v1305.py
python3 scripts/revalidation/native_wifi_ap2mdm_transition_window_classifier_v1305.py run
```

Both passed.

## Safety

- Host-only classifier; no bridge/device command.
- No PMIC write, userspace GPIO request/hold, direct eSoC ioctl, PM/CNSS actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
