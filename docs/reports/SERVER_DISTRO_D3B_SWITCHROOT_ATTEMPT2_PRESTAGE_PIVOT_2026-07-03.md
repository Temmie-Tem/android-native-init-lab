# Server-Distro D3B Switchroot Attempt 2 Prestage Pivot

- Date: `2026-07-03`
- Scope: D3B live checked `switch_root` handoff attempt
- Candidate: `A90 Linux init 0.11.130 (v3369-server-distro-switchroot)`
- Candidate boot SHA256: `13fa09320a42d98af7cc2712347dba0c35283af0085b7f87c12f81691f737505`
- Rollback target: `v2321-usb-clean-identity-rodata`
- Result: `ABORTED-BY-DESIGN-PIVOT-RECOVERED`

## Gate

- Baseline before attempt was clean `v2321`, `selftest fail=0`.
- Rollback images and TWRP recovery artifacts were present.
- V3369 candidate was flashed only through `native_init_flash.py`.

## Live Attempt

- Candidate flash passed.
  - Local, pushed, and readback SHA256 matched the V3369 candidate SHA.
  - Post-flash native-init verify passed with `selftest fail=0`.
- The runner reached the SD image staging phase.
- Operator steered the design to pre-stage the D3 image on SD before the candidate flash.
- The in-flight staging subprocess was stopped intentionally before any `switch_root` command was sent.

## Recovery

- Runner entered the failure path and performed checked rollback to `v2321`.
- Final after-error checks recorded:
  - `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
  - `selftest`: `pass=11 warn=1 fail=0`

## Follow-Up Fix

The runner is changed so the keyed D3 sysvinit image is installed and SHA-verified on SD while the device
is still running the clean resident. After the candidate flash, D3B only rechecks the remote SHA and then
invokes the gated `switch_root` command. This reduces candidate-resident time and avoids tying rollback
safety to a large post-flash image transfer.

No `switch_root` was executed in this attempt. No userdata format/mount/write was performed. No forbidden
partition was touched. No public tunnel was exposed.
