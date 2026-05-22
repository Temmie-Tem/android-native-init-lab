# Native Init V649 Android Full Audio/Wi-Fi Recapture Live Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- handoff evidence:
  `tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/`
- replay classifier evidence: `tmp/wifi/v649-live-replay-classifier/`
- corrected decision: `v649-android-audio-pm-qos-warning-reference-captured`

## Scope

V649 temporarily booted Android, captured read-only audio/ASoC + lower Wi-Fi
dmesg evidence, and restored native v641. It did not enable Wi-Fi,
scan/connect, use credentials, run DHCP, change routes, start Wi-Fi HALs from
native, start native daemons, write sysfs, or ping externally.

Native rollback completed and current native state returned to:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok, NCM absent, tcpctl stopped, rshell stopped
```

## Result

The initial live handoff manifest reported `v649-lower-wifi-evidence-gap`
because the first collector parsed manifest-truncated text instead of the full
captured command files. The corrected replay classifier reprocessed the full
evidence files and produced:

```text
decision: v649-android-audio-pm-qos-warning-reference-captured
pass: True
reason: replayed Android evidence contains service/audio context and duplicate pm_qos warning; the warning is not native-only
next: plan V650 Android/V644 warning timing comparison; do not retry V644 or start HAL/scan/connect
```

## Android Timeline

| marker | count | first_ts |
| --- | ---: | ---: |
| service `180` | `1` | `7.063652` |
| service `74` | `1` | `7.062886` |
| ASoC probe | `6` | `7.071196` |
| duplicate `pm_qos` | `5` | `7.071837` |
| QoS warning | `5` | `7.071853` |
| WLFW start | `1` | `8.354789` |
| WLAN-PD | `2` | `9.423396` |
| QMI server connected | `1` | `9.425819` |
| BDF `regdb.bin` | `1` | `9.487968` |
| BDF `bdwlan.bin` | `1` | `9.502708` |
| WLAN FW ready | `2` | `14.609320` |
| `wlan0` | `6` | `14.774208` |

## Timing

| delta | ms |
| --- | ---: |
| service `74` → ASoC probe | `8.310` |
| ASoC probe → duplicate `pm_qos` | `0.641` |
| duplicate `pm_qos` → QoS warning | `0.016` |
| service `74` → WLFW start | `1291.903` |
| service `74` → WLAN-PD | `2360.510` |
| service `74` → QMI server connected | `2362.933` |

## Interpretation

V649 changes the blocker model. The `pm_qos_add_request` warning is not
native-only: Android also emits the same warning class shortly after service
`74`, yet continues to WLFW, WLAN-PD, BDF, firmware-ready, and `wlan0`.

Therefore V644's failure should no longer be treated as "any QoS warning means
stop forever." The more precise gap is:

```text
Android: service 74 -> ASoC pm_qos warning -> WLFW/WLAN-PD/QMI/BDF/wlan0
Native:  service 74 -> ASoC pm_qos warning -> no WLFW/WLAN-PD/QMI/BDF/wlan0
```

The next decision must compare the post-warning continuation path rather than
only warning presence.

## Next Gate

Proceed to V650 host-only Android/V644 warning timing comparison:

1. compare Android V649 and native V644 from service `74` through ASoC warning;
2. compare post-warning continuation to WLFW/WLAN-PD/QMI/BDF/wlan0;
3. identify the first native post-warning marker that is missing;
4. keep V644 retry, Wi-Fi HAL, `qcwlanstate`, scan/connect, credentials, DHCP,
   route changes, and external ping blocked until the continuation gap is
   classified.
