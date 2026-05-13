# v225 Report: Wi-Fi Exposure / Credential Security Gate v3

## Summary

v225 implements a host-side read-only exposure/security gate v3 and runs it
against v220-v224 Wi-Fi prerequisite evidence.

- script: `scripts/revalidation/wifi_exposure_security_gate_v3.py`
- plan:
  `docs/plans/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_PLAN_2026-05-13.md`
- output: `tmp/wifi/v225-exposure-security-gate-v3`
- result: PASS
- decision: `still-no-go`
- reason: `gate has blocked prerequisites: vendor_evidence, shim_materialization`

This is the expected safe result. v225 documents and validates the exposure and
credential policy, but it does not close the missing source vendor root or
source-backed shim materialization blockers.

## What Was Implemented

`wifi_exposure_security_gate_v3.py` now:

- loads v220-v224 manifests;
- inventories reference security/exposure reports;
- builds a gate v3 status table;
- builds an ACM/NCM/tcpctl/rshell/broker/netservice/future-Wi-Fi exposure
  matrix;
- keeps vendor evidence and shim materialization as hard blockers;
- records credential collection as denied;
- emits private `manifest.json`, `gate-v3.json`, and `summary.md` outputs.

## Validation

Static validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_exposure_security_gate_v3.py
git diff --check
```

Command guard:

```text
v225 command guard PASS
```

Gate run:

```bash
python3 scripts/revalidation/wifi_exposure_security_gate_v3.py \
  --v220-manifest tmp/wifi/v220-bringup-gate-v2/manifest.json \
  --v221-manifest tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json \
  --v222-manifest tmp/wifi/v222-vendor-root-evidence-export/manifest.json \
  --v223-manifest tmp/wifi/v223-recovery-rollback-policy/manifest.json \
  --v224-manifest tmp/wifi/v224-android-env-shim-materialize/manifest.json \
  --out-dir tmp/wifi/v225-exposure-security-gate-v3
```

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v225-exposure-security-gate-v3 decision=still-no-go reason=gate has blocked prerequisites: vendor_evidence, shim_materialization
```

Manifest assertion:

```text
v225 manifest assertion PASS
blockers= vendor_evidence,shim_materialization
counts= {'blocked': 2, 'fail': 0, 'pass': 4, 'warn': 0}
```

Output file modes:

```text
0o700 tmp/wifi/v225-exposure-security-gate-v3
0o600 tmp/wifi/v225-exposure-security-gate-v3/manifest.json
0o600 tmp/wifi/v225-exposure-security-gate-v3/gate-v3.json
0o600 tmp/wifi/v225-exposure-security-gate-v3/summary.md
```

## Gate Items

| name | status | evidence |
| --- | --- | --- |
| vendor_evidence | blocked | v221=`vendor-root-required`, v222=`export-source-required` |
| recovery_policy | pass | v223=`reboot-recovery-accepted` |
| shim_materialization | blocked | v224=`shim-source-required` |
| root_control_exposure | pass | v134/v193/v196 reference reports present |
| credential_policy | pass | credential collection denied in v219/v224 path |
| active_wifi_operations | pass | v220=`no-go`, v225 remains read-only |

## Exposure Matrix

| surface | boundary | future Wi-Fi rule |
| --- | --- | --- |
| USB ACM serial bridge | trusted local USB operator path | must not be bridged to wireless client reachability |
| USB NCM tcpctl | USB-local control network | must not be routed from wireless client reachability |
| rshell | USB-local optional root-control path | must remain disabled or USB-local only |
| host broker | host-local control coordination | broker must not publish device root control to WLAN |
| netservice persistence | operator-controlled USB service flag | persistent flags must not widen to WLAN listeners |
| future wireless network | untrusted until proven isolated | active network work requires a later reviewed plan |

## Artifact Hashes

```text
50eff156c711447f0b5a2a0c119c195a6447072f5dac27996d789fe9fa959c2f  scripts/revalidation/wifi_exposure_security_gate_v3.py
e3b3696add90d3872a5c93dd37be3ea1a41334c9411ccd36d3b26e27a9a827b0  docs/plans/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_PLAN_2026-05-13.md
33275ee60335921d76778ec400e103a54fd4f570c5aeef99ac788f73d797580d  tmp/wifi/v225-exposure-security-gate-v3/manifest.json
25acbd35b8ab75d7a54ecb41983d7a3dc098128c0d392d8751132cf95769f697  tmp/wifi/v225-exposure-security-gate-v3/gate-v3.json
5fc8ea260d24aa44bce5140d058dcf3fc61ac3bb95051b13e9a75124cc2026e1  tmp/wifi/v225-exposure-security-gate-v3/summary.md
```

## Interpretation

v225 closes the security/exposure review gap as a documented gate, but the Wi-Fi
bring-up path remains blocked.

Still blocked:

- source vendor root evidence for v222/v221;
- source-backed shim materialization for v224;
- daemon execution;
- radio state transition;
- active scan/connect;
- credential handling;
- listener reachability broadening.

## Next

Do not proceed to active Wi-Fi. The next actionable path is:

1. provide a host-visible vendor root to v222;
2. rerun v222 and then v221 with the exported `vendor-root/`;
3. rerun v224 with source-backed shim materialization;
4. rerun v225 gate v3;
5. only then write a separate controlled CNSS start plan.
