# Native Init V676 V535 Property-seeded Android Userspace-order Live Report

## Summary

- direct runner: `scripts/revalidation/native_wifi_v535_property_android_order_v676.py`
- orchestrator: `scripts/revalidation/native_wifi_v535_property_android_order_orchestrator_v676.py`
- plan evidence: `tmp/wifi/v676-v535-property-android-order-orchestrated-plan/`
- live evidence: `tmp/wifi/v676-v535-property-android-order-orchestrated-live/`
- decision: `v676-property-gap-persists-classified`
- pass: `true`
- cleanup: pass
- Wi-Fi HAL/`wificond` start-only: executed
- supplicant/scan/connect/DHCP/external ping: not executed

V676 replayed the V671 Android userspace-order path using the V535 private
property root instead of the older V317 root. The V535 root covers all V675
property targets and seeds the runtime-required values identified in V675.

## Current-boot Prep

| Step | Result |
| --- | --- |
| V641 clean-DSP boot window | pass |
| `mountsystem ro` | pass |
| V401 SELinuxfs surface | pass |
| V490 policy-load proof | pass |
| firmware mount cleanup | pass |

The live arm used the fresh V490 manifest produced during the V676 prep.

## V675/V535 Coverage

| Check | Result |
| --- | --- |
| V675 target count | `24` |
| V535 seed coverage | pass |
| V535 mapping coverage | pass |
| runtime-required seeded | `ro.vendor.redirect_socket_calls`, `ro.debuggable`, `ro.vndk.version` |

The old V675 denials were reduced by the V535 property root. V675 had `16916`
property lookup failures across `24` unique keys. V676 still has property
failures, but the set is different and much smaller.

## Live Result

| Marker | Count |
| --- | ---: |
| service-notifier `180` | `1` |
| service-notifier `74` | `1` |
| Binder transaction failure | `1` |
| CNSS Binder transaction failure | `1` |
| kernel warning | `1` |
| QMI server connected | `0` |
| WLFW start | `0` |
| WLFW service request | `0` |
| BDF `regdb.bin` | `0` |
| BDF `bdwlan.bin` | `0` |
| WLAN firmware-ready | `0` |
| `wlan0` | `0` |

Android userspace-order children started, but WLFW/BDF/firmware-ready/`wlan0`
still did not advance.

## Remaining Property Surface

V676 remaining property denials:

| Metric | Value |
| --- | ---: |
| total | `370` |
| unique | `20` |
| Binder `-22` failures | `5` |

Top remaining denied keys:

| Property | Count |
| --- | ---: |
| `persist.log.tag.ServiceManager` | `132` |
| `log.tag.ServiceManager` | `132` |
| `debug.ld.app.vndservicemanager` | `20` |
| `debug.ld.app.android.hardware.wifi@1.0-service` | `20` |
| `debug.ld.app.wificond` | `20` |
| `persist.log.tag.wificond` | `6` |
| `log.tag.wificond` | `6` |
| `persist.log.tag.android.hardware.wifi@1.0-service` | `4` |
| `log.tag.android.hardware.wifi@1.0-service` | `4` |
| `persist.log.tag.PerMgrLib` | `4` |
| `log.tag.PerMgrLib` | `4` |
| `ro.boot.product.vendor.sku` | `2` |
| `ro.boot.product.hardware.sku` | `2` |
| `persist.log.tag.libvintf` | `2` |
| `log.tag.libvintf` | `2` |
| `arm64.memtag.process.vndservicemanager` | `2` |

## Interpretation

V676 proves that V535 materially improves the property surface but does not
fully close it:

```text
V535 private property root
  -> V675 target coverage pass
  -> old property denial set mostly removed
  -> new post-service-manager/HAL/wificond property denials remain
  -> Binder failures still visible
  -> WLFW/BDF/wlan0 still absent
```

The next shortest path is not supplicant, scan/connect, or credentials. The
next unit should extend the private property layout for the V676 remaining
denial set, especially service-manager, Wi-Fi HAL, `wificond`, SKU, libvintf,
and vndservicemanager debug/memtag keys. After that, rerun the same bounded
V676-style arm and only move to Binder repair if property denials drop to zero
or near-zero.

## Cleanup

The live arm performed reboot cleanup. Post-cleanup native control returned
with healthy status:

| Check | Result |
| --- | --- |
| version seen | pass |
| status healthy | pass |
| wait | `32.34s` |

## Validation

```sh
python3 -m py_compile \
  scripts/revalidation/native_wifi_v535_property_android_order_v676.py \
  scripts/revalidation/native_wifi_v535_property_android_order_orchestrator_v676.py

python3 scripts/revalidation/native_wifi_v535_property_android_order_orchestrator_v676.py \
  --out-dir tmp/wifi/v676-v535-property-android-order-orchestrated-plan \
  plan

python3 scripts/revalidation/native_wifi_v535_property_android_order_orchestrator_v676.py \
  --out-dir tmp/wifi/v676-v535-property-android-order-orchestrated-live \
  --apply \
  --assume-yes \
  run
```

All commands completed. The live proof produced
`v676-property-gap-persists-classified` and confirmed that scan/connect,
Wi-Fi bring-up, DHCP, and external ping were not executed.
