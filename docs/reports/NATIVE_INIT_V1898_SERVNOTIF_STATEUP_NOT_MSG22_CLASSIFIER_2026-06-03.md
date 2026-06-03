# Native Init V1898 Service-notifier State-up Not Msg22 Classifier

## Summary

- Cycle: `V1898`
- Type: host-only classifier over autonomous Android-good V1897 and native post-open evidence
- Decision: `v1898-service180-present-wlan-pd-stateup-gap-host-pass`
- Label: `service180-present-wlan-pd-stateup-gap`
- Result: PASS
- Reason: Normal Android reaches ordered internal service-notifier state-up without pm-service msg22 hits; native post-open has service180 visible but remains service74/wlan_pd absent, service-notifier uninit, and no WLFW69/wlanmdsp/wlan0
- Evidence: `tmp/wifi/v1898-servnotif-stateup-not-msg22-classifier`

## Android Normal Internal Path

- Evidence: `tmp/wifi/v1897-android-normal-pm-msg22-edge-handoff-live3-20260603-193411/android-postfs-evidence/a90-v1897-pm-edge`
- V1897 decision/label/pass/rollback fail=0: `v1897-android-stateup-msg22-uprobe-observability-gap-rollback-pass` / `android-stateup-msg22-uprobe-observability-gap` / `True` / `True`
- ordered SSCTL/service74/service180/WLFW request/wlan_pd/wlan0: `True`
- times seconds: `{"service180": 7.259086, "service74": 7.258872, "ssctl_modem": 7.220222, "wlan0": 14.881999, "wlan_pd": 9.622854, "wlfw_request": 8.735257}`
- PM vote/WLFW request/service74/service180/wlan_pd/wlanmdsp counts: `2` / `2` / `1` / `1` / `2` / `20`
- contamination pre-wlan0 PCIe-MHI/eSoC/degraded257: `0` / `0` / `False`
- pm-service msg22 log/uprobe hits: `0` / `0` / msg22 `0`
- V1888/V1894 labels: `android-stateup-without-msg22-log-observability-gap` / `android-stateup-pending-client-observability-gap`
- first service180 line: `[    7.259086]  [3:  kworker/u16:1:   75] service-notifier: service_notifier_new_server: Connection established between QMI handle and 180 service`
- first wlan_pd line: `[    9.622854]  [4:  kworker/u16:3:  245] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1`

## Native Post-open Gap

- V1885 decision/label/pass: `v1885-internal-pm-qmi-servreg-trigger-source-diff-host-pass` / `pm-msg22-servreg-trigger-trace-gap` / `True`
- PM register/connect/open: `0` / `0` / `/dev/subsys_modem` fd `0x7` state `0x2`
- post-open/msg22/WLFW request/ind-register/cap: `1` / `0` / `1` / `0` / `0`
- service180/service74/wlan_pd counts V1885: `1,1,1` / n/a / `0,0,0`
- service180/service74/wlan_pd counts V1816: `1,1,1` / `0,0,0` / `0,0,0`
- service180/service74/wlan_pd counts V1826: `1,1,1` / `0,0,0` / `0,0,0`
- service-notifier state and lower gates: `uninit` -> `uninit` / WLFW69 `0` / wlanmdsp `0` / wlan0 `0`

## Selected Diff

- Label: `service180-present-wlan-pd-stateup-gap`.
- V1897 was the rollbackable autonomous Android handoff path, not the no-flash V1890 runner.
- Normal Android proves the internal modem path: SSCTL modem, service-notifier 74/180, CNSS WLFW request, `msm/modem/wlan_pd`, `wlanmdsp.mbn`, then `wlan0` near 15s.
- The same normal window has zero pm-service msg22 log hits and zero hits on the known msg22 dispatch uprobes, so msg22 is not the selected trigger label.
- Native already opens `/dev/subsys_modem` and sees service180/SSCTL preconditions, but service74 and `msm/modem/wlan_pd` never publish and service-notifier remains `uninit`.

## Safety Scope

V1898 is host-only. It parses retained manifests/logs and writes local classifier artifacts only. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or partition write.

## Next

- If another live comparison is needed, use the same V1753/V1897 autonomous Android-handoff and pre-arm CNSS/QRTR/service-notifier observability before `cnss-daemon` starts.
- Keep the target on internal modem service-notifier/WLFW state-up; do not use SDX50M, PCIe/MHI, eSoC, GDSC, PMIC, GPIO, or regulator gates.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0`.
