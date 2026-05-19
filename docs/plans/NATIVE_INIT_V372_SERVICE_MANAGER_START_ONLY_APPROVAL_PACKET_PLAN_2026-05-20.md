# v372 Plan: Service-Manager Start-Only Approval Packet

- date: `2026-05-20`
- scope: approval packet for a future bounded service-manager start-only smoke
- boot image change: none
- native baseline: `A90 Linux init 0.9.61 (v319)`
- prerequisite: V371 runtime repair smoke live executor PASS

## Summary

V371 proved that the temporary runtime repair surface can be created, used for a
private property lookup, cleaned, and postflight-checked. V372 does not start any
daemon. It only generates the next approval packet for a future V373
service-manager start-only runner.

The future V373 scope is narrower than Wi-Fi bring-up. It may only recreate the
runtime nodes needed by the runner, start bounded service-manager candidates,
observe briefly, terminate/reap, and clean up. Wi-Fi HAL, `wificond`, supplicant,
hostapd, CNSS daemons, scan/connect/link-up, credentials, DHCP, and routing stay
blocked.

## Implementation

Add:

```text
scripts/revalidation/wifi_service_manager_start_only_approval_packet.py
```

Modes:

```bash
python3 scripts/revalidation/wifi_service_manager_start_only_approval_packet.py \
  --out-dir tmp/wifi/v372-service-manager-start-only-approval-packet-plan-20260520-013401 \
  plan

python3 scripts/revalidation/wifi_service_manager_start_only_approval_packet.py \
  --out-dir tmp/wifi/v372-service-manager-start-only-approval-packet-live-20260520-013344 \
  run
```

## Read-Only Live Checks

- V371 manifest decision is `runtime-repair-smoke-live-executor-run-pass`.
- V371 router decision is `runtime-repair-smoke-router-service-runtime-next-ready`.
- V366 manifest decision is `runtime-repair-smoke-pass`.
- Current `status` and `selftest` are clean with `fail=0`.
- `servicemanager` and `hwservicemanager` binaries are visible.
- No current service-manager process exists.
- No `wlan*`/`p2p*` link surface exists.
- Temporary Binder nodes from V366 are absent after cleanup.

## Required Future Approval Phrase

```text
approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_service_manager_start_only_approval_packet.py

git diff --check
```

Expected decisions:

```text
plan: service-manager-start-only-approval-packet-plan-ready
run: service-manager-start-only-approval-packet-ready
```

## Acceptance

- V372 writes an approval packet with `live_execution_approved=false` and
  `device_mutations=false`.
- V372 may execute only read-only `cmdv1` captures.
- V372 records the future V373 approval phrase and explicitly excludes Wi-Fi HAL
  start and Wi-Fi bring-up.
- V372 does not create nodes, start daemons, change rfkill, or alter Android
  partitions.
