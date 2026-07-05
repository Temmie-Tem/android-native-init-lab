# WSTA204 WSTA198 Live Result Verifier

Date: 2026-07-05 18:11 KST

## Verdict

WSTA204 adds a host-only post-live verifier for the future WSTA198 live result.
It consumes the private WSTA203 wrapper manifest audit, re-runs WSTA203 from
the same WSTA202 preflight, compares a token-independent stable audit view, and
emits a private verifier script for the eventual WSTA198 `wsta198_result.json`.

Result: PASS.

Current verifier state:

```text
POST_LIVE_RESULT_VERIFIER_READY_TOKEN_REQUIRED_DEFAULT_OFF
```

The pre/live/post host-side gates are prepared through post-result validation,
but immediate live execution remains false because the private
`A90_PRIVATE_WSTA161_LOAD_TOKEN` environment variable was not present in this
host-only proof.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta204_wsta203_live_result_verifier.py`.
- Added focused tests in
  `tests/test_server_distro_wsta204_wsta203_live_result_verifier.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta204-wsta198-live-result-verifier-20260705T181121KST/
```

Decision:

```text
wsta204-wsta203-live-result-verifier-source-pass
```

Input:

```text
workspace/private/runs/server-distro/wsta203-wsta202-wrapper-manifest-audit-20260705T180223KST/wsta203_wsta202_wrapper_manifest_audit.json
```

Generated private artifacts:

```text
workspace/private/runs/server-distro/wsta204-wsta198-live-result-verifier-20260705T181121KST/wsta204_result.json
workspace/private/runs/server-distro/wsta204-wsta198-live-result-verifier-20260705T181121KST/wsta204_wsta198_live_result_verifier.json
workspace/private/runs/server-distro/wsta204-wsta198-live-result-verifier-20260705T181121KST/wsta204_verify_wsta198_live_result.sh
workspace/private/runs/server-distro/wsta204-wsta198-live-result-verifier-20260705T181121KST/wsta204_wsta198_live_result_verifier.md
workspace/private/runs/server-distro/wsta204-wsta198-live-result-verifier-20260705T181121KST/wsta203-recheck/wsta203_result.json
```

Key checks:

```text
audit_valid=true
wsta203_recheck_valid=true
audit_stable_view_match=true
live_result_verifier_valid=true
ready_for_post_live_verification=true
ready_for_immediate_live_execute=false
private_token_env_present=false
private_token_matches_wsta161=false
```

## Verifier Contract

WSTA204 verify mode accepts only a private WSTA198 live result where:

- decision is `wsta198-seccomp-load-canary-ssh-adapter-live-pass`,
- all required live checks are true,
- bounded SSH/chroot/dropbear/seccomp safety flags are true,
- flash, reboot, Wi-Fi, public tunnel, userdata, packet-filter mutation, and
  switch-root flags are false,
- canary load/apply/single-service/policy markers are present,
- token literal is absent from execution output and result JSON,
- cleanup is accepted, and
- fresh and post native health checks are true.

The focused tests cover both a synthetic accepted live result and a rejected
live result with a missing canary marker.

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
execute the WSTA200 handoff shell, run WSTA198 live, supply the WSTA161 token
to the device, run native health, load a seccomp filter, or enforce seccomp.

## Validation

- `py_compile`:
  - `run_wsta204_wsta203_live_result_verifier.py`
  - `test_server_distro_wsta204_wsta203_live_result_verifier.py`
- Focused WSTA204 tests: `7 tests OK`.
- WSTA204 proof run: pass.
- Full server-distro regression: `755 tests OK`.

## Next

Deliberately export the private token, re-run WSTA202/WSTA203/WSTA204 to reach
token-ready default-off states, manually run the existing private WSTA200
handoff wrapper, then feed the resulting private WSTA198 `wsta198_result.json`
into WSTA204 verify mode.
