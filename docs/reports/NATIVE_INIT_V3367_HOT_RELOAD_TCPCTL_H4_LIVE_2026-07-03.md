# Native Init V3367 Hot-Reload Tcpctl H4 Live

- Cycle: `V3367`
- Candidate: `A90 Linux init 0.11.128 (v3367-hot-reload-tcpctl)`
- Source-build commit: `bcd12808`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3367_hot_reload_tcpctl.img`
- Candidate boot SHA256: `acc721cafc2389404c4e9ce316f55ae7371339a21a47608995dd9bfe48f4abf0`
- Candidate init SHA256: `cf7dd2fa1ae986fce08813034d3aee36542d102bc7ca6f5f6802288e8d4dc38d`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Result: `PASS`

## Gate

- Rollback boot image `v2321` existed and matched SHA256
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback images `v2237` and `v48` existed and matched their expected SHA256 values.
- TWRP recovery artifacts existed and matched SHA256:
  `recovery.img=b1ef377a52ec8ab43b49a5fcc7a0b27e8efff91bf2d8cccdc565ecadadcc646c`,
  `twrp_recovery.tar=6d9e929462ea4c85f257b080431d387d5bfb787ff800bd4178c823c3874d862a`.
- Preflight device state was clean `v2321`: `BOOT OK`, `selftest fail=0`, SD runtime/storage,
  serial ready, and tcpctl ping succeeded over the USB-local transport.

## Live Sequence

1. Flashed resident `V3364` through `native_init_flash.py`.
   - Image SHA256: `934f70384b3a470461666da8603620856219fdddf25cebff3d4378df04d8c8e7`
   - Readback SHA matched.
   - Post-flash verify passed: `0.11.125 (v3364-hot-reload-fastpath)`, `BOOT OK`, `selftest fail=0`.
   - Flash helper total time: `63.460s`.

2. Staged the V3367 init ELF under the SD flash-staging root using tcpctl upload.
   - Device-side SHA256 matched `cf7dd2fa1ae986fce08813034d3aee36542d102bc7ca6f5f6802288e8d4dc38d`.

3. Ran `reload INIT-RELOAD-EXECVE <staged-init> <sha>`.
   - Expected serial END marker absence occurred because PID1 executed the new image.
   - New banner appeared immediately: `A90 Linux init 0.11.128 (v3367-hot-reload-tcpctl)`.
   - Reload transcript included the H4 marker: hot-reload skipped autohud/rshell re-init and refreshed tcpctl.

4. Post-reload validation passed.
   - `version`: `0.11.128 build=v3367-hot-reload-tcpctl`
   - `status`: `BOOT OK`, SD runtime/storage retained, `tcpctl=running`, `transport.tcpctl=ready`
   - `selftest`: `fail=0`
   - Host tcpctl `ping`: `pong`
   - Native log confirmed: existing NCM was reused, USB gadget reconfigure was skipped, and the existing tcpctl listener was adopted via `tcpctl-adopt`.

## Rollback

- Rolled back to `v2321` through `native_init_flash.py`.
  - Readback SHA matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
  - Rollback helper total time: `51.249s`.
- Removed the staged V3367 init file from SD flash-staging after rollback.
- Final device state:
  - `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
  - `status`: `BOOT OK`, SD runtime/storage, serial ready, tcpctl ready
  - `selftest`: `fail=0`
  - Host tcpctl `ping`: `pong`

## Conclusion

H4 is live-proven. PID1 hot-reload now preserves the V3366 clean-storage behavior and restores the
tcpctl control plane without rebooting or reopening autohud, rshell, or USB gadget setup. The device
was returned to clean `v2321`.
