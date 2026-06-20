# Native Init V3010 DOOM Input Flash Gate Assets

## Summary

- Decision: `v3010-doom-input-flash-gate-assets-ready-hardware-wait`
- Device action: `none` in this host-only unit.
- Track: active Video playback / DOOM input prerequisite plus T3 safety tooling.
- Required assets present: `1`
- Expected SHA256 checks pass: `1`
- Current gate reports pass: `1`
- External hardware wait retained: `1`
- V3004 live actionable now: `0`

## Asset Audit

| asset | kind | ok | sha256_ok | path |
| --- | --- | ---: | ---: | --- |
| `fallback_v2237` | `fallback-boot-image` | `1` | `1` | `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img` |
| `fallback_v48` | `fallback-boot-image` | `1` | `-` | `workspace/private/inputs/boot_images/boot_linux_v48.img` |
| `flash_helper` | `checked-flash-helper` | `1` | `-` | `workspace/public/src/scripts/revalidation/native_init_flash.py` |
| `rollback_v2321` | `rollback-boot-image` | `1` | `1` | `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img` |
| `twrp_recovery` | `recovery-image` | `1` | `-` | `workspace/private/inputs/firmware/twrp/recovery.img` |
| `v3004_candidate_v2989` | `boot-image-candidate` | `1` | `1` | `workspace/private/inputs/boot_images/boot_linux_v2989_doominput_state.img` |

## Current Gate Evidence

- V3004 report markers ok: `1`
- V3007 current-audit markers ok: `1`
- V3008 reconciliation markers ok: `1`
- V3009 selector markers ok: `1`
- The next live run remains gated on an A90-side USB keyboard/OTG path plus operator DOOM key presses.
- Command when the external prerequisite is true: `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doominput_keyboard_live_gate_v3004.py --live --count 32 --timeout-ms 60000`

## Drop-Tier Trigger

- Active DOOM input live work still needs external hardware stimulus; this V3010 unit performs host-only flash-gate asset readiness instead of repeating low-information touch/button samples.

## Host Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doom_input_flash_gate_assets_v3010.py tests/test_native_doom_input_flash_gate_assets_v3010.py`: PASS
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doom_input_flash_gate_assets_v3010`: PASS
- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doom_input_flash_gate_assets_v3010.py`: PASS (host-only report materialized)
- `git diff --check`: PASS

## Safety

- Host-only file existence and SHA256 audit; no flash, no serial command, no evdev open, no input injection, and no sysfs write.
- The checked flash helper is only treated as an audited file path; it is not invoked.
- No Wi-Fi/audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.
- Private boot/recovery images remain under `workspace/private/`; this report records metadata only.
