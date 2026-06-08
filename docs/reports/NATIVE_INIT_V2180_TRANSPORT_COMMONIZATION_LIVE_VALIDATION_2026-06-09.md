# Native Init V2180 Transport Commonization Live Validation

Date: `2026-06-09`

## Summary

- Run ID: `V2180`
- Baseline under test: `A90 Linux init 0.9.253 (v2178-wifi-profile-autoconnect)`
- Decision: `v2180-transport-commonization-live-validation-pass`
- Scope: host/live validation of shared phase timers and serial recovery
  evidence plumbing.
- Flash: `0`
- Boot autoconnect enable: `0`
- External ping: `0`
- Credential values logged in public report: `0`
- Final device state: V2178 baseline, autoconnect disabled, `selftest fail=0`

## Transport-Only Validation

Runner:
`workspace/public/src/scripts/revalidation/a90_ncm_transport_smoke.py`

Command scope:

- 1 MiB host-to-device NCM transfer.
- 1 MiB device-to-host NCM upload.
- Remote cleanup.
- No Wi-Fi scan/connect/DHCP/ping.

Private artifact:

- `tmp/wifi/bench/a90-ncm-transport-smoke-v2180-phase-transport-final-20260609-073949/`

Result:

| Field | Value |
| --- | --- |
| Pass | `true` |
| Transport selected | `ncm` |
| Download OK | `true` |
| Upload OK | `true` |
| `phase_timer_contract` | `1` |

Observed phases:

| Phase | Elapsed Sec | OK |
| --- | ---: | --- |
| `preflight` | `1.359` | `true` |
| `helper_stage` | `2.115` | `true` |
| `selftest` | `0.443` | `true` |
| `artifact_upload` | `0.0` | `true` |

Serial recovery:

- No `AT`/protocol-noise recovery fired during this run.
- No unsafe retry was exercised.

## Wi-Fi Current-Baseline Validation

Runner:
`workspace/public/src/scripts/revalidation/native_wifi_v2178_autoconnect_phase_validation.py`

Command scope:

- Read current V2178 version/status.
- Use the already-staged default private Wi-Fi profile without printing its
  name in this report.
- Run one bounded `wifi autoconnect once <profile>`.
- Run `wifi cleanup`.
- Restore `wifi autoconnect disable`.
- Run final `wifi status` and `selftest`.
- No flash, boot-autoconnect enable, or external ping.

Private artifact:

- `tmp/wifi/runs/v2180-v2178-wifi-autoconnect-phase-validation-v2180-phase-wifi-final2-20260609-073953/`

Result:

| Field | Value |
| --- | --- |
| Pass | `true` |
| Decision | `v2180-wifi-phase-validation-pass` |
| Transport selected | `ncm` |
| Connect decision | `wifi-autoconnect-pass` |
| Cleanup decision | `wifi-cleanup-done` |
| Disable restore | `wifi-autoconnect-disabled` |
| Final selftest | `fail=0` |
| `phase_timer_contract` | `1` |

Observed phases:

| Phase | Elapsed Sec | OK |
| --- | ---: | --- |
| `preflight` | `2.194` | `true` |
| `connect_window` | `5.915` | `true` |
| `selftest` | `0.421` | `true` |
| `cleanup` | `0.955` | `true` |
| `selftest_final` | `0.836` | `true` |
| `artifact_upload` | `0.0` | `true` |

Serial recovery:

- No `AT`/protocol-noise recovery fired during this run.
- The shared recovery path remains implemented and ready, but live-fired
  evidence is still opportunistic.

## Final Device State

After validation:

- Version: `A90 Linux init 0.9.253 (v2178-wifi-profile-autoconnect)`.
- `wifi autoconnect status`: `autoconnect=0`,
  `decision=wifi-autoconnect-disabled`.
- `wifi status`: `autoconnect.decision=wifi-autoconnect-disabled`,
  `supplicant.process_count=0`.
- Selftest: `pass=11 warn=1 fail=0`.

## Notes

- A first control attempt invoked `wifi autoconnect once` without an explicit
  profile and correctly returned `wifi-autoconnect-disabled`; the final runner
  now reads the device default profile and invokes `once <profile>` while
  keeping the profile name private.
- The phase timer implementation now has live evidence in both a transport-only
  runner and a current-baseline Wi-Fi runner.
- The dominant live windows in this bounded run were NCM transfer
  `helper_stage` and Wi-Fi `connect_window`; this run did not reproduce the
  multi-minute boot-autoconnect latency path because it intentionally avoided
  flashing/rebooting.
