# v361 Plan: CNSS Start-Only Approval Packet Refresh

- date: `2026-05-19`
- scope: generate a no-start approval packet for the next bounded CNSS start-only run
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisites: V320 live property lookup PASS, V360 no-start runner refresh PASS

## Summary

V361 refreshes the CNSS start-only approval packet after V320/V360. The packet
must prove that the proposed live command is bounded, uses the v11 helper/profile,
and still fails closed without the explicit helper allow flag.

This step does not execute the daemon. It only prepares a concrete future command
for a separately approved start-only run.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_live_approval_packet.py
python3 scripts/revalidation/wifi_cnss_live_approval_packet.py \
  --out-dir tmp/wifi/v361-cnss-live-approval-packet-v11-after-v320 \
  --live-out-dir tmp/wifi/v361-cnss-live-start-only-run-v11-after-v320 \
  --max-runtime-sec 10
git diff --check
```

Expected result:

- decision: `live-approval-packet-ready`
- pass: `true`
- `daemon_start_executed=false`
- helper no-allow check reports `start-only-blocked` with `exec_attempted=false`

## Approval Boundary

The packet may generate, but must not run, this future command:

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py \
  --out-dir tmp/wifi/v361-cnss-live-start-only-run-v11-after-v320 \
  --max-runtime-sec 10 \
  run \
  --allow-daemon-start \
  --assume-yes \
  --i-understand-reboot-only-recovery
```

Running that command starts a bounded CNSS daemon attempt. It requires a separate
explicit operator instruction. V361 itself does not grant that execution.

## Non-Goals

- Do not run `wifi_cnss_start_only_runner.py run`.
- Do not start Wi-Fi scan/connect/link-up, supplicant, wificond, hostapd, or Wi-Fi HAL.
- Do not run `cnss_diag`.
- Do not write rfkill, ICNSS bind/unbind, firmware paths, partitions, or Android properties.
- Do not treat start-only PASS as Wi-Fi bring-up approval.
