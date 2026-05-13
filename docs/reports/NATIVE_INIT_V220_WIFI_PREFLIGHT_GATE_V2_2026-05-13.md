# v220 Wi-Fi Bring-Up Preflight Gate v2

## Summary

v220 adds a host-side lifecycle-aware Wi-Fi bring-up gate. It consumes existing
v210-v219 evidence and decides whether active Wi-Fi work can move toward scan
preparation.

Result: PASS.

Final decision: `no-go`.

Reason: gate has blocked prerequisites:

- `icnss_recovery`
- `shim_policy`
- `security_exposure`

This is the expected safe outcome. `no-go` is a successful gate result because
the gate is designed to stop active Wi-Fi work when unresolved blockers remain.

## Changes

- Added `scripts/revalidation/wifi_bringup_gate_v2.py`.
- Added version master plan:
  `docs/plans/NATIVE_INIT_V215_V225_WIFI_VERSION_MASTER_PLAN_2026-05-13.md`.
- Linked the master plan from:
  - `docs/plans/NATIVE_INIT_V215_V225_WIFI_LIFECYCLE_ROADMAP_2026-05-13.md`
  - `docs/plans/NATIVE_INIT_TASK_QUEUE_2026-04-25.md`
  - `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md`

## Scope

The gate is manifest-only and writes:

- `tmp/wifi/v220-bringup-gate-v2/manifest.json`
- `tmp/wifi/v220-bringup-gate-v2/gate.json`
- `tmp/wifi/v220-bringup-gate-v2/summary.md`

It does not run device commands and does not perform active Wi-Fi operations.

## Static Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_bringup_gate_v2.py
```

Result: PASS.

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import wifi_bringup_gate_v2
wifi_bringup_gate_v2.validate_no_active_commands()
print('v220 command guard PASS')
PY
```

Result:

```text
v220 command guard PASS
```

## Gate Run

Command:

```bash
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

Result:

```text
PASS out_dir=/home/temmie/dev/A90_5G_rooting/tmp/wifi/v220-bringup-gate-v2 decision=no-go reason=gate has blocked prerequisites: icnss_recovery, shim_policy, security_exposure
```

## Gate Summary

```text
pass=3
warn=1
fail=0
blocked=3
```

| Gate | Status | Source | Reason |
| --- | --- | --- | --- |
| `vendor_assets` | pass | v210 | vendor Wi-Fi/CNSS binaries and firmware are visible |
| `firmware_path` | pass | v211/v212 | temporary firmware path policy has rollback evidence |
| `service_replay` | pass | v216 | Android Wi-Fi/CNSS service chain is modeled |
| `icnss_recovery` | blocked | v217 | writable/recovery controls remain unsafe; reboot is only proven recovery |
| `daemon_dryrun` | warn | v218 | daemon visibility is mapped but ELF/library/recovery blockers remain |
| `shim_policy` | blocked | v219 | shim matrix still has blocked property/QMI/recovery/security areas |
| `security_exposure` | blocked | v219/v224-pending | pre-connect security and listener binding policy is not complete |

## Guardrails

- No live device commands.
- No daemon execution.
- No service start.
- No sysfs/debugfs writes.
- No rfkill write.
- No link-up.
- No scan/connect.

## Hashes

```text
50e0eac31958a455b5fbf614452fc72a32b64c334e0d11a968835e9f21239155  scripts/revalidation/wifi_bringup_gate_v2.py
4fdef0b7e9661a7c3084daffa6e0bd7a3555023a3fca822b7ffcaf31746f1dc5  docs/plans/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_PLAN_2026-05-13.md
07f5f41941ef25959a6ec672452af70275016629e93b008e6ce9e85c7079b562  docs/plans/NATIVE_INIT_V215_V225_WIFI_VERSION_MASTER_PLAN_2026-05-13.md
48e174c1402a42264bd1482819ee066533e66abd6afef51fcdaf65af3286b19b  tmp/wifi/v220-bringup-gate-v2/manifest.json
a51c372c07f346a1b08f51d8ce3fe12457c39e05570a89a874cf1ff7e5b2c88e  tmp/wifi/v220-bringup-gate-v2/gate.json
b6b8fd8f32bb2f1229dd688dcf330a6333dd8d5388845f460cc163280e81b09d  tmp/wifi/v220-bringup-gate-v2/summary.md
```

## Decision

Active Wi-Fi work remains blocked. v221 must not be a controlled CNSS start
experiment yet.

The next safe v221 candidate is host vendor ELF/library evidence closure for
`cnss-daemon` and `cnss_diag`, plus recovery/security prerequisite closure.

## Next

Plan v221 as prerequisite closure unless a new reviewed gate supersedes v220.
The current default v221 direction is:

- host vendor ELF/library evidence closure
- reboot-only recovery policy hardening
- security exposure prerequisites before any scan or connect work
