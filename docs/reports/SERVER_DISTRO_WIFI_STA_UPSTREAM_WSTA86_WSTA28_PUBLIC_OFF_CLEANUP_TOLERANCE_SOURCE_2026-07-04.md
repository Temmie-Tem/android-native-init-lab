# WSTA86 WSTA28 Public-Off Cleanup Tolerance Source

- Date: 2026-07-04
- Scope: host-side WSTA28 cleanup gate fix after WSTA85
- Decision: `wsta86-wsta28-public-off-cleanup-tolerance-source-pass`

## Summary

WSTA85 showed that WSTA28 could block after a healthy native reboot even when
the final `wifi status` state proved the public exposure path was off:

```text
autoconnect.decision=wifi-autoconnect-disabled
supplicant.process_count=0
secret_values_logged=0
```

The blocker was not a public-state leak.  It was a gate-shape issue: WSTA28
required `decision=` parses from individual cleanup commands, although those
commands may return `status=ok rc=0` with sparse parsed key/value output after
a reboot or bridge transition.  The load-bearing safety property is the final
public-off state, not the presence of every intermediate `decision=` field.

## Source Changes

Updated `run_wsta28_reboot_materialization_gate.py`:

- Added `post_reboot_public_off_cleanup_ok()`.
- Accepts sparse intermediate cleanup summaries when:
  - `wifi autoconnect disable` completed with the expected decision or
    `status=ok`;
  - `wifi cleanup` completed with the expected decision or `status=ok`;
  - final `wifi status` reports autoconnect disabled;
  - final `wifi status` reports `secret_values_logged=0`;
  - final `wifi status` reports `supplicant.process_count=0`.
- Keeps the gate fail-closed if the final state has autoconnect enabled,
  nonzero secret logging, or a live supplicant process.
- Treats `hide` as noncritical cleanup metadata for this gate; final public-off
  state remains the proof.
- Adds `final_state_public_off` and `hide_noncritical` to the public cleanup
  summary so future blocked runs are easier to classify.

Updated WSTA28 tests:

- Sparse intermediate decisions with final public-off state now pass.
- Final autoconnect enabled, secret logging, or live supplicant still fails.

## Safety

- Source-only change; no device command ran for WSTA86.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
  userdata action, switch-root, or non-boot partition write ran.
- The WSTA28 explicit live gate, native health gate, and fail-closed final-state
  checks remain intact.
- No raw public URLs, confirm-token values, credentials, network identifiers,
  routable addresses, or device identifiers are committed here.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests.test_server_distro_wsta28_reboot_materialization_gate \
  tests.test_server_distro_wsta43_orchestrated_native_uplink_dpublic \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof \
  tests.test_server_distro_wsta80_persistent_operator_execute_gate -v
```

Result: `Ran 41 tests ... OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py \
  tests/test_server_distro_wsta28_reboot_materialization_gate.py
```

Result: pass.

```text
git diff --check
```

Result: pass.

## Next

Rerun the bounded WSTA80 -> WSTA58 live measurement so WSTA42 can reach the
clean-image cache path and prove whether the second leg avoids host-side rootfs
upload.
