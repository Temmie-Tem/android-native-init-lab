# Native Init V1894 Android Pending Client Msg22 Parser

## Summary

- Cycle: `V1894`
- Type: host-only normal-Android pending-client/msg22 parser against native V1893 absence
- Decision: `v1894-android-stateup-pending-client-observability-gap-host-pass`
- Label: `android-stateup-pending-client-observability-gap`
- Result: PASS
- Reason: Android normal state-up is present, but retained capture has zero pending-client/msg22 observability; native post-open still lacks msg22/WLFW/wlanmdsp
- Evidence: `tmp/wifi/v1894-android-pending-client-msg22-parser-v1909`

## Android Parse

- Android dir: `tmp/wifi/v1909-android-servloc-domain-handoff-live-20260603-213346/android-postfs-evidence/a90-v1909-servloc-domain`
- PM vote/WLFW request/wlan_pd/wlanmdsp/wlan0: `2` / `2` / `2` / `10` / `14.904181`
- contamination: PCIe-MHI `0` / esoc-boot-failed `0` / degraded257 `False`
- pending-client/msg22 counts: QMI-client `0` / msg22 `0` / restart-ind `0`
- first pending-client/msg22 lines: `` / `` / ``

## Source And Native Gate

- V1893 label/pass: `pm-msg22-pending-client-gate` / `True`
- source pending-client/msg22: `True` / `True`
- native open/msg22/wlanmdsp/WLFW69/wlan0: `1` / `0` / `0` / `0` / `0`

## Capture Filter Coverage

- commands path: `tmp/wifi/v1890-android-pm-msgid-log-capture-runner/host/android-pm-msgid-log-capture-commands.json`
- PerMgrSrv/QMI-client/QMI-service/peripheral-restart: `True` / `True` / `True` / `True`
- wlanmdsp/wlan_pd/WLFW request/service-notifier: `True` / `True` / `True` / `True`

## Selected Diff

- Label: `android-stateup-pending-client-observability-gap`.
- The retained V1753 normal Android capture still proves the internal path to `wlanmdsp.mbn` and `wlan0`, but it lacks the V1893 pending-client/msg22 log edge.
- The V1890 capture filter is adequate for the narrowed edge because it includes `PerMgrSrv`, `QMI client`, `QMI service`, and `peripheral restart` lines.
- The next live evidence remains one normal Android ADB/root capture followed by this parser and V1888; reject degraded 257s or pre-wlan0 PCIe/MHI captures.

## Safety Scope

- V1894 is host-only. It parses retained/generated text and writes local artifacts only.
- It performs no device command, flash, reboot, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.

## Next

- From native v724, use the rollbackable V1753/V1897 Android handoff and then run V1894/V1888 against the captured `android/` directory.
- Use V1890 only when normal Android ADB/root is already booted; it is not a flash-handoff runner.
- Promote only if pending-client/msg22 or another servreg/SSCTL trigger appears before the first `wlanmdsp.mbn` request.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
