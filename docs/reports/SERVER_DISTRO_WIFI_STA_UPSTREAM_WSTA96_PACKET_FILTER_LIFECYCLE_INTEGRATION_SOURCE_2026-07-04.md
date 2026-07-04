# WSTA96 Packet Filter Lifecycle Integration Source Gate

- Date: 2026-07-04
- Scope: D-public packet-filter integration into the explicit public-live path
- Decision: `wsta96-packet-filter-lifecycle-integration-source-pass`
- Device action: none
- Boot flash / native reboot: none
- Wi-Fi / DHCP / public tunnel / public smoke: none
- Packet-filter mutation: none

## Summary

WSTA96 turns the WSTA95 operator contract into source-level lifecycle behavior in
the actual WSTA42 public-live runner.  The live path now stages the packet-filter
helper with the other D-public binaries and executes:

1. packet-filter `preflight`
2. local loopback smoke proof
3. packet-filter `apply-loopback-default-drop`
4. `cloudflared` quick tunnel start
5. public smoke
6. D-public cleanup
7. packet-filter `restore`

The restore step runs in the `finally` cleanup path after any packet-filter apply
attempt, not only after a successful apply.  This closes the failure-cleanup case
for partial or failed apply attempts.

## Changes

- `run_wsta42_native_uplink_dpublic_tunnel.py`
  - stages `/usr/local/bin/a90-dpublic-packet-filter`;
  - parses packet-filter helper output;
  - requires preflight before native/public work advances;
  - applies loopback default-drop after local smoke and before `cloudflared`;
  - restores rules during cleanup after any apply attempt;
  - classifies missing preflight/apply/restore as explicit WSTA42 blockers.
- `run_wsta55_short_lived_public_proof.py`
  - requires nested WSTA42 `packet_filter_restore_ok`;
  - includes packet-filter restore in TTL/public-off cleanup proof.
- `run_wsta58_renewal_manual_stop_proof.py`
  - requires both initial and renewal WSTA55 runs to report packet-filter restore
    proof before returning live pass.

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py workspace/public/src/scripts/server-distro/run_wsta55_short_lived_public_proof.py workspace/public/src/scripts/server-distro/run_wsta58_renewal_manual_stop_proof.py
```

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest tests.test_server_distro_wsta42_native_uplink_dpublic_tunnel tests.test_server_distro_wsta55_short_lived_public_proof tests.test_server_distro_wsta58_renewal_manual_stop_proof tests.test_server_distro_wsta80_persistent_operator_execute_gate tests.test_server_distro_wsta88_persistent_operator_workflow -v
```

Result: 52 tests passed.

## Safety

This was a host/source-only integration step.  It did not flash, reboot,
associate Wi-Fi, run DHCP, start a public tunnel, run public smoke, touch
userdata, switch root, or mutate packet-filter state.  The packet-filter mutation
remains behind the existing explicit WSTA42/WSTA55/WSTA58/WSTA80 public-live
acknowledgement stack.

## Next

WSTA97 should run the bounded live proof through the explicit WSTA80/WSTA58
public-live gate and verify the full sequence on device: preflight, apply before
tunnel start, public smoke, D-public cleanup, exact packet-filter restore, and
final resident health.
