# WSTA197 Seccomp-Load Canary Transport Gate

Date: 2026-07-05 17:14 KST

## Verdict

WSTA197 selects and validates the transport for a future attended WSTA196
seccomp-load canary execution.  It consumes WSTA196 source-gate evidence plus
prior Debian/chroot transport proofs, then emits a private transport packet.

Result: PASS.

Selected transport:

```text
debian-chroot-dropbear-ssh-over-ncm
```

WSTA196 direct host-local subprocess execution is explicitly not allowed for
live device execution.  A future WSTA198 adapter must run the canary inside the
Debian/chroot transport and keep the token private.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta197_seccomp_load_canary_transport_gate.py`.
- Added focused tests in
  `tests/test_server_distro_wsta197_seccomp_load_canary_transport_gate.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta197-seccomp-load-canary-transport-gate-20260705T171427KST/
```

Decision:

```text
wsta197-seccomp-load-canary-transport-gate-pass
```

Inputs:

```text
workspace/private/runs/server-distro/wsta196-seccomp-load-canary-source-gate-20260705T170553KST/wsta196_result.json
workspace/private/runs/server-distro/wsta196-seccomp-load-canary-source-gate-20260705T170553KST/wsta196_seccomp_load_canary_source_gate.json
workspace/private/runs/server-distro/wsta149-dpublic-hud-intent-syscall-trace-live-20260705T1058KST/wsta149_result.json
workspace/private/runs/server-distro/wsta167-seccomp-live-observation-source-gate-20260705T1354KST/wsta167_result.json
```

Generated private artifacts:

```text
workspace/private/runs/server-distro/wsta197-seccomp-load-canary-transport-gate-20260705T171427KST/wsta197_result.json
workspace/private/runs/server-distro/wsta197-seccomp-load-canary-transport-gate-20260705T171427KST/wsta197_seccomp_load_canary_transport_gate.json
workspace/private/runs/server-distro/wsta197-seccomp-load-canary-transport-gate-20260705T171427KST/wsta197_seccomp_load_canary_transport_gate.md
```

Transport state:

```text
TRANSPORT_DECIDED_WSTA196_LIVE_BLOCKED_UNTIL_ADAPTER
```

Key checks:

```text
wsta196_result_valid=true
wsta196_source_gate_valid=true
wsta149_live_transport_valid=true
wsta167_seccomp_asset_gate_valid=true
transport_gate_valid=true
selected_transport=debian-chroot-dropbear-ssh-over-ncm
wsta196_direct_host_subprocess_execute_allowed=false
ready_for_wsta198_transport_adapter=true
ready_for_wsta196_live_execute=false
token_literal_absent=true
no_external_network_inputs=true
```

## Transport Decision

WSTA197 picks the same transport class already proven by WSTA149 for
`a90-service-launch dpublic-hud`: SD work image mounted as a Debian chroot,
temporary Dropbear over USB/NCM, command execution over SSH, then cleanup and
post health.

The future WSTA198 adapter must:

- run fresh native read-only health before and after the canary;
- stage or verify service launcher, seccomp policy/map, filter artifact, and
  WSTA161 helper in the chroot;
- pass the correct WSTA161 token only through the private operator environment;
- avoid putting the token on a command line or in public stdout/stderr;
- execute only `/usr/local/bin/a90-service-launch dpublic-hud /bin/true`;
- parse the single-service load markers;
- clean up Dropbear/chroot even on failure.

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
invoke WSTA196 execution, generate or execute a live command, supply the
correct WSTA161 token, load a seccomp filter, or enforce seccomp.

## Validation

- `py_compile`:
  - `run_wsta197_seccomp_load_canary_transport_gate.py`
  - `test_server_distro_wsta197_seccomp_load_canary_transport_gate.py`
- Focused WSTA197 tests: `5 tests OK`.
- Full server-distro regression: `713 tests OK`.
- WSTA197 proof run: pass.

## Next

Proceed to WSTA198: implement the SSH/chroot transport adapter for the WSTA196
canary path, still fail-closed by default and still not run the live load
without operator token and fresh native health.
