# Native Init V261 PID1 Orphan Reaper

## Summary

- Cycle label: `v261`
- Native build: `A90 Linux init 0.9.60 (v261)`
- Goal: add a PID1 generic orphan/zombie reaper and use process-table cleanliness as the gate before another CNSS start-only retry.
- Result: PASS. Real-device flash, reaper regression, CNSS zombie audit, and explicitly approved bounded CNSS start-only retry all passed.

## Implementation

- Added `stage3/linux_init/a90_reaper.c` and `stage3/linux_init/a90_reaper.h`.
- Added `reaper [status|run|verbose]` shell command.
- Added reaper summary to `status`, `bootstatus`, and `pid1guard`.
- Added generic `waitpid(-1, WNOHANG)` orphan reap polling:
  - before each shell prompt
  - after command dispatch
  - after service registry reap-all
- Bumped native build metadata to `0.9.60 (v261)`.

## Artifacts

- `stage3/linux_init/init_v261`
- `stage3/ramdisk_v261.cpio`
- `stage3/boot_linux_v261.img`

SHA256:

```text
88d2212bfd0aa249381728da040d0601f47bce5deef63d774f70c950b04bc72a  stage3/linux_init/init_v261
1a38ccc156abb649ce03b72eb2e36c23e370840719d4808cdfe458807f643031  stage3/ramdisk_v261.cpio
5a314c2adbd5547b7de8b6dd76ba380e41a8dec61184166efda412389355a31e  stage3/boot_linux_v261.img
```

Ramdisk contents:

```text
.
./bin
./bin/a90_cpustress
./bin/a90_longsoak
./bin/a90_rshell
./bin/a90sleep
./init
```

## Static Validation

```text
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra ... init_v261.c ... a90_reaper.c
file stage3/linux_init/init_v261
strings stage3/linux_init/init_v261 | rg 'A90 Linux init 0.9.60 \(v261\)|A90v261|0.9.60 v261 PID1 ORPHAN REAPER|reaper \[status'
git diff --check
python3 -m py_compile scripts/revalidation/a90ctl.py scripts/revalidation/native_init_flash.py scripts/revalidation/wifi_cnss_zombie_audit.py scripts/revalidation/wifi_cnss_start_only_runner.py scripts/revalidation/wifi_cnss_live_evidence_analyzer.py
```

Result: PASS.

## Device Flash Validation

Command:

```text
python3 scripts/revalidation/native_init_flash.py stage3/boot_linux_v261.img --from-native --expect-version "A90 Linux init 0.9.60 (v261)" --verify-protocol auto
```

Result: PASS.

Evidence:

```text
A90 Linux init 0.9.60 (v261)
cmdv1 verify passed: version/status rc=0 status=ok
```

Selected `status` evidence:

```text
selftest: pass=11 warn=1 fail=0 duration=34ms
pid1guard: pass=11 warn=1 fail=0 duration=1ms
reaper: total=0 last_poll=0 last_pid=- age=0ms
runtime: backend=sd root=/mnt/sdext/a90 fallback=no writable=yes
netservice: disabled tcpctl=stopped
```

## Reaper Validation

Commands:

```text
python3 scripts/revalidation/a90ctl.py reaper verbose
python3 scripts/revalidation/a90ctl.py pid1guard verbose
```

Result: PASS.

Evidence:

```text
reaper: total=0 last_poll=0 last_pid=- age=0ms
reaper: total=0 last_poll=0 last_pid=-1 last_status=0x0 last_text=exit=0 last_ms=0
08 PASS  reaper     rc=0 errno=0 total=0 last_poll=0 last_pid=- age=0ms
```

## CNSS Clean-State Audit

Post-flash audit:

```text
python3 scripts/revalidation/wifi_cnss_zombie_audit.py --out-dir tmp/wifi/v261-cnss-zombie-audit-after-flash-rerun
```

Result: PASS.

```text
decision: cnss-process-clean
pass: True
reason: no CNSS target processes found
```

Post-live retry audit:

```text
python3 scripts/revalidation/wifi_cnss_zombie_audit.py --out-dir tmp/wifi/v261-cnss-zombie-audit-after-live-retry
```

Result: PASS.

```text
decision: cnss-process-clean
pass: True
reason: no CNSS target processes found
target_zombie_count: 0
target_running_count: 0
```

## Approved CNSS Live Retry

Preflight:

```text
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v261-cnss-live-retry-preflight-20260519-084558 --expect-version "A90 Linux init 0.9.60 (v261)" --max-runtime-sec 10 preflight
```

Result: PASS.

```text
decision: preflight-ready
pass: True
ok commands: 19/19
CNSS target_process_count: 0
CNSS target_zombie_count: 0
CNSS target_running_count: 0
```

Live retry was executed only after explicit operator approval.

```text
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v261-cnss-live-retry-run-20260519-084629 --expect-version "A90 Linux init 0.9.60 (v261)" --max-runtime-sec 10 run --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery
```

Result: PASS.

```text
decision: start-only-pass
pass: True
reason: observed-until-timeout-clean-stop
daemon_start_executed: True
helper result: start-only-pass
child started: True
postflight safe: True
postflight process clean: True
reaped: True
```

Evidence analysis:

```text
python3 scripts/revalidation/wifi_cnss_live_evidence_analyzer.py --run-dir tmp/wifi/v261-cnss-live-retry-run-20260519-084629 --out-dir tmp/wifi/v261-cnss-live-evidence-analysis-final --post-processes tmp/wifi/v261-cnss-live-retry-run-20260519-084629/commands/post-cnss-processes.txt
```

Result: PASS.

```text
decision: cnss-start-only-evidence-classified
pass: True
PASS post-cnss-process-clean: target_process_count=0 target_running_count=0 target_zombie_count=0
```

Runtime warnings remain non-blocking and unchanged from earlier analysis:

- `perfd-client-unavailable`
- `kmsg-write-denied`
- `shell-quote-noise`

## Guardrails

Maintained during v261 validation:

- no Wi-Fi scan/connect/link-up/credential/DHCP/routing
- no `cnss_diag`
- no rfkill unblock
- no ICNSS bind/unbind
- no persistent Android partition writes

## Conclusion

V261 closes the V260 zombie cleanup blocker. `pidof` is no longer the only postflight signal; process-table audit and PID1 orphan reaping are now part of the validated workflow. The next Wi-Fi work can proceed to a no-scan QRTR/QMI endpoint interaction probe or to cleanup of the known CNSS warning surface.
