# Native Init v278 QCA6390 Driver / WLAN Parameter Report

## Summary

- status: PASS
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_qca6390_driver_param_classifier.py`
- evidence: `tmp/wifi/v278-qca6390-driver-param/`
- decision: `qca6390-match-visible-driver-unbound`
- packet transmission: none
- daemon execution: none
- sysfs writes: none

v278 classified the QCA6390 platform node and selected WLAN module parameters.
The QCA6390 OF compatible/modalias is visible, but the platform node has no
`driver` symlink and no WLAN readiness surface appears.

## Live Findings

| field | result |
| --- | --- |
| QCA6390 OF compatible | `qcom,cnss-qca6390` |
| QCA6390 modalias | `of:Nqcom,cnss-qca6390TCqcom,cnss-qca6390` |
| QCA6390 driver link | absent |
| platform driver candidates | `3` |
| WLAN module parameters read | `9/9` |
| `wlan*` netdev | absent |
| wiphy | absent |
| Wi-Fi rfkill | absent |
| CNSS process table | clean |

Platform driver candidates observed:

- `/sys/bus/platform/drivers/ipa/soc:ipa_smmu_wlan`
- `/sys/bus/platform/drivers/icnss`
- `/sys/bus/platform/drivers/icnss/18800000.qcom,icnss`

## WLAN Module Parameters

| parameter | value |
| --- | --- |
| `con_mode` | `0` |
| `con_mode_epping` | `0` |
| `con_mode_ftm` | `0` |
| `country_code` | `(null)` |
| `enable_11d` | `-1` |
| `enable_dfs_chan_scan` | `-1` |
| `fwpath` | empty |
| `prealloc_disabled` | `1` |
| `timer_multiplier` | `1` |

## Checks

All critical checks passed:

- expected native init version
- required live captures
- v277 prerequisite decision `icnss-platform-present-no-wlan-netdev`
- QCA6390 compatible/modalias visible
- WLAN module parameters readable
- CNSS process table clean
- no `wlan*`, wiphy, or Wi-Fi rfkill readiness surface

## Interpretation

- This is now narrower than “Wi-Fi platform exists but no interface”: the
  concrete QCA6390 OF match is visible, yet the QCA6390 node is not bound to a
  driver in current native state.
- The visible platform driver candidates only show ICNSS and IPA WLAN SMMU; no
  separate QCA6390-bound platform driver link appears.
- WLAN module parameters are readable, but `fwpath` is empty and `country_code`
  is `(null)`. This does not prove a cause, but it provides a stable baseline for
  any later start-only observation.
- QMI payloads and Wi-Fi link actions remain blocked. The next useful step is a
  start-only observation plan that watches QCA6390 driver-link/module parameter
  deltas, or a no-start source/evidence comparison of CNSS probe expectations.

## Guardrails Preserved

- no module/sysfs/control writes
- no ICNSS `bind`, `unbind`, `driver_override`, recovery, ramdump, or assert controls
- no QRTR nameservice packet transmission
- no QMI request payload
- no `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd start
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no reboot or remount

## Postflight

- `version`: `A90 Linux init 0.9.60 (v261)`
- `status`: shell responsive, `selftest fail=0`, `netservice: disabled tcpctl=stopped`
- `pidof cnss-daemon`: rc `1`, process absent
- `/proc/net/dev`: `ncm0` present; no `wlan*` interface observed

## Next Step

v279 should decide between two safe paths:

1. No-start source/evidence comparison for CNSS/QCA6390 probe expectations.
2. Explicit-approval bounded CNSS start-only observation that watches only
   QCA6390 driver-link, WLAN module parameters, QRTR nameservice visibility, and
   postflight cleanliness without scan/connect/link-up.
