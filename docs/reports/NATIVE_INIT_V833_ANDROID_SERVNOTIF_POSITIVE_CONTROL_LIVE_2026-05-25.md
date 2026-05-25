# Native Init V833 Android Service-notifier Positive-control Live Report

## Result

- handoff decision: `v833-handoff-pass`
- collector decision: `v833-android-servnotif-positive-control-state-other`
- corrected interpretation: `state-up`
- pass: `true`
- evidence: `tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136/`

## What Ran

```bash
python3 scripts/revalidation/android_servnotif_positive_control_handoff_v833.py \
  --out-dir tmp/wifi/v833-android-servnotif-handoff-live-20260525-125136 \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
```

The handoff booted stock Android, waited for boot-complete, ran the bounded
service-notifier helper, then restored native v724.

## Handoff Summary

| Step | Result |
| --- | --- |
| helper build | pass |
| native preflight | pass |
| recovery/TWRP transition | pass |
| stock Android boot flash/readback | pass |
| Android boot-complete | pass |
| V833 service-notifier collector | pass |
| native v724 rollback | pass |
| post-rollback native status | pass |

## Positive-control Evidence

| Signal | Value |
| --- | --- |
| endpoint | service-notifier `66/46081`, node `0`, port `2` |
| register response | seen, QMI result `0`, error `0` |
| raw current state | `0x1fffffff` |
| OSRC constant | `SERVREG_NOTIF_SERVICE_STATE_UP_V01 = 0x1FFFFFFF` |
| canonical state | `up` |
| indication | not needed; no indication observed in bounded window |
| Wi-Fi bring-up | not executed |

The live collector labeled `0x1fffffff` as `other` because the new small helper
used an incomplete local state-name table. OSRC source and the existing
`a90_android_execns_probe` table both define `0x1fffffff` as service state
`UP`. The helper was corrected after this live run so future output will label
the state as `up` directly.

## Interpretation

V833 proves the listener payload/model is valid. The same service-notifier
listener request that returns `uninit` in native returns `UP` on Android.

This closes the V832 ambiguity:

```text
Android:
  service-notifier listener msm/modem/wlan_pd -> UP

Native V830/V831:
  service-notifier listener msm/modem/wlan_pd -> UNINIT
```

Therefore native is genuinely missing a lower WLAN-PD state transition before
WLFW/service69, BDF, wiphy, and `wlan0`.

## Safety

- No Wi-Fi enable, scan, connect, link-up, credential use, DHCP, route change,
  or external ping executed.
- No Wi-Fi HAL, wificond, supplicant, hostapd, or service-manager start/stop was
  executed by V833.
- The only QMI payload was the bounded service-notifier listener request.
- Boot image writes were limited to stock Android handoff and native v724
  rollback.
- No custom OSRC diagnostic kernel was flashed.
- No Wi-Fi secret material was written to tracked output.

## Next

V834 should be a host-only Android/native state-up delta classifier. It should
compare:

- Android V833 `UP` response and Android service-notifier source constants;
- native V830/V831 `UNINIT` responses;
- existing mdm3/esoc/sysmon/companion evidence from V817–V819.

The goal is to select the next native lower-state trigger candidate without
repeating service-locator, listener timing, `boot_wlan`, `qcwlanstate`,
`mdm_helper`, HAL, scan/connect, DHCP, external ping, or custom-kernel flash.
