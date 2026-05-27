# V1124 Private Firmware PM Observer Live Plan

Date: `2026-05-27`

## Goal

Test whether helper-private firmware mounts preserve the V1108 provider-positive
PM observer path while adding firmware visibility needed by the lower modem
path.

## Preconditions

- Helper `v212` is deployed to `/cache/bin/a90_android_execns_probe`.
- Helper sha256 is
  `65fe14f0d7095786d8228750e309e0a1b5d40c33825d1debb87870d9caba0ef3`.
- Native init remains healthy and NCM/cmdv1 control is available.
- No global firmware mount wrapper is active before the run.

## Scope

- Replay the V1108 no-pre-CNSS `per_proxy` order.
- Add `--pm-observer-private-firmware-mounts`.
- Add zero-delay CNSS-after-`per_mgr` from helper `v211`.
- Arm existing tracefs-only PM/CNSS observer probes.
- Capture provider visibility, PM register/connect returns, and lower mdm3/WLFW
  surface markers.

## Guardrails

- No global `/vendor/firmware_mnt` or `/vendor/firmware-modem` mount wrapper.
- No `/dev/subsys_esoc0` open or eSoC ioctl/control.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/route, external ping, partition
  write, boot image write, flash, or reboot unless cleanup requires explicit
  follow-up.

## Success Criteria

V1124 passes diagnostically if:

- helper `v212` sha and usage markers match;
- tracefs-only observer completes;
- helper reports both private firmware mounts active;
- forbidden Wi-Fi actions remain false;
- result is classified as either:
  - provider preserved with CNSS PM register/connect progress, or
  - provider regressed under private firmware mounts.

Both outcomes are useful. Provider preservation routes back to the lower
firmware/modem blocker. Provider regression routes to `pm-service` early clean
exit tracing inside the private firmware namespace.
