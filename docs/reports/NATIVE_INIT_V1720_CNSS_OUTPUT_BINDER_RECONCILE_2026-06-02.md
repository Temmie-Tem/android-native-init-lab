# Native Init V1720 CNSS Output/Binder Reconciliation

## Summary

- Cycle: `V1720`
- Type: host-only reconciliation and next-gate classifier
- Decision: `v1720-cnss-output-binder-reconcile-pass`
- Result: PASS
- Evidence: `tmp/wifi/v1720-cnss-output-binder-reconcile`

## Corrections Applied

- The QCACLD `REGISTER_DRIVER` premise is retracted for WLFW server triggering. ICNSS driver registration waits for later firmware readiness and should not be added as a `wlfw_start` trigger.
- Native `wlfw_start_seen=0` is treated as a logging visibility artifact. `cnss-daemon` logging goes through Android logging unless the kmsg property path is explicitly enabled.
- The requested output-visibility branch is already resolved by non-log trace evidence: V1702/V1716 hit `wlfw_start@0xec00`.

## Evidence Reconciliation

- V1703 corrected premise present: `True`
- V1716 decision: `v1716-pm-init-register-call-no-return-rollback-pass`
- V1716 `wlfw_start` hit: `True`
- V1716 `pm_init(1, NULL)` call hit: `True`
- V1716 `pm_client_register` no-return label: `True`
- V1719 decision: `v1719-peripheral-default-service-manager-call-no-return-rollback-pass`
- V1719 non-log label: `peripheral-default-service-manager-call-no-return`
- V1719 `/dev/vndbinder` init reached: `True`
- V1719 `defaultServiceManager()` reached: `True`
- V1719 concrete `vendor.qcom.PeripheralManager` name not reached: `True`
- V1680 firmware-serve label: `firmware-not-requested`

## Current Blocker

The latest evidence is narrower than a generic downstream WLFW wait:

```text
cnss-daemon
  -> wlfw_start
    -> pm_init(1, NULL)
      -> get_system_info OK
      -> pm_client_register
        -> libperipheral_client.so
          -> ProcessState::initWithDriver('/dev/vndbinder')
          -> defaultServiceManager()
             [blocks before String16('vendor.qcom.PeripheralManager')]
```

Therefore the active blocker is default vendor Binder service-manager acquisition, not QCACLD registration, not missing `wlfw_start`, and not yet WLFW QMI service waiting.

## Historical Binder Evidence

- V659 isolated `vndservicemanager` readiness passed: `True`
- V659 was an older service-74-gated route and did not combine with the current V1680/V1716 internal-modem route.
- V655 timed out before service `74`; it does not invalidate V659 readiness, but it is not the current route.
- V1184/V1188 PM-trio/per_mgr work remains separate and should not be reintroduced as a pre-CNSS actor path for this gate.

## Host Artifact Snapshot

- `tmp/wifi/v1073-host-only/vendor-extract/files/libperipheral_client.so`
- `tmp/wifi/v222-synthetic-vendor/bin/cnss-daemon`
- `tmp/wifi/v222-vendor-root-evidence-export/vendor-root/bin/cnss-daemon`
- `tmp/wifi/v222-vendor-root-evidence-export/vendor-root/lib/libperipheral_client.so`
- `tmp/wifi/v222-vendor-root-evidence-export/vendor-root/lib64/libperipheral_client.so`
- `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib/libperipheral_client.so`
- `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libperipheral_client.so`
- `tmp/wifi/v396-frame-elf-pull-20260520-073940/system-root/system/bin/servicemanager`

The current host evidence export contains `cnss-daemon` and one older `servicemanager` artifact, but not a complete current `vndservicemanager`/`libbinder.so` staging set for a new live gate. A future source/build or handoff step must materialize and verify those inputs before live execution.

## Next Gate

- Do not add PM/service-window actors, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, or Wi-Fi HAL/scan/connect.
- First perform a host-only V1721 vendor Binder bootstrap materialization/classifier: locate or pull current `vndservicemanager`, `libbinder.so`, binder device paths, property keys, and SELinux labels required by `defaultServiceManager()`.
- Only after V1721 proves a narrow contract should the next live gate be considered: service-manager-only readiness or a non-mutating vendor Binder availability probe, still without PM trio or `vendor.qcom.PeripheralManager` service startup.

## Safety Scope

This script performed host-only analysis only. It did not contact the device, flash, reboot, start service-manager/PM actors, start `boot_wlan`, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.
