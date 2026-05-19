# v369 Plan: Runtime Repair Smoke Approval Packet

- date: `2026-05-20`
- scope: approval packet for future V366 bounded runtime repair smoke
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisite: V368 cleanup approval gate

## Summary

V366/V367/V368 made the runtime repair smoke runner fail-closed for `run` and
`cleanup`. V369 creates the operator approval packet for the future bounded live
smoke.

The packet does not execute the approved smoke. It runs only safe gates:

- V366 live preflight;
- V366 no-approval `run` refusal;
- V366 no-approval `cleanup` refusal;
- V367/V368 host-only synthetic regression.

It then writes `approval-command.sh`, `cleanup-command.sh`,
`rollback-checklist.md`, `approval-packet.md`, and `manifest.json` under a
private evidence directory.

## Implementation

Add:

```text
scripts/revalidation/wifi_runtime_repair_smoke_approval_packet.py
```

The generated approved run command is:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke.py --out-dir tmp/wifi/v366-runtime-repair-smoke-live-approved --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' --apply --assume-yes run
```

The generated approved cleanup command is:

```bash
python3 scripts/revalidation/wifi_runtime_repair_smoke.py --out-dir tmp/wifi/v366-runtime-repair-smoke-cleanup-approved --approval-phrase 'approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up' --apply --assume-yes cleanup
```

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_runtime_repair_smoke_approval_packet.py \
  scripts/revalidation/wifi_runtime_repair_smoke.py \
  scripts/revalidation/wifi_runtime_repair_smoke_regression.py

python3 scripts/revalidation/wifi_runtime_repair_smoke_approval_packet.py \
  --out-dir tmp/wifi/v369-runtime-repair-smoke-approval-packet-final-20260520-011223 \
  run

bash -n tmp/wifi/v369-runtime-repair-smoke-approval-packet-final-20260520-011223/approval-command.sh
bash -n tmp/wifi/v369-runtime-repair-smoke-approval-packet-final-20260520-011223/cleanup-command.sh

git diff --check
```

Expected decision:

```text
runtime-repair-smoke-approval-packet-ready
```

## Acceptance

- Approval packet is ready and records `live_execution_approved=false`.
- Packet safe gates all pass.
- Generated command contracts include the exact phrase plus `--apply` and
  `--assume-yes`.
- `cleanup` command is also exact-approval gated.
- No service-manager/HAL/scan/connect execution occurs.
