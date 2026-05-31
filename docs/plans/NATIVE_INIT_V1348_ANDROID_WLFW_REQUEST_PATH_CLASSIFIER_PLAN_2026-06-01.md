# Native Init V1348 — Android WLFW Request Path Classifier Plan

- Date: 2026-06-01
- Cycle: `V1348` (project axis; host-only)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: host-only evidence classifier
- Status: PLAN

## Goal

V1347 recaptured Android and found the first public `cnss-daemon wlfw_start`
marker before the captured `__subsystem_get(esoc0)` marker:

```text
Android:
  wlfw_start=8.035751
  subsys_get_esoc0=8.251801
  icnss_qmi=9.353921
  BDF=9.517672
  FW-ready=14.464681
  wlan0=14.779047

Native V1345:
  private SDX50M route -> mdm_subsys_powerup
  no GPIO142 / PCIe / MHI / ks / WLFW / wlan0 transition
```

V1348 should classify what this means before any new live mutation.

## Inputs

| Evidence | Role |
| --- | --- |
| `docs/reports/NATIVE_INIT_V1345_CURRENT_ROUTE_MDM2AP_TIMING_SAMPLER_LIVE_2026-06-01.md` | current native private `SDX50M` route reaches `mdm_subsys_powerup` but no lower transition |
| `docs/reports/NATIVE_INIT_V1346_ANDROID_ONLY_RESPONSE_PREREQ_RECLASSIFIER_2026-06-01.md` | selected Android recapture because prior Android ordering was too coarse |
| `docs/reports/NATIVE_INIT_V1347_ANDROID_EARLIEST_RESPONSE_RECAPTURE_LIVE_2026-06-01.md` | Android `wlfw_start`/QMI/BDF/`wlan0` chain was recaptured on one monotonic timeline |

## Classifier Contract

Add `scripts/revalidation/native_wifi_android_wlfw_request_path_classifier_v1348.py`.

The classifier must be host-only:

- read existing manifests and reports only;
- execute no device command;
- deploy no helper;
- start no daemon;
- write no tracefs/sysfs/debugfs/eSoC interface;
- perform no Wi-Fi HAL, scan/connect, credential, DHCP/route, or external ping action.

## Decision Labels

| Decision | Meaning | Next |
| --- | --- | --- |
| `v1348-cnss-wlfw-request-path-before-lower-mutation` | Android-positive `wlfw_start` precedes captured eSoC marker and reaches QMI/BDF/`wlan0`, while native lower route still has no response | inspect CNSS/WLFW runtime prerequisites before lower mutation |
| `v1348-android-lower-order-captured-needs-native-parity` | Android lower PCIe/MHI/eSoC ordering was captured and points to a concrete native parity gap | design the narrowest native observer for that captured gap |
| `v1348-evidence-incomplete` | required V1345/V1346/V1347 evidence is missing or inconsistent | refresh missing host-only evidence |
| `v1348-forbidden-action-detected` | reconciled evidence reports active Wi-Fi/network/credential action outside scope | stop and audit |

## Expected Classification

The expected conservative result is
`v1348-cnss-wlfw-request-path-before-lower-mutation`.

Reasoning:

- V1345 proves the current native route can reach `mdm_subsys_powerup` without a
  lower SDX50M response.
- V1347 proves Android reaches `wlfw_start`, ICNSS QMI, BDF, firmware-ready, and
  `wlan0`.
- V1347 still does not expose public PCIe/MHI/`ks` markers, but it does show
  `wlfw_start` before the captured `subsys_get_esoc0` marker.

The next practical branch should therefore classify the Android-only
`cnss-daemon`/WLFW runtime prerequisites that let `wlfw_start` progress to
QMI/BDF, instead of adding PMIC/GPIO/GDSC/eSoC mutation.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_android_wlfw_request_path_classifier_v1348.py
python3 scripts/revalidation/native_wifi_android_wlfw_request_path_classifier_v1348.py plan
python3 scripts/revalidation/native_wifi_android_wlfw_request_path_classifier_v1348.py run
git diff --check
```

V1348 must not use stored Wi-Fi credentials or attempt connectivity.
