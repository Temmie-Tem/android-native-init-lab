# WSTA203 WSTA202 Wrapper Manifest Audit

Date: 2026-07-05 18:02 KST

## Verdict

WSTA203 adds a host-only wrapper manifest audit for the existing
WSTA200/WSTA198 attended-live chain.  It consumes the private WSTA202 live
preflight artifact, re-runs WSTA202 from the same WSTA201 status, compares a
token-independent stable preflight view, and audits both wrapper layers that a
human would run after deliberately supplying the private token.

Result: PASS.

Current audit state:

```text
WRAPPER_MANIFEST_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF
```

The WSTA200 handoff wrapper and WSTA198 SSH/chroot live wrapper remain current,
but immediate live execution remains false because the private
`A90_PRIVATE_WSTA161_LOAD_TOKEN` environment variable was not present in this
host-only proof.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta203_wsta202_wrapper_manifest_audit.py`.
- Added focused tests in
  `tests/test_server_distro_wsta203_wsta202_wrapper_manifest_audit.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta203-wsta202-wrapper-manifest-audit-20260705T180223KST/
```

Decision:

```text
wsta203-wsta202-wrapper-manifest-audit-pass
```

Input:

```text
workspace/private/runs/server-distro/wsta202-wsta201-live-preflight-20260705T175342KST/wsta202_wsta201_live_preflight.json
```

Generated private artifacts:

```text
workspace/private/runs/server-distro/wsta203-wsta202-wrapper-manifest-audit-20260705T180223KST/wsta203_result.json
workspace/private/runs/server-distro/wsta203-wsta202-wrapper-manifest-audit-20260705T180223KST/wsta203_wsta202_wrapper_manifest_audit.json
workspace/private/runs/server-distro/wsta203-wsta202-wrapper-manifest-audit-20260705T180223KST/wsta203_wsta202_wrapper_manifest_audit.md
workspace/private/runs/server-distro/wsta203-wsta202-wrapper-manifest-audit-20260705T180223KST/wsta202-recheck/wsta202_result.json
```

Key checks:

```text
preflight_valid=true
wsta202_recheck_valid=true
preflight_stable_view_match=true
handoff_wrapper_audit_valid=true
wsta198_wrapper_audit_valid=true
wrapper_manifest_audit_valid=true
ready_for_attended_live_handoff=true
ready_for_immediate_live_execute=false
private_token_env_present=false
private_token_matches_wsta161=false
```

## Wrapper Coverage

WSTA203 verifies the WSTA200 wrapper still:

- re-runs WSTA199 before live handoff,
- requires the private token environment variable,
- asserts the adapter is current,
- preserves the WSTA198 ACK stack,
- execs the private WSTA198 wrapper, and
- excludes flash, token literal, public URL, SSID, PSK, and external-network
  surfaces.

WSTA203 verifies the WSTA198 wrapper/source still:

- carries the explicit live execute gate,
- carries the complete WSTA198 ACK stack,
- emits full JSON,
- requires the private token environment variable,
- transports the token through redacted SSH stdin in the source path,
- has fresh and post native health hooks,
- has cleanup/postcheck gating, and
- marks seccomp loaded only after the canary markers are observed.

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
execute the WSTA200 handoff shell, run WSTA198 live, supply the WSTA161 token
to the device, run native health, load a seccomp filter, or enforce seccomp.

## Validation

- `py_compile`:
  - `run_wsta203_wsta202_wrapper_manifest_audit.py`
  - `test_server_distro_wsta203_wsta202_wrapper_manifest_audit.py`
- Focused WSTA203 tests: `7 tests OK`.
- WSTA203 proof run: pass.
- Full server-distro regression: `748 tests OK`.

## Next

The remaining live blocker is still operator-token/default-off.  Deliberately
export the private token, re-run WSTA202 and WSTA203 to reach token-ready
default-off states, then manually run the existing private WSTA200 handoff
wrapper.
