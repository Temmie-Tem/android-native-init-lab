# V887 Helper v140 Deploy-only Plan

## Goal

Deploy helper `v140` to `/cache/bin/a90_android_execns_probe` and prove remote
checksum/version/mode parity. V887 must not execute the new eSoC response path;
it only installs the helper needed for a later bounded response gate.

## Inputs

- V886 build report:
  `docs/reports/NATIVE_INIT_V886_ESOC_REQ_IMG_RESPONSE_HELPER_BUILD_2026-05-26.md`
- local helper artifact:
  `tmp/wifi/v886-execns-helper-v140-build/a90_android_execns_probe`
- deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v140_deploy_preflight.py`

## Method

1. Run plan mode with no device command.
2. Run read-only preflight against current native v724.
3. If preflight passes, install helper `v140` only.
4. Verify remote sha256, helper marker, mode token, selftest, actor-clean, and
   Wi-Fi-link-clean state.
5. Do not execute the response scaffold or any live eSoC operation.

## Hard Gates

- Deploy-only mutation: `/cache/bin/a90_android_execns_probe` replacement only.
- No live eSoC ioctl.
- No `/dev/subsys_esoc0` open.
- No `ESOC_NOTIFY`.
- No Android actor start, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, or reboot.

## Success Criteria

- Decision is `execns-helper-v140-deploy-pass`.
- Remote sha256 matches V886 artifact.
- Remote helper advertises `a90_android_execns_probe v140`.
- Remote helper advertises
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`.
- Native health and Wi-Fi surfaces stay clean.

## Next

If V887 passes, the next cycle can plan a bounded response proof. That proof
must separately decide whether to notify `ESOC_IMG_XFER_DONE`, `ESOC_BOOT_DONE`,
or both, and must include reboot cleanup criteria before any live attempt.
