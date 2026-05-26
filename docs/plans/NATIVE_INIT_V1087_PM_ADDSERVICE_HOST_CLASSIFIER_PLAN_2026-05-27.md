# Native Init V1087 PM addService Host Classifier Plan

## Goal

Classify the current `pm-service` blocker after V1086 without starting any
device actor. V1086 supersedes the older V1071 exit-255 diagnosis:

```text
get_system_info success
  -> ProcessState::initWithDriver("/dev/vndbinder")
  -> defaultServiceManager()
  -> addService("vendor.qcom.PeripheralManager", ...)
  -> addService failure log
  -> clean return 0
```

## Inputs

- V1086 live trace:
  `tmp/wifi/v1086-pm-service-success-path-trace-live/manifest.json`.
- V1086 observer transcript:
  `tmp/wifi/v1086-pm-service-success-path-trace-live/host/pm-service-tracefs-uprobe-observer.txt`.
- V694 provider-positive control:
  `tmp/wifi/v694-peripheral-vndservice-query-orchestrated-live-rerun/manifest.json`.
- V1072 service-manager/context reference:
  `tmp/wifi/v1072-pm-observer-pm-actor-exit-fd-trace-v192-live/host/pm-service-trigger-observer.txt`.

## Checks

1. Verify V1086 reached `addService` and failed before QMI thread startup.
2. Verify V1086 `per_mgr` now exits `0`, making the V1071 exit-255 branch stale.
3. Verify V694 still proves `vendor.qcom.PeripheralManager` registration.
4. Compare V694 positive-control preconditions against V1086:
   - explicit `vndservicemanager_ready`;
   - V490 SELinux policy-load proof;
   - provider query after `per_mgr`.
5. Preserve the result as private host-only evidence.

## Guardrails

- Host-only classifier.
- No device command.
- No tracefs write.
- No BPF attach.
- No PM actor start.
- No Wi-Fi HAL, scan/connect, credentials, DHCP, route, or external ping.
- No partition write, flash, or reboot.

## Success Criteria

- Emit a deterministic V1087 decision label.
- State whether the V1071 BPF/syscall route is still the primary next step.
- Identify the next minimal live gate for PM-service addService parity.
