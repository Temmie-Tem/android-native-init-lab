# Native Init V1768 WLAN-PD PM Server Branch Classifier

## Summary

- Cycle: `V1768`
- Type: host-only PM server branch classifier
- Decision: `v1768-pm-server-register-entry-only-before-match-host-pass`
- Label: `pm-server-register-entry-only-before-match`
- Result: PASS
- Reason: cnss-daemon reaches pm-service register entry but no supported-peripheral match, permission, state, add-client, or return checkpoint
- Evidence: `tmp/wifi/v1768-wlan-pd-pm-server-branch-classifier`

## Inputs

- V1101 tracefs live manifest: `tmp/wifi/v1101-pm-server-register-path-tracefs-live/manifest.json`
- V1101 tracefs report: `docs/reports/NATIVE_INIT_V1101_PM_SERVER_REGISTER_PATH_TRACEFS_2026-05-27.md`
- V1766 request-trigger classifier: `tmp/wifi/v1766-wlan-pd-request-trigger-directive-classifier/manifest.json`
- V1767 PM contract extraction: `tmp/wifi/v1767-wlan-pd-pm-contract-extraction/manifest.json`

## Facts

- V1766 request-trigger gap live-suspended: `True`
- V1767 PM contract extracted: `True`
- V1101 tracefs result: `True`
- Corrected CNSS client args documented: `True`
- CNSS server register comms: `['Binder:2193_3']`
- CNSS entry / match / return counts: `1` / `0` / `0`
- CNSS absent after entry: `True`
- Positive-control comm: `Binder:2193_2`
- Positive-control sequence complete: `True`
- Positive-control register/connect return: `['0x0']` / `['0x0']`
- CNSS client register return: `[]`

## Server Branch Boundary

| checkpoint | offset | positive control | cnss-daemon |
| --- | --- | ---: | ---: |
| entry | `0x6048` | `1` | `1` |
| supported-peripheral match | `0x60cc` | `1` | `0` |
| permission ok | `0x60e8` | `1` | `0` |
| state read | `0x6110` | `1` | `0` |
| add-client call | `0x611c` | `1` | `0` |
| success return | `0x6140` | `1` | `0` |
| function return | `entry retprobe` | `1` | `0` |

## Interpretation

- The positive-control `pm-proxy` path proves the provider, Binder service, and traced register implementation can complete in this boot/runtime shape.
- The CNSS path reaches the same `pm-service` register implementation entry but stops before `0x60cc`, the first retained supported-peripheral match checkpoint.
- This keeps the active request gap before PM register/vote success and before any `wlanmdsp.mbn` firmware request.
- The next aligned work, while live PM gates remain suspended, is host/source-only disassembly of `pm-service+0x6048..0x60cc`.

## Host-only Next Targets

- String argument access/conversion between entry and `0x60cc`.
- Supported peripheral list iteration and comparison setup.
- Early Binder caller/process/context checks before the permission checkpoint.
- Any blocking call or mutex taken only by the CNSS Binder server thread before `0x60cc`.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD load, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.

## Next

- Continue with host/source-only `pm-service` branch disassembly before `0x60cc`.
- Do not deploy/live-run a service-object or PM actor helper unless a new directive explicitly reopens that narrow gate.
- Completion remains unproven: native Wi-Fi has not reached WLFW service 69, `wlan0`, scan/connect, or external ping.
