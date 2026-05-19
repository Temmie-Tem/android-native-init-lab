# v364 Plan: Wi-Fi HAL/Service-Manager Readiness Gate

- date: `2026-05-20`
- scope: no-scan/no-connect readiness gate before any Wi-Fi HAL/service-manager start-only attempt
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisites: V292 Binder open smoke, V320 private property lookup, V362 CNSS start-only, V363 Phase 0 baseline

## Summary

V364 is the next Wi-Fi bring-up gate after V363. It does not attempt Wi-Fi
scan/connect/link-up and does not start service-manager, Wi-Fi HAL, `wificond`,
supplicant, hostapd, `cnss-daemon`, or `cnss_diag`.

The goal is to decide whether a later bounded service/HAL start-only approval
packet is technically defensible. The gate combines older evidence with current
read-only live checks:

- V292: temporary Binder devnode/open primitive exists.
- V320: private Android property lookup proof passed.
- V362: bounded CNSS start-only passed and cleaned up.
- V363: current native Wi-Fi/CNSS baseline has no accidental link surface.
- V364: current Binder/property/service-manager/linkerconfig/VINTF visibility is checked.

## Guardrails

V364 explicitly forbids:

- service-manager execution;
- Wi-Fi HAL, `wificond`, supplicant, hostapd, `cnss-daemon`, or `cnss_diag` execution;
- Wi-Fi scan/connect/link-up/credential/DHCP/routing;
- rfkill unblock, ICNSS bind/unbind, module load/unload, or firmware mutation;
- Android partition writes.

Allowed live commands are limited to native `cmdv1` status/stat/ls/cat/run
read-only probes plus `mountsystem ro` for visibility.

## Implementation

Add host collector:

```text
scripts/revalidation/wifi_hal_service_readiness_gate.py
```

Modes:

```bash
python3 scripts/revalidation/wifi_hal_service_readiness_gate.py \
  --out-dir tmp/wifi/v364-hal-service-readiness-gate-plan-20260520 \
  plan

python3 scripts/revalidation/wifi_hal_service_readiness_gate.py \
  --out-dir tmp/wifi/v364-hal-service-readiness-gate-live-20260520 \
  run
```

The script writes private evidence under the selected output directory:

```text
manifest.json
checks.json
summary.md
native/*.txt
```

## Checks

The gate checks the following blocker classes:

- missing V292/V320/V362/V363 prerequisite manifests;
- leftover `cnss-daemon`/`cnss_diag` process;
- absent current Binder devnodes: `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder`;
- absent service-manager processes;
- absent current property runtime: `/dev/socket/property_service` or `/dev/__properties__`;
- absent service-manager/HAL binary visibility;
- missing linkerconfig visibility;
- missing Wi-Fi VINTF metadata.

Warnings are allowed when they provide useful but incomplete readiness evidence,
for example partial binary visibility or present VINTF metadata without a running
service runtime.

## Acceptance

- script compiles with `python3 -m py_compile`;
- plan mode returns `hal-service-readiness-gate-plan-ready`;
- live mode writes private evidence and returns one of:
  - `hal-service-readiness-blocked`, or
  - `hal-service-start-only-candidate-ready`;
- live mode does not create `wlan*`, Wi-Fi rfkill, or CNSS process leaks;
- if blocked, the blocker list is specific enough to define the next smallest
  runtime primitive.

## Next

If V364 is blocked, do not run Wi-Fi HAL/service-manager. Plan the smallest
missing primitive first. Expected candidates are:

1. temporary Binder devnode namespace recreation for the start-only sandbox;
2. private property runtime/service-manager prerequisite model;
3. linkerconfig/private namespace visibility fix;
4. only after those are satisfied, a separate bounded service-manager/HAL
   start-only approval packet.
