# v324 Report: Private Property Live Approval Refresh

- date: `2026-05-19`
- scope: refreshed host-only approval packet for v317 live proof
- boot image change: none
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- result: `private-property-approval-refresh-ready`

## Summary

v324 adds `scripts/revalidation/wifi_private_property_approval_refresh.py` and
generates a refreshed approval packet that includes the post-v319 transfer path
and post-v323 gate audit result.

No device command was executed. The packet is ready, but live execution remains
not approved.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_approval_refresh.py
python3 scripts/revalidation/wifi_private_property_approval_refresh.py \
  --out-dir tmp/wifi/v324-private-property-approval-refresh \
  run
git diff --check
```

Result:

```text
decision: private-property-approval-refresh-ready
pass: True
live_execution_approved: False
device_commands_executed: False
device_mutations: False
```

## Transfer Estimate

| field | value |
| --- | --- |
| files | 5 |
| bytes | 524988 |
| chunk_size | 1536 |
| chunks | 471 |
| estimated_commands | 505 |
| max_script_chars | 3294 |
| status | pass |

## Required Exact Approval Phrase

```text
approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up
```

## Explicitly Not Approved

- Global `/dev/__properties__` replacement or bind mount.
- Global `/dev/socket/property_service` creation.
- Property mutation or `setprop`-like writes.
- service-manager, hwservicemanager, Wi-Fi HAL, `wificond`, `supplicant`,
  `hostapd`, CNSS, or diag daemon start.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- rfkill write, module load/unload, firmware mutation, or partition write.
- NCM/tcpctl transfer for this v317 proof.

## Evidence

- manifest: `tmp/wifi/v324-private-property-approval-refresh/manifest.json`
- approval packet: `tmp/wifi/v324-private-property-approval-refresh/approval-packet.md`

## Decision

- decision: `private-property-approval-refresh-ready`
- live execution approved: `false`
- next step: if the operator accepts the boundary, provide the exact v317 phrase;
  otherwise continue with read-only Wi-Fi/kernel inventory work.
