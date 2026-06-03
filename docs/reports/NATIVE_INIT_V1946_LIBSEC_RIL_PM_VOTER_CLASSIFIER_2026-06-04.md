# Native Init V1946 libsec-ril PM Voter Classifier

## Summary

- Cycle: `V1946`
- Type: host-only ELF/string/logcat classifier over V1945 libsec-ril export
- Decision: `v1946-libsec-ril-peripheral-manager-voter-caller-identified-host-pass`
- Label: `libsec-ril-peripheral-manager-voter-caller-identified`
- Pass: `True`
- Reason: build.prop points rild to lib64/libsec-ril.so; libsec-ril needs libperipheral_client.so, imports pm_client_register/connect/event_acknowledge, and defines ModemBoot PeripheralManagerInit/Vote; this matches Android's PerMgrSrv QCRIL modem vote before wlanmdsp while remaining SDX50M-coupled source evidence
- Evidence: `tmp/wifi/v1946-libsec-ril-pm-voter-classifier`

## Matrix

| area | value | detail |
| --- | --- | --- |
| build.prop libpath | True | vendor.sec.rild.libpath=/vendor/lib64/libsec-ril.so |
| ril-daemon uses rild | True | init.vendor.rilchip.rc service ril-daemon |
| libperipheral needed | True | libsec-ril NEEDED libperipheral_client.so |
| pm_client imports | True | register/connect/event_acknowledge |
| ModemBoot PM symbols | True | PeripheralManagerInit/Vote |
| Android edge matches | True | PerMgrSrv QCRIL vote before wlanmdsp plus SDX50M vote |
| No explicit WLAN strings | True | no wlan_pd/wlanmdsp/wlfw strings in libsec-ril |

## Key Needed Libraries

| library |
| --- |
| libmdmdetect.so |
| libperipheral_client.so |
| libqmi_cci.so |
| libqmiservices.so |
| libril_sem.so |

## PM Voter Symbols

| symbol |
| --- |
| 139: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND pm_client_connect |
| 140: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND pm_client_disconnect |
| 141: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND pm_client_event_acknowledge |
| 142: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND pm_client_register |
| 143: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND pm_client_unregister |
| 2072: 0000000000249cd0   272 FUNC    GLOBAL DEFAULT   15 _ZN9ModemBoot21PeripheralManagerVoteEi |
| 2568: 0000000000248bfc   304 FUNC    GLOBAL DEFAULT   15 _ZN9ModemBoot22CheckAndRegisterWithPMEv |
| 3623: 0000000000249f34   176 FUNC    GLOBAL DEFAULT   15 _ZN9ModemBoot23PeripheralManagerDeinitEv |
| 5255: 0000000000248d44   184 FUNC    GLOBAL DEFAULT   15 _ZN9ModemBoot18BootupModemUsingPMEv |
| 6408: 000000000024924c   228 FUNC    GLOBAL DEFAULT   15 _ZN9ModemBoot28PeripheralManagerReleaseVoteEi |
| 7629: 000000000037d3f0    76 FUNC    GLOBAL DEFAULT   15 _Z11DoModemBootv |
| 11214: 0000000000249b88   328 FUNC    GLOBAL DEFAULT   15 _ZN9ModemBoot21PeripheralManagerInitEiPc |

## String Samples

| string |
| --- |
| RIL_Init |
| PeripheralInfo |
| _ZN9ModemBoot18BootupModemUsingPMEv |
| _ZN9ModemBoot21PeripheralManagerInitEiPc |
| _ZN9ModemBoot21PeripheralManagerVoteEi |
| _ZN9ModemBoot22CheckAndRegisterWithPMEv |
| _ZN9ModemBoot23PeripheralManagerDeinitEv |
| _ZN9ModemBoot28PeripheralManagerReleaseVoteEi |
| pm_client_connect |
| pm_client_disconnect |
| pm_client_event_acknowledge |
| pm_client_register |
| pm_client_unregister |
| libperipheral_client.so |
| PeripheralManagerDeinit |
| PeripheralManagerReleaseVote[%d] |

## Android QCRIL Edge

| line | text |
| --- | --- |
| 168 | 06-04 02:03:50.849   926   964 D PerMgrSrv: modem state: is on-line, add client QCRIL |
| 169 | 06-04 02:03:50.849   926   964 D PerMgrSrv: QCRIL registered |
| 170 | 06-04 02:03:50.849   926   964 D PerMgrSrv: SDX50M state: is off-line, add client QCRIL |
| 171 | 06-04 02:03:50.849   926   964 D PerMgrSrv: QCRIL registered |
| 172 | 06-04 02:03:50.850   926   964 D PerMgrSrv: QCRIL voting for modem |
| 174 | 06-04 02:03:50.850   926   964 D PerMgrSrv: QCRIL voting for SDX50M |

## Interpretation

- This identifies the source owner for the Android `PerMgrSrv: QCRIL voting for modem` edge as the dynamically loaded Samsung RIL implementation, not a missing QTI `qcrild` binary.
- It remains read-only source evidence and is still SDX50M-coupled: the same Android window logs `QCRIL voting for SDX50M`.
- Next host-only step: disassemble `ModemBoot::PeripheralManagerInit/Vote/BootupModemUsingPM` to recover peripheral IDs/client names and decide whether a bounded internal-modem-only native shim is possible without starting radio/QCRIL/eSoC/PCIe.

## Inputs

- Android logcat: `tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/android-postfs-evidence/a90-v1934-libqmi69/logcat-filtered.txt`
- V1945 manifest: `tmp/wifi/v1945-ril-impl-export/manifest.json`
- V1945 vendor source: `tmp/wifi/v1945-ril-impl-export/vendor-source`
- libsec-ril: `tmp/wifi/v1945-ril-impl-export/vendor-source/lib64/libsec-ril.so`

## Safety Scope

Host-only parser over already exported files. No live device command, flash, reboot, rild/radio/QCRIL start, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request was used.
