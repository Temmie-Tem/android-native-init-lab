# WSTA207 Seccomp Live Canary Pass

Date: 2026-07-05 18:52 KST

## Summary

WSTA207 closed the attended live canary gate from the 2026-07-05 operator GO block.
The WSTA198 SSH/chroot adapter loaded a seccomp filter in the throwaway canary
process, observed the expected bounded canary exit, cleaned up the chroot/Dropbear
transport, and WSTA204 accepted the resulting live JSON.

No boot flash, native reboot, Wi-Fi connect, DHCP, public tunnel, packet-filter
mutation, userdata write, or switch_root occurred in this unit. The private
WSTA161 token was supplied only through the redacted environment/stdin path and is
not present in committed artifacts.

## Code Changes

- WSTA198 now exposes the downstream D1/WSTA42 transfer-timeout CLI contract
  (`bridge/connect/tcp/transfer` timeouts, transfer delay, toybox).
- WSTA198 stages the WSTA153 policy, WSTA156 filter artifact, WSTA161 gated apply
  helper, launcher, and launcher map into the mounted Debian chroot before the
  live canary.
- WSTA204 now verifies WSTA198's staged seccomp-asset checks and accepts the
  bounded `(0, 65)` canary return-code semantics from WSTA196.
- D2 and WSTA42 suppress OpenSSH weak-crypto warning text so verifier redaction
  checks are not polluted by the OpenSSH documentation URL.

## Live Evidence

- Transaction: `workspace/private/runs/server-distro/wsta206-fresh-transaction-preparer-20260705T184916KST/wsta205-replay/`
- WSTA198 live result: `workspace/private/runs/server-distro/wsta206-fresh-transaction-preparer-20260705T184916KST/wsta205-replay/wsta205_wsta198_live_stdout_20260705T184924KST.json`
- WSTA204 verify result: `workspace/private/runs/server-distro/wsta206-fresh-transaction-preparer-20260705T184916KST/wsta205-replay/wsta205_wsta204_verify_20260705T184924KST.json`

Observed decisions:

- `wsta198-seccomp-load-canary-ssh-adapter-live-pass`
- `wsta204-wsta198-live-result-verify-pass`
- Verification state: `WSTA198_LIVE_RESULT_ACCEPTED`
- Canary execution return code: `65` (bounded expected canary outcome)
- Final native selftest: `pass=12 warn=1 fail=0`

Key WSTA198 safety booleans:

- `live_command_executed=true`
- `seccomp_assets_staged=true`
- `seccomp_filter_loaded=true`
- `seccomp_enforced=true`
- `fresh_native_health_checked=true`
- `post_run_native_health_checked=true`
- `post_run_audit_executed=true`
- `secret_values_logged=0`

## Validation

Host validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_d2_ssh_in_chroot.py \
  workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py \
  workspace/public/src/scripts/server-distro/run_wsta198_seccomp_load_canary_ssh_adapter.py \
  workspace/public/src/scripts/server-distro/run_wsta204_wsta203_live_result_verifier.py
```

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests/test_server_distro_wsta198_seccomp_load_canary_ssh_adapter.py \
  tests/test_server_distro_wsta204_wsta203_live_result_verifier.py \
  tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py
```

Result: `33 tests OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest \
  tests/test_server_distro_d2_ssh_in_chroot.py
```

Result: `3 tests OK`.

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest discover \
  -s tests -p 'test_server_distro*.py'
```

Result: `769 tests OK`.

Live validation:

```text
workspace/private/runs/server-distro/wsta206-wsta201-fresh-transaction-preparer-20260705T182447KST/wsta206_prepare_fresh_transaction.sh
workspace/private/runs/server-distro/wsta206-fresh-transaction-preparer-20260705T184916KST/wsta205-replay/wsta205_run_wsta200_and_verify.sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest
```

## Next

The canary load/enforce milestone is closed. The operator DoD still requires the
real D-harden service proof: load/enforce the derived seccomp profile on an actual
service, starting with `dpublic-smoke-httpd`, and prove the service remains
functional under enforcement.
