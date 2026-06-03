# Native Init V1834 QIPCRTR Bound Poll/Recv Handoff

## Summary

- Cycle: `V1834`
- Type: one-run rollbackable QIPCRTR bound socket poll/recv discriminator
- Decision: `v1834-qipcrtr-bound-recv-poll-timeout-passive-rollback-pass`
- Result: PASS
- Reason: bound local QRTR port saw no inbound datagram during the 250 ms poll window and service74/wlan_pd stayed absent
- Evidence: `tmp/wifi/v1834-qipcrtr-bound-recv-poll-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`
- Post-rollback version evidence: `tmp/wifi/v1834-qipcrtr-bound-recv-poll-handoff/post-rollback-version-filtered.stdout.txt`
- Post-rollback selftest evidence: `tmp/wifi/v1834-qipcrtr-bound-recv-poll-handoff/post-rollback-selftest.stdout.txt`

## Post-Run Native Verification

- Version: `A90 Linux init 0.9.68 (v724)`
- Selftest: `pass=11 warn=1 fail=0`

## Gate Label

- QIPCRTR bound poll/recv label: `qipcrtr-bound-recv-poll-timeout-passive`
- WLFW QRTR readback label: `wlfw-readback-empty`
- service-locator domain label: `servloc-domain-wlan-pd-instance180`
- service-notifier label: `service-notifier-uninit`
- service74 raw label: `service74-raw-absent`
- PM-client return label: `pm-client-return-success`
- lower-state label: `stable-mdm3-offlining`
- safety ok: `True`

## Bound Poll/Recv State

- mode/family/type: `observed-local-node-bind-poll-recv-close` / `AF_QIPCRTR` / `SOCK_DGRAM`
- open/bind/close rc: `0` / `0` / `0`
- before-bind getsockname rc/node/port: `0` / `1` / `0`
- bind request family/node/port: `42` / `1` / `0`
- after-bind getsockname rc/family/node/port: `0` / `42` / `1` / `24227`
- bind skipped/reason: `` / ``
- poll attempted/skipped/reason: `1` / `` / ``
- poll timeout-ms/set-nonblock/poll rc/timeout/revents: `250` / `0` / `0` / `1` / `0`
- recv rc/skipped/reason/bytes: `` / `1` / `poll-timeout` / ``
- recv from family/node/port/first-u32: `` / `` / `` / ``
- socket counts before/before-poll/after-poll/after-close: `0` / `0` / `0` / `0`
- no connect/send/lookup/control/service-start: `1` / `1` / `1` / `1` / `1`
- `before_open` qipcrtr present/size/sockets: `1` / `1416` / `0`
- `while_bound_before_poll` qipcrtr present/size/sockets: `1` / `1416` / `0`
- `while_bound_after_poll` qipcrtr present/size/sockets: `1` / `1416` / `0`
- `after_close` qipcrtr present/size/sockets: `1` / `1416` / `0`

## Inherited QRTR/QMI Probes

- WLFW readback allowed/matrix/qmi-payload/result: `1` / `wlfw:69:0,1` / `0` / `complete`
- WLFW case0 service/empty/end/timeout events: `0` / `1` / `1` / `0`
- WLFW case1 service/empty/end/timeout events: `0` / `1` / `1` / `0`
- service-locator endpoint/status/result: `1`:`16464` / `found` / `domain-list-response-success`
- service-locator domain/name/instance: `1` / `msm/modem/wlan_pd` / `180`
- service-notifier early qmi/state/indication/result: `1` / `uninit` / `0` / `listener-response-success`
- service-notifier late qmi/state/indication/result: `1` / `uninit` / `0` / `listener-response-success`

## Registry And Publication State

- registry readable: `False`
- proc_net_qrtr open counts: `0,0,0`
- service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `2,2,2` / `0,0,0` / `0,0,0` / `0,0,0` / `0,0,0`
- service180/service74/wlan_pd raw: `1,1,1` / `0,0,0` / `0,0,0`
- precondition pd-mapper/subsys/pil/qmi/wlfw: `0,0,0` / `9,10,10` / `5,5,5` / `7,7,7` / `30,30,30`

## Lower State

- early/late service-notifier state: `uninit` / `uninit`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- PM-client register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1833/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The new V1834 observer opened one AF_QIPCRTR datagram socket, bound it with the observed local node and port `0`, set `O_NONBLOCK`, ran one 250 ms `poll(POLLIN)`, called `recvfrom` only if `POLLIN` was set, and closed it without connect or send on that socket.
- The inherited service-object route also ran bounded QRTR/QMI probes: WLFW `NEW_LOOKUP`/`DEL_LOOKUP` readback with `qmi_payload=0`, service-locator domain-list QMI, and service-notifier register/listener QMI.
- No WLFW request payload, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
- The route did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.
- `boot_wlan`, restart-PD request, forced RC1, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Classify the combined V1834 state before any next live action: bound-poll timeout, WLFW readback empty, service-locator `msm/modem/wlan_pd` instance `180`, and service-notifier state `uninit`.
- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
