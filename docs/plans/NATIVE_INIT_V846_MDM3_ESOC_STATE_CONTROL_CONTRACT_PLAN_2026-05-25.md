# Native Init V846 mdm3/eSoC State-Control Contract Plan

## Goal

Map the V845 live mdm3/ext-sdx50m writable-looking candidates to Samsung OSRC
source paths, then select the safest next gate that can actually advance mdm3
toward WLFW service 69 publication.

## Scope

V846 is host-only. It reads V844/V845 manifests, V845 evidence files, and local
Samsung OSRC source. It does not contact the device, create device nodes, open
`esoc0` or `subsys_esoc0`, write sysfs/GPIO/debugfs, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, ping externally, write boot images, write partitions, or flash a
custom kernel.

## Inputs

- V844 boot-interface classifier:
  `tmp/wifi/v844-mdm3-ext-sdx50m-boot-interface-classifier/manifest.json`
- V845 read-only surface snapshot:
  `tmp/wifi/v845-mdm3-ext-sdx50m-surface-snapshot/manifest.json`
- Samsung OSRC source:
  - `drivers/soc/qcom/subsystem_restart.c`
  - `include/linux/esoc_client.h`
  - `include/uapi/linux/esoc_ctrl.h`
  - `drivers/bus/mhi/controllers/mhi_arch_qcom.c`
  - `drivers/bus/mhi/controllers/mhi_qcom.c`
  - `drivers/soc/qcom/icnss.c`

## Classification Rules

V846 passes if:

1. V844 and V845 inputs are present and passing.
2. OSRC proves subsystem `state` is read-only via `DEVICE_ATTR_RO(state)`, so
   direct `/sys/.../subsys9/state` write is rejected.
3. OSRC proves the exported subsystem char-device open path calls
   `subsystem_get_with_fwname()` and then `subsys_start()`.
4. OSRC proves close/release calls `subsystem_put()` and can stop the subsystem.
5. V845 supplies `subsys_esoc0` uevent major/minor/devname but no active `/dev`
   node, so materialization must be explicit and reversible.
6. MHI/eSoC hooks are present downstream, but MHI `power_up` is deferred until
   after the char-device path is tested.

## Expected Decision

Expected result: `v846-mdm3-esoc-char-open-contract-selected`.

This means direct sysfs writes are not the next gate. The next live action, if
performed, should be a bounded `subsys_esoc0` char-device materialize/open/hold
smoke with watchdog, dmesg capture, and cleanup reboot.

## Next Gate

V847 should perform one bounded live `subsys_esoc0` char-device materialize/open
smoke. It must remain below service-manager, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, and boot-image work.
