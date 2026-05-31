# V1265 Response Sampler GPIO Line-info Support

## Result

- decision: `v1265-response-sampler-lineinfo-build-pass`
- evidence: `tmp/wifi/v1265-execns-helper-v264-build/manifest.json`
- helper: `a90_android_execns_probe v264`
- helper SHA256: `a06ff29245023c265c69e58e2ae3f32a4facbc291bcb63a4450f39efd9515dc5`
- scope: source/build-only; no deploy, live command, GPIO line request, PMIC write, eSoC ioctl, Wi-Fi action, flash, boot image write, or partition write

## Changes

- Bumped `stage3/linux_init/helpers/a90_android_execns_probe.c` to helper v264.
- Extended the existing late `per_proxy` / PM-service response sampler with
  read-only PMIC GPIO9 `GPIO_GET_LINEINFO_IOCTL` snapshots.
- Added per-sample fields for line-info readiness, flags, kernel ownership,
  direction, name, consumer, and zero-action markers.
- Extended the V1242/V1243 parser to recognize the new line-info sample fields
  while remaining compatible with older helper output.

## Validation

- Static aarch64 build passed through
  `scripts/revalidation/build_android_execns_probe_helper.sh`.
- `readelf -l` shows no `INTERP` segment.
- `readelf -d` reports no dynamic section.
- Binary strings include the helper v264 marker, `gpiochip_lineinfo_*` fields,
  zero-action markers, and the existing late response sampler mode.

## Next

V1266 should deploy helper v264 only.  V1267 should run the bounded read-only
ext-mdm/AP2MDM observer using the existing late `per_proxy` response window, now
including PMIC GPIO9 line-info state in the same window.
