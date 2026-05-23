# Native Init V686 PeripheralManager Helper Mode Plan

## Objective

V686 implements the V685 next gate in source: add a bounded
`vendor.per_mgr`/`vendor.per_proxy` helper path before a fresh CNSS retry.

V686 is not a Wi-Fi connect attempt. It does not deploy to the device by
itself, start daemons live, start Wi-Fi HAL, scan/connect, run DHCP, or ping
externally. It prepares and verifies the helper mode needed for the next live
proof.

## Scope

Modify `stage3/linux_init/helpers/a90_android_execns_probe.c` only:

1. bump helper marker to `a90_android_execns_probe v113`;
2. add mode
   `wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only`;
3. allow SELinux context `u:r:per_mgr:s0`;
4. map `/vendor/bin/pm-service` and `/vendor/bin/pm-proxy` to `u:r:per_mgr:s0`;
5. add `COMPOSITE_ID_PER_MGR` and `COMPOSITE_ID_PER_PROXY`;
6. apply Android init's `user system`, `group system`, no-capability contract;
7. preserve existing service `74` gated order and insert:

```text
... vndservicemanager_ready
  -> cnss_daemon_initial_cleanup
  -> per_mgr /vendor/bin/pm-service
  -> per_proxy /vendor/bin/pm-proxy
  -> cnss_daemon_retry
```

## Build Validation

Build a static helper artifact:

```sh
mkdir -p tmp/wifi/v686-execns-helper-v113-build
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v686-execns-helper-v113-build/a90_android_execns_probe
```

Required strings:

- `a90_android_execns_probe v113`
- `wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only`
- `/vendor/bin/pm-service`
- `/vendor/bin/pm-proxy`
- `wifi_companion_start.peripheral_manager.enabled=%d`
- `wifi_companion_start.peripheral_manager.per_mgr.ready=%d`
- `wifi_companion_start.peripheral_manager.per_proxy.ready=%d`

## Success Criteria

- helper source compiles for AArch64 static;
- built artifact has no dynamic section;
- built artifact contains the required v113/provider mode strings;
- no live device mutation is performed by V686;
- no Wi-Fi HAL, scan/connect, DHCP, route, credential, or external ping is
  executed.

## Next Gate

V687 should deploy helper v113 to `/cache/bin/a90_android_execns_probe`, verify
the marker and mode remotely, then run the bounded provider start-only proof.
Only if `per_mgr`/`per_proxy` are observable and cleanup-safe should a fresh
`cnss-daemon` retry be accepted as meaningful.
