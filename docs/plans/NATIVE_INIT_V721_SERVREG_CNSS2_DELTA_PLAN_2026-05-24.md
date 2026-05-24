# Native Init V721 SERVREG/CNSS2 Delta Plan

- date: `2026-05-24 KST`
- scope: host-only Android-vs-native SERVREG/CNSS2 delta classifier
- runner: `scripts/revalidation/native_wifi_servreg_cnss2_delta_v721.py`

## Goal

Use existing evidence to decide whether the next native Wi-Fi blocker is still
QRTR service publication or a later SERVREG/WLAN-PD/CNSS2 callback edge.

V720 already proved that native can reproduce:

```text
qrtr-ns observable
  -> service-locator visible
    -> service-notifier 180/74 visible
```

V721 compares that same-window native evidence against the Android V622 lower
Wi-Fi timeline, where Android reaches WLAN-PD, QMI, BDF, firmware-ready, and
`wlan0`.

## Inputs

- Android reference:
  `tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/v622-android-mdm-helper-timing-recapture-run/manifest.json`
- Native same-window reference:
  `tmp/wifi/latest-v720-same-window-cnss2-observer.txt`

## Guardrails

V721 is host-only:

- no device command;
- no daemon or service-manager start;
- no Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- no scan/connect/link-up;
- no credential use;
- no DHCP, route change, or external ping;
- no sysfs/debugfs write;
- no `esoc0` open/hold;
- no boot image or partition write.

## Classification Checks

1. Confirm Android V622 and native V720 manifests are present and passing.
2. Confirm both sides have service `180/74`, so QRTR publication itself is not
   the current blocker.
3. Confirm native `qrtr-ns` is observable and postflight-safe.
4. Confirm Android continues into WLAN-PD/QMI/BDF/fw-ready/`wlan0`.
5. Confirm native has no `SERVICE_STATE_UP`/WLAN-PD/CNSS2/QCA/WLFW/BDF/`wlan0`
   progression in the same window.
6. Record whether native `cnss-daemon` starts but does not enter WLFW, so the
   next gate can separate daemon runtime continuation from kernel callback
   absence.

## Success Criteria

- `python3 -m py_compile` passes.
- `plan` and `run` produce manifests.
- final manifest proves no live device action or Wi-Fi bring-up occurred.
- final decision chooses one of:
  - `v721-servreg-wlanpd-cnss2-event-gap-classified`;
  - `v721-native-wlfw-or-wlan-ready`;
  - `v721-servreg-cnss2-delta-blocked`;
  - `v721-servreg-cnss2-delta-review`.

## Expected Next Gate

If V721 classifies the native gap after service `180/74`, V722 should remain
below Wi-Fi HAL and connection attempts. It should observe or instrument the
SERVREG/service-locator indication and CNSS2 callback boundary in a bounded
same-window run.
