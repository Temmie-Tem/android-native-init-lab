# Native Init V749 Non-bind Trigger Selector Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_nonbind_trigger_selector_v749.py`
- plan evidence: `tmp/wifi/v749-nonbind-trigger-selector-plan/`
- preflight evidence: `tmp/wifi/v749-nonbind-trigger-selector-preflight/`
- run evidence: `tmp/wifi/v749-nonbind-trigger-selector/`
- decision: `v749-lower-window-boot-wlan-trigger-selected`
- status: `pass`

## Summary

V749 ran read-only current native captures and host-side evidence comparison.
It did not write `fs_ready`, `boot_wlan`, `qcwlanstate`, bind/unbind, driver
state, partitions, or boot images.

```text
current native: boot_wlan exists, qcwlanstate exists and is OFF
current native: fs_ready is not exposed
V508 standalone boot_wlan wrote successfully but did not produce wlan0/wiphy
V513 standalone qcwlanstate reached the driver but failed with errno 22
V748 selected non-bind trigger work
  -> next gate is boot_wlan inside the lower-ready window, not standalone
```

Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain
blocked because `wlan0` and wiphy are still absent.

## Checks

| check | result |
| --- | --- |
| V748 route input | pass |
| current WLAN control surface | pass; `boot_wlan` and `qcwlanstate` exist |
| current `fs_ready` surface | finding; absent |
| standalone `boot_wlan` retry | rejected by V508 |
| standalone `qcwlanstate` retry | rejected by V513 |
| module readiness gap | confirmed by V514 |
| connection gate | still blocked; no `wlan0`/wiphy |

## Current Surface

| item | value |
| --- | --- |
| `boot_wlan` | present |
| `qcwlanstate` | present, `OFF` |
| `fwpath` | empty |
| `/dev/wlan` | absent |
| `wlan0` | absent |
| `ieee80211` count | `0` |
| `fs_ready` | absent |
| `cnss2` platform driver path | absent |
| `icnss` platform driver path | present |

## Candidate Matrix

| candidate | disposition |
| --- | --- |
| `fs_ready` | Android-handoff-needed; source-backed but absent in current native sysfs |
| standalone `boot_wlan` | rejected |
| standalone `qcwlanstate` | rejected |
| lower-window `boot_wlan` | selected |
| HAL/scan/connect | rejected until `wlan0`/wiphy exists |

## Source References

- Qualcomm CNSS2 `fs_ready` sysfs source:
  <https://android.googlesource.com/kernel/msm/+/53f9955dd5876826f623fb9a1a736cfe36bec176/drivers/net/wireless/cnss2/main.c>
- QCACLD `qcwlanstate`/driver start source:
  <https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c>

## Interpretation

`fs_ready` is not the immediate native live target because this kernel currently
exposes `icnss`, not a visible `cnss2` driver path with `fs_ready`. It remains
worth checking during a future Android handoff, but it should not block the next
native gate.

The useful next experiment is not a repeat of V508 or V513. It must combine
the later lower-readiness work with the existing boot control:

```text
firmware-mounted lower window
  + subsys_modem holder
  + lower companion stack
  + bounded boot_wlan observe
  -> observe qcwlanstate, MHI/QCA6390, WLFW/BDF, wiphy/wlan0
```

## Next Gate

V750 should implement a bounded lower-window `boot_wlan` proof:

1. set up the same safe lower-ready window used by the recent modem/companion
   proofs;
2. run only fixed-target `a90_wlanbootctl boot-observe`;
3. capture `qcwlanstate`, `/dev/wlan`, MHI/QCA6390, WLFW service `69`, BDF,
   fw-ready, wiphy, and `wlan0`;
4. clean up with shutdown/reboot if needed;
5. keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and
   external ping blocked.
