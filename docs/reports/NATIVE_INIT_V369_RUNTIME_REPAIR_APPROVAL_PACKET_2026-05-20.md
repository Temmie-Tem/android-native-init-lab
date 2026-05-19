# v369 Report: Runtime Repair Smoke Approval Packet

- date: `2026-05-20`
- scope: approval packet for future V366 bounded runtime repair smoke
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V369_RUNTIME_REPAIR_APPROVAL_PACKET_PLAN_2026-05-20.md`
- result: `PASS`, decision `runtime-repair-smoke-approval-packet-ready`

## Summary

V369 generates the approval packet for the next V366 live smoke. The packet does
not approve or execute the live smoke by itself. It verifies the current gates,
records the exact command contract, and preserves the rollback checklist.

## Evidence

| item | path | decision |
| --- | --- | --- |
| approval packet | `tmp/wifi/v369-runtime-repair-smoke-approval-packet-final-20260520-011223/` | `runtime-repair-smoke-approval-packet-ready` |

Packet summary:

```text
decision: runtime-repair-smoke-approval-packet-ready
pass: True
live_execution_approved: False
device_mutations: False
reason: approval packet ready; live execution is still not approved by this packet
```

## Gate Results

| gate | decision |
| --- | --- |
| preflight | `runtime-repair-smoke-preflight-ready` |
| run-refusal | `runtime-repair-smoke-approval-required` |
| cleanup-refusal | `runtime-repair-smoke-cleanup-approval-required` |
| regression | `runtime-repair-smoke-regression-pass` |

Additional checks:

- `preexisting-temp-nodes-clean`: PASS, `present=[]`
- `service-and-wifi-surface-clean`: PASS, `manager=0 cnss=0`, `wlan_surface=False`
- `cleanup-refusal-no-steps`: PASS, `steps=0`
- `approval-command-contract`: PASS
- `cleanup-command-contract`: PASS
- `bash -n approval-command.sh`: PASS
- `bash -n cleanup-command.sh`: PASS

## Generated Commands

Approved smoke command:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke.py --out-dir tmp/wifi/v366-runtime-repair-smoke-live-approved --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' --apply --assume-yes run
```

Approved cleanup command:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke.py --out-dir tmp/wifi/v366-runtime-repair-smoke-cleanup-approved --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' --apply --assume-yes cleanup
```

## Guardrails Kept

- No approved smoke was executed.
- No temporary `/dev` node was created or deleted by this packet.
- No service-manager, Wi-Fi HAL, `wificond`, supplicant, hostapd,
  `cnss-daemon`, or `cnss_diag` was started.
- No Wi-Fi scan/connect/link-up was executed.
- The real V366 live smoke remains blocked until the exact approval phrase is
  supplied and the generated command is intentionally run.
