# Native Init V753 HDD/PLD Prerequisite Classifier Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_hdd_pld_prereq_classifier_v753.py`
- plan evidence: `tmp/wifi/v753-hdd-pld-prereq-classifier-plan/`
- run evidence: `tmp/wifi/v753-hdd-pld-prereq-classifier/`
- decision: `v753-hdd-pld-register-driver-gap-needs-instrumentation`
- status: `pass`

## Summary

V753 consumed V752 and captured the current native surface read-only. It
confirmed that V752 is not an ordering issue with CNSS companions:

```text
V752 HDD entry:
  boot_wlan write executed ✓
  wlan: Loading driver ✓
  wlan_hdd_state wlan major(...) initialized ✓
  qcwlanstate present / OFF ✓

Missing:
  explicit hdd_init / PLD / driver-load failure marker ✗
  wlan: driver loaded ✗
  ICNSS-QMI connected ✗
  WLAN FW ready ✗
  WLFW/service 69/BDF ✗
  wiphy / wlan0 ✗
```

Current native after cleanup is healthy and contained: version/status/selftest
pass, `boot_wlan` and `/sys/module/wlan` surfaces exist, ICNSS parent exists,
but there is no ICNSS net/ieee80211 child, MHI device, `/dev/wlan`, wiphy, or
`wlan0`.

## Checks

| check | result |
| --- | --- |
| V752 input | pass; `v752-cnss-then-boot-wlan-hdd-init-still-stalls` |
| V752 safety envelope | pass; no service-manager/HAL/connect/credential/DHCP/external ping |
| HDD entry confirmed | pass; `boot_wlan=True`, `wlan_loading=1`, `hdd_state_major=1`, `qcwlanstate=30` |
| success markers absent | pass; driver-loaded/QMI/FW-ready/WLFW/BDF/netdev all `0` |
| explicit failure marker absent | pass; no `hdd_init failed`, driver-load failure, or PLD failure marker |
| current native still contained | pass; version/status/selftest healthy and no wiphy/`wlan0` |
| surface before netdev | pass; `boot_wlan`, `wlan` module, ICNSS parent present; net/ieee80211/MHI absent |
| Android reference complete path | pass; reference still has ICNSS-QMI, BDF, FW-ready, and `wlan0` |

## Key Signals

| signal | value |
| --- | --- |
| decision | `v753-hdd-pld-register-driver-gap-needs-instrumentation` |
| device commands | `true` |
| device mutations | `false` |
| service-manager started | `false` |
| Wi-Fi HAL started | `false` |
| scan/connect executed | `false` |
| credential use executed | `false` |
| DHCP/routes executed | `false` |
| external ping executed | `false` |
| V752 explicit HDD failure | `false` |
| V752 modules-uninitialized count | `30` |
| current recent HDD failure | `false` |
| current recent modules-uninitialized count | `1` |
| current debug ICNSS dir | `false` |

## Interpretation

The remaining blocker is not yet a concrete failure code. Source order shows
that `wlan_hdd_state` is created before `pld_init`, `hdd_init`, and
`wlan_hdd_register_driver`, while `wlan: driver loaded` is logged only after
register-driver success. V752 reached the first marker but none of the later
success or failure markers.

Therefore the next useful unit is not another `boot_wlan`, CNSS, or HAL retry.
V754 should add bounded, source-backed observability around the HDD/PLD/register
driver path, with enough signal to distinguish:

1. `pld_init` did not complete,
2. `hdd_init` blocked or failed without a visible marker,
3. `wlan_hdd_register_driver`/PLD driver registration blocked before ICNSS-QMI,
4. driver completion happened but the current marker set missed it.

## Safety Result

V753 was read-only. It executed no `boot_wlan`/`qcwlanstate` writes, no
bind/unbind, no module or subsystem writes, no service-manager, no Wi-Fi HAL, no
scan/connect, no credentials, no DHCP/routes, and no external ping.

## Next Gate

V754 should be an instrumentation design/implementation unit for
HDD/PLD/register-driver observability. If instrumentation requires a boot image
change, it should be separated behind the standard build/flash/rollback gate and
still avoid Wi-Fi scan/connect/credential/routing behavior.

## Evidence

- `tmp/wifi/v753-hdd-pld-prereq-classifier/manifest.json`
- `tmp/wifi/v753-hdd-pld-prereq-classifier/summary.md`
- `tmp/wifi/v753-hdd-pld-prereq-classifier/native/wlan-icnss-surface.txt`
- `tmp/wifi/v753-hdd-pld-prereq-classifier/native/dmesg-hdd-pld-focus.txt`

## Source References

- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9266>
- <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c>
