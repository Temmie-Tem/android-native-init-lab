# Native Init V1324 — Provider Response Delta Classifier Plan

- Date: 2026-05-31
- Cycle: `V1324` (project axis; no device flash implied)
- Native build: `A90 Linux init 0.9.68 (v724)` (unchanged)
- Type: host/source-only classifier plan
- Status: PLAN

## Goal

V1324 should classify the Android-vs-native delta inside the proprietary
ext-mdm provider response window identified by V1323:

```text
pm-service -> /dev/subsys_esoc0 -> mdm_subsys_powerup
  -> sdx50m_toggle_soft_reset / mdm4x_do_first_power_on
  -> GPIO1270 soft-reset + GPIO135/AP2MDM activity
  -> [native gap]
  -> GPIO142/MDM2AP IRQ + PCIe RC1 + MHI/ks + WLFW/BDF + wlan0
```

The classifier must decide what existing evidence already proves about the gap
between GPIO135/AP2MDM activity and the first Android-only downstream response.
It must not run a new live trigger.

## Current Facts

| Fact | Evidence |
| --- | --- |
| Public `wait_for_err_ready()` is not the current blocker | `docs/reports/NATIVE_INIT_V1323_PROVIDER_WAIT_CAUSE_CLASSIFIER_2026-05-31.md` |
| Native reaches proprietary ext-mdm power-up path | V849/V918/V963 reports and V1323 classifier |
| Native lower trace reaches PMIC soft-reset GPIO1270 and GPIO135/AP2MDM high | `tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json` |
| Native does not receive GPIO142/MDM2AP, PCIe RC1, MHI, WLFW, or `wlan0` | V1318/V1319/V1239/V1323 evidence |
| Android-positive reference receives GPIO142 IRQ, PCIe RC1, MHI/ks, WLFW/BDF, and `wlan0` | V852/V896/V1239 references |
| AP2MDM_ERRFATAL GPIO141 is touched in native trace, while MDM errfatal GPIO53 IRQ remains count 0 | V1318 trace/interrupt evidence |

## Inputs

V1324 should read only existing files:

- `tmp/wifi/v1323-provider-wait-cause-classifier/manifest.json`
- `tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json`
- `tmp/wifi/v1319-gpio135-response-gap-classifier/manifest.json`
- `tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json`
- `tmp/wifi/v1240-sdx50m-response-surface-live/manifest.json`
- `tmp/wifi/v1291-static-gpio-parity-classifier/manifest.json`
- `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/manifest.json`
- `tmp/wifi/v896-android-mdm-helper-image-contract-validate/manifest.json`
- `docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md`
- `docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md`
- Samsung OSRC DTS/source files already staged under `kernel_build/`.

## Classifier Design

Add `scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py`.
The script should be host-only and produce:

- `tmp/wifi/v1324-provider-response-delta-classifier/manifest.json`
- `tmp/wifi/v1324-provider-response-delta-classifier/summary.md`
- `docs/reports/NATIVE_INIT_V1324_PROVIDER_RESPONSE_DELTA_CLASSIFIER_2026-05-31.md`

Required checks:

1. **V1323 branch ready** — V1323 PASS and decision is
   `v1323-provider-wait-cause-is-proprietary-powerup-response`.
2. **Native trigger reaches AP side** — V1318 has GPIO1270 soft-reset lines,
   GPIO135 high count >= 1, and post-GPIO135 sample span >= 10s.
3. **Native MDM side silent** — GPIO142 lines/count remain 0; PCIe RC1, MHI,
   MHI pipe, WLFW/BDF, and `wlan0` are absent.
4. **Android downstream response present** — Android reference has GPIO142 IRQ,
   PCIe RC1/L0, MHI/ks pipe, WLFW/BDF, and `wlan0`.
5. **Errfatal branch classified** — AP2MDM_ERRFATAL/GPIO141 and
   MDM2AP_ERRFATAL/GPIO53 evidence is present enough to decide whether it is a
   likely cause, a non-causal side signal, or an evidence gap.
6. **Static shape not primary** — V1291/V1322 static GPIO parity evidence remains
   compatible with the conclusion that the gap is dynamic provider response.
7. **Guardrails clear** — no Wi-Fi HAL/connect/credential/network/flash/PMIC
   write/GPIO request/direct eSoC/GDSC mutation in V1324.

## Expected Decision Labels

Use one of these explicit labels:

| Decision | Meaning | Next |
| --- | --- | --- |
| `v1324-delta-is-post-ap2mdm-mdm2ap-response-gap` | Existing evidence proves AP-side soft-reset/AP2MDM fires, but MDM2AP/PCIe response is absent | Design a bounded read-only live sampler focused on GPIO142/errfatal/PCIe timing |
| `v1324-delta-needs-android-provider-timing-recapture` | Existing Android evidence is insufficient for exact timing | Android read-only positive-control recapture; no native mutation |
| `v1324-delta-needs-native-focused-sampler` | Existing native evidence is insufficient around a specific line/surface | Bounded read-only or reboot-bounded native sampler; no writes |
| `v1324-evidence-incomplete` | Required inputs missing or inconsistent | Refresh missing host evidence before live work |

## Safety Contract

V1324 is host/source-only:

- No device command.
- No helper deploy.
- No PM actor, `mdm_helper`, service-manager, CNSS, Wi-Fi HAL, scan/connect, or
  credential use.
- No DHCP/routes or external ping.
- No tracefs write.
- No eSoC ioctl/notify/BOOT_DONE.
- No PMIC write, GPIO line request/hold, GDSC write, boot image write, flash, or
  partition write.

## Validation

Run:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py
python3 scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py plan
python3 scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py run
git diff --check
run the local secret-scan pattern without hard-coding credentials into docs
```

Device health check is optional because V1324 must not touch the device. If a
bridge is already available, `selftest`/`netservice status` may be recorded as a
postflight sanity check, but it is not part of the classifier contract.

## Next After V1324

If V1324 classifies the gap as post-AP2MDM MDM2AP response, V1325 should be a
small source/build plan for a bounded observer or host-only Android recapture,
not a mutation. The next live gate, if needed, must be read-only or explicitly
reboot-bounded and must keep Wi-Fi HAL/connect blocked.
