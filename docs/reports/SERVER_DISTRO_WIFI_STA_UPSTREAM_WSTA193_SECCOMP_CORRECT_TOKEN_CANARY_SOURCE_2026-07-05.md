# WSTA193 Seccomp Correct-Token Canary Source

Date: 2026-07-05 16:42 KST

## Verdict

WSTA193 adds the host-only source proof for the first future correct-token
seccomp-load canary.  It consumes the WSTA192 risk charter, keeps the closed
WSTA187/WSTA190 no-load workflow separate, and emits a source-only
single-service canary contract that references a private runtime token
environment variable.

Result: PASS.

## Source Changes

- Added
  `workspace/public/src/scripts/server-distro/run_wsta193_seccomp_correct_token_canary_source.py`.
- Added focused tests in
  `tests/test_server_distro_wsta193_seccomp_correct_token_canary_source.py`.

## Proof

Run:

```text
workspace/private/runs/server-distro/wsta193-seccomp-correct-token-canary-source-20260705T1642KST/
```

Decision:

```text
wsta193-seccomp-correct-token-canary-source-pass
```

Input:

```text
workspace/private/runs/server-distro/wsta192-seccomp-load-risk-charter-20260705T1640KST/wsta192_result.json
```

Generated private artifacts:

```text
workspace/private/runs/server-distro/wsta193-seccomp-correct-token-canary-source-20260705T1642KST/wsta193_correct_token_canary_contract.json
workspace/private/runs/server-distro/wsta193-seccomp-correct-token-canary-source-20260705T1642KST/wsta193_correct_token_canary_source.sh
```

Contract state:

```text
SOURCE_ONLY_CANARY_NOT_EXECUTABLE
```

Canary shape:

```text
canary_service=dpublic-hud
policy_service=dpublic-hud-intent
launcher_command=/usr/local/bin/a90-service-launch dpublic-hud /bin/true
private_token_env=A90_PRIVATE_WSTA161_LOAD_TOKEN
token_value_included=false
correct_wsta161_token_supplied=false
seccomp_filter_loaded_in_this_unit=false
seccomp_enforced_in_this_unit=false
```

Key checks:

```text
wsta192_result_valid=true
wsta192_charter_valid=true
contract_valid=true
source_valid=true
shell_syntax_ok=true
single_service_canary=true
token_placeholder_only=true
token_literal_absent=true
does_not_call_wsta187=true
does_not_call_wsta190=true
```

## Safety Boundary

This proof did not flash, reboot, contact the device, connect Wi-Fi, run DHCP,
open a public tunnel, mutate packet filters, write userdata, switch root,
generate a live command, execute a live command, supply the correct WSTA161
token, load a seccomp filter, or enforce seccomp.

The generated shell is source-only and exits with code 65 if run directly.  It
contains only a private-token environment placeholder, not a token value.

## Validation

- `py_compile`:
  - `run_wsta193_seccomp_correct_token_canary_source.py`
  - `test_server_distro_wsta193_seccomp_correct_token_canary_source.py`
- Focused WSTA193 tests: `8 tests OK`.
- Full server-distro regression: `686 tests OK`.
- WSTA193 proof run: pass.

## Next

Proceed to WSTA194: consume the WSTA193 source contract and render a private,
default-off operator packet for one attended single-service seccomp-load
canary.  WSTA194 should still not execute the live load.
