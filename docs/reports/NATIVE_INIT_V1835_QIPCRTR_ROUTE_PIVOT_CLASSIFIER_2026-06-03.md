# Native Init V1835 QIPCRTR Route Pivot Classifier

## Summary

- Cycle: `V1835`
- Type: host-only classifier over V1834 rollback-verified QIPCRTR bound poll/recv evidence
- Decision: `v1835-qipcrtr-mechanics-cleared-wlan-pd-uninit-blocker-host-pass`
- Result: PASS
- Reason: Bound local QRTR port works but ambient poll times out; inherited WLFW readback is empty, service-locator resolves msm/modem/wlan_pd instance 180, and service-notifier stays uninit/no-indication, so stop QRTR socket mechanics and target the WLAN-PD UNINIT transition prerequisite before Wi-Fi HAL/scan/connect
- Evidence: `tmp/wifi/v1835-qipcrtr-route-pivot-classifier`
- Source evidence: `tmp/wifi/v1834-qipcrtr-bound-recv-poll-handoff`

## Source Gates

- V1834 decision: `v1834-qipcrtr-bound-recv-poll-timeout-passive-rollback-pass`
- V1834 reason: bound local QRTR port saw no inbound datagram during the 250 ms poll window and service74/wlan_pd stayed absent
- rollback ok: `True`
- safety ok: `True`
- PM projection/list commit/init-fail: `list-commit-progress` / `2` / `0`
- PM names/devnodes: `SDX50M,modem` / `/dev/subsys_esoc0,/dev/subsys_modem`
- PM client register/connect/return rc: `0` / `0` / `0`

## Bound QIPCRTR Observer

- label/mode: `qipcrtr-bound-recv-poll-timeout-passive` / `observed-local-node-bind-poll-recv-close`
- family/type: `AF_QIPCRTR` / `SOCK_DGRAM`
- open/bind/close rc: `0` / `0` / `0`
- before-bind node/port: `1` / `0`
- bind request family/node/port: `42` / `1` / `0`
- after-bind family/node/port: `42` / `1` / `24227`
- poll timeout-ms/set-nonblock/rc/timeout/revents: `250` / `0` / `0` / `1` / `0`
- recv rc/skipped/reason: `` / `1` / `poll-timeout`
- socket counts before/before-poll/after-poll/after-close: `0` / `0` / `0` / `0`
- observer no connect/send/lookup/control/service-start: `1` / `1` / `1` / `1` / `1`

## Inherited QRTR/QMI Probes

- WLFW readback label/matrix/qmi/result: `wlfw-readback-empty` / `wlfw:69:0,1` / `0` / `complete`
- `case_0` service/instance/status: `69` / `0` / `complete`
- `case_0` qmi/send/new/del: `0` / `1` / `0` / `0`
- `case_0` events/service/empty/end/timeout: `1` / `0` / `1` / `1` / `0`
- `case_1` service/instance/status: `69` / `1` / `complete`
- `case_1` qmi/send/new/del: `0` / `1` / `0` / `0`
- `case_1` events/service/empty/end/timeout: `1` / `0` / `1` / `1` / `0`
- service-locator label: `servloc-domain-wlan-pd-instance180`
- service-locator allowed/qmi/send/response/result: `1` / `1` / `1` / `1` / `domain-list-response-success`
- service-locator endpoint: `found` node `1` port `16464`
- service-locator domains: count `1`, wlan-like `1`, first `msm/modem/wlan_pd` instance `180`
- service-notifier label: `service-notifier-uninit`
- early listener allowed/qmi: `1` / `1`
- early listener endpoint: `found` node `0` port `2`
- early listener response: success `1`, state `uninit` (`0x7fffffff`)
- early listener indication/ack/result: `0` / `0` / `listener-response-success`
- late probe allowed/qmi/endpoint/result: `1` / `0` / `found` node `0` port `2` / `endpoint-found`
- late listener allowed/qmi: `1` / `1`
- late listener endpoint: `found` node `0` port `2`
- late listener response: success `1`, state `uninit` (`0x7fffffff`)
- late listener indication/ack/result: `0` / `0` / `listener-response-success`

## Lower Publication State

- lower state/service74 label: `stable-mdm3-offlining` / `service74-raw-absent`
- raw service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `2,2,2` / `0,0,0` / `0,0,0` / `0,0,0` / `0,0,0`
- raw service180/service74/wlan_pd/WLFW counts: `1,1,1` / `0,0,0` / `0,0,0` / `30,30,30`
- service-notifier early/late state: `uninit` / `uninit`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- requested wlanmdsp / service69 seen / wlan0 present: `0` / `0` / `0`

## Interpretation

- The new V1834 bound observer socket allocates a local QRTR port and then times out on passive poll without inbound ambient data.
- QRTR socket mechanics are no longer the highest-value next target: local bind, nonzero local port, nonblocking poll, and clean close are all proven.
- The inherited route shows QRTR lookup/control and QMI service-locator/notifier surfaces are reachable, but WLFW service 69 remains absent and wlan_pd service-notifier stays `uninit` early and late.
- The next unit should stay below Wi-Fi HAL/scan/connect and classify the safe prerequisite that can move service-notifier out of `uninit` or cause WLFW service 69 publication.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

The new V1834 bound observer socket had no connect/send/QRTR lookup/control/service-start. The inherited V1834 route did run bounded QRTR NEW_LOOKUP/DEL_LOOKUP readback without QMI payload, service-locator domain-list QMI, and service-notifier register/listener QMI; no WLFW request payload was sent.
