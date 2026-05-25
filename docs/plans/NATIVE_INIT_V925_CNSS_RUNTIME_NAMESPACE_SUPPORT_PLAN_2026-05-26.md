# Native Init V925 CNSS Runtime Namespace Support Plan

## Goal

Implement the source/build-only repair requested by V924 before any additional
CNSS-before-eSoC live gate.

V925 targets two V924 gaps:

1. repeated CNSS surface polling produced oversized helper transcripts;
2. the `mdm_helper` + CNSS runtime still lacked explicit linkerconfig/APEX/VNDK
   and property-context namespace reporting.

## Scope

V925 is host-only and source/build-only. It may edit and statically build
`stage3/linux_init/helpers/a90_android_execns_probe.c`, but it must not deploy
or run the helper on the device.

## Inputs

- `docs/reports/NATIVE_INIT_V923_CNSS_BEFORE_ESOC_LIVE_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V924_CNSS_WLFW_PRECONDITION_GAP_2026-05-26.md`
- `tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/manifest.json`
- `tmp/wifi/v924-cnss-wlfw-precondition-gap/manifest.json`

## Required Helper Changes

1. Bump the helper marker to `a90_android_execns_probe v153`.
2. Add `--cnss-surface-mode full|compact`, valid only for
   `wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture`.
3. Default that mode to compact output so repeated Wi-Fi/CNSS surface captures
   do not exhaust the 1 MiB transcript buffer before final result keys.
4. Keep full surface mode available for manual deep capture.
5. Set the CNSS-before-eSoC runtime defaults to the Android-like namespace
   surfaces already used by later HAL-order gates:
   - `--null-device-mode dev-null`;
   - `--vndk-apex-alias-mode v30-to-system-ext-v30`;
   - `--linkerconfig-mode copy-real`;
   - `--linkerconfig-source /cache/bin/a90_real_ld.config.txt`;
   - `--apex-libraries-source /cache/bin/a90_real_apex.libraries.config.txt`;
   - `--android-selinux-context-mode service-defaults`.
6. Emit explicit runtime namespace fields in the helper stdout so V926 can
   verify which namespace was actually used.

## Hard Guardrails

- No device contact, serial live command, ADB, Android boot, helper deploy,
  actor start, eSoC ioctl, `/dev/subsys_esoc0` open, service-manager, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, boot image write,
  partition write, firmware mutation, GPIO/sysfs/debugfs write, module
  load/unload, bind, or unbind.
- Preserve the existing fail-closed WLFW gate: `/dev/subsys_esoc0` may remain
  reachable only inside the gated child and only after a WLFW precondition
  marker is observed by a later live run.

## Success Criteria

- `python3 -m py_compile` passes for the V925 verifier.
- Static ARM64 helper build succeeds and has no dynamic section.
- The verifier proves:
  - helper `v153` marker;
  - compact output throttle;
  - full mode remains available;
  - runtime namespace defaults/reporting are present;
  - service-manager/HAL/scan/connect/credentials/DHCP/external ping remain
    blocked;
  - `/dev/subsys_esoc0` open remains child-only and WLFW-gated.
- Produce private evidence under `tmp/wifi/v925-cnss-runtime-namespace-support`.

## Expected Next

If V925 passes, V926 should be deploy-only for helper `v153`, followed by a
bounded compact CNSS-before-eSoC live precondition gate. V926 still must not
start service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
external ping.
