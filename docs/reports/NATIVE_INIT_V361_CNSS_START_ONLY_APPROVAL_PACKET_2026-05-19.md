# v361 Report: CNSS Start-Only Approval Packet Refresh

- date: `2026-05-19`
- scope: no-start approval packet for future bounded CNSS start-only run
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V361_CNSS_START_ONLY_APPROVAL_PACKET_PLAN_2026-05-19.md`
- result: `PASS`

## Summary

V361 generated a refreshed CNSS start-only approval packet using the v11 helper
state established by V320/V360. The packet passed all no-start gates and produced
a concrete future live command. That future command was not executed.

## Evidence

| item | path | result |
| --- | --- | --- |
| approval packet | `tmp/wifi/v361-cnss-live-approval-packet-v11-after-v320/` | `live-approval-packet-ready` |
| future live output path | `tmp/wifi/v361-cnss-live-start-only-run-v11-after-v320/` | not executed |

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_live_approval_packet.py
python3 scripts/revalidation/wifi_cnss_live_approval_packet.py \
  --out-dir tmp/wifi/v361-cnss-live-approval-packet-v11-after-v320 \
  --live-out-dir tmp/wifi/v361-cnss-live-start-only-run-v11-after-v320 \
  --max-runtime-sec 10
git diff --check
```

Observed output:

```text
decision: live-approval-packet-ready
pass: True
```

Key checks:

| check | status |
| --- | --- |
| prerequisites match | PASS |
| runtime materialization profile | PASS |
| approved helper argv has required profile | PASS |
| approved helper argv denied patterns | PASS |
| `pidof cnss-daemon` before | PASS |
| no `wlan*` interface before | PASS |
| helper no-allow fail-closed | PASS |
| `pidof cnss-daemon` after no-allow | PASS |
| real `/data/vendor/wifi` state unchanged | PASS |

No-start proof:

```text
daemon_start_executed=false
helper_result=start-only-blocked
exec_attempted=false
postflight_safe=true
```

## Future Command Generated But Not Executed

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py \
  --out-dir tmp/wifi/v361-cnss-live-start-only-run-v11-after-v320 \
  --max-runtime-sec 10 \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

This command is a daemon start-only attempt. It remains blocked until a separate
explicit operator instruction is given for that exact boundary. It does not imply
Wi-Fi scan/connect/link-up approval.

## Decision

- decision: `cnss-start-only-approval-packet-ready`
- current status: ready for an explicit bounded start-only decision
- blocked actions: Wi-Fi scan/connect/link-up, credentials, DHCP, routing,
  rfkill writes, ICNSS bind/unbind, firmware mutation, Android property writes,
  and broader Wi-Fi bring-up.
