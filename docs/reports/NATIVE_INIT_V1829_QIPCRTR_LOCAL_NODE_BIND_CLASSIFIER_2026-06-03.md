# Native Init V1829 QIPCRTR Local-Node Bind Classifier

## Summary

- Cycle: `V1829`
- Type: host-only classifier over V1828 QIPCRTR auto-bind handoff
- Decision: `v1829-qipcrtr-local-node-autobind-target-host-pass`
- Result: PASS
- Reason: Binding AF_QIPCRTR with node 0 and port 0 fails with EINVAL while the unbound socket reports local node 1; the next source target can try observed-local-node/port-0 bind without connect, send, lookup, service start, or QRTR control payload
- Evidence: `tmp/wifi/v1829-qipcrtr-local-node-bind-classifier`
- Source evidence: `tmp/wifi/v1828-qipcrtr-autobind-handoff`

## Native V1828 Shape

- V1828 decision: `v1828-qipcrtr-autobind-fails-rollback-pass`
- auto-bind label/mode: `qipcrtr-autobind-fails` / `local-autobind-getsockname-close`
- open/bind/close rc: `0` / `-1` / `0`
- before-bind node/port: `1` / `0`
- bind request family/node/port: `42` / `0` / `0`
- bind errno/error: `22` / `Invalid argument`
- sockets before/while-bound/after-close: `0` / `0` / `0`
- no connect/send/lookup/control/service-start: `1` / `1` / `1` / `1` / `1`
- service180/service74/wlan_pd counts: `1,1,1` / `0,0,0` / `0,0,0`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`

## Interpretation

- Node-zero bind is not the correct native QRTR endpoint-allocation form on this kernel.
- The next source/build target should try the observed local node `1` with port `0`, still without connect, send, service lookup, service start, or QRTR control payload.
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain invalid because WLFW service 69 and `wlan0` are absent.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, bind/connect/send QRTR sockets, send QRTR lookup/control packets, start services, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
