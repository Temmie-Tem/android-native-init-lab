# WSTA206 WSTA201 Fresh Transaction Preparer

Date: 2026-07-05 18:25 KST

## Verdict

WSTA206 adds a host-only fresh transaction preparer.  It consumes the private
WSTA201 status, replays WSTA202, WSTA203, WSTA204, and WSTA205 from that current
status, and emits a private prepare script that can later regenerate a fresh
WSTA205 transaction bundle after the operator deliberately supplies the private
token.

Result: PASS.

Current preparer state:

```text
FRESH_TRANSACTION_PREPARER_READY_TOKEN_REQUIRED_DEFAULT_OFF
```

The fresh pre-live chain is structurally ready, but immediate live execution
remains false because the private `A90_PRIVATE_WSTA161_LOAD_TOKEN` environment
variable was not present in this host-only proof.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta206_wsta201_fresh_transaction_preparer.py`.
- Added focused tests in
  `tests/test_server_distro_wsta206_wsta201_fresh_transaction_preparer.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta206-wsta201-fresh-transaction-preparer-20260705T182447KST/
```

Decision:

```text
wsta206-wsta201-fresh-transaction-preparer-pass
```

Input:

```text
workspace/private/runs/server-distro/wsta201-wsta200-handoff-status-20260705T175021KST/wsta201_wsta200_handoff_status.json
```

Generated private artifacts:

```text
workspace/private/runs/server-distro/wsta206-wsta201-fresh-transaction-preparer-20260705T182447KST/wsta206_result.json
workspace/private/runs/server-distro/wsta206-wsta201-fresh-transaction-preparer-20260705T182447KST/wsta206_fresh_transaction_preparer.json
workspace/private/runs/server-distro/wsta206-wsta201-fresh-transaction-preparer-20260705T182447KST/wsta206_prepare_fresh_transaction.sh
workspace/private/runs/server-distro/wsta206-wsta201-fresh-transaction-preparer-20260705T182447KST/wsta206_fresh_transaction_preparer.md
workspace/private/runs/server-distro/wsta206-wsta201-fresh-transaction-preparer-20260705T182447KST/wsta205-replay/wsta205_run_wsta200_and_verify.sh
```

Key checks:

```text
wsta201_status_valid=true
wsta202_replay_valid=true
wsta203_replay_valid=true
wsta204_replay_valid=true
wsta205_replay_valid=true
fresh_transaction_preparer_valid=true
ready_for_fresh_prepare=true
ready_for_immediate_live_execute=false
private_token_env_present=false
private_token_matches_wsta161=false
```

## Fresh Prepare Contract

The generated private prepare script will:

1. require `A90_PRIVATE_WSTA161_LOAD_TOKEN`,
2. rerun WSTA206 from the current WSTA201 status,
3. require token-ready state,
4. confirm no live command ran during prepare, and
5. print the fresh WSTA205 transaction script path.

The generated WSTA205 transaction script still remains the separate supervised
live step.

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
execute the generated prepare script, execute the generated WSTA205 transaction
script, execute the WSTA200 handoff shell, run WSTA198 live, supply the WSTA161
token to the device, run native health, load a seccomp filter, or enforce
seccomp.

## Validation

- `py_compile`:
  - `run_wsta206_wsta201_fresh_transaction_preparer.py`
  - `test_server_distro_wsta206_wsta201_fresh_transaction_preparer.py`
- Focused WSTA206 tests: `6 tests OK`.
- WSTA206 proof run: pass.
- Full server-distro regression: `768 tests OK`.

## Next

After deliberately exporting the private token, run the generated WSTA206
prepare script to refresh WSTA202-205 and print a fresh WSTA205 transaction
script, then run that WSTA205 transaction script under supervision if the
token-ready state is confirmed.
