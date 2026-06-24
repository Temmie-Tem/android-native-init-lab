# Native Init V3181 GPU G0 Flash Gate Blocked

## Summary

- Cycle: `V3181`
- Track: GPU G0 KGSL open-hang diagnosis.
- Decision: `v3181-gpu-g0-flash-gate-blocked`
- Result: BLOCKED before flash.
- Device flash: `no`.
- Candidate awaiting live validation: `boot_linux_v3180_gpu_g0_fwpath_status.img`
- Candidate SHA256: `9ae222ea5a878d6b6233023f92223af2de4ad01d7955f47bab7c362d045ca2d7`

## Gate Evidence

- `lsusb`: no A90/Samsung target device was visible.
- `adb devices`: no attached Android device was listed.
- `a90_bridge.py status --json`: bridge process was running, but `bridge_probe=serial-missing`, `selected_device=""`, and `serial_candidates=[]`.
- Rollback image SHA256 checks passed:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `boot_linux_v48.img`: present with SHA256 recorded locally during the gate check.

## Repeated Blocker Context

- `V3175` also recorded a flash-gate block because the A90 target was not visible.
- `V3178` recorded the same GPU G0 live-gate block for the V3177 candidate.
- `V3181` records the same external-state blocker for the improved V3180 candidate.

The current host-side G0 work is staged as far as it can go without target visibility:

- V3176: source root-cause audit of KGSL first-open/GMU/firmware/power path.
- V3177: bounded parent-safe KGSL open probe image.
- V3179: factory firmware artifact visibility audit for SQE, GMU, and ZAP payloads.
- V3180: expanded runtime firmware path status probe for `/vendor/firmware_mnt/image/a640_zap.*`.

## Safety Decision

Flash was not attempted because the target device was not visible over USB, ADB, or the managed serial bridge.
Recovery/TWRP availability was also not proven during this gate because there was no attached target to inspect.

This preserves the AGENTS flash rules:

- no raw partition writes;
- no forbidden partition access;
- no cascading flash after an unproven live gate;
- no KGSL live probe until the V3180 boot candidate can be flashed and health-checked through the checked helper path.

## Next Action

Reconnect or boot the A90 target so USB/ADB/serial bridge visibility can be proven first.
After that, re-run the flash precondition gate, flash only with `native_init_flash.py`, run `a90ctl version`, `status`,
and `selftest`, then run `gpu g0-status` and one bounded `gpu g0-open-probe --timeout-ms 2000 --materialize-devnode`.
