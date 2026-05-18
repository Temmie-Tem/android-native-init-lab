# Native Init v247 CNSS Start/Observe/Stop Body Plan

## Summary

- target: v247 CNSS start-only helper body implementation plan
- baseline: v246 `cnss-start-only` helper guard PASS
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host wrapper: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- default behavior: no daemon execution
- live daemon start: blocked unless explicit operator approval is given after this plan

v247 should turn the v246 helper guard surface into a real bounded
start/observe/stop implementation path, while preserving the fail-closed host
runner default. This step is still not Wi-Fi bring-up: it is only a short
`/vendor/bin/cnss-daemon -n -l` process lifecycle test inside the private Android
execution namespace.

## Current State

- v244 proved harmless dynamic child execution with the required Android identity
  and `CAP_NET_ADMIN` contract.
- v245 added the host runner with `plan`, `preflight`, `dry-run`, and fail-closed
  `run` modes.
- v246 added helper mode `--mode cnss-start-only` and guard
  `--allow-cnss-start-only`.
- v246 safe validation showed:
  - helper namespace setup is `namespace-ready`
  - `/vendor/bin/cnss-daemon` is visible in the private namespace
  - no-allow execution returns `cnss_start.result=start-only-blocked`
  - runner `plan`/`preflight`/`dry-run` pass
  - runner `run` without dangerous flags remains fail-closed

## Goal

Implement the daemon lifecycle envelope without expanding the Wi-Fi operation
surface:

1. start `/vendor/bin/cnss-daemon -n -l` only when the helper receives
   `--allow-cnss-start-only` from an approved host `run`
2. apply the v244 launcher contract in the child:
   - uid/gid `system=1000`
   - groups `inet=3003`, `net_admin=3005`, `wifi=1010`
   - ambient/effective/permitted `CAP_NET_ADMIN`
   - clean Android environment
   - private chroot namespace with bind-backed APEX farm and real linkerconfig
3. observe the daemon for bounded `--timeout-sec`
4. capture process metadata before stopping:
   - pid and process group
   - `/proc/<pid>/status` selected fields
   - `/proc/<pid>/fd` count/summary if readable
   - `/proc/<pid>/maps` path summary if readable
   - stdout/stderr transcript caps
5. stop the process group with SIGTERM, then SIGKILL if needed
6. reap the direct child
7. emit stable `cnss_start.*` key/value output
8. classify the result without automatic reboot or unsafe recovery

## Non-Goals

v247 must not do any of the following:

- Wi-Fi scan/connect/link-up
- credential handling
- DHCP/routing
- `cnss_diag`
- `rfkill unblock`
- `ip link set wlan* up`
- `iw scan` / `iw connect`
- supplicant/HAL/wificond/hostapd start
- ICNSS generic bind/unbind
- firmware path mutation
- persistent Android partition writes
- public network listener expansion
- automatic reboot

## Helper Implementation Contract

### Parser And Guard

Keep v246 parser behavior:

```text
--mode cnss-start-only
--allow-cnss-start-only
```

- Without `--allow-cnss-start-only`, the helper must not fork the daemon.
- With the flag, the helper may perform exactly one daemon start attempt.
- Target and argv remain fixed:

```text
/vendor/bin/cnss-daemon -n -l
```

### Child Setup

The child should reuse the identity-probe path instead of creating a second
launcher contract implementation. Required order:

1. create stdout/stderr pipes
2. `fork()`
3. child: `setsid()` so the daemon has its own process group
4. child: `chroot(paths->root)` and `chdir("/")`
5. child: apply uid/gid/groups/capability contract
6. child: clean environment
7. child: `execve("/vendor/bin/cnss-daemon", argv, envp)`
8. child: on exec failure, write a structured error to stderr and `_exit(127)`

### Parent Observation

Parent behavior:

- record `cnss_start.pid`
- record `cnss_start.pgid`
- poll child stdout/stderr in nonblocking mode
- poll `waitpid(pid, WNOHANG)` until child exits or timeout expires
- if still running after timeout, mark `cnss_start.observable=1`
- if it exits immediately, classify based on exit/signal and captured stderr
- before stopping a still-running child, attempt read-only `/proc/<pid>` probes

### Stop And Reap

Stop sequence:

1. `kill(-pgid, SIGTERM)`
2. wait up to a short fixed grace window, e.g. 1000 ms
3. if still alive, `kill(-pgid, SIGKILL)`
4. bounded wait/reap
5. emit `term_sent`, `kill_sent`, `reaped`, and `postflight_safe`

If the helper cannot prove that the process was stopped/reaped, classify as
`start-only-reboot-required`. Do not attempt ICNSS bind/unbind recovery.

## Output Contract

v247 should extend v246 output but keep old keys stable:

