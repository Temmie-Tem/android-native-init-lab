# Native Init V1346 — Android-only Response Prerequisite Reclassifier Plan

- Date: 2026-06-01
- Cycle: `V1346` (project axis; no boot image or partition write implied)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: host-only evidence reclassifier plan
- Status: PLAN

## Goal

V1345 proved that the current provider-ready private `SDX50M` route still reaches
`mdm_subsys_powerup` without any downstream SDX50M response:

```text
provider-ready private cnss-daemon.sdx50m route
  -> pm-service enters /dev/subsys_esoc0 / mdm_subsys_powerup
  -> timing window sees no GPIO142, errfatal IRQ, PCIe RC1, MHI/ks,
     WLFW/BDF, or wlan0
```

V1346 should not start another live gate yet. It should reconcile V1345 with
the older Android-positive and native-negative evidence and decide the next
safe branch.

## Inputs

| Evidence | Role |
| --- | --- |
| `docs/reports/NATIVE_INIT_V1345_CURRENT_ROUTE_MDM2AP_TIMING_SAMPLER_LIVE_2026-06-01.md` | current route reaches `mdm_subsys_powerup`, full lower-response window has no transition |
| `docs/reports/NATIVE_INIT_V1329_ANDROID_ONLY_SDX50M_PREREQ_CLASSIFIER_2026-05-31.md` | earlier conclusion that Android has a prerequisite before native's no-response window |
| `docs/reports/NATIVE_INIT_V1331_ANDROID_SDX50M_TIMING_HANDOFF_2026-05-31.md` | Android-positive monotonic timeline for `wlfw_start`, `__subsystem_get(esoc0)`, BDF, and `wlan0` |
| `docs/reports/NATIVE_INIT_V1332_WLFW_BEFORE_ESOC_CLASSIFIER_2026-05-31.md` | host-only classifier that native misses early WLFW/provider state |
| `docs/reports/NATIVE_INIT_V1335_EARLY_CNSS_WLFW_PARITY_OBSERVER_2026-05-31.md` | native observe-only early-CNSS still lacks WLFW precondition |
| `docs/reports/NATIVE_INIT_V1341_ANDROID_PRE_CNSS_PROVIDER_POLICY_READY_2026-06-01.md` | provider and policy prerequisites are repaired |
| `docs/reports/NATIVE_INIT_V1343_PROVIDER_READY_SDX50M_ROUTE_LIVE_2026-06-01.md` | current private `SDX50M` route reaches eSoC without WLFW/`wlan0` |

## Classifier Contract

Add `scripts/revalidation/native_wifi_android_only_response_prereq_reclassifier_v1346.py`.

The classifier must be host-only:

- read existing reports and manifests only;
- execute no device command;
- deploy no helper;
- start no daemon;
- write no tracefs/sysfs/debugfs/eSoC interface;
- perform no Wi-Fi HAL, scan/connect, credential, DHCP/route, or external ping action.

## Decision Labels

| Decision | Meaning | Next |
| --- | --- | --- |
| `v1346-need-android-earliest-response-recapture` | Android-positive ordering is still too coarse: V1331 lacks enough PCIe/MHI ordering detail on the same timeline as WLFW and `subsys_esoc0` | plan an Android read-only recapture with tighter markers before native mutation |
| `v1346-current-route-missing-android-only-prepower-prereq` | evidence is sufficient that native lacks an Android-only prerequisite before/around `mdm_subsys_powerup` | design the narrowest native read-only parity observer for that prerequisite |
| `v1346-current-route-ready-for-bounded-prereq-reproduction` | evidence identifies one concrete, bounded prerequisite that can be reproduced without PMIC/GPIO/eSoC writes | plan a separate live gate with explicit allow flags |
| `v1346-forbidden-action-detected` | reconciled evidence reports Wi-Fi/network/flash/lower mutation activity outside scope | stop and audit evidence |
| `v1346-evidence-incomplete` | required V1329/V1331/V1332/V1335/V1341/V1343/V1345 evidence is missing or inconsistent | refresh the missing host-only evidence |

## Expected Classification

The expected conservative result is `v1346-need-android-earliest-response-recapture`.

Reasoning:

- V1345 proves the current native route reaches `mdm_subsys_powerup` and still
  gets no GPIO142/PCIe/MHI/WLFW/`wlan0` transition.
- V1331 proves Android reaches `wlfw_start`, BDF, and `wlan0`, but that run did
  not capture PCIe RC1/L0 or MHI pipe dmesg markers on the same timeline.
- V1332/V1335/V1336 show an early provider/CNSS ordering gap, but V1341/V1343
  repaired the provider and `SDX50M` route enough to reach eSoC again.

That leaves an ordering ambiguity: Android's first real SDX50M response may
depend on a marker before the captured `subsys_esoc0` line, or the captured
`wlfw_start` marker may be a userspace-start marker that still needs PCIe/MHI
timing to interpret correctly.

## Proposed V1347 If V1346 Chooses Recapture

Android read-only handoff/recapture only:

1. boot known Android image and collect without Wi-Fi credentials or external ping;
2. capture `dmesg -T`/monotonic lines for `mdm_subsys_powerup`, AP2MDM/MDM2AP,
   GPIO142 IRQ, PCIe RC1/LTSSM, MHI, `ks`, `wlfw`, BDF, and `wlan0`;
3. capture `getprop ro.boottime.*` for PM/provider/CNSS/Wi-Fi services;
4. capture read-only process/fd snapshots for `pm-service`, `per_proxy`,
   `mdm_helper`, `ks`, `cnss_diag`, and `cnss-daemon`;
5. rollback to native and verify `version`/`selftest`.

## Validation

Before committing V1346:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_only_response_prereq_reclassifier_v1346.py
python3 scripts/revalidation/native_wifi_android_only_response_prereq_reclassifier_v1346.py
git diff --check
```

V1346 must not use the stored Wi-Fi SSID/password or attempt connectivity.
