# Native Init V256 CNSS Cleanup Race Fix Plan

## Summary

- V255 first bounded live start-only was executed with explicit operator approval.
- Result was not safe PASS: runner returned `manual-review-required` and `cnss-daemon` remained alive as PID `5900`.
- Manual recovery succeeded with `kill -TERM 5900`; post-check `pidof cnss-daemon` returned rc=1 and no `wlan*` interface appeared.
- V256 fixes the helper process-group cleanup race before any future live retry.

## Root Cause

`a90_android_execns_probe` forks the CNSS child, then immediately stores `pgid = getpgid(pid)`.
The child calls `setsid()` after fork. If the parent reads the pgid before `setsid()`, it stores the inherited process group instead of the child session/process-group id.
On timeout, `kill(-pgid, SIGTERM)` can signal the helper/control process group instead of the CNSS child group.
That killed the helper with signal 15 and left `cnss-daemon` running.

## Key Changes

- Bump helper version to `a90_android_execns_probe v10`.
- In `run_cnss_start_only_guarded()`, never use an inherited pre-`setsid()` pgid for cleanup.
- Add a small helper that waits briefly for the child to enter its own session/group.
- If the child pgid cannot be proven as `pid`, use `pid` as the only safe process-group target and keep direct `kill(pid, ...)` fallback.
- Preserve all live guardrails:
  - no scan/connect/link-up/credential/DHCP/routing;
  - no `cnss_diag`;
  - no rfkill unblock;
  - no ICNSS bind/unbind;
  - no persistent Android writes.

## Validation

- Build static helper:
  - `scripts/revalidation/build_android_execns_probe_helper.sh`
- Static checks:
  - `git diff --check`
  - `python3 -m py_compile scripts/revalidation/wifi_cnss_start_only_runner.py scripts/revalidation/wifi_cnss_live_approval_packet.py`
- Deploy helper:
  - `tcpctl_host.py install` to `/cache/bin/a90_android_execns_probe`
- No-start validation only:
  - direct helper no-allow run must report `cnss_start.result=start-only-blocked`, `exec_attempted=0`;
  - `pidof cnss-daemon` must remain rc=1;
  - live start is not retried in V256 without a new explicit operator approval.

## Acceptance

- Helper v10 is deployed and hash documented.
- No-allow guard still blocks daemon execution.
- The V255 live attempt is documented as recovered manual-review, not as PASS.
- Future live retry is blocked until explicit approval after reviewing V256.
