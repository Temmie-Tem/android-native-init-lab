# Native Init V1350 — PM Register Supersession Classifier Plan

- Date: 2026-06-01
- Cycle: `V1350` (project axis; host-only)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: host-only corrective evidence classifier
- Status: PLAN

## Goal

V1349 selected the CNSS PM register/connect/vote path as the next prerequisite.
That was a useful local conclusion from V1100-V1102/V1171-V1172, but it did not
yet account for later evidence that already bypassed or superseded the old PM
register mutex branch.

V1350 should reconcile the full current chain and decide whether V1350 should
repeat PM register/mutex work or move to the next blocker.

## Inputs

| Evidence | Role |
| --- | --- |
| `docs/reports/NATIVE_INIT_V1103_PM_SERVER_NAME_HELPER_TRACEFS_2026-05-27.md` | proves the old CNSS register path blocked on the modem record mutex |
| `docs/reports/NATIVE_INIT_V1107_PM_SERVER_MUTEX_OWNER_CLASSIFIER_2026-05-27.md` | identifies the old owner as a pre-CNSS `per_proxy`/PM path blocked in `__subsystem_get` |
| `docs/reports/NATIVE_INIT_V1108_PM_ORDERING_NO_PRE_CNSS_PER_PROXY_2026-05-27.md` | proves skipping pre-CNSS `per_proxy` lets CNSS PM register/connect return `0x0` |
| `docs/reports/NATIVE_INIT_V1109_PM_CONNECT_SUBSYSTEM_GET_CLASSIFIER_2026-05-27.md` | proves successful CNSS PM connect moves the blocker downward into lower subsystem-get |
| `docs/reports/NATIVE_INIT_V1345_CURRENT_ROUTE_MDM2AP_TIMING_SAMPLER_LIVE_2026-06-01.md` | current private `SDX50M` route reaches `mdm_subsys_powerup` but no lower response |
| `docs/reports/NATIVE_INIT_V1347_ANDROID_EARLIEST_RESPONSE_RECAPTURE_LIVE_2026-06-01.md` | Android positive anchors: `wlfw_start`, ICNSS QMI, BDF, FW-ready, `wlan0` |
| `docs/reports/NATIVE_INIT_V1348_ANDROID_WLFW_REQUEST_PATH_CLASSIFIER_2026-06-01.md` | current branch selection: CNSS/WLFW runtime path before lower mutation |
| `docs/reports/NATIVE_INIT_V1349_CNSS_WLFW_RUNTIME_PREREQ_CLASSIFIER_2026-06-01.md` | prior local conclusion to verify or supersede |

## Classifier Contract

Add `scripts/revalidation/native_wifi_pm_register_supersession_classifier_v1350.py`.

The classifier must be host-only:

- read only the specific evidence files listed above;
- execute no device command;
- deploy no helper;
- start no daemon;
- write no tracefs/sysfs/debugfs/eSoC interface;
- perform no Wi-Fi HAL, scan/connect, credential, DHCP/route, or external ping action.

## Decision Labels

| Decision | Meaning | Next |
| --- | --- | --- |
| `v1350-pm-register-blocker-superseded-by-current-route` | old PM register mutex blocker is real but no longer the current next blocker because later routes reached PM connect/lower eSoC/powerup | plan current-route CNSS/WLFW precondition observer |
| `v1350-pm-register-blocker-still-current` | later supersession evidence is missing, so V1349 remains the next branch | define compact PM register helper/mutex observer |
| `v1350-evidence-incomplete` | required evidence is missing or inconsistent | refresh missing host-only evidence |
| `v1350-forbidden-action-detected` | evidence claims active Wi-Fi/network/credential behavior in this classifier | stop and audit |

## Expected Classification

The expected result is
`v1350-pm-register-blocker-superseded-by-current-route`.

Reasoning:

- V1103/V1107 prove the PM register mutex blocker existed.
- V1108 proves the pre-CNSS `per_proxy` ordering caused that blocker and that
  CNSS can register/connect successfully when that ordering is removed.
- V1109 proves successful CNSS PM connect moves the blocker to lower
  `__subsystem_get` / firmware wait.
- V1345 proves the current private `SDX50M` route reaches `mdm_subsys_powerup`
  and still sees no lower SDX50M response.
- V1347/V1348 keep the next branch on Android's `cnss-daemon` WLFW request path,
  not blind PMIC/GPIO/GDSC/eSoC mutation.

## Proposed Follow-up

If V1350 passes with the expected decision, V1351 should be source/build-only:

1. define a compact current-route CNSS/WLFW precondition observer;
2. capture native `cnss-daemon` progress before `wlfw_start` under the current
   provider-ready private `SDX50M` route;
3. compare against Android V1347 anchors without using credentials or attempting
   Wi-Fi scan/connect;
4. keep lower PMIC/GPIO/GDSC/eSoC mutation blocked unless a concrete missing
   Android prerequisite is identified.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_register_supersession_classifier_v1350.py
python3 scripts/revalidation/native_wifi_pm_register_supersession_classifier_v1350.py plan
python3 scripts/revalidation/native_wifi_pm_register_supersession_classifier_v1350.py run
git diff --check
```
