# Native Init V3178 GPU G0 Flash Gate Blocked

## Summary

- Cycle: `V3178`
- Track: GPU G0 KGSL open-hang diagnosis.
- Decision: `v3178-gpu-g0-flash-gate-blocked`
- Result: BLOCKED before flash.
- Device flash: `no`.
- Candidate awaiting live validation: `boot_linux_v3177_gpu_g0_bounded_probe.img`
- Candidate SHA256: `6aea73ef99a05fbc86336597a7631d9de80a57b162e74d95b20217c3d7a11fee`

## Gate Evidence

- `lsusb`: no A90/Samsung target device was visible.
- `adb devices`: no attached Android device was listed.
- `a90_bridge.py status --json`: bridge process was running, but `bridge_probe=serial-missing`, `selected_device=""`, and `serial_candidates=[]`.
- Rollback image SHA256 checks passed:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - `boot_linux_v2237_supplicant_terminate_poll.img`: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - `boot_linux_v48.img`: present with SHA256 recorded locally during the gate check.

## Safety Decision

Flash was not attempted because the target device was not visible over USB, ADB, or the managed serial bridge.
Recovery/TWRP availability was also not proven during this gate because there was no attached target to inspect.

This preserves the AGENTS flash rules:

- no raw partition writes;
- no forbidden partition access;
- no cascading flash after an unproven live gate;
- no KGSL live probe until the V3177 boot candidate can be flashed and health-checked through the checked helper path.

## Next Action

Reconnect or boot the A90 target so that USB/ADB/serial bridge visibility can be proven first.
After that, re-run the flash precondition gate, flash only with `native_init_flash.py`, then run `a90ctl version`, `status`, and `selftest` before the bounded GPU G0 commands.
