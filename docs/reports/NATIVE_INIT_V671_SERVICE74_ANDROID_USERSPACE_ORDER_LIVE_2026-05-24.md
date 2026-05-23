# Native Init V671 Service74 Android Userspace-order Live

- cycle: `v671`
- date: `2026-05-24`
- runner: `scripts/revalidation/native_wifi_service74_android_order_v671.py`
- helper: `a90_android_execns_probe v111`
- evidence: `tmp/wifi/v671-service74-android-userspace-live/`
- decision: `v671-service74-gate-timeout`
- pass: `true`

## Scope

V671 extends the V668 service `74` positive path with an Android-like
userspace order:

```text
qrtr-ns -> rmt_storage -> tftp_server -> pd-mapper -> cnss_diag ->
cnss-daemon -> service74 gate -> servicemanager/hwservicemanager/
vndservicemanager -> Wi-Fi HAL legacy/ext -> wificond -> fresh cnss-daemon
```

The run remained start-only. It did not start supplicant, perform scan/connect,
use credentials, run DHCP, change routes, or perform an external ping.

## Preconditions

| item | result |
| --- | --- |
| helper v111 deployment | pass |
| V401 SELinux filesystem surface | pass |
| V490 native policy-load proof | pass |
| V641 clean DSP state | pass |
| V671 preflight | pass |

The first V671 preflight was blocked because V641 had left
`/vendor/firmware_mnt` and `/vendor/firmware-modem` mounted. Those read-only
mounts were unmounted so the V596/V671 runner-owned firmware mount path could
perform its own bounded mount window.

## Live Result

| signal | result |
| --- | --- |
| modem holder | started |
| QRTR RX | observed |
| QRTR TX | observed |
| `sysmon-qmi` | observed |
| service-notifier `74` | not observed |
| service-notifier `180` | not observed |
| service `74` gate | timeout, `seen=0`, `open=0`, `wait_ms=12029` |
| Wi-Fi HAL legacy/ext child start | withheld by gate |
| `wificond` child start | withheld by gate |
| fresh `cnss-daemon` retry | withheld by gate |
| WLFW service `69` | no service events |
| BDF / firmware-ready / `wlan0` | not observed |
| kernel warning | not observed |
| reboot cleanup | healthy |

The V671 code now records start requests separately from actual child start.
For this live evidence, the authoritative child `start_order` fields are empty,
so Wi-Fi HAL and `wificond` were configured for the gated path but did not
actually start.

## Interpretation

V671 did not reach the intended Android userspace-order experiment because the
lower service `74` gate did not open. This makes the current blocker lower than
Wi-Fi HAL, `wificond`, supplicant, scan/connect, or external networking.

The relevant delta is now between:

- prior V668/V666 paths where service-notifier `180/74` could be observed; and
- this V671 run where QRTR RX/TX and `sysmon-qmi` appeared, but service-notifier
  `180/74` did not.

The likely next unit is a V672 regression classifier comparing V668-positive
and V671-timeout conditions: firmware mount ownership, V641 persistent mounts
versus runner-owned mounts, companion service timing, service-locator output,
and `pd-mapper`/`rmt_storage`/`tftp_server` stdout/stderr around the service
`74` publication window.

## Next Step

Plan V672 as a lower-surface service-notifier regression classifier before
another Wi-Fi HAL or `wificond` attempt. Keep Wi-Fi bring-up, credentials,
scan/connect, DHCP, and external ping blocked until service `74/180` publication
is reproducible again.
