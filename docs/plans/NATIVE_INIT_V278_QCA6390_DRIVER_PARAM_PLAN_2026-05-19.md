# Native Init v278 QCA6390 Driver / WLAN Parameter Plan

## Summary

- target: v278 QCA6390 driver-match and WLAN module parameter classifier
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- new tool: `scripts/revalidation/wifi_qca6390_driver_param_classifier.py`
- packet transmission: none
- daemon execution: none
- sysfs writes: none

v277 found that the QCA6390 platform node is present but has no `driver` symlink,
while `/sys/module/wlan` exists and no WLAN netdev/wiphy/rfkill surface is
visible. v278 reads the QCA6390 OF modalias/compatible state, platform driver
candidates, and selected safe WLAN module parameters to decide whether the gap is
“device match visible but driver unbound” or a broader runtime sequencing issue.

## References

- Qualcomm CNSS2 Android kernel source includes `qcom,cnss-qca6390` in its OF
  match table: https://android.googlesource.com/kernel/msm.git/+/28ec0fbdef41e99b01d87e5d4d267f72dddf1dec/drivers/net/wireless/cnss2/main.c
- Linux wireless documentation lists QCA6390 as an ath11k-supported device family,
  useful only as driver-family context, not as a native-init bring-up approval:
  https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath11k.html

## Scope

Read-only live captures:

- QCA6390 `uevent` and `modalias`
- QCA6390 `driver` symlink stat
- platform driver candidates under `/sys/bus/platform/drivers`
- selected `/sys/module/wlan/parameters/*` values:
  - `fwpath`, `con_mode`, `country_code`, `enable_11d`, `enable_dfs_chan_scan`
  - `con_mode_ftm`, `con_mode_epping`, `prealloc_disabled`, `timer_multiplier`
- `/sys/class/net`, `/sys/class/ieee80211`, rfkill names/types, process table,
  and `/proc/net/dev` post-state

## Decision Model

Expected likely decision:

```text
qca6390-match-visible-driver-unbound
```

This means:

- `qcom,cnss-qca6390` OF compatible/modalias is visible.
- QCA6390 platform node has no `driver` symlink in current native state.
- WLAN module parameters are readable enough to classify current mode/path.
- No WLAN netdev/wiphy/rfkill readiness surface is visible.

Alternative decisions:

- `qca6390-driver-bound-no-netdev`: driver link exists but no interface appears.
- `qca6390-wlan-readiness-visible`: read-only state unexpectedly exposes WLAN
  netdev/wiphy/rfkill.
- `qca6390-driver-param-incomplete`: required read-only evidence is missing.

## Guardrails

v278 must not:

- write to module parameters, sysfs, rfkill, firmware, ICNSS, debugfs, or configfs
- use ICNSS `bind`, `unbind`, `driver_override`, recovery, ramdump, or assert controls
- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP,
  or routing commands
- scan/connect/link-up Wi-Fi
- send QRTR nameservice packets or QMI payloads
- reboot or remount partitions

## Validation

Run:

```bash
python3 scripts/revalidation/wifi_qca6390_driver_param_classifier.py \
  --out-dir tmp/wifi/v278-qca6390-driver-param \
  run
```

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_qca6390_driver_param_classifier.py \
  scripts/revalidation/wifi_icnss_platform_surface_classifier.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

Postflight:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py status
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
python3 scripts/revalidation/a90ctl.py cat /proc/net/dev
```

## Acceptance

- v278 sends no packets, starts no daemon, and writes no sysfs/control paths.
- required v277 manifest is loaded and checked.
- QCA6390 OF compatible/modalias and driver-link state are classified.
- selected WLAN module parameter values are captured read-only.
- postflight remains clean: no `cnss-daemon`, no `wlan*` interface.
