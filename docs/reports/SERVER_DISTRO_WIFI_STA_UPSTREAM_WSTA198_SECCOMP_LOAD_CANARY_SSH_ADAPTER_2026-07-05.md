# WSTA198 Seccomp-Load Canary SSH Adapter

Date: 2026-07-05 17:26 KST

## Verdict

WSTA198 implements the SSH/chroot transport adapter selected by WSTA197 for the
future attended WSTA196 seccomp-load canary.  The adapter is default-off and
source-gated by default.  It emits a private adapter packet and shell wrapper,
and it blocks live execution unless the operator supplies the explicit live
acknowledgement stack, the private WSTA161 token environment variable, and
fresh native health checks.

Result: PASS.

Selected transport:

```text
debian-chroot-dropbear-ssh-over-ncm
```

The WSTA196 host-local subprocess path remains disallowed.  WSTA198's live path
uses temporary Dropbear over USB/NCM and passes the token through redacted SSH
stdin into the remote launcher environment, not on a command line or in public
artifacts.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py`.
- Added focused tests in
  `tests/test_server_distro_wsta198_seccomp_load_canary_ssh_adapter.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta198-seccomp-load-canary-ssh-adapter-20260705T172612KST/
```

Decision:

```text
wsta198-seccomp-load-canary-ssh-adapter-source-pass
```

Input:

```text
workspace/private/runs/server-distro/wsta197-seccomp-load-canary-transport-gate-20260705T171427KST/wsta197_seccomp_load_canary_transport_gate.json
```

Generated private artifacts:

```text
workspace/private/runs/server-distro/wsta198-seccomp-load-canary-ssh-adapter-20260705T172612KST/wsta198_result.json
workspace/private/runs/server-distro/wsta198-seccomp-load-canary-ssh-adapter-20260705T172612KST/wsta198_seccomp_load_canary_ssh_adapter.json
workspace/private/runs/server-distro/wsta198-seccomp-load-canary-ssh-adapter-20260705T172612KST/wsta198_seccomp_load_canary_ssh_adapter.sh
workspace/private/runs/server-distro/wsta198-seccomp-load-canary-ssh-adapter-20260705T172612KST/wsta198_seccomp_load_canary_ssh_adapter.md
```

Adapter state:

```text
READY_SSH_CHROOT_ADAPTER_DEFAULT_OFF_LIVE_BLOCKED_UNTIL_TOKEN_AND_HEALTH
```

Key checks:

```text
wsta197_transport_gate_valid=true
adapter_packet_valid=true
selected_transport=debian-chroot-dropbear-ssh-over-ncm
ready_for_attended_live=true
ready_for_unattended_live=false
live_execution_requested=false
correct_wsta161_token_supplied=false
seccomp_filter_loaded=false
seccomp_enforced=false
token_value_not_included=true
token_stdin_redacted=true
no_external_network_inputs=true
```

## Live Adapter Shape

The optional live path now exists but was not run in this unit.  It requires:

- `--execute-real-seccomp-load-canary-over-ssh`;
- `--allow-correct-wsta161-token`;
- the seccomp-load risk, single-service, no-flash/no-reboot, cleanup, and
  SSH/chroot acknowledgements;
- `A90_PRIVATE_WSTA161_LOAD_TOKEN` in the operator environment;
- fresh native read-only health before the canary;
- temporary Dropbear over the USB/NCM chroot transport;
- post-run cleanup and native read-only health.

The runner deliberately does not call WSTA196's host-local `subprocess.run`
canary path.  Its SSH execution helper records the SSH command and redacts
stdout/stderr, while marking the stdin payload as redacted.

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
run the live canary, supply the correct WSTA161 token, load a seccomp filter,
or enforce seccomp.

## Validation

- `py_compile`:
  - `run_wsta198_seccomp_load_canary_ssh_adapter.py`
  - `test_server_distro_wsta198_seccomp_load_canary_ssh_adapter.py`
- Focused WSTA198 tests: `6 tests OK`.
- WSTA198 proof run: pass.
- Full server-distro regression: `719 tests OK`.

## Next

Proceed to WSTA199: live-readiness status for the WSTA198 adapter, or an
attended WSTA198 live execution only after the operator deliberately supplies
the private token and confirms fresh native health.
