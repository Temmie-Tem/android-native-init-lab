# WSTA166 Seccomp Live-Observation Runner Source Pass

Date: 2026-07-05 13:38 KST

## Verdict

WSTA166 consumes the WSTA165 no-load observation plan and emits the remote
shell script shape a later live unit can run inside Debian.  This is a
host-only source proof: it does not contact the device and does not execute the
remote script.  The generated script covers only the three WSTA165 no-load
scenarios and does not contain the correct WSTA161 load token.

This unit did not touch the device, flash, reboot, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, load BPF, load a
seccomp filter, enforce seccomp, chroot, switch root, or run the generated
remote script.

Result: PASS.  The generated script includes the WSTA163 helper apply gate,
the WSTA164 load-env gate, and the deliberately wrong token placeholder, but
does not include `WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD`.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta166_seccomp_live_observation_runner_source.py`.
- Added focused tests in
  `tests/test_server_distro_wsta166_seccomp_live_observation_runner_source.py`.

## Generated Proof

Proof run:

```text
workspace/private/runs/server-distro/wsta166-seccomp-live-observation-runner-source-20260705T1344KST/
```

Input:

```text
workspace/private/runs/server-distro/wsta165-seccomp-live-observation-plan-20260705T1335KST/wsta165_live_observation_plan.json
```

Decision:

```text
wsta166-seccomp-live-observation-runner-source-pass
```

Generated remote script:

```text
workspace/private/runs/server-distro/wsta166-seccomp-live-observation-runner-source-20260705T1344KST/wsta166_remote_seccomp_observation.sh
```

Contract artifact:

```text
workspace/private/runs/server-distro/wsta166-seccomp-live-observation-runner-source-20260705T1344KST/wsta166_live_runner_contract.json
```

Remote script shape:

```text
run_scenario no-load-env-gate ...
run_scenario load-env-gate-missing-token ...
run_scenario load-env-gate-wrong-token ...
```

Contract summary:

```text
schema=a90-wsta166-seccomp-live-observation-runner-source-v1
state=SOURCE_ONLY_REMOTE_SCRIPT_NOT_EXECUTED
scenario_count=3
expected_scenario_returncode=65
correct_wsta161_token_included=false
seccomp_filter_load_expected=false
seccomp_enforcement_expected=false
```

## Checks

WSTA166 fail-closes unless:

- source proof emission is explicitly gated.
- run dir and WSTA165 plan JSON are private.
- WSTA165 plan schema and host-only state match.
- WSTA165 plan has exactly the three no-load scenarios.
- WSTA165 plan says correct token not supplied, filter load false, and
  enforcement false.
- WSTA165 plan contains the load-attempt marker only as a forbidden marker.
- generated script has begin/done markers and all three scenarios.
- generated script uses `/usr/bin/env -i`.
- generated script calls only
  `/usr/local/bin/a90-service-launch dpublic-hud /bin/true`.
- generated script contains WSTA163/WSTA164 gates and the wrong-token
  placeholder.
- generated script does not contain the correct WSTA161 load token.
- generated script has no external network inputs: no cloudflared, tunnel,
  Wi-Fi, or DHCP strings.
- contract says source-only, no correct token, no filter load, no enforcement,
  and three scenarios.

## Validation

- `py_compile`:
  - `run_wsta166_seccomp_live_observation_runner_source.py`
  - `test_server_distro_wsta166_seccomp_live_observation_runner_source.py`
- Focused WSTA165 + WSTA166 tests: `6 tests OK`.
- Full server-distro regression: `568 tests OK`.
- WSTA166 source proof generation from the real WSTA165 plan JSON: pass.

## Next

WSTA167 can implement the actual device-side live observation using this
remote script contract, still without the correct WSTA161 load token.  Actual
seccomp load/enforcement remains unproven and must remain behind a separate
explicit design review and gate.
