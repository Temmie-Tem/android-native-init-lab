# V1123 Private Firmware PM Observer Helper Build Plan

Date: `2026-05-27`

## Goal

Add an opt-in helper path that mounts Wi-Fi firmware partitions inside the
private Android runtime namespace used by the PM observer, without mutating
global `/vendor`.

## Rationale

V1087 already made the V1071 exit-255 BPF/uprobe direction obsolete. V1122 then
classified the current delta as global firmware `/vendor` surface breaking the
provider-positive path. V1123 therefore keeps PM observer behavior unchanged by
default and adds a narrow opt-in flag for the next live gate.

## Scope

- Bump `a90_android_execns_probe` to `v212`.
- Add `--pm-observer-private-firmware-mounts`.
- Enable `apnhlos` and `modem` firmware mounts only when PM observer mode uses
  that explicit flag.
- Emit PM observer contract markers for requested and mounted firmware
  surfaces.
- Build the static AArch64 helper artifact.

## Guardrails

- Source/build-only.
- No helper deploy.
- No device command.
- No global firmware mount.
- No PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials, DHCP/route,
  external ping, reboot, partition write, boot image write, or flash.

## Success Criteria

V1123 passes if:

- source contains the `v212` marker and private firmware flag/contract strings;
- static AArch64 helper builds successfully;
- built helper has no dynamic interpreter;
- built helper contains:
  - `a90_android_execns_probe v212`;
  - `--pm-observer-private-firmware-mounts`;
  - `private_firmware_mounts_requested`;
  - `private_firmware_mnt_mounted`;
  - `private_firmware_modem_mounted`.

## Expected Next

V1124 should deploy helper `v212` and run a bounded PM observer live gate that
replays the V1108 no-pre-CNSS `per_proxy` order with helper-private firmware
mounts.
