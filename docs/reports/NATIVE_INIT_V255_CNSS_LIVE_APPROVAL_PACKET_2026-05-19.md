# Native Init V255 CNSS Live Approval Packet Report

## Summary

- Status: PASS
- Decision: `live-approval-packet-ready`
- Scope: no-start live approval packet
- Device build: `A90 Linux init 0.9.59 (v159)`
- Daemon start: not executed
- Output: `tmp/wifi/v255-cnss-live-approval-packet/`

## Implemented

- Added `scripts/revalidation/wifi_cnss_live_approval_packet.py`.
- Added plan document `docs/plans/NATIVE_INIT_V255_CNSS_LIVE_APPROVAL_PACKET_PLAN_2026-05-19.md`.
- The tool generates:
  - `manifest.json`
  - `approval-command.sh`
  - `rollback-checklist.md`
  - `summary.md`
  - command captures under `commands/`

## Generated Manual Command

The command below was generated but not executed:

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py --out-dir tmp/wifi/v255-cnss-live-start-only-run --max-runtime-sec 10 run --allow-daemon-start --assume-yes --i-understand-reboot-only-recovery
```

## Validation

Static:

- `python3 -m py_compile scripts/revalidation/wifi_cnss_live_approval_packet.py scripts/revalidation/wifi_cnss_start_only_runner.py`: PASS
- `git diff --check`: PASS

Real-device no-start:

```bash
python3 scripts/revalidation/wifi_cnss_live_approval_packet.py --out-dir tmp/wifi/v255-cnss-live-approval-packet
```

Result:

```text
decision: live-approval-packet-ready
pass: True
```

## Gate Results

| gate | result |
| --- | --- |
| prerequisites-match | PASS |
| runtime-materialization-profile | PASS |
| approved-helper-argv-has-required-profile | PASS |
| approved-helper-argv-denied-patterns | PASS |
| pidof-cnss-daemon-before | PASS |
| no-wlan-interface-before | PASS |
| helper-noallow-fail-closed | PASS |
| pidof-cnss-daemon-after-noallow | PASS |
| real-data-wifi-state-unchanged | PASS |

Key no-allow evidence:

```text
helper_result=start-only-blocked
exec_attempted=false
postflight_safe=true
helper_reason=missing-allow-cnss-start-only
```

Post-check:

```text
pidof cnss-daemon rc=1
real /data/vendor/wifi before rc=-2
real /data/vendor/wifi after rc=-2
```

## Interpretation

- The proposed first live start-only command is now explicit and reproducible.
- The future approved helper argv contains:
  - `--null-device-mode dev-null-selinux`
  - `--data-wifi-mode private-empty`
  - `--allow-cnss-start-only`
- The no-approval helper path still fails closed and does not attempt daemon exec.
- The real Android `/data/vendor/wifi` path remains unchanged.
- There is still no authorization to execute the live command until the operator explicitly approves it.

## Next

The next step is an explicit approval decision:

- approve and run the generated bounded start-only command, or
- stop here and perform another no-start review.

Still blocked without explicit approval:

- Wi-Fi scan/connect/link-up/credential/DHCP/routing
- `cnss_diag`
- rfkill unblock
- ICNSS bind/unbind
- firmware mutation
- persistent Android partition writes
- automatic reboot
