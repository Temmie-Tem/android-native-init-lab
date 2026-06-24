# Native Init V3182 GPU G0 Flash Request Blocked

## Summary

- Cycle: `V3182`
- Track: GPU G0 KGSL open-hang diagnosis.
- Decision: `v3182-gpu-g0-flash-request-blocked`
- Result: BLOCKED before flash.
- Device flash: `no`.
- User request: flash and continue with GPU G0 validation.
- Candidate selected for flash: `boot_linux_v3180_gpu_g0_fwpath_status.img`
- Candidate SHA256: `9ae222ea5a878d6b6233023f92223af2de4ad01d7955f47bab7c362d045ca2d7`

## Gate Evidence

- `lsusb`: no A90/Samsung target device was visible.
- `adb devices`: no attached Android or recovery device was listed.
- `/dev/serial/by-id`, `/dev/ttyACM*`, `/dev/ttyUSB*`: no matching serial device was present.
- `a90_bridge.py status --json`: bridge process was running, but `bridge_probe=serial-missing`, `selected_device=""`, and `serial_candidates=[]`.
- `native_init_flash.py --help`: checked helper is present and supports the required pinned-image flash path.
- Rollback image SHA256 checks passed:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `boot_linux_v48.img`: present with SHA256 recorded locally during the gate check.

## Safety Decision

The flash helper was not invoked. The target was absent from USB, ADB, and the managed serial bridge, so recovery/TWRP
availability could not be proven. Calling the flash helper in this state would not satisfy the AGENTS rollback and flash
gates.

This preserves:

- boot-only flash discipline through `native_init_flash.py`;
- no raw partition writes;
- no forbidden partition access;
- no cascading flash after an unproven live gate;
- no KGSL live probe before a flashed image has passed `version`, `status`, and `selftest`.

## Ready Command Once Target Is Visible

After the A90 enumerates in recovery/TWRP or the current native-init bridge is visible, the intended pinned flash command is:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v3180_gpu_g0_fwpath_status.img \
  --expect-sha256 9ae222ea5a878d6b6233023f92223af2de4ad01d7955f47bab7c362d045ca2d7 \
  --expect-version "A90 Linux init 0.11.20 (v3180-gpu-g0-fwpath-status)"
```

Then run `a90ctl version`, `a90ctl status`, `a90ctl selftest verbose`, `gpu g0-status`, and one bounded
`gpu g0-open-probe --timeout-ms 2000 --materialize-devnode`.
