# Native Init V699 Provider-first CNSS Helper Report

- date: `2026-05-24 KST`
- status: `helper-build-pass`; Wi-Fi external ping is **not** complete
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- build artifact: `tmp/wifi/v699-execns-helper-v119-build/a90_android_execns_probe`
- helper marker: `a90_android_execns_probe v119`
- artifact sha256:
  `53c7d74d9a7d4ec2cbbaf7dc98e37af9bb165a9ccaabc45616dc3c12949d794c`

## Scope

V699 changed and built the local helper only. It did not contact the device,
deploy the helper, start daemons on the live device, start Wi-Fi HAL,
scan/connect/link-up, use credentials, run DHCP, change routes, ping
externally, write sysfs/debugfs, or write boot partitions.

## Result

| check | result |
| --- | --- |
| helper marker bumped to v119 | pass |
| provider-first CNSS mode exposed in usage | pass |
| initial `cnss-daemon` suppression field emitted | pass |
| static ARM64 helper build | pass |
| artifact sha256 captured | pass |

## Implemented Mode

Mode:

```text
wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only
```

Expected order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,service74_gate,
servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,
per_mgr,vndservice_query,per_proxy,vndservice_query,cnss_daemon_retry
```

Key behavior:

- `cnss_diag` remains before the service `74` gate.
- Initial pre-provider `cnss-daemon` is not started.
- The service `74` gate waits after `cnss_diag` for this mode.
- `vndservicemanager` and `vendor.qcom.PeripheralManager` proof still happen
  before the single fresh `cnss-daemon`.
- Helper output includes
  `wifi_companion_start.initial_cnss_daemon.suppressed=1`.

## Validation

Executed:

```bash
mkdir -p tmp/wifi/v699-execns-helper-v119-build
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v699-execns-helper-v119-build/a90_android_execns_probe
file tmp/wifi/v699-execns-helper-v119-build/a90_android_execns_probe
sha256sum tmp/wifi/v699-execns-helper-v119-build/a90_android_execns_probe
strings tmp/wifi/v699-execns-helper-v119-build/a90_android_execns_probe | \
  rg 'a90_android_execns_probe v119|wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only|initial_cnss_daemon\\.suppressed'
```

Result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked
53c7d74d9a7d4ec2cbbaf7dc98e37af9bb165a9ccaabc45616dc3c12949d794c
a90_android_execns_probe v119
wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only
wifi_companion_start.initial_cnss_daemon.suppressed=%d
```

## Next Gate

Plan V700 as the bounded live proof:

- deploy helper v119 only;
- run the provider-first initial-suppressed CNSS mode;
- capture helper stdout/stderr, child pids, fd targets, maps/status, dmesg
  tail, WLFW/BDF/`wlan0` markers, and cleanup;
- keep Wi-Fi HAL, scan/connect, DHCP, credentials, route changes, and external
  ping blocked.
