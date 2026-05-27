# V1125 Private Firmware PM Service Early Exit Trace Plan

Date: `2026-05-27`

## Goal

Trace the `pm-service` terminal branch when the PM observer runtime namespace has
helper-private firmware mounts, but before starting CNSS, Wi-Fi HAL, scan, or
connect paths.

## Rationale

V1124 proved that private firmware mounts succeed but the
`vendor.qcom.PeripheralManager` provider still disappears. The next useful
question is which `pm-service` branch causes the clean exit under that
namespace surface.

## Scope

- Reuse the existing tracefs-only `pm-service` success-path offsets from V1086.
- Use helper `v212`.
- Add only `--pm-observer-private-firmware-mounts` to the PM observer child.
- Capture `addService`, QMI thread creation, clean-return, and failure-return
  branches.
- Keep CNSS, Wi-Fi HAL, scan/connect, credentials, DHCP/route, and external ping
  disabled.

## Guardrails

- No BPF attach.
- No CNSS daemon start.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/route, external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl/control, partition write, boot image
  write, flash, or intentional reboot.
- Tracefs events must be removed during cleanup.
- The trace collector runs through the serial `cmdv1 run` path instead of
  `a90_tcpctl run`, because `a90_tcpctl` enforces a 10 second device-side run
  timeout and the PM observer window can exceed that before trace cleanup.

## Success Criteria

V1125 passes diagnostically if:

- helper `v212` sha matches;
- PM observer reports private firmware mounts active;
- tracefs-only uprobes register, enable, disable, and cleanup;
- forbidden Wi-Fi/CNSS actions remain false;
- one terminal branch is classified, such as:
  - `binder-add-service-failure`;
  - `qmi-thread-create-failure`;
  - `signal-driven-clean-shutdown`;
  - `clean-return-zero`;
  - `failure-return-minus1`.

## Expected Next

The next gate should target the exact terminal branch. If addService fails,
compare binder/service-manager readiness under private firmware. If QMI thread
creation is reached, return to peripheral-manager lower side effects.
