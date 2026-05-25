# V904 mdm_helper Runtime Input Parity Plan

## Goal

Classify why native V903 direct `mdm_helper` does not enter the Android
`/dev/esoc-0` / `ks` / MHI path.

V904 is host-only. It compares existing Android positive-control evidence
against V903 native evidence and identifies the missing runtime inputs before
any new subsystem-open retry.

## Inputs

- V903 native negative evidence:
  `tmp/wifi/v903-mdm-helper-only-deep-capture-live/manifest.json`
- V853 Android actor evidence:
  `tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/manifest.json`
- V896 Android image-link classifier:
  `tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json`
- V903 report:
  `docs/reports/NATIVE_INIT_V903_MDM_HELPER_ONLY_DEEP_CAPTURE_2026-05-26.md`

## Method

1. Extract Android `mdm_helper` holder/process/service/SELinux/ueventd lines.
2. Extract native V903 `mdm_helper` attr, wchan/syscall, fd targets, and
   helper contract counters.
3. Compare:
   - SELinux context;
   - init service and `vendor.per_mgr` trigger;
   - `/dev/esoc-0`, `/dev/subsys_*`, MHI, and `ks` fd surface;
   - socket/data directory surface.
4. Produce a host-only decision and next live-safe repair direction.

## Hard Gates

- No device contact, Android boot, ADB command, actor start, daemon start,
  live eSoC ioctl, subsystem open, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, or Wi-Fi link-up.
- No boot image write, partition write, firmware mutation, module load/unload,
  GPIO/sysfs/debugfs write, or reboot.

## Success Criteria

- Classifier returns a pass decision from existing evidence.
- Android positive contract and native V903 negative contract are both proven.
- Deltas identify the specific runtime-input mismatch that should be repaired
  next.

## Next

If Android/native parity shows missing init/SELinux/peripheral-manager context,
V905 should design a fail-closed runtime-input repair before another
`/dev/subsys_esoc0` retry.
