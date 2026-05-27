# Native Init V1119 PM Register Failure Host Classifier Plan

Date: `2026-05-27`

## Goal

Classify the V1118 CNSS `pm_client_register` `0xffffffff` return without
running another live Wi-Fi gate.

## Context

V1071-era `pm-service` exit tracing has already been superseded by later gates.
V1083 narrowed that path to `libmdmdetect::get_system_info()`, and V1118 moved
the active blocker to CNSS PM client registration:

- `pm_client_register_entry=1`
- `pm_client_register_ret=['0xffffffff']`
- `pm_client_connect_entry=0`
- `pm_server_register_entry=0`

## Inputs

- V1118 manifest:
  `tmp/wifi/v1118-global-holder-zero-delay-cnss-live/manifest.json`
- Vendor PM client library:
  `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libperipheral_client.so`

## Work

1. Parse V1118 tracefs counts, CNSS register args, PM contract, and provider
   state.
2. Disassemble `pm_client_register` and `pm_register_connect` from
   `libperipheral_client.so`.
3. Confirm whether `pm_client_register` fails through argument validation,
   `pm_register_connect`, server-side reject, or post-connect path.
4. Emit V1120 live trace candidates for the exact internal branch if host-only
   evidence cannot prove the final branch.

## Safety

- Host-only.
- No device command.
- No tracefs write.
- No daemon start.
- No Wi-Fi HAL, scan/connect, DHCP, route, credential use, or external ping.
- No partition write, flash, or reboot.

## Success Criteria

- V1118 input decision is current.
- CNSS args are valid `peripheral=modem`, `client=cnss-daemon`.
- Failure is classified as pre-server, server-side, or inconclusive with a
  bounded next trace plan.
