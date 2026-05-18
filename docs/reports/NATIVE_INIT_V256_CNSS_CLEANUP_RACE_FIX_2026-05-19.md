# Native Init V256 CNSS Cleanup Race Fix Report

## Summary

- Status: PASS for cleanup fix and no-start validation
- Device build: `A90 Linux init 0.9.59 (v159)`
- Helper update: `a90_android_execns_probe v10`
- Helper SHA-256: `1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750`
- V255 live start-only result: `manual-review-required`
- V256 live retry: not executed

## V255 Live Attempt Result

The first approved bounded live start-only command was executed:

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v255-cnss-live-start-only-run --max-runtime-sec 10 run --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery
```

Runner result:

```text
decision: manual-review-required
pass: False
reason: helper run command failed before a trusted result was parsed
```

Immediate postflight found `cnss-daemon` still running:

```text
pidof cnss-daemon -> 5900
```

Manual recovery:

```text
kill -TERM 5900 -> rc=0
pidof cnss-daemon -> rc=1
```

Network state after recovery:

```text
/proc/net/dev: no wlan* interface, ncm0 still present
```

## Root Cause

The helper forked the CNSS child and immediately recorded `pgid = getpgid(pid)`.
The child calls `setsid()` after fork. When the parent wins the race, it records the inherited process group rather than the child session/process-group id.
At timeout, `kill(-pgid, SIGTERM)` can signal the helper/control process group, killing the helper and leaving the child daemon alive.

Evidence from V255 output:

```text
run: pid=5898
allow_cnss_start_only=1
helper_status=namespace-ready
[signal 15]
A90P1 END ... rc=143 status=error
```

The trusted `cnss_start.*` end markers were not emitted, so the runner correctly returned `manual-review-required`.

## Fix

Changed `stage3/linux_init/helpers/a90_android_execns_probe.c`:

- version bumped to `a90_android_execns_probe v10`
- added `wait_for_child_session_pgid(pid, 1000)`
- parent now waits briefly for child `setsid()` to make `pgid == pid`
- if the child pgid cannot be proven, cleanup uses `pid` as the safe group target and still keeps direct `kill(pid, ...)` fallback
- runner default helper SHA updated to v10
- live approval packet default output updated to `tmp/wifi/v256-cnss-live-start-only-run`

## Build And Deploy

Build:

```text
scripts/revalidation/build_android_execns_probe_helper.sh
```

Result:

```text
artifact: stage3/linux_init/helpers/a90_android_execns_probe
static ARM64: yes
sha256: 1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750
```

Deploy:

```text
tcpctl installed /cache/bin/a90_android_execns_probe sha256=1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750
```

Device SHA check:

```text
1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750  /cache/bin/a90_android_execns_probe
```

## Validation

Static:

```text
python3 -m py_compile scripts/revalidation/wifi_cnss_start_only_runner.py scripts/revalidation/wifi_cnss_live_approval_packet.py
scripts/revalidation/build_android_execns_probe_helper.sh
```

No-start helper validation:

```text
A90_EXECNS_BEGIN version="a90_android_execns_probe v10"
allow_cnss_start_only=0
cnss_start.result=start-only-blocked
cnss_start.reason=missing-allow-cnss-start-only
cnss_start.exec_attempted=0
cnss_start.postflight_safe=1
A90_EXECNS_END rc=0
```

Post no-allow:

```text
pidof cnss-daemon -> rc=1
```

Runner v10 safe modes:

| mode | decision | pass |
| --- | --- | --- |
| plan | `dry-run-ready` | `True` |
| preflight | `preflight-ready` | `True` |
| dry-run | `preflight-ready` | `True` |

V10 live approval packet:

```text
decision: live-approval-packet-ready
pass: True
daemon_start_executed: False
```

Generated future command:

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v256-cnss-live-start-only-run --max-runtime-sec 10 run --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery
```

## Current Safety State

Final checks after recovery and v10 no-start validation:

```text
pidof cnss-daemon -> rc=1
/proc/net/dev -> no wlan* interface, ncm0 present
```

## Decision

- V255 live attempt is classified as recovered `manual-review-required`, not PASS.
- V256 helper cleanup fix is PASS under no-start validation.
- Do not retry live automatically.
- A future live retry requires another explicit operator approval after reviewing this report.
