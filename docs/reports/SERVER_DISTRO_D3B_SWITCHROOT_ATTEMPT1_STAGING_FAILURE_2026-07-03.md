# Server-Distro D3B Switchroot Attempt 1 Staging Failure

- Date: `2026-07-03`
- Scope: D3B live checked `switch_root` handoff attempt
- Candidate: `A90 Linux init 0.11.130 (v3369-server-distro-switchroot)`
- Candidate boot SHA256: `13fa09320a42d98af7cc2712347dba0c35283af0085b7f87c12f81691f737505`
- Rollback target: `v2321-usb-clean-identity-rodata`
- Result: `FAIL-RECOVERED`

## Gate

- Rollback images `v2321`, `v2237`, and `v48` existed before live work.
- TWRP recovery artifacts existed before live work.
- Baseline device state was clean `v2321`, `BOOT OK`, `selftest fail=0`, SD runtime/storage ready.
- V3369 candidate was flashed only through `native_init_flash.py`.

## Live Attempt

- Candidate flash passed.
  - Local, pushed, and readback SHA256 matched the V3369 candidate SHA.
  - Post-flash native-init verify passed with `selftest fail=0`.
  - Candidate `version` reported `0.11.130 build=v3369-server-distro-switchroot`.
- D3 keyed rootfs image preparation passed on the host.
  - The per-run SSH public key was injected into the private keyed copy.
- Staging the 2 GiB keyed image to SD failed before `switch_root`.
  - The host attempted to connect to the temporary device receive port immediately after launching
    `run ... netcat -l ... dd ...`.
  - The connection was refused.
  - The foreground native-init `run` remained active, so the first automatic rollback attempt could not
    enter recovery until the foreground run was cancelled.

## Recovery

- Sent the documented foreground-run cancel key `q`.
  - Device printed `run: cancelled by q`.
  - The native-init prompt returned.
- Re-ran checked rollback to `v2321` through `native_init_flash.py`.
  - Rollback write/readback SHA matched
    `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
  - Final `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`.
  - Final `selftest`: `pass=11 warn=1 fail=0`.

## Root Cause

D3B runner set `--transfer-delay` default to `0.0`, unlike the D1/D2 staging runners which wait `2.0s`
for the temporary `netcat` receiver to start. The host raced the listener and got `Connection refused`.
The failure path also tried rollback while the foreground receiver was still active, so rollback was
blocked until the run was manually cancelled.

## Fix

- Set D3B runner `DEFAULT_TRANSFER_DELAY=2.0`.
- Track staging start/completion.
- If staging fails before `switch_root`, send best-effort raw `q` and record
  `cancel_foreground_run_after_stage_error` before attempting rollback.

No `switch_root` was executed in this attempt. No userdata format/mount/write was performed. No forbidden
partition was touched. No public tunnel was exposed.
