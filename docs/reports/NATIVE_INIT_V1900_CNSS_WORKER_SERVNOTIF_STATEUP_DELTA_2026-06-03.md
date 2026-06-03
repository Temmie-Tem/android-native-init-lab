# Native Init V1900 CNSS Worker Service-notifier State-up Delta

## Summary

- Cycle: `V1900`
- Type: host-only classifier over Android V1899 worker trace and native worker/post-open evidence
- Decision: `v1900-cnss-worker-parity-servnotif-stateup-gap-host-pass`
- Label: `cnss-worker-parity-servnotif-stateup-gap`
- Result: PASS
- Reason: Android-good proves CNSS worker execution is sufficient only when service-notifier service74/wlan_pd state-up follows; native already reaches the worker/request path but remains service74/wlan_pd absent, service-notifier uninit, and no WLFW69/wlanmdsp/wlan0
- Evidence: `tmp/wifi/v1900-cnss-worker-servnotif-stateup-delta-classifier`

## Android Worker State-up

- V1899 decision/label/pass/rollback fail=0: `v1899-android-cnss-wlfw-worker-not-msg22-rollback-pass` / `android-cnss-wlfw-worker-not-msg22` / `True` / `True`
- CNSS uprobe/worker hits: `5` / `1`
- msg22/pending-client hits: `0` / `0`
- WLFW request/wlan_pd/wlanmdsp/wlan0: `5` / `2` / `20` / `15.181203`
- contamination pre-wlan0 PCIe-MHI/eSoC/degraded257: `0` / `0` / `False`
- CNSS trace: `wlfw_start -> dms_init -> pthread_create -> worker_create_success -> wlfw_service_request_entry`.

## Native Worker Parity

- V1736 decision/pass: `v1736-wlfw-start-reached-downstream-block-rollback-pass` / `True`
- WLFW start/worker/request hits: `1` / `1` / `1`
- WLFW ind-register/cap/requested-wlanmdsp/service69: `0` / `0` / `0` / `0`
- V1760 legacy label/pass: `request-generation-gap-before-firmware-serving` / `True`

## Latest Native Post-open

- V1885 decision/label/pass: `v1885-internal-pm-qmi-servreg-trigger-source-diff-host-pass` / `pm-msg22-servreg-trigger-trace-gap` / `True`
- V1898 decision/label/pass: `v1898-service180-present-wlan-pd-stateup-gap-host-pass` / `service180-present-wlan-pd-stateup-gap` / `True`
- PM register/connect/open: `0` / `0` / `/dev/subsys_modem` fd `0x7` state `0x2`
- DMS/WLFW request/ind-register/cap/msg22: `1` / `1` / `0` / `0` / `0`
- service180/service74/wlan_pd: `1,1,1` / `0,0,0` / `0,0,0`
- service-notifier/WLFW69/wlanmdsp/wlan0: `uninit` -> `uninit` / `0` / `0` / `0`

## Selected Diff

- Label: `cnss-worker-parity-servnotif-stateup-gap`.
- Do not chase pm-service msg22: Android state-up still has zero msg22/pending-client hits.
- Do not chase CNSS worker creation: Android proves the worker path, and native V1736 already reached worker/request without downstream progress.
- Do not chase firmware serving: Android requests and serves `wlanmdsp.mbn`; native still has no request.
- The remaining blocker is the internal service-notifier/WLFW server state-up edge: service74/`msm/modem/wlan_pd` publication and WLFW service 69 before `wlanmdsp.mbn`.

## Safety Scope

V1900 is host-only. It parses retained manifests/reports and writes local classifier artifacts only. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or partition write.

## Next

- Next live/native unit should instrument the service-notifier service74/180 and WLFW service 69 transition around native post-open without changing eSoC/PCIe/GDSC or Wi-Fi connection state.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0`.
