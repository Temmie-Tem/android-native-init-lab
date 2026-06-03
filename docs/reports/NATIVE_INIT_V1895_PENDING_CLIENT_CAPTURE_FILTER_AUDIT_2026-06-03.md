# Native Init V1895 Pending Client Capture Filter Audit

## Summary

- Cycle: `V1895`
- Type: host-only audit for V1890/V1894 pending-client capture-filter coverage
- Decision: `v1895-pending-client-capture-filter-audit-host-pass`
- Label: `pending-client-capture-filter-qmi-client-covered`
- Result: PASS
- Reason: V1890 and V1894 now both cover QMI client pending-slot logs for the V1893 msg22 gate
- Evidence: `tmp/wifi/v1895-pending-client-capture-filter-audit`

## Checks

- V1890/V1894 ready: `True` / `True`
- V1890 filter/request-lines QMI client: `True` / `True`
- V1894 requires QMI client: `True`
- core filter terms present: `True`

## Coverage

- coverage file: `tmp/wifi/v1894-android-pending-client-msg22-parser/host/capture-filter-coverage.json`
- PerMgrSrv/QMI-client/QMI-service/peripheral-restart: `True` / `True` / `True` / `True`
- wlanmdsp/wlan_pd/WLFW/service-notifier: `True` / `True` / `True` / `True`

## Selected Diff

- Label: `pending-client-capture-filter-qmi-client-covered`.
- V1893 narrowed the missing edge to pm-service pending QMI client creation and msg22 indication.
- V1890 previously covered `QMI service` and `peripheral restart`, but not the standalone `QMI client` connected/disconnected log string.
- The future normal-Android capture now includes `QMI client`, so V1894 can promote if pending-client/msg22 appears before `wlanmdsp.mbn`.

## Safety Scope

- host-only/device-contact: `True` / `False`
- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `False` / `False` / `False` / `False` / `False`
- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `False` / `False` / `False` / `False` / `False` / `False`

## Next

- Run the normal Android capture only when ADB/root is available; reject degraded 257s captures and any pre-wlan0 PCIe/MHI path.
- Parse that capture with V1894 and V1888 before any native trigger replay or Wi-Fi connect attempt.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
