# Native Init V257 CNSS V10 Live Retry Plan

## Summary

- V257 is a one-shot bounded live retry of the CNSS start-only runner after the V256 cleanup race fix.
- Device build remains `A90 Linux init 0.9.59 (v159)`; no native init boot image or helper source change is planned.
- The only live action is `/vendor/bin/cnss-daemon -n -l` through `a90_android_execns_probe v10` with a 10 second observe window.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain out of scope.

## Preconditions

- Operator explicitly approves exactly one bounded live retry after reviewing V256.
- `/cache/bin/a90_android_execns_probe` must match SHA-256 `1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750`.
- `pidof cnss-daemon` must be absent before the run.
- `/proc/net/dev` must have no `wlan*` interface before the run.
- V257 live approval packet must pass all no-start gates.

## Command

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py \
  --out-dir tmp/wifi/v257-cnss-live-start-only-run \
  --max-runtime-sec 10 \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

## Guardrails

- Execute the live command once only.
- Do not run `cnss_diag`.
- Do not run rfkill unblock.
- Do not bind/unbind ICNSS.
- Do not start Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- Do not mutate firmware path or Android partitions.
- Do not automatically reboot.

## Validation

- Preflight:
  - `version`
  - `run /cache/bin/toybox pidof cnss-daemon`
  - `cat /proc/net/dev`
  - helper SHA check
  - `wifi_cnss_live_approval_packet.py` with v257 output paths
- Live result:
  - runner decision must be `start-only-pass`, or otherwise preserve evidence and stop.
  - trusted `cnss_start.begin=1` and `cnss_start.end=1` markers must be present.
  - cleanup must prove `postflight_safe=1` and `reaped=1`.
- Postflight:
  - `pidof cnss-daemon` absent
  - `/proc/net/dev` has no `wlan*`
  - `status` remains healthy
  - `wifiinv full` confirms no wlan-like interface
  - `selftest verbose` remains acceptable

## Acceptance

- `cnss-daemon` was started only inside the bounded start-only runner.
- Runner returns `pass=True` and decision `start-only-pass`.
- No daemon remains after cleanup.
- No `wlan*` interface appears.
- NCM/bridge control remains usable.
- Next work can move from cleanup correctness to interpreting captured CNSS runtime evidence.
