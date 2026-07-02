# Native Init V3368 Hot-Reload Autohud H5 Live

- Cycle: `V3368`
- Candidate: `A90 Linux init 0.11.129 (v3368-hot-reload-autohud)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3368_hot_reload_autohud.img`
- Candidate boot SHA256: `3f16c77cd6bf43e47bfd4767bf212da1981dda2e3d585d7f68678894a549c888`
- Candidate init SHA256: `1b17a43014e407a44782f729bcebbffabe4b3beaacc988a83d9c88c0789f3b8a`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Result: `PASS`

## Gate

- Rollback boot image `v2321` existed and matched SHA256
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback images `v2237` and `v48` existed before live work.
- TWRP recovery artifacts existed before live work.
- Baseline device state was clean `v2321`: `BOOT OK`, `selftest fail=0`, SD runtime/storage,
  serial ready, and tcpctl reachable over the USB-local transport.

## Attempt 1

- Flashed the first V3368 H5 candidate through `native_init_flash.py`.
  - Boot SHA256: `c8bd3eab12eaa17502ac187053353c50e1a0a35d86492b15932d66969f56948c`
  - Init SHA256: `9fada3f0ef22d88cdc6f2f606fa0d7f5ac99d40440fc0b6e13f849419ea7efa3`
- Reload adopted autohud, refreshed tcpctl, and started rshell, but post-reload selftest failed:
  `kms not initialized`.
- Root cause: the reloaded PID1 correctly did not re-own KMS, because the preserved HUD child owns
  the display path. The selftest still required the new PID1's local `a90_kms` state to be initialized.
- Recovered immediately to clean `v2321` before any new experimental flash. Rollback health:
  `BOOT OK`, `selftest fail=0`.

## Final Live Sequence

1. Flashed fixed V3368 through `native_init_flash.py`.
   - Local, pushed, and readback SHA256 matched
     `3f16c77cd6bf43e47bfd4767bf212da1981dda2e3d585d7f68678894a549c888`.
   - Post-flash verify passed: `0.11.129 (v3368-hot-reload-autohud)`, `BOOT OK`,
     `selftest fail=0`.

2. Prepared rshell for a clean restart proof.
   - `rshell stop` left `enabled=yes running=no`, so the hot-reloaded init had to start it from the
     persistent opt-in flag without colliding with an inherited listener.

3. Staged the fixed V3368 init ELF under the SD flash-staging root using tcpctl upload.
   - Device-side SHA256 matched
     `1b17a43014e407a44782f729bcebbffabe4b3beaacc988a83d9c88c0789f3b8a`.

4. Ran `reload INIT-RELOAD-EXECVE <staged-init> <sha>`.
   - Expected serial END marker absence occurred because PID1 executed the new image.
   - Reload transcript included:
     - `reload: preserving autohud for DRM-master handoff`
     - `Hot-reload: autohud adopted`
     - `Hot-reload: tcpctl ready`
     - `Hot-reload: rshell ready`
     - `Hot-reload: selftest/guard refreshed: pass=12 warn=0 fail=0`

5. Post-reload validation passed.
   - `version`: `0.11.129 build=v3368-hot-reload-autohud`
   - `status`: `BOOT OK`, SD runtime/storage retained, `display: adopted-autohud`,
     `autohud=running`, `tcpctl=running`, `transport.tcpctl=ready`, `rshell=running`
   - `selftest verbose`: `pass=12 warn=1 fail=0`
   - `selftest:kms`: `kms adopted by autohud`
   - `pid1guard verbose`: `pass=12 warn=0 fail=0`
   - Host tcpctl `ping`: `pong`

## Cleanup And Rollback

- Removed the staged H5 init file from SD flash-staging.
- Disabled the temporary rshell opt-in flag used for the restart proof.
- Rolled back to `v2321` through `native_init_flash.py`.
  - Readback SHA matched
    `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Final device state:
  - `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
  - `status`: `BOOT OK`, SD runtime/storage, serial ready, tcpctl ready, rshell stopped
  - `selftest`: `pass=11 warn=1 fail=0`
  - Host tcpctl `ping`: `pong`

## Conclusion

H5 is live-proven. PID1 hot-reload now preserves the already-lit display path by keeping the HUD child
alive, adopting its pidfile in the reloaded init, refreshing tcpctl, restarting rshell from the opt-in
flag, and refreshing selftest/pid1guard after service adoption. No panel re-init, SETCRTC retry,
backlight, PMIC, regulator, GDSC, or GPIO power write was used. The device was returned to clean
`v2321`.
