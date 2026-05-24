# Native Init V803 Provider-first HDD/PLD Prerequisite Classifier Report

## Result

- decision: `v803-hdd-pld-register-boundary-selected`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_provider_first_hdd_pld_prereq_classifier_v803.py`
- evidence: `tmp/wifi/v803-provider-first-hdd-pld-prereq-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_provider_first_hdd_pld_prereq_classifier_v803.py

python3 scripts/revalidation/native_wifi_provider_first_hdd_pld_prereq_classifier_v803.py \
  --out-dir tmp/wifi/v803-provider-first-hdd-pld-prereq-plan-check \
  plan

python3 scripts/revalidation/native_wifi_provider_first_hdd_pld_prereq_classifier_v803.py run
```

V803 was host-only. It did not execute any device command.

## Evidence Summary

| Signal | Result |
| --- | --- |
| V802 reference | pass |
| V802 provider-first context | executed |
| V802 `boot_wlan` write | executed |
| connection boundary | not crossed |
| `wlan: Loading driver` | `1` |
| HDD state major marker | `1` |
| `qcwlanstate` markers | `30` |
| `wlan: driver loaded` | `0` |
| ICNSS-QMI / FW-ready | `0 / 0` |
| WLFW / BDF / wiphy / `wlan0` | `0 / 0 / 0 / 0` |
| `/sys/class/wlan_dev` after boot | `478:0` |
| `qcwlanstate` after boot | `OFF` |

## Source Boundary

| Anchor | Line |
| --- | --- |
| `wlan: Loading driver` | `15937` |
| `hdd_init()` call | `15957` |
| `wlan_hdd_state_ctrl_param_create()` call | `15980` |
| `pld_init()` call | `15987` |
| `wlan_hdd_register_driver()` call | `16000` |
| `wlan: driver loaded` marker | `16007` |
| `wlan_hdd_register_driver()` -> `pld_register_driver()` | `1915` |
| `pld_snoc_register_driver()` -> `icnss_register_driver()` | `367` |
| ICNSS `Modules not initialized just return` qcwlanstate marker | `3763` |

## Classification

V803 narrows the V802 blocker to the source window before or inside PLD/ICNSS
registration/probe completion:

```text
hdd_driver_load()
  -> Loading driver
  -> hdd_init()
  -> qcwlanstate control surface exists
  -> pld_init()
  -> wlan_hdd_register_driver()
  -> pld_register_driver()
  -> icnss_register_driver()
  -> missing driver-loaded / ICNSS-QMI / WLFW / netdev
```

Because `/sys/class/wlan_dev` materializes but `qcwlanstate` remains `OFF`, the
early HDD control surface exists. The next useful blocker is not another
provider-first or `boot_wlan` replay. It is the PLD/ICNSS register/probe
prerequisite gap that prevents the driver-loaded marker and downstream WLFW
path.

## Safety

- Host-only classifier; no device command executed.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credential use,
  DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, module, partition, boot
  image, reboot, or custom kernel action.
- No Wi-Fi secret material was written to tracked output.

## Next

V804 should classify PLD/ICNSS register/probe prerequisites without custom
kernel flash. The useful target is to prove whether `icnss_register_driver()` is
waiting for an ICNSS platform ready/probe condition, an absent firmware/WLFW
condition, or a native-only runtime prerequisite that Android satisfies before
`boot_wlan`.
