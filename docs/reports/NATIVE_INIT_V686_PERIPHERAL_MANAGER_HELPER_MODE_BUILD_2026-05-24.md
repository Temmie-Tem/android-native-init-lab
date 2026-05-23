# Native Init V686 PeripheralManager Helper Mode Build Report

## Result

- decision: `v686-peripheral-manager-helper-mode-build-ready`
- pass: `true`
- changed source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- built artifact: `tmp/wifi/v686-execns-helper-v113-build/a90_android_execns_probe`
- helper marker: `a90_android_execns_probe v113`
- device commands: `false`
- daemon start: `false`
- Wi-Fi bring-up: `false`

## Implementation

V686 adds one new bounded mode:

```text
wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only
```

The new mode preserves the existing service `74` gate and
`vndservicemanager_ready` checkpoint, then inserts Android's peripheral manager
provider before the fresh CNSS retry:

```text
qrtr_ns
  -> rmt_storage
  -> tftp_server
  -> pd_mapper
  -> cnss_diag
  -> cnss_daemon
  -> service74_gate
  -> servicemanager
  -> hwservicemanager
  -> vndservicemanager
  -> vndservicemanager_ready
  -> cnss_daemon_initial_cleanup
  -> per_mgr /vendor/bin/pm-service
  -> per_proxy /vendor/bin/pm-proxy
  -> cnss_daemon_retry
```

The helper now:

- accepts `u:r:per_mgr:s0`;
- maps `/vendor/bin/pm-service` and `/vendor/bin/pm-proxy` to
  `u:r:per_mgr:s0`;
- runs both provider children as `system:system` with no supplemental groups and
  no Linux capabilities, matching the A90 vendor init contract from V685;
- records readiness lines for `per_mgr` and `per_proxy` before allowing
  `cnss_daemon_retry` to be meaningful.

## Build Evidence

```text
artifact: tmp/wifi/v686-execns-helper-v113-build/a90_android_execns_probe
size: 969K
sha256: 60ed7a14d3b33b2f700fb644fd1ccd7a037ac8d9c50db082fa0dea7646965ce9
file: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
dynamic section: none
```

Required strings are present:

- `a90_android_execns_probe v113`
- `wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only`
- `/vendor/bin/pm-service`
- `/vendor/bin/pm-proxy`
- `wifi_companion_start.peripheral_manager.enabled=%d`
- `wifi_companion_start.peripheral_manager.per_mgr.ready=%d`
- `wifi_companion_start.peripheral_manager.per_proxy.ready=%d`

## Guardrails

V686 is source/build only:

- no helper deployment;
- no daemon start;
- no service-manager start;
- no Wi-Fi HAL start;
- no scan/connect/link-up;
- no credentials, DHCP, routes, or external ping;
- no sysfs/debugfs, boot image, or partition writes.

## Next Gate

V687 should deploy helper v113 and run a bounded live proof:

1. verify remote helper marker `a90_android_execns_probe v113`;
2. verify remote usage contains the new provider mode;
3. run service `74` gated provider start-only;
4. require `per_mgr` and `per_proxy` observable/cleanup-safe evidence;
5. only then evaluate whether the fresh `cnss-daemon` retry advances WLFW/BDF;
6. keep Wi-Fi HAL, scan/connect, DHCP, routes, and external ping blocked.
