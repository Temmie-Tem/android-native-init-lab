# Native Init V722 CNSS Launch-window Plan

- date: `2026-05-24 KST`
- scope: host-only CNSS launch timing and failure tradeoff classifier
- runner: `scripts/revalidation/native_wifi_cnss_launch_window_v722.py`

## Goal

Classify whether the next native Wi-Fi gate should repeat early `cnss-daemon`,
repeat provider-first delayed `cnss-daemon`, or create a new placement that
preserves provider readiness while starting CNSS earlier.

V721 proved that QRTR service `180/74`, `qrtr-ns`, and service-locator are not
the current blockers. V722 checks why native still stops before WLFW:

```text
early CNSS native paths
  -> binder transaction failure
provider-first native path
  -> no binder transaction failure
  -> cnss-daemon starts too late relative to Android WLFW timing
```

## Inputs

- Android timing reference:
  `tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/v622-android-mdm-helper-timing-recapture-run/manifest.json`
- early native CNSS evidence:
  `tmp/wifi/v659-vndservicemanager-readiness-only-live/manifest.json`
- ready retry evidence:
  `tmp/wifi/v660-ready-cnss-retry-live/manifest.json`
- provider-first native evidence:
  `tmp/wifi/latest-v720-same-window-cnss2-observer.txt`

## Guardrails

V722 is host-only:

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

1. Confirm all input evidence exists and passes.
2. Use Android V622 as a timing reference for service `180/74`,
   `cnss_diag`, `cnss-daemon`, WLFW start, and WLAN-PD.
3. Confirm V659/V660 early native CNSS paths start CNSS but hit the known
   binder transaction failure and do not reach WLFW.
4. Confirm V720 provider-first path has service `180/74` and `cnss_diag`, does
   not hit the binder transaction failure, but starts `cnss-daemon` after the
   Android reference would already have started WLFW.
5. Mark service `74` and `cnss_diag` as non-blockers when present in the
   provider-first evidence.

## Success Criteria

- `python3 -m py_compile` passes.
- `plan` and `run` produce manifests.
- final manifest proves no live device action or Wi-Fi bring-up occurred.
- final decision chooses one of:
  - `v722-cnss-launch-window-tradeoff-classified`;
  - `v722-cnss-launch-window-blocked`;
  - `v722-cnss-launch-window-review`.

## Expected Next Gate

If V722 classifies the launch-window tradeoff, V723 should introduce a bounded
provider-preserving earlier CNSS retry placement below Wi-Fi HAL/connect. The
target is not scan/connect yet; the target is first WLFW/QMI/BDF/fw-ready or
safe `wlan0` evidence.
