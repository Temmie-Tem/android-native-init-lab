# Native Init V1347 Android Earliest Response Recapture Live

## Summary

- Cycle: `V1347`
- Type: bounded Android handoff plus read-only earliest response recapture
- Decision: `v1347-android-wlfw-before-subsys-esoc0`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1347-android-earliest-response-handoff/manifest.json`
  - `tmp/wifi/v1347-android-earliest-response-handoff/summary.md`
  - `tmp/wifi/v1347-android-earliest-response-handoff/v1347-android-earliest-response-recapture-run/manifest.json`
  - `tmp/wifi/v1347-android-earliest-response-handoff/v1347-android-earliest-response-recapture-run/summary.md`
- Scripts:
  - `scripts/revalidation/android_earliest_response_handoff_v1347.py`
  - `scripts/revalidation/native_wifi_android_earliest_response_recapture_v1347.py`

V1347 temporarily booted the known Android image, collected read-only Android
timing surfaces, then restored native v724. The handoff and rollback sequence
completed successfully.

## Marker Order

| marker | count | first_s | evidence |
| --- | ---: | ---: | --- |
| `subsys_get_modem` | 2 | 5.822170 | `[5.822170] __subsystem_get: modem count:0` |
| `cnss-daemon wlfw_start` | 4 | 8.035751 | `[8.035751] cnss-daemon wlfw_start: Starting` |
| `subsys_get_esoc0` | 1 | 8.251801 | `[8.251801] __subsystem_get: esoc0 count:0` |
| `icnss_qmi` | 1 | 9.353921 | `[9.353921] icnss_qmi: QMI Server Connected: state: 0x980` |
| `BDF` | 2 | 9.517672 | `[9.517672] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin` |
| `WLAN FW ready` | 2 | 14.464681 | `[14.464681] icnss: WLAN FW is ready: 0xd87` |
| `wlan0` | 3 | 14.779047 | `[14.779047] dev : wlan0 : event : 16` |
| `PCIe RC1/L0` | 0 |  | no public marker captured |
| `MHI` / MHI pipe | 0 |  | no public marker captured |
| `ks` | 0 |  | no process marker captured |

## Interpretation

Android again shows the first `cnss-daemon` WLFW userspace marker before the
captured `__subsystem_get(esoc0)` line. The Android-positive chain then reaches
ICNSS QMI, BDF download, firmware-ready, and `wlan0`.

This weakens the earlier assumption that the captured eSoC marker is the first
observable prerequisite for the Android-positive path. It may be late,
secondary, or simply not the public marker that explains why Android reaches
WLFW while native does not.

## Limitations

- `v1347-process-fds` timed out after 30 seconds, so process/fd absence for
  `ks`, `/dev/subsys_esoc0`, `/dev/subsys_modem`, and MHI pipe is weak evidence.
- Public Android dmesg/sysfs still did not expose PCIe RC1/L0 or MHI surfaces,
  even though `wlan0` was created.
- The useful positive anchors are therefore the Android dmesg chain:
  `wlfw_start` -> `icnss_qmi` -> BDF -> firmware-ready -> `wlan0`.

## Post-rollback Health

| check | result |
| --- | --- |
| native version | `A90 Linux init 0.9.68 (v724)` |
| selftest | `pass=11 warn=1 fail=0` |
| netservice | `enabled=no`, `ncm0=absent`, `tcpctl=stopped` |

## Safety

The only device mutation was the bounded Android boot-image handoff and native
rollback. V1347 did not start Wi-Fi HAL from our tools, did not scan/connect,
did not use credentials, did not run DHCP or route changes, and did not perform
an external ping.

## Next

V1348 should be host-only. It should reconcile V1345's native lower-route
no-transition result with V1347's Android-positive `wlfw_start`/QMI/BDF/`wlan0`
chain and decide whether the next branch should target CNSS/WLFW runtime
prerequisites rather than more PMIC/GPIO/GDSC/eSoC mutation.
