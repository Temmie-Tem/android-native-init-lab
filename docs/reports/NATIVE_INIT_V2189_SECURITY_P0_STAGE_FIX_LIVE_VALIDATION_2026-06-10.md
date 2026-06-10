# Native Init V2189 Security P0 Stage Fix Live Validation

## Summary

- Candidate: `v2189-security-p0-stage-fix`
- Init: `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img`
- Boot SHA256: `a7332612199cfd275f2dfc6fdb25843af401a1ecef2fa54ac0f52afe705f1ffe`
- Evidence root: `workspace/private/runs/security/v2189-p0-stage-fix-flash-20260610-142549`
- Decision: `v2189-security-p0-stage-fix-live-validation-pass`
- Result: PASS

## Flash Verification

- `native_init_flash.py` enforced `--expect-sha256` before flashing.
- Recovery handoff from native init succeeded.
- ADB push completed at `84.9 MB/s`.
- Remote `/tmp/native_init_boot.img` SHA256 matched the pinned local SHA.
- Boot partition readback prefix SHA256 matched the pinned local SHA.
- Native selftest after reboot reported `fail=0`.
- Version verification matched `A90 Linux init 0.9.261 (v2189-security-p0-stage-fix)`.
- Total flash cycle time: `65.419s`.

## P0 Runtime Checks

- `selftest`: `pass=11 warn=1 fail=0`.
- `pid1guard`: `pass=12 warn=0 fail=0`.
- `/cache/a90-wifi`: `uid=0 gid=0 mode=0755`.
- `/cache/a90-wifi/sockets`: `uid=1010 gid=1010 mode=0770`.
- `/cache/a90-wifi/wpa_supplicant.conf`: `uid=0 gid=0 mode=0600` after config preparation.
- `/cache/a90-wifi/wpa-standalone`: `uid=0 gid=0 mode=0755` after fixed cache profile staging.
- `/cache/a90-wifi/wpa-standalone/wpa_supplicant-a90.sh`: `uid=0 gid=0 mode=0700` after fixed cache profile staging.
- `wifi status` reported `supplicant.root_exec_rc=0` and `supplicant.root_exec_ok=1`.

## Wi-Fi Smoke

- Boot helper summary reported `wlan0_present=1`, `baseline_ready=1`, and `supervisor_result=wlan0-ready`.
- `wifi connect <profile>` used standalone `wpa_supplicant` with `supplicant.root_exec_ok=1`; the profile label is redacted in the public report.
- Carrier reached in `2000ms`.
- WPA state reached `COMPLETED`.
- Connected frequency was `5745 MHz`; DHCP/routing/external ping were not run in this validation.
- `wifi cleanup` terminated the supplicant and completed successfully.
- Final selftest again reported `fail=0`.

## V2188 Finding Closed

- V2188 live validation correctly exposed stale staged Wi-Fi executable ownership with `supplicant.root_exec_rc=-13`.
- The first host-side shell-based stage hardener did not work because `tcpctl run` does not preserve shell quoting for `sh -c`.
- V2189 host staging now uses direct tcpctl commands for `mkdir`, `chown -R`, and `chmod -R`; the live cache-stage retest converted a deliberately reset `1000:1000` standalone bundle back to `0:0`.

## Current Device State

- The device is intentionally left running `v2189-security-p0-stage-fix` after the successful validation.
- Rollback target remains `v2187-screenapp-ui-validation` if needed.
- Credential values were not logged.
