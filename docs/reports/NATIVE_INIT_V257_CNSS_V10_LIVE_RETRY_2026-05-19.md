# Native Init V257 CNSS V10 Live Retry Report

## Summary

- Status: PASS
- Device build: `A90 Linux init 0.9.59 (v159)`
- Helper: `a90_android_execns_probe v10`
- Helper SHA-256: `1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750`
- Live command: one bounded CNSS start-only retry with explicit operator approval
- Decision: `start-only-pass`
- Wi-Fi scan/connect/link-up: not executed

## Approval And Preflight

The operator explicitly approved a V256/v10 live retry. Before execution:

```text
version -> A90 Linux init 0.9.59 (v159)
pidof cnss-daemon -> rc=1
/proc/net/dev -> no wlan* interface, ncm0 present
/cache/bin/a90_android_execns_probe sha256 -> 1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750
```

A fresh v257 approval packet was generated:

```text
out_dir: tmp/wifi/v257-cnss-live-approval-packet
decision: live-approval-packet-ready
pass: True
checks: 9/9
```

## Live Execution

Command:

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py \
  --out-dir tmp/wifi/v257-cnss-live-start-only-run \
  --max-runtime-sec 10 \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Runner result:

```text
decision: start-only-pass
pass: True
reason: observed-until-timeout-clean-stop
runner-exit=0
```

Trusted helper markers:

```text
A90_EXECNS_BEGIN version="a90_android_execns_probe v10"
allow_cnss_start_only=1
cnss_start.begin=1
cnss_start.argv=/vendor/bin/cnss-daemon -n -l
cnss_start.cnss_diag=0
cnss_start.scan_connect_linkup=0
cnss_start.exec_attempted=1
cnss_start.child_started=1
cnss_start.pid=5965
cnss_start.pgid=5965
cnss_start.observable=1
cnss_start.term_sent=1
cnss_start.kill_sent=1
cnss_start.reaped=1
cnss_start.postflight_safe=1
cnss_start.result=start-only-pass
cnss_start.reason=observed-until-timeout-clean-stop
cnss_start.end=1
A90_EXECNS_END rc=0
```

Interpretation:

- `cnss-daemon` was observable during the 10 second start-only window.
- The V256 pgid cleanup fix was effective: child `pid` and `pgid` matched, cleanup reaped the daemon, and no orphan remained.
- The helper used `SIGTERM` followed by `SIGKILL`; final signal `9` is expected for bounded cleanup when the daemon stays alive until the observation timeout.

## Postflight

```text
pidof cnss-daemon -> rc=1
/proc/net/dev -> no wlan* interface, ncm0 present
status -> rc=0, selftest fail=0, netservice disabled, storage SD healthy
wifiinv full -> wlan_like=0, rfkill_wifi=0, no wlan-like interface
```

Evidence files:

- `tmp/wifi/v257-cnss-live-approval-packet/manifest.json`
- `tmp/wifi/v257-cnss-live-start-only-run/manifest.json`
- `tmp/wifi/v257-cnss-live-start-only-run/commands/cnss-start-only-run.txt`
- `tmp/wifi/v257-live-post-pidof.txt`
- `tmp/wifi/v257-live-post-proc-net-dev.txt`
- `tmp/wifi/v257-live-post-status.txt`
- `tmp/wifi/v257-live-post-wifiinv-full.txt`
- `tmp/wifi/v257-live-post-selftest.txt`

## Decision

- V257 proves the v10 start-only runner can start, observe, stop, and reap `cnss-daemon` without leaving a daemon or creating a `wlan*` interface.
- This does not mean Wi-Fi is ready for scan/connect/link-up.
- Next work should analyze the captured CNSS runtime evidence and decide whether the next blocker is property/socket/device-node/QRTR/firmware interaction before any broader Wi-Fi operation.
