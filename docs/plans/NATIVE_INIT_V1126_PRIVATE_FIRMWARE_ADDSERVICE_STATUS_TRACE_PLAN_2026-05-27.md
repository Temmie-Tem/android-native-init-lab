# V1126 Private Firmware addService Status Trace Plan

Date: `2026-05-27`

## Goal

Capture the exact `pm-service` `addService()` return value when helper-private
firmware mounts are active and `vendor.qcom.PeripheralManager` registration
fails.

## Rationale

V1125 proved the private-firmware PM observer path reaches the Binder service
registration branch and then logs `Adding Peripheral Manager service fail`.
The next useful evidence is the concrete Binder `status_t` returned by
`IServiceManager::addService()`.

## Scope

- Reuse helper `a90_android_execns_probe v212`.
- Reuse the V1125 private-firmware PM observer child command.
- Add tracefs-only instruction uprobes around:
  - `defaultServiceManager()`;
  - `addService()` call;
  - post-`addService()` return register;
  - `addService` failure log;
  - clean return.
- Record the `status_t` value from ARM64 `x0` immediately after the indirect
  `addService()` call.

## Guardrails

- No BPF attach.
- No CNSS daemon start.
- No Wi-Fi HAL, scan/connect, credentials, DHCP/route, external ping.
- No `/dev/subsys_esoc0` open, eSoC ioctl/control, partition write, boot image
  write, flash, or intentional reboot.
- Tracefs events must be removed during cleanup.
- The collector runs through serial `cmdv1 run` to avoid the 10 second
  `a90_tcpctl run` device-side timeout.

## Success Criteria

V1126 passes diagnostically if:

- helper `v212` sha matches;
- private firmware mounts are active;
- `vndservicemanager` readiness is reported ready;
- tracefs uprobes register, enable, disable, and cleanup;
- `pm_add_service_call`, `pm_add_service_status`, and
  `pm_add_service_fail_log` are all observed;
- the non-zero `status_t` value is captured and decoded;
- forbidden Wi-Fi/CNSS actions remain false.

## Expected Next

Use the decoded status to choose the next gate:

- permission/policy error: compare service context and SELinux service-manager
  permissions under the private firmware namespace;
- already-exists/name error: inspect duplicate provider registration or service
  name contract;
- dead-object/transaction error: classify `vndservicemanager` Binder state at
  registration time.
