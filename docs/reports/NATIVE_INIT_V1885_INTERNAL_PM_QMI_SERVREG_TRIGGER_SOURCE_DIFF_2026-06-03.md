# Native Init V1885 Internal PM QMI/servreg Trigger Source Diff

## Summary

- Cycle: `V1885`
- Type: host-only source/retained-trace classifier for the internal-modem guest-PD trigger gap
- Decision: `v1885-internal-pm-qmi-servreg-trigger-source-diff-host-pass`
- Label: `pm-msg22-servreg-trigger-trace-gap`
- Result: PASS
- Reason: pm-service exposes QMI msg 0x22 peripheral-restart request/indication and libperipheral is Binder-only; Android normal reaches wlanmdsp after PM vote, but the retained normal trace lacks pm-service QMI observability while native post-open has zero msg22 indication and stays wlan_pd uninit
- Evidence: `tmp/wifi/v1885-internal-pm-qmi-servreg-trigger-source-diff`

## Source Map

- pm-service binary: `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service`
- QMI imports present: `True`
- QMI msg dispatch 0x20/0x21/0x22: `True` / `True` / `True`
- msg 0x22 request string: `True`
- msg 0x22 response/indication paths: `True` / `True`
- msg 0x22 pending-client slot seen: `True`
- libperipheral Binder/vndbinder/PM-register/QMI-imports: `True` / `True` / `True` / `False`
- source artifacts: `{"libperipheral-binder-strings.txt": "host/libperipheral-binder-strings.txt", "libperipheral-pm-register-connect-0x612c-0x6700.S": "host/libperipheral-pm-register-connect-0x612c-0x6700.S", "pm-service-peripheral-restart-handler-0x716c-0x72e0.S": "host/pm-service-peripheral-restart-handler-0x716c-0x72e0.S", "pm-service-post-ack-msg22-ind-0x8950-0x8a80.S": "host/pm-service-post-ack-msg22-ind-0x8950-0x8a80.S", "pm-service-qmi-loop-0x73b0-0x761c.S": "host/pm-service-qmi-loop-0x73b0-0x761c.S", "pm-service-qmi-msgid-dispatch-0x6ebc-0x7380.S": "host/pm-service-qmi-msgid-dispatch-0x6ebc-0x7380.S", "pm-service-qmi-servreg-strings.txt": "host/pm-service-qmi-servreg-strings.txt"}`

## Android Normal Window

- Evidence: `tmp/wifi/v1753-android-good-wlan-pd-firmware-request/android-postfs-evidence/a90-v1753-wlan-pd-fwreq`
- PM register/vote counts: `2` / `2`
- PM vote / WLFW request / wlanmdsp first times: `04:17:30.688` / `04:17:30.756` / `04:17:31.380`
- wlan_pd indication / wlan0 seconds: `9.672951` / `15.242158`
- PCIe-or-MHI lines before wlan0: `0`
- Retained pm-service msg22 log hits: `0`
- service-notifier line: `[    9.672951]  [5: kworker/u16:13:  335] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1`
- WLFW connected line: `06-03 04:17:31.660  2124  2227 I cnss-daemon: WLFW service connected`

## Native Post-open State

- V1884 decision/label/pass: `v1884-post-pm-success-guest-pd-trigger-diff-selected-host-pass` / `post-pm-success-wlfw-qmi-servreg-trigger-gap` / `True`
- PM client register/connect rc: `0` / `0`
- open context path/fd/state: `/dev/subsys_modem` / `0x7` / `0x2`
- post-ack open call/return/msg22-ind hits: `1` / `1` / `0`
- SSCTL/service180/wlan_pd raw counts: `1,1,1` / `1,1,1` / `0,0,0`
- WLFW request/DMS/ind-register/cap hits: `1` / `1` / `0` / `0`
- requested wlanmdsp / WLFW service69 / wlan0: `0` / `0` / `0`
- service-notifier early/late state: `uninit` / `uninit`

## Selected Diff

- Label: `pm-msg22-servreg-trigger-trace-gap`.
- pm-service has a concrete modem-facing QMI msg `0x22` peripheral-restart request/indication path; libperipheral_client only covers the Binder PM register/vote surface.
- Android-normal retained evidence proves the correct internal sequence through PM vote, `wlanmdsp.mbn`, `msm/modem/wlan_pd`, and `wlan0` with no PCIe/MHI contamination.
- Native proves PM vote/open now succeeds but no msg `0x22` indication path fires, service-notifier remains `uninit`, WLFW service 69 is absent, and no `wlanmdsp.mbn` request occurs.
- The next useful live comparison is a read-only normal-Android pm-service QMI/servreg/SSCTL trace around PM vote to `wlanmdsp`, then the same native post-open trace; do not infer this from SDX50M, PCIe, or GDSC evidence.

## Safety Scope

V1885 is host-only. It reads retained evidence and local binaries, runs local disassembly/string extraction, and writes local reports only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.

## Next

- Capture normal Android boot, not the degraded 257s boot, with read-only pm-service QMI msg-id/servreg/SSCTL visibility from PM vote through the first `wlanmdsp.mbn` request.
- Diff that against native post-`/dev/subsys_modem` open; expected discriminator is msg `0x22`/servreg transition observed on Android and absent on native, or proof that another servreg/SSCTL request is the actual trigger.
- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present in native init.
