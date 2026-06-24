# Native Init V3175 Bad Apple/Nyan Silence Tail Flash Blocked

## Summary

- Cycle: `V3175`
- Track: Bad Apple/Nyan A/V playback silence-tail stabilization.
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3175_badapple_nyan_silence_tail.img`
- Candidate SHA256: `7c2973f7afc482786425e4d17c004a5dff062f4194504ff3f370d780ead4092d`
- Result: BLOCKED before flash.

## Gate Evidence

- Rollback image `boot_linux_v2321_usb_clean_identity_rodata.img`: SHA256 matched `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Deeper fallback `boot_linux_v2237_supplicant_terminate_poll.img`: SHA256 matched `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
- Final fallback `boot_linux_v48.img`: present, SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`.
- `lsusb`: no A90/Samsung target visible.
- `adb devices`: no devices listed.
- `a90_bridge.py status --json`: bridge process running, but `serial_candidates` was empty and `selected_device` was empty.
- `a90ctl.py version`: failed before health check with `A90P1 END marker not found before timeout (10.0s)`.

## Decision

No flash was attempted. The device/recovery path was not currently reachable, so proceeding would violate the flash gate requiring recoverable infrastructure and post-flash health validation.

## Next Action

Reconnect or boot the A90 into the expected USB/native-init or recovery state, then rerun the flash gate and flash only through `workspace/public/src/scripts/revalidation/native_init_flash.py` with the V3175 candidate SHA pinned.
