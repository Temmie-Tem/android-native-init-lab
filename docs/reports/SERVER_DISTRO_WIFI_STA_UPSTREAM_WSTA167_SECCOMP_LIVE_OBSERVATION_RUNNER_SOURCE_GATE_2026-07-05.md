# WSTA167 Seccomp Live-Observation Runner Source Gate Pass

Date: 2026-07-05 13:46 KST

## Verdict

WSTA167 adds the actual bounded live-observation runner for the staged
seccomp apply/load-env gates.  The runner is fail-closed and device-inert by
default.  It only proceeds to bridge/device/chroot work when all explicit live
acknowledgements are supplied:

```text
--execute-seccomp-live-observation
--allow-seccomp-live-observation
--ack-no-correct-wsta161-token
--ack-no-seccomp-load
--ack-cleanup-required
```

This unit did not run the live gate.  It generated a no-live-gate proof that
validated the WSTA166 contract and local inputs, then stopped before any device
action with `wsta167-blocked-seccomp-live-observation-required`.

Result: SOURCE/GATE PASS.  The runner can stage the current launcher, WSTA153
policy/map, WSTA156 filter manifest/object, WSTA161 gated-apply helper, and
WSTA166 remote script into a Debian chroot when explicitly live-gated.  Its
observation parser requires all three no-load scenarios to return `65`, forbids
`A90WSTA161_SECCOMP_LOAD_ATTEMPT=1`, forbids launcher exec/fake setpriv, and
requires the expected no-gate, missing-token, and wrong-token block markers.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta167_seccomp_live_observation.py`.
- Added focused tests in
  `tests/test_server_distro_wsta167_seccomp_live_observation.py`.

## Generated Proof

No-live-gate proof run:

```text
workspace/private/runs/server-distro/wsta167-seccomp-live-observation-source-gate-20260705T1354KST/
```

Inputs:

```text
workspace/private/runs/server-distro/wsta166-seccomp-live-observation-runner-source-20260705T1344KST/wsta166_live_runner_contract.json
workspace/private/runs/server-distro/wsta166-seccomp-live-observation-runner-source-20260705T1344KST/wsta166_remote_seccomp_observation.sh
workspace/private/runs/server-distro/wsta153-seccomp-policy-source-20260705T1207KST/wsta153_seccomp_policy.json
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filter_manifest.json
workspace/private/runs/server-distro/wsta156-seccomp-nonloaded-filter-artifact-20260705T1227KST/wsta156_seccomp_filters.o
workspace/private/runs/server-distro/wsta161-seccomp-loader-gated-apply-helper-20260705T1307KST/wsta161_seccomp_loader_helper_manifest.json
workspace/private/runs/server-distro/wsta161-seccomp-loader-gated-apply-helper-20260705T1307KST/a90-seccomp-loader-gated-apply
```

Decision:

```text
wsta167-blocked-seccomp-live-observation-required
```

No-live-gate proof summary:

```text
contract_valid=true
local_inputs_present=true
explicit_live_gate=false
device_action=false
seccomp_filter_loaded=false
seccomp_enforced=false
correct_wsta161_token_supplied=false
```

## Checks

WSTA167 live execution will fail closed unless:

- every explicit live/no-load/cleanup acknowledgement is present.
- WSTA166 contract validates:
  - schema
  - source-only state
  - three scenarios
  - expected return code `65`
  - correct WSTA161 token false
  - filter load and enforcement false
  - correct token literal absent
  - no external network inputs
- all local private inputs are present.
- baseline selftest has fail zero.
- native stale cleanup passes.
- remote work image is ready.
- chroot mount and temporary Dropbear start.
- Debian SSH marker passes.
- seccomp observation assets stage successfully.
- remote observation returns:
  - all scenario begin/end markers
  - all scenario rc `65`
  - `blocked-load-gate-required`
  - `blocked-seccomp-helper-load-token-required`
  - `blocked-load-token-required`
  - no `A90WSTA161_SECCOMP_LOAD_ATTEMPT=1`
  - no exec/fake setpriv
  - no loaded marker
- chroot cleanup passes.
- final selftest has fail zero.

## Validation

- `py_compile`:
  - `run_wsta167_seccomp_live_observation.py`
  - `test_server_distro_wsta167_seccomp_live_observation.py`
- Focused WSTA166 + WSTA167 tests: `8 tests OK`.
- Full server-distro regression: `573 tests OK`.
- WSTA167 no-live-gate proof with real WSTA166/WSTA153/WSTA156/WSTA161 inputs:
  source/gate pass.

## Next

WSTA168 can run the explicit live observation if the operator supplies the
WSTA167 live acknowledgements.  That live run still must not provide the
correct WSTA161 load token and must still expect no seccomp load/enforcement.
The first real seccomp-load experiment remains a separate design review and
gate.
