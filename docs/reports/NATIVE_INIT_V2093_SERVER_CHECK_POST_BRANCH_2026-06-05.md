# Native Init V2093 Server-Check Post-Branch Classifier

## Summary

- Cycle: `V2093`
- Type: host-only corrective classifier over existing rollback-verified native evidence.
- Decision: `v2093-server-check-complete-no-ota-wlanmdsp-host-pass`
- Label: `server-check-complete-no-ota-wlanmdsp`
- Pass: `True`
- Reason: native repeatedly completes the server_check.txt WRQ payload but never enters the ota_firewall or wlanmdsp branch despite AP-side PerMgr/WLFW and wlan_pd/icnss_qmi progress
- Evidence: `tmp/wifi/v2093-server-check-post-branch`

## Correction

- The simplified `server_check=0` wording from logdw-only counters is incomplete: the readwrite sampler shows `server_check.txt` appears with the Android 5-byte `hello` payload in every checked native run.
- The live gap is therefore after the `server_check.txt` WRQ completes and before the Android `ota_firewall/ruleset` and `wlanmdsp.mbn` requests.
- `mcfg.tmp` remains downstream/noise for this gate; Android requests `wlanmdsp.mbn` before the compared `mcfg` window.

## Matrix

| run | label | rollback | per_mgr | cap_bdf_cal | msg21 | server_check_file | sample | payload | ota_file | ota_log | mcfg | wlanmdsp | fw_ready | wlan0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V2059 | cnss-permgr-register-vote-success-no-wlanmdsp | True | True | True | False | True | 1 | hello | False | 0 | 11 | 0 | 0 | 0 |
| V2081 | wlfw-late-msg21-native-msg21-no-fw-ready | True | True | True | True | True | 1 | hello | False | 0 | 3 | 0 | 0 | 0 |
| V2083 | icnss-qcacld-no-wlanmdsp-request | True | True | True | True | True | 1 | hello | False | 0 | 5 | 0 | 0 | 0 |
| V2091 | macloader-no-mac-addr-write | True | True | False | True | True | 1 | hello | False | 0 | 6 | 0 | 0 | 0 |

## Next Gate

- Next live discriminator should target the transition immediately after `server_check.txt=hello`: why the modem does not issue Android's `ota_firewall/ruleset` RRQ and then `wlanmdsp.mbn` RRQ.
- Do not spend more cycles on MAC assignment, AP-side PerMgr/pm-service/rild, `server_check` reachability, mcfg readback, or external SDX50M/PCIe/eSoC paths for this unit.

## Inputs

| run | manifest | helper |
| --- | --- | --- |
| v2059 | tmp/wifi/v2059-permgr-vote-focused-handoff/manifest.json | tmp/wifi/v2059-permgr-vote-focused-handoff/v2058-handoff/test-v1393-helper-result.stdout.txt |
| v2081 | tmp/wifi/v2081-wlfw-late-msg21-native-handoff/manifest.json | tmp/wifi/v2081-wlfw-late-msg21-native-handoff/v2080-handoff/test-v1393-helper-result.stdout.txt |
| v2083 | tmp/wifi/v2083-icnss-qcacld-post-bdf-handoff/manifest.json | tmp/wifi/v2083-icnss-qcacld-post-bdf-handoff/v2082-handoff/test-v1393-helper-result.stdout.txt |
| v2091 | tmp/wifi/v2091-macloader-property-service-handoff/manifest.json | tmp/wifi/v2091-macloader-property-service-handoff/v2090-handoff/test-v1393-helper-result.stdout.txt |

## Related Reports

- Android/native ordering reference: `docs/reports/NATIVE_INIT_V2053_PRE_WLANMDSP_TRIGGER_EVENT_DIFF_2026-06-04.md`
- Superseded simplification to correct: `docs/reports/NATIVE_INIT_V2092_MAC_FALSIFIER_TFTP_REDIRECT_2026-06-05.md`

## Safety

- Host-only parse/report generation; no flash, reboot, adb device mutation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, tftp ptrace, eSoC/PCIe/GDSC/PMIC/GPIO path, firmware/partition write, or `sda29` write.