```text
cnss_start.begin=1
cnss_start.mode=guarded
cnss_start.target=/vendor/bin/cnss-daemon
cnss_start.argv=/vendor/bin/cnss-daemon -n -l
cnss_start.cnss_diag=0
cnss_start.scan_connect_linkup=0
cnss_start.allowed=0|1
cnss_start.exec_attempted=0|1
cnss_start.child_started=0|1
cnss_start.pid=<pid|-1>
cnss_start.pgid=<pgid|-1>
cnss_start.observable=0|1
cnss_start.exited=0|1
cnss_start.exit_code=<n|-1>
cnss_start.signal=<n|0>
cnss_start.timed_out=0|1
cnss_start.term_sent=0|1
cnss_start.kill_sent=0|1
cnss_start.reaped=0|1
cnss_start.proc_status_captured=0|1
cnss_start.fd_summary_captured=0|1
cnss_start.maps_summary_captured=0|1
cnss_start.postflight_safe=0|1
cnss_start.result=start-only-pass|start-only-runtime-gap|start-only-reboot-required|start-only-blocked|manual-review-required
cnss_start.reason=<stable-token>
cnss_start.end=1
```

The existing `A90_EXECNS_STDOUT_BEGIN/END` and `A90_EXECNS_STDERR_BEGIN/END`
sections remain the transcript carrier.

## Host Runner Changes

Update `scripts/revalidation/wifi_cnss_start_only_runner.py` after helper body
exists:

- keep `plan`, `preflight`, and `dry-run` non-starting
- keep `run` fail-closed unless all dangerous flags are set
- parse helper `cnss_start.*` keys from the `run` output
- write `start-observation.json`, `postflight.json`, and `cleanup.json`
- set `daemon_start_executed=true` only if helper reports
  `cnss_start.exec_attempted=1`
- classify decisions from helper keys, not prose

Expected decision mapping:

| helper result | host decision | pass |
| --- | --- | --- |
| `start-only-pass` | `start-only-pass` | true |
| `start-only-runtime-gap` | `start-only-runtime-gap` | true if postflight safe |
| `start-only-reboot-required` | `start-only-reboot-required` | false |
| `start-only-blocked` | `start-only-blocked` | false |
| missing keys | `manual-review-required` | false |

## Validation Plan

### Static

```bash
scripts/revalidation/build_android_execns_probe_helper.sh
python3 -m py_compile scripts/revalidation/wifi_cnss_start_only_runner.py scripts/revalidation/wifi_cnss_identity_probe.py
git diff --check
strings stage3/linux_init/helpers/a90_android_execns_probe | rg 'cnss-start-only|allow-cnss-start-only|start-only-pass|start-only-reboot-required'
```

### Safe Live Validation Without Daemon Start

These commands may be run without operator approval because they must not start
`cnss-daemon`:

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v247-cnss-start-body-plan plan
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v247-cnss-start-body-preflight preflight
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v247-cnss-start-body-dryrun dry-run
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v247-cnss-start-body-run-blocked run
```

Expected:

- `plan`: PASS / `dry-run-ready`
- `preflight`: PASS / `preflight-ready`
- `dry-run`: PASS / `preflight-ready`
- `run` without dangerous flags: expected fail-closed / `start-only-blocked`
- `daemon_start_executed=false` for all safe validations

### First Live Start-Only Validation

This is not automatic. It requires explicit operator approval after reviewing the
safe validation evidence.

Preconditions:

- ACM bridge or NCM/tcpctl path is stable
- host can reboot/recover the phone if needed
- device is not in the middle of long-soak or storage-sensitive tests
- NCM/ACM exposure is local-only as documented by v225/v245 preflight

Candidate command after approval:

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py \
  --out-dir tmp/wifi/v247-cnss-start-body-live1 \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

The live command must still not perform scan/connect/link-up. If the daemon
starts and exits due to missing Android property/diag/QRTR/SELinux primitives,
classify as `start-only-runtime-gap` if cleanup is safe.

## Acceptance Criteria

- v246 no-allow guard behavior remains unchanged.
- Helper implements exactly one guarded daemon lifecycle attempt behind
  `--allow-cnss-start-only`.
- Host runner remains non-starting by default.
- Safe validation passes before any live start is considered.
- Live validation, if explicitly approved, records stable machine-readable
  lifecycle evidence and either stops/reaps cleanly or marks reboot-required.
- No Wi-Fi scan/connect/link-up or persistent Android mutation occurs.

## Next Step After v247

If v247 safe implementation is ready but live execution is not approved, stop at
`LIVE APPROVAL REQUIRED` with the dry-run evidence. If a live run is approved and
it ends as `start-only-runtime-gap`, the next planning target is the missing
runtime primitive classification, likely property socket, diag/QRTR device, or
SELinux/service context emulation inventory.
