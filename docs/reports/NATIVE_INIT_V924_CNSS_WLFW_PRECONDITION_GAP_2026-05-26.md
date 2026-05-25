# Native Init V924 CNSS/WLFW Precondition Gap Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| V924 host-only classifier | `tmp/wifi/v924-cnss-wlfw-precondition-gap/manifest.json` | `v924-cnss-wlfw-runtime-namespace-gap` |

V924 classifies the post-V923 blocker as a CNSS runtime namespace gap. Native
`cnss_diag` and `cnss-daemon` reach the kernel `cld80211` netlink surface, but
do not reach Android's `cnss-daemon wlfw_start`, BDF download, or `wlan0`
progression.

## Inputs

- V923 live manifest:
  `tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/manifest.json`
- V923 helper transcript:
  `tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/native/mdm-helper-cnss-before-esoc.txt`
- V923 post dmesg:
  `tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/native/post-dmesg-wifi-esoc-tail.txt`
- V914 Android timeline classifier:
  `tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json`
- V919 soft-reset blocker classifier:
  `tmp/wifi/v919-sdx50m-soft-reset-blocker-classifier/manifest.json`

## Classification

| Field | Value |
| --- | --- |
| native CNSS reaches `cld80211` netlink | `true` |
| native upper Wi-Fi markers absent | `true` |
| Android upper Wi-Fi positive control | `true` |
| native runtime namespace gap | `true` |
| service-manager/HAL not next | `true` |
| subsystem-open retry not next | `true` |

Native evidence:

| Marker | Value |
| --- | --- |
| V923 decision | `v923-wlfw-precondition-missing-no-open` |
| `cnss_diag_start_executed` | `true` |
| `cnss_daemon_start_executed` | `true` |
| `netlink_cld80211_count` | `12` |
| native `wlfw_start` count | `0` |
| native BDF count | `0` |
| native `wlan0` positive count | `0` |
| `/dev/subsys_esoc0` open attempted | `false` |

Android positive-control evidence remains:

| Marker | Time |
| --- | --- |
| `cnss-daemon wlfw_start` | `8.349631` |
| WLAN-PD indication | `9.414862` |
| `regdb.bin` BDF | `9.476146` |
| `bdwlan.bin` BDF | `9.487515` |
| `wlan0` event | `14.950217` |

## Namespace Signals

V923 stderr still contains runtime namespace symptoms:

| Signal | Count / Values |
| --- | --- |
| missing linkerconfig warning | `18` |
| `/dev/kmsg` write denied | `4` |
| shell quote error | `1` |
| missing property contexts | `arm64.memtag.process.mdm_helper`, `log.tag.mdm_helper`, `persist.log.tag.mdm_helper`, `persist.vendor.mdm_helper.fail_action`, `persist.vendor.mdm_helper.timeout`, `ro.vndk.lite` |
| property access denied | same six properties |

The `ro.vndk.lite` and linkerconfig warnings mean the private Android runtime
namespace still differs from the Android boot environment. The repeated
`mdm_helper` property-context failures mean the companion runtime is not yet
running with Android-equivalent property metadata.

## Guardrails

V924 is host-only:

- no device contact;
- no serial command;
- no ADB or Android boot;
- no actor start;
- no eSoC ioctl or `/dev/subsys_esoc0` open;
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping;
- no boot image, partition, firmware, GPIO, sysfs, debugfs, module, bind, or
  unbind mutation.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss_wlfw_precondition_gap_v924.py
python3 scripts/revalidation/native_wifi_cnss_wlfw_precondition_gap_v924.py
```

The manifest records all live-action guardrails as `false`.

## Interpretation

Repeating `/dev/subsys_esoc0` open is not the right next move. V923 already
proved the fail-closed CNSS-before-eSoC gate: without WLFW precondition, the
subsystem trigger remains closed.

The next useful unit is to repair or strictly prove the CNSS runtime namespace
before another live gate. That work should also reduce helper output volume so
future transcripts preserve final result keys without relying on derived
truncation classification.

## Next

V925 should be source/build-only:

1. add a low-volume CNSS/WLFW evidence mode or output throttle;
2. add explicit linkerconfig/APEX/VNDK/property-context surface reporting for
   `cnss-daemon` and `mdm_helper`;
3. keep service-manager, HAL, scan/connect, credentials, DHCP/routes, external
   ping, and `/dev/subsys_esoc0` open blocked;
4. only after that, run a bounded live V926 namespace-repaired CNSS precondition
   gate.
