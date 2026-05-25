# V889 eSoC Conditional Response Helper v141 Plan

## Goal

Add source/build-only helper support for the V888 response gate. V889 must not
deploy the helper and must not execute a live response.

The new helper mode prepares a fail-closed sequence:

1. observe `ESOC_REQ_IMG`
2. notify `ESOC_IMG_XFER_DONE`
3. poll `ESOC_GET_STATUS`
4. notify `ESOC_BOOT_DONE` only if status readiness is proven

## Inputs

- V888 classifier:
  `docs/reports/NATIVE_INIT_V888_ESOC_RESPONSE_GATE_CLASSIFIER_2026-05-26.md`
- helper source:
  `stage3/linux_init/helpers/a90_android_execns_probe.c`
- build script:
  `scripts/revalidation/build_android_execns_probe_helper.sh`

## Method

1. Bump helper marker to `a90_android_execns_probe v141`.
2. Add mode `wifi-companion-esoc-conditional-response-preflight`.
3. Add allow flag `--allow-esoc-conditional-response-preflight`.
4. Reuse the REQ-registered `/dev/subsys_esoc0` hold framework.
5. Add conditional response child logic under the new mode only.
6. Build static ARM64 artifact and verify required markers.

## Hard Gates

- Source/build-only.
- No helper deploy.
- No bridge or device command.
- No live eSoC ioctl.
- No `/dev/subsys_esoc0` open.
- No live `ESOC_NOTIFY`.
- No Android actor start, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, or reboot.

## Success Criteria

- Static ARM64 build succeeds.
- Artifact has no dynamic section.
- Artifact advertises helper marker `a90_android_execns_probe v141`.
- Artifact advertises mode
  `wifi-companion-esoc-conditional-response-preflight`.
- Artifact advertises allow flag
  `--allow-esoc-conditional-response-preflight`.
- Artifact includes `ESOC_IMG_XFER_DONE` planned, `ESOC_BOOT_DONE` conditional,
  status-ready, and boot-done-sent markers.

## Next

If V889 passes, V890 should deploy helper `v141` only. The first live
conditional response run remains a separate bounded gate after deploy parity.
