# Native Init V1904 Service-notifier Passive-edge Handoff

## Summary

- Cycle: `V1904`
- Type: one-run rollbackable internal-modem service-notifier passive-edge discriminator
- Decision: `v1904-servnotif-new-server-180-only-stateup-edge-absent-rollback-pass`
- Result: PASS
- Reason: service-notifier new-server/service180 is visible, but service74, wlan_pd, requested wlanmdsp, WLFW69, and wlan0 remain absent with uninit listener state
- Evidence: `tmp/wifi/v1904-servnotif-passive-edge-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- service-notifier passive-edge label: `servnotif-new-server-180-only-stateup-edge-absent`
- WLFW QRTR readback label: `wlfw-readback-empty`
- service-locator domain label: `servloc-domain-wlan-pd-instance180`
- service-notifier listener label: `service-notifier-uninit`
- PM-client return label: `pm-client-return-success`
- lower-state label: `stable-mdm3-offlining`
- safety ok: `True`

## Passive Edge Evidence

- new-server/service180 positive: `True` / `True`
- service74/wlan_pd absent: `True` / `True`
- listener uninit/WLFW69 absent/wlan0 absent/requested-wlanmdsp absent: `True` / `True` / `True` / `True`
- raw service-notifier/new-server/qmi counts: `1,1,1` / `1,1,1` / `2,2,2`
- raw service180/service74/wlan_pd counts: `1,1,1` / `0,0,0` / `0,0,0`
- dmesg function-name counts new-server/new-server-work/root-ind/ack: `1` / `0` / `0` / `0`
- dmesg printk counts connection/state-indication: `2` / `0`

## QMI/QRTR Context

- service-locator endpoint/status/result: `1`:`16464` / `found` / `domain-list-response-success`
- service-locator domain/name/instance: `1` / `msm/modem/wlan_pd` / `180`
- service-notifier early qmi/state/indication/result: `1` / `uninit` / `0` / `listener-response-success`
- service-notifier late qmi/state/indication/result: `1` / `uninit` / `0` / `listener-response-success`
- WLFW readback allowed/matrix/qmi-payload/result: `1` / `wlfw:69:0,1` / `0` / `complete`

## Lower State

- early/late response state: `uninit` / `uninit`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- requested `wlanmdsp`/WLFW service69/wlan0 trigger flags: `0` / `0` / `0`
- PM-client register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1903/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The observer stayed on the internal modem route and used rollbackable native test boot plus `stage3/boot_linux_v724.img` rollback.
- It did not use private SDX50M, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCIe/MHI optimization, GDSC/PMIC/GPIO/regulator writes, forced RC1/case, fake-ONLINE, PCI rescan, or platform bind/unbind.
- It did not use Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request.

## Next

- If this label is 180-only absence, the next unit must target the passive servreg state-up indication source before any mutating restart-PD or connect attempt.
- If this label shows progress, stop and run the smallest WLFW69/`wlan0` prerequisite check before any credential-bearing action.
