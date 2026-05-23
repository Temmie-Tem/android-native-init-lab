# Native Init V667 cnss2/WLAN-PD Notifier Classifier Plan

- date: `2026-05-24 KST`
- cycle: `V667`
- status: planned
- script: `scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py`

## Goal

Classify the gap left by V666: service-notifier `180/74` appears, but WLFW
service `69`, BDF download, firmware-ready, and `wlan0` do not appear.

The specific question is whether service-notifier publication is followed by
cnss2/WLAN-PD kernel progression: `pd_notifier`, WLAN/QCA6390 power-on,
PCIe/MHI, WLFW, BDF, firmware-ready, or `wlan0` markers.

## Scope

V667 starts as a host-only classifier over the V666 live evidence. It may also
capture current device read-only sysfs/dmesg surface, but it does not perform
another daemon start by default.

Allowed:

- parse existing V666 `dmesg-delta.txt`;
- compare service-notifier `180/74` timing against cnss2/WLAN-PD progression
  markers;
- optionally read current `/sys/bus/msm_subsys/devices/`,
  `/sys/bus/platform/drivers/cnss2`, matching cnss platform devices, and a
  filtered current dmesg tail.

Forbidden:

- sysfs writes;
- `esoc0` open/hold;
- daemon or service-manager start;
- Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, credential use, DHCP, route changes, or external ping;
- boot image or partition writes.

## Success Criteria

The classifier passes if it can make one of these bounded decisions:

| decision | meaning |
| --- | --- |
| `v667-cnss2-pd-notifier-gap-classified` | V666 reached service-notifier `180/74`, but no cnss2/WLAN-PD power/WLFW progression marker followed |
| `v667-cnss2-progression-without-wlfw-classified` | cnss2/WLAN-PD progression exists, but WLFW/BDF/`wlan0` is still missing |
| `v667-wlfw-advanced-review-next-gate` | WLFW/BDF/firmware-ready/`wlan0` advanced enough to plan the next gate |

It fails if the V666 input does not prove both service-notifier `180` and `74`,
because then the classifier cannot answer the intended question.

## Commands

Plan:

```bash
python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py \
  --out-dir tmp/wifi/v667-cnss2-pd-notifier-plan \
  plan
```

Host-only classification:

```bash
python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py \
  --out-dir tmp/wifi/v667-cnss2-pd-notifier-classifier \
  run
```

Optional current read-only capture:

```bash
python3 scripts/revalidation/native_wifi_cnss2_pd_notifier_classifier_v667.py \
  --out-dir tmp/wifi/v667-cnss2-pd-notifier-current-readonly \
  --capture-current-readonly \
  run
```

## Next

If V667 classifies a cnss2/WLAN-PD progression gap, the next bounded live gate
should stop another binder-only retry and instead target cnss2 kernel
progression evidence before any Wi-Fi HAL, scan/connect, DHCP, or external
ping.
