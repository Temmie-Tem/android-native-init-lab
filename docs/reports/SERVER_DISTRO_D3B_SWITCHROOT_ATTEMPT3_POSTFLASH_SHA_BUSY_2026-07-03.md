# Server-Distro D3B Switchroot Attempt 3 Post-Flash SHA Busy

- Date: `2026-07-03`
- Scope: D3B live checked `switch_root` handoff attempt with SD pre-stage
- Candidate: `A90 Linux init 0.11.130 (v3369-server-distro-switchroot)`
- Candidate boot SHA256: `13fa09320a42d98af7cc2712347dba0c35283af0085b7f87c12f81691f737505`
- Rollback target: `v2321-usb-clean-identity-rodata`
- Result: `FAIL-RECOVERED`

## Live Attempt

- Keyed D3 sysvinit image was installed on SD before the candidate flash.
  - Transfer completed: `2147483648 bytes`, about `30 MB/s`.
  - Pre-flash SD SHA matched the keyed image SHA.
- Candidate flash passed.
  - Local, pushed, and readback SHA256 matched the V3369 candidate SHA.
  - Post-flash native-init verify passed with `selftest fail=0`.
- The first post-flash SD SHA recheck returned `busy` because the candidate auto menu was active.
- The runner treated the missing SHA as mismatch and rolled back before `switch_root`.

## Recovery

- Checked rollback to `v2321` through `native_init_flash.py` passed.
- Final after-error checks recorded:
  - `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
  - `selftest`: `pass=11 warn=1 fail=0`

## Follow-Up Fix

The runner now wraps post-flash remote-image SHA verification in a bounded hide/retry helper. If the
candidate reports the auto menu as busy, the runner sends `hide`, waits briefly, and retries the SHA read
before deciding the image is missing or mismatched.

No `switch_root` was executed in this attempt. No userdata format/mount/write was performed. No forbidden
partition was touched. No public tunnel was exposed.
