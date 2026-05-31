# Native Init V1342 — PM Actionability Gap Classifier Plan

- Date: 2026-06-01
- Cycle: `V1342` (project axis; no device flash implied)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: host/source-only classifier plan
- Status: PLAN

## Goal

V1341 restored the Android-order pre-CNSS provider-ready gate:

```text
V490 policy load
  -> servicemanager/hwservicemanager/vndservicemanager ready
  -> pm-service and pm-proxy run in vendor domains
  -> vendor.qcom.PeripheralManager provider appears
```

The lower transition still did not happen:

```text
provider-positive
  -> no /dev/subsys_esoc0 window
  -> no mdm_helper /dev/esoc-0 hold
  -> no ks/MHI
  -> no WLFW service 69
  -> no wlan0
```

V1342 should classify whether this is still a PM provider/actionability problem,
or whether V1341 simply lacks the SDX50M client-registration trigger already
proven by the V1221 private `cnss-daemon` path.

## Current Facts

| Fact | Evidence |
| --- | --- |
| Provider registration can be positive with V490 policy load and vndservice readiness | `docs/reports/NATIVE_INIT_V1092_PM_PROVIDER_READY_2026-05-27.md` |
| V1339 reproduced the Android-order actor chain but missed provider prerequisites | `docs/reports/NATIVE_INIT_V1339_ANDROID_PRE_CNSS_PROVIDER_OBSERVER_2026-05-31.md` |
| V1340 classified that gap as missing policy-load/vndservice gate | `docs/reports/NATIVE_INIT_V1340_PRE_CNSS_PROVIDER_RUNTIME_GAP_CLASSIFIER_2026-06-01.md` |
| V1341 repaired the current provider-ready gate | `docs/reports/NATIVE_INIT_V1341_ANDROID_PRE_CNSS_PROVIDER_POLICY_READY_2026-06-01.md` |
| V1341 still has `per_mgr_subsys_esoc0_window=0`, `mdm_helper_esoc0_window=0`, `ks_window=0`, and `mhi_cmdline_window=0` | `tmp/wifi/v1341-android-pre-cnss-provider-policy-ready-live/manifest.json` |
| V1221 private patched `cnss-daemon` selected real eSoC name `SDX50M`, registered CNSS PM clients, and moved `pm-service` to `__subsystem_get(): esoc0 count:0` | `docs/reports/NATIVE_INIT_V1221_PRIVATE_CNSS_DAEMON_SDX50M_LIVE_2026-05-31.md` |

## Classifier Design

Add `scripts/revalidation/native_wifi_pm_actionability_gap_classifier_v1342.py`.
The script should be host-only and produce:

- `tmp/wifi/v1342-pm-actionability-gap-classifier/manifest.json`
- `tmp/wifi/v1342-pm-actionability-gap-classifier/summary.md`
- `docs/reports/NATIVE_INIT_V1342_PM_ACTIONABILITY_GAP_CLASSIFIER_2026-06-01.md`

Required checks:

1. **V1341 provider gate positive** — confirm decision
   `v1341-provider-positive-no-lower-transition`, provider after `pm-service`
   and `pm-proxy` both true, and PM domains are
   `u:r:vendor_per_mgr:s0` / `u:r:vendor_per_proxy:s0`.
2. **V1341 lower transition absent** — confirm no automatic
   `/dev/subsys_esoc0`, `mdm_helper` `/dev/esoc-0`, `ks`, MHI, WLFW, or
   `wlan0` evidence.
3. **V1221 positive control present** — confirm private `cnss-daemon` SDX50M
   path produced CNSS PM client registration and `pm-service` eSoC open.
4. **No Wi-Fi HAL dependency introduced** — confirm both V1341 and V1221 kept
   scan/connect, credentials, DHCP/routes, and external ping blocked.
5. **Next-gate implication** — decide whether the next live unit should be a
   provider-positive + SDX50M-client lower observer, not another provider repair.

## Expected Decision Labels

| Decision | Meaning | Next |
| --- | --- | --- |
| `v1342-sdx50m-client-registration-is-required` | Provider registration is positive, but no lower request occurs without the CNSS SDX50M client trigger; V1221 proves SDX50M client registration moves PM to eSoC | Build a bounded V1343 gate that preserves V1341 provider prerequisites and adds only the already-proven SDX50M CNSS client route |
| `v1342-pm-provider-actionability-still-unproven` | Evidence cannot yet prove provider-positive state is actionable, or V1221 is not comparable enough | Add a narrower observer around PM Binder/client request handling before any lower retry |
| `v1342-evidence-incomplete` | Required manifests/reports are missing or inconsistent | Refresh host evidence before another live run |

## Safety Contract

V1342 is host/source-only:

- No device command.
- No helper deploy.
- No service-manager, PM actor, `mdm_helper`, CNSS, Wi-Fi HAL, or `wificond`
  start.
- No scan/connect, credentials, DHCP/routes, or external ping.
- No manual `/dev/subsys_esoc0` open.
- No eSoC ioctl, notify, BOOT_DONE spoof, PMIC/GPIO write, GDSC write, boot
  image write, flash, or partition write.
- No use or logging of Wi-Fi credentials.

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_actionability_gap_classifier_v1342.py
python3 scripts/revalidation/native_wifi_pm_actionability_gap_classifier_v1342.py plan
python3 scripts/revalidation/native_wifi_pm_actionability_gap_classifier_v1342.py run
git diff --check
run the local secret-scan pattern without hard-coding credentials into docs
```

No device health check is required because V1342 must not touch the device.

## Next After V1342

If V1342 returns `v1342-sdx50m-client-registration-is-required`, V1343 should be
a small source/build plan for a bounded live gate that combines:

1. current-boot V490 policy load;
2. V1341 vndservice/provider-positive readiness;
3. the V1221-proven SDX50M CNSS client registration route;
4. compact lower observation of `/dev/subsys_esoc0`, `mdm_helper` `/dev/esoc-0`,
   `ks`, MHI, WLFW service 69, BDF markers, and `wlan0`.

V1343 still must not start Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
external ping unless WLFW/BDF/`wlan0` readiness is first proven.
