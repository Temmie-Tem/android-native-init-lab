# V886 ESOC_REQ_IMG Response Helper v140 Plan

## Goal

Repair helper-side `ESOC_WAIT_FOR_REQ` semantics and add a guarded
source/build-only response scaffold after V885 classified V884 value `1` as
`ESOC_REQ_IMG`.

V886 must not execute a live response. It prepares helper `v140` so a later
deploy/live gate can reason about `ESOC_IMG_XFER_DONE` and `ESOC_BOOT_DONE`
without repeating the V884 D-state path blindly.

## Inputs

- V885 report:
  `docs/reports/NATIVE_INIT_V885_ESOC_REQ_IMG_RESPONSE_CLASSIFIER_2026-05-26.md`
- helper source:
  `stage3/linux_init/helpers/a90_android_execns_probe.c`
- build script:
  `scripts/revalidation/build_android_execns_probe_helper.sh`

## Method

1. Bump helper marker to `a90_android_execns_probe v140`.
2. Treat `ESOC_WAIT_FOR_REQ` success as a nonnegative copied `u32` byte count,
   not as rc `0`.
3. Emit request name and `ESOC_REQ_IMG` classification markers.
4. Add fail-closed response scaffold markers for `ESOC_IMG_XFER_DONE` and
   `ESOC_BOOT_DONE`.
5. Keep live `ESOC_NOTIFY` execution blocked.
6. Build a static ARM64 artifact and verify required marker strings.

## Hard Gates

- Source/build-only.
- No helper deploy.
- No bridge or device command.
- No live eSoC ioctl or `/dev/subsys_esoc0` open.
- No live `ESOC_NOTIFY`.
- No Android actor start, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, or reboot.

## Success Criteria

- Static ARM64 build succeeds.
- Artifact has no dynamic section.
- Artifact advertises marker `a90_android_execns_probe v140`.
- Artifact includes request-observed semantic markers:
  `byte_count`, `request_name`, and `request_observed`.
- Artifact includes fail-closed response scaffold markers and still reports
  `notify_attempted=0`.

## Next

If V886 passes, V887 should deploy helper `v140` only and prove remote
checksum/version/mode parity. A later live response proof must be a separate
bounded gate.
