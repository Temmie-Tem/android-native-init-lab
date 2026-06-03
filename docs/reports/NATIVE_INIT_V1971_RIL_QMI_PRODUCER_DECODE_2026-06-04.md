# V1971 RIL QMI Producer Decode

- generated: `2026-06-03T20:25:35.390014+00:00`
- decision: `v1971-ril-dms-nas-observed-post-wlanpd-up-producer-window-missed`
- label: `ril-dms-nas-observed-post-up`
- pass: `True`
- reason: RIL DMS/NAS QMI traffic is decoded, but rild attached after wlan_pd UP; V1970 is not a pre-UP producer-window trace
- source evidence: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1970-android-ril-qmi-producer-capture-handoff/android-postfs-evidence/a90-v1970-ril-qmi-producer`
- output: `/home/temmie/dev/A90_5G_rooting/tmp/wifi/v1971-ril-qmi-producer-decode`

## Timing

| field | value |
| --- | --- |
| wlan_pd UP | 44.573169 |
| attach times | {"cnss_daemon": 46.42, "pm_service": 47.44, "rild": 48.68} |
| producer window captured | False |

## RIL QMI

| field | value |
| --- | --- |
| DMS message ids | ["0x0025", "0x002e"] |
| NAS message ids | ["0x0002", "0x0003", "0x0034", "0x004d", "0x004f", "0x0050", "0x0051", "0x0052", "0x0070", "0x00ac", "0x010c"] |
| other RIL services | ["SEC_RIL_SIDE_SERVICE", "VOICE", "WMS", "service17", "service68"] |
| service counts | {"cnss_daemon:QRTR_CTRL:tx:qrtr-del-lookup": 4, "cnss_daemon:WLFW:rx:indication": 1, "cnss_daemon:service57:rx:response": 1, "cnss_daemon:service57:tx:request": 1, "pm_service:QRTR_CTRL:rx:qrtr-resume-tx": 131, "rild:DMS:rx:response": 2, "rild:DMS:tx:request": 2, "rild:NAS:rx:indication": 5, "rild:NAS:rx:response": 24, "rild:NAS:tx:request": 24, "rild:SEC_RIL_SIDE_SERVICE:rx:indication": 15, "rild:SEC_RIL_SIDE_SERVICE:rx:response": 19, "rild:SEC_RIL_SIDE_SERVICE:tx:request": 20, "rild:VOICE:rx:response": 1, "rild:VOICE:tx:request": 1, "rild:WMS:rx:response": 1, "rild:WMS:tx:request": 1, "rild:service17:rx:response": 8, "rild:service17:tx:request": 8, "rild:service68:rx:response": 3, "rild:service68:tx:request": 3} |
| result/errors | {"DMS:0x0025:result=0:error=0": 1, "DMS:0x002e:result=0:error=0": 1, "NAS:0x0002:result=0:error=0": 2, "NAS:0x0003:result=0:error=0": 2, "NAS:0x0034:result=0:error=0": 2, "NAS:0x004d:result=0:error=0": 9, "NAS:0x004f:result=0:error=0": 1, "NAS:0x0050:result=0:error=0": 2, "NAS:0x0052:result=0:error=0": 1, "NAS:0x0070:result=0:error=0": 2, "NAS:0x00ac:result=1:error=74": 2, "NAS:0x010c:result=1:error=71": 1, "SEC_RIL_SIDE_SERVICE:0x0006:result=0:error=0": 19, "VOICE:0x0040:result=0:error=0": 1, "WMS:0x0034:result=1:error=52": 1, "service17:0x0001:result=0:error=0": 8, "service57:0x0020:result=0:error=0": 1, "service68:0x0022:result=0:error=0": 3} |

## Conclusion

- V1970 confirms RIL uses DMS and NAS QMI services directly on the internal-modem QRTR node.
- V1970 does not prove the pre-UP producer trigger because `rild` attached after `wlan_pd` UP.
- A corrected live capture must attach strace first, then run QRTR enumeration asynchronously or after the producer edge.

## Safety

Host-only decode of existing evidence. No device command, Wi-Fi action, boot flash, partition write, eSoC/PCIe/GDSC/GPIO/PMIC operation, scan/connect, DHCP/routes, credentials, or ping was executed.
