# Native Init V1692 CNSS Non-log Control-flow Classifier

## Summary

- Cycle: `V1692`
- Type: host-only cnss-daemon static control-flow classifier
- Decision: `v1692-cnss-nonlog-control-flow-map-pass`
- Result: `PASS`
- Reason: V1691 closed the property lookup gap; cnss-daemon static control-flow targets are mapped for bounded non-log live evidence
- Evidence: `tmp/wifi/v1692-cnss-nonlog-control-flow`

## V1691 Basis

- V1691 decision: `v1691-cnss-output-still-invisible-rollback-pass`
- V1691 label: `cnss-output-still-invisible`
- Rollback OK: `True`
- property lookup all_match: `1`
- kmsg/debug values: `1` / `4`
- cnss-daemon running: `1`
- wlfw_start seen through logs: `0`
- first failure slug: `none`

## Static Targets

- Binary: `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- SHA256: `bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc`
- Size: `95112` bytes
- logging helper candidate: `cnss-daemon+0xa21c`
- `wlfw_start` entry: `cnss-daemon+0xec00`
- main `wlfw_start` call: `cnss-daemon+0x9220`
- main `wlfw_start` failure log: `cnss-daemon+0x9318`

## Main Init Sequence

| Step | call site | target | failure site | failure/log string |
| --- | --- | --- | --- | --- |
| `debug_level_property_get` | `0x9128` | `property_get_int32@plt` | `-` | `persist.vendor.cnss-daemon.debug_level` |
| `kmsg_logging_property_get` | `0x9140` | `property_get_int32@plt` | `-` | `persist.vendor.cnss-daemon.kmsg_logging` |
| `nl_loop_init` | `0x91c0` | `0x939c` | `0x924c` | `Failed to init nl_loop` |
| `netlink_common_init` | `0x91c8` | `0x12880` | `0x929c` | `Failed to init netlink common` |
| `interop_issues_ap_init` | `0x91d0` | `0x1397c` | `0x92b0` | `Failed to init interop issues ap` |
| `hang_issues_ap_init` | `0x91d8` | `0x13b8c` | `0x92c4` | `Failed to init hang issues ap` |
| `gw_update_loop_init` | `0x91e0` | `0x11960` | `0x92d8` | `Failed to init gw update loop` |
| `user_interface_init` | `0x91e8` | `0xfdc4` | `0x92ec` | `Failed to init user interface` |
| `wlan_service_start` | `0x91f4` | `0xafdc` | `0x9300` | `Failed to start wlan service` |
| `wlan_datapath_service_start` | `0x91fc` | `0xb2a4` | `0x930c` | `Failed to start wlan datapath service` |
| `wlfw_start` | `0x9220` | `0xec00` | `0x9318` | `Failed to start wlfw service` |

## Interpretation

- V1691 already proves the private property namespace can read `persist.vendor.cnss-daemon.kmsg_logging=1` and `persist.vendor.cnss-daemon.debug_level=4`.
- Missing `wlfw_start` in dmesg/syslog is therefore not explained by property lookup failure.
- The stripped stock `cnss-daemon` contains a direct `wlfw_start` target at `cnss-daemon+0xec00`, called from the main init sequence at `+0x9220`.
- The next proof should avoid Android log output entirely and observe process control flow, liveness, thread state, file descriptors, sockets, and WLFW service 69 directly.

## V1693 Next Gate

- Reuse the V1680/V1691 internal-modem firmware-serve route only: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.
- Add bounded non-log evidence around `cnss-daemon+0xec00` using tracefs uprobe if available; otherwise use a documented fallback of maps/liveness/thread-state/fd/socket sampling.
- Labels: `cnss-wlfw-entry-hit-downstream-wait`, `cnss-wlfw-entry-not-hit-init-stall`, `cnss-process-exited-before-wlfw`, `cnss-uprobe-unavailable-fallback-needed`.
- Keep service-manager, PM trio, `boot_wlan` as a WLFW trigger, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping disabled.
