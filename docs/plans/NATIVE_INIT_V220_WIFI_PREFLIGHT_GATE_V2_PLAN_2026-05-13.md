# v220 Plan: Wi-Fi Bring-Up Preflight Gate v2

## Summary

v220 follows v219 `shim-plan-partial`. The goal is to upgrade Wi-Fi bring-up
preflight from static inventory to a lifecycle-aware gate that consumes v216-v219
evidence and returns an explicit `go-scan-prep` or `no-go`.

This version is read-only and host-side by default. It must not execute
`cnss-daemon`, `cnss_diag`, Wi-Fi HAL, supplicant, hostapd, rfkill, link-up,
scan, or connect.

- baseline native runtime: `A90 Linux init 0.9.59 (v159)`
- previous result: v219 PASS, `shim-plan-partial`
- planned gate: `scripts/revalidation/wifi_bringup_gate_v2.py`
- evidence input:
  - v210 vendor asset classifier
  - v211/v212 firmware path policy and rollback
  - v216 service replay model
  - v217 ICNSS debug/recovery inventory
  - v218 CNSS daemon dry-run model
  - v219 native Android-env shim matrix
- evidence output: `tmp/wifi/v220-bringup-gate-v2`
- report after execution:
  `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`

## Gate Inputs

Required evidence:

- vendor Wi-Fi/CNSS assets visible
- firmware path policy and rollback evidence available
- service replay model ready
- ICNSS recovery/debug inventory available
- CNSS daemon dry-run model available
- native Android-env shim matrix available
- security/exposure policy remains USB-local and credential-safe

## Gate Checks

The gate should evaluate:

- `vendor_assets`
  - v210 decision is `asset-map-ready` or `firmware-path-policy-needed`
  - `cnss-daemon`, `cnss_diag`, firmware, init rc are visible
- `firmware_path`
  - v211/v212 policy and rollback evidence exist
  - temporary path flow is reversible
- `service_replay`
  - v216 decision is `replay-model-ready`
- `icnss_recovery`
  - v217 decision is `state-only-inventory` or better
  - dangerous controls remain denied
  - reboot-only recovery is explicitly acknowledged if no safe recovery exists
- `daemon_dryrun`
  - v218 decision is `daemon-dryrun-ready` or `daemon-dryrun-partial`
  - daemon execution remains blocked
- `shim_policy`
  - v219 decision is `shim-plan-ready` or `shim-plan-partial`
  - blocked shim items are represented in the final gate result
- `security_exposure`
  - no Wi-Fi credentials collected
  - no `/data/misc/wifi`
  - ACM/NCM rescue remains required
  - root control channels must not be exposed beyond intended USB-local policy

## Decision Model

- `go-scan-prep`
  - all required evidence is present
  - no high-risk blocker remains except explicitly accepted reboot-only recovery
  - security exposure policy is ready for scan-only planning
- `no-go`
  - one or more required gate checks are missing, blocked, or too risky
- `manual-review-required`
  - evidence conflicts or cannot be interpreted deterministically

Expected v220 outcome is likely `no-go` because v219 still has blocked
property/QMI/recovery items and v218 lacks host ELF/library evidence.

## Output Model

The gate should write:

- `manifest.json`
- `gate.json`
- `summary.md`

Each gate item should include:

- name
- status: `pass`, `warn`, `fail`, or `blocked`
- source version
- evidence
- reason
- required next action

## Validation

Static:

```sh
python3 -m py_compile scripts/revalidation/wifi_bringup_gate_v2.py
git diff --check
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_bringup_gate_v2
wifi_bringup_gate_v2.validate_no_active_commands()
print('v220 command guard PASS')
PY
```

Gate run:

```sh
python3 scripts/revalidation/wifi_bringup_gate_v2.py \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json \
  --v216-manifest tmp/wifi/v216-service-replay-model/manifest.json \
  --v217-native-manifest tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json \
  --v218-manifest tmp/wifi/v218-cnss-daemon-dryrun/manifest.json \
  --v219-manifest tmp/wifi/v219-native-android-env-shim/manifest.json \
  --out-dir tmp/wifi/v220-bringup-gate-v2
```

## Acceptance

- The gate executes no live device command by default.
- The gate result is deterministic from existing manifests.
- `go-scan-prep` is impossible while unresolved high-risk blockers remain.
- The summary clearly states exactly what must be fixed before v221 can plan a
  temporary-mutating CNSS experiment.

## Next Step

If v220 returns `go-scan-prep`, v221 can plan a controlled CNSS start
experiment. If v220 returns `no-go`, v221 must be replaced with the highest
priority missing prerequisite, likely host ELF/library evidence or recovery
policy hardening.
