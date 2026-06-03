# Native Init V1832 QIPCRTR Bound Poll/Recv Classifier

## Summary

- Cycle: `V1832`
- Type: host-only classifier over V1831 QIPCRTR observed-local-node bind handoff
- Decision: `v1832-passive-bound-qipcrtr-poll-recv-target-host-pass`
- Result: PASS
- Reason: Native can allocate a local QIPCRTR port without lookup/control traffic, but no lower publication follows; the next source target can hold that bound socket briefly and run timeout-bounded poll/recvfrom with no connect, send, lookup, service start, or QRTR control payload
- Evidence: `tmp/wifi/v1832-qipcrtr-bound-recv-poll-classifier`
- Source evidence: `tmp/wifi/v1831-qipcrtr-local-node-bind-handoff`

## Native V1831 Shape

- V1831 decision: `v1831-qipcrtr-local-node-bind-gets-local-port-passive-rollback-pass`
- local-bind label/mode: `qipcrtr-local-node-bind-gets-local-port-passive` / `observed-local-node-bind-getsockname-close`
- open/bind/close rc: `0` / `0` / `0`
- before-bind node/port: `1` / `0`
- bind request family/node/port: `42` / `1` / `0`
- after-bind family/node/port: `42` / `1` / `24246`
- socket counts before/while-bound/after-close: `0` / `0` / `0`
- no connect/send/lookup/control/service-start: `1` / `1` / `1` / `1` / `1`
- registry readable/proc open counts: `False` / `0,0,0`
- service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `2,2,2` / `0,0,0` / `0,0,0` / `0,0,0` / `0,0,0`
- service180/service74/wlan_pd counts: `1,1,1` / `0,0,0` / `0,0,0`
- precondition pd-mapper/subsys/pil/qmi/wlfw: `0,0,0` / `9,10,10` / `5,5,5` / `7,7,7` / `30,30,30`
- notifier early/late state: `uninit` / `uninit`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`

## Interpretation

- Local-node bind is the first native QIPCRTR endpoint allocation that returns a nonzero local port.
- Endpoint allocation alone does not publish service 74, wlan_pd, WLFW service 69, MHI, or `wlan0`.
- The next source/build target should only add a short timeout-bounded bound-socket `poll` plus `recvfrom` observer; it must not connect, send, issue QRTR lookup/control packets, or start services.
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain invalid because WLFW service 69 and `wlan0` are absent.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, bind/connect/send QRTR sockets, send QRTR lookup/control packets, start services, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
