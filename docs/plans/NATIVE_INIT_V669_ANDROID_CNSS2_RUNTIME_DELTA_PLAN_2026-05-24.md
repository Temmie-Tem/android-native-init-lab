# Native Init V669 Android/native cnss2 Runtime Delta Plan

- date: `2026-05-24 KST`
- cycle: `V669`
- status: planned
- script: `scripts/revalidation/native_wifi_android_cnss2_runtime_delta_v669.py`

## Goal

V668 proved the native service `74` window can see the icnss/QCA6390 platform
devices, but still does not advance into WLFW, BDF, firmware-ready, or `wlan0`.
V669 compares that native evidence with existing Android evidence that does
advance to `wlan0`.

## Scope

V669 is host-only. It consumes:

- V668 native focused capture manifest, dmesg delta, and helper output;
- V649 Android audio/Wi-Fi dmesg recapture;
- V204 Android ICNSS sysfs baseline.

## Guardrails

V669 does not authorize:

- device commands or live mutation;
- sysfs writes;
- daemon, service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, credentials, DHCP, routes, or external ping;
- boot image or partition writes.

## Success Criteria

The classifier passes if it proves:

- Android evidence advances through WLFW, BDF, firmware-ready, and `wlan0`;
- Android ICNSS sysfs exposes `wlan0` and `phy0`;
- V668 native focused capture sees icnss/QCA6390 devices but no `wlan0`;
- V668 native remains before WLFW/BDF/firmware-ready/`wlan0`.

## Commands

```bash
python3 scripts/revalidation/native_wifi_android_cnss2_runtime_delta_v669.py \
  --out-dir tmp/wifi/v669-android-cnss2-runtime-delta-plan \
  plan

python3 scripts/revalidation/native_wifi_android_cnss2_runtime_delta_v669.py \
  --out-dir tmp/wifi/v669-android-cnss2-runtime-delta \
  run
```

## Next

If V669 classifies the gap, V670 should inspect Android init/service ordering
and trigger differences before changing any live Wi-Fi HAL or scan/connect
surface.
