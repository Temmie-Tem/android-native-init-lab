# Native Init V1349 — CNSS/WLFW Runtime Prerequisite Classifier Plan

- Date: 2026-06-01
- Cycle: `V1349` (project axis; host-only)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: host-only evidence classifier
- Status: PLAN

## Goal

V1348 selected the `cnss-daemon` WLFW request path as the next branch. V1349
should reconcile that with the older PM/CNSS trace evidence and select the
smallest next actionable prerequisite before any new live mutation.

## Inputs

| Evidence | Role |
| --- | --- |
| `docs/reports/NATIVE_INIT_V924_CNSS_WLFW_PRECONDITION_GAP_2026-05-26.md` | native reaches `cld80211` netlink but not `wlfw_start`/BDF/`wlan0` |
| `docs/reports/NATIVE_INIT_V966_ANDROID_WLFW_START_ATTRIBUTION_2026-05-26.md` | Android `wlfw_start` is attributed to the service window and precedes captured eSoC open |
| `docs/reports/NATIVE_INIT_V1100_CNSS_PM_REGISTER_RETURN_TRACEFS_2026-05-27.md` | native CNSS PM register enters but does not return/connect |
| `docs/reports/NATIVE_INIT_V1101_PM_SERVER_REGISTER_PATH_TRACEFS_2026-05-27.md` | blocker is inside early `pm-service` register path |
| `docs/reports/NATIVE_INIT_V1102_PM_SERVER_EARLY_REGISTER_TRACEFS_2026-05-27.md` | blocker is the second/modem supported-peripheral helper/mutex path |
| `docs/reports/NATIVE_INIT_V1171_PM_RECEIVER_CALLBACK_LIVE_2026-05-27.md` | PM `state=2` callback reaches `cnss-daemon` |
| `docs/reports/NATIVE_INIT_V1172_CNSS_CALLBACK_BODY_LIVE_2026-05-27.md` | `cnss-daemon` PM callback is ack-only, not an eSoC action branch |
| `docs/reports/NATIVE_INIT_V1348_ANDROID_WLFW_REQUEST_PATH_CLASSIFIER_2026-06-01.md` | current branch selection: CNSS/WLFW runtime prerequisite before lower mutation |

## Classifier Contract

Add `scripts/revalidation/native_wifi_cnss_wlfw_runtime_prereq_classifier_v1349.py`.

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
| `v1349-cnss-pm-register-blocker-is-next-prereq` | Existing evidence converges on CNSS PM register/connect/vote as the missing prerequisite before WLFW progress | design a compact PM register/ack observer or repair gate |
| `v1349-cnss-runtime-namespace-still-primary` | Evidence still points mainly at namespace/property/linker surface rather than PM register semantics | inspect runtime namespace surfaces before tracefs/live work |
| `v1349-evidence-incomplete` | one or more required reports are missing or inconsistent | refresh missing host-only evidence |
| `v1349-forbidden-action-detected` | evidence claims active Wi-Fi/network/credential behavior in this classifier | stop and audit |

## Expected Classification

The expected result is `v1349-cnss-pm-register-blocker-is-next-prereq`.

Reasoning:

- V924/V966 show native `cnss-daemon` can reach netlink but not Android's
  `wlfw_start`.
- V1100-V1102 narrow the native CNSS gap to PM register semantics:
  `cnss-daemon` enters PM register for `peripheral="modem"` /
  `client="cnss-daemon"` but does not return, so it never calls PM connect/vote.
- V1171-V1172 close the PM callback receiver path as ack-only, not an eSoC
  action branch.
- V1348 says not to add lower PMIC/GPIO/GDSC/eSoC mutation until the CNSS/WLFW
  runtime prerequisite is classified.

## Proposed Follow-up

If V1349 passes with the expected decision, V1350 should be source/build-only
first:

1. define a compact PM register observer for the `pm-service` helper/mutex path
   around the V1102 `0x9538` boundary;
2. record owner/wchan/state around the second/modem supported-peripheral entry;
3. keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC,
   GPIO, GDSC, and direct eSoC mutation blocked;
4. only then consider a bounded live observer.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss_wlfw_runtime_prereq_classifier_v1349.py
python3 scripts/revalidation/native_wifi_cnss_wlfw_runtime_prereq_classifier_v1349.py plan
python3 scripts/revalidation/native_wifi_cnss_wlfw_runtime_prereq_classifier_v1349.py run
git diff --check
```
