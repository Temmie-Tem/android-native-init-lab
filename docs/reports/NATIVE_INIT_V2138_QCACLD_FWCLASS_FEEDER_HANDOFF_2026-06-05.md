# Native Init V2138 QCACLD Firmware Class Feeder Handoff

## Summary

- Cycle: `V2138`
- Decision: `v2138-qcacld-fwclass-feeder-wlan0-progress-rollback-pass`
- Label: `qcacld-fwclass-feeder-wlan0-progress`
- Pass: `True`
- Reason: V2137 firmware_class feeder route advanced QCACLD startup to wlan0; stop before credentials and run the connectivity gate
- Evidence: `tmp/wifi/v2138-qcacld-fwclass-feeder-handoff`
- Inner handoff: `tmp/wifi/v2138-qcacld-fwclass-feeder-handoff/v2137-handoff/manifest.json`

## Matrix

| area | value | detail |
| --- | --- | --- |
| artifact | True | helper=a90_android_execns_probe v426 |
| fwclass_sampler | False | entries=0 interesting=0 |
| feeder | False | seen=0 fed=0 ini_fed=False |
| helper_capture |  | summary_armed=True helper_missing=True wlan0_probe=True |
| stack | False | targets=0 request_firmware=False qdf_ini=False hdd_ctx=False |
| cascade |  | wlan_pd=1 icnss_qmi=1 wlfw69=0 fw_ready=0 wlan0=1 |

## Feeder

| request | state | detail |
| --- | --- | --- |
|  | seen=0 fed=0 | src= bytes=0 loading=0/0 data=0/0 |
|  | seen=0 fed=0 | src= bytes=0 loading=0/0 data=0/0 |
|  | seen=0 fed=0 | src= bytes=0 loading=0/0 data=0/0 |

## Firmware Class Entries

- `none`

## Stack Samples

- `none`

## Wlan0 Proof

- Probe: `tmp/wifi/v2138-qcacld-fwclass-feeder-handoff/v2137-handoff/test-wlan0.stdout.txt` present `True`
- `tmp/wifi/v2138-qcacld-fwclass-feeder-handoff/v2137-handoff/test-v1393-dmesg.stdout.txt: [   84.960448] [6:  kworker/u16:1:   75] dev : wlan0 : event : 16`
- `tmp/wifi/v2138-qcacld-fwclass-feeder-handoff/v2137-handoff/test-v1393-dmesg.stdout.txt: [   84.960576] [6:  kworker/u16:1:   75] icnss 18800000.qcom,icnss wlan0: set_features() failed (-11); wanted 0x0000000000004000, left 0x0000000000004800`
- `tmp/wifi/v2138-qcacld-fwclass-feeder-handoff/v2137-handoff/test-v1393-dmesg.stdout.txt: [   84.960616] [6:  kworker/u16:1:   75] dev : wlan0 : event : 5`
- `tmp/wifi/v2138-qcacld-fwclass-feeder-handoff/v2137-handoff/test-v1393-dmesg.stdout.txt: [   84.960749] [6:  kworker/u16:1:   75] [kworke][0x7621c74f][21:35:21.228452] wlan: [75:E:HDD] hdd_open_concurrent_interface: 13749: failed to generating swlan0 mac addr.`

## Capture Caveat

- Helper summary was still armed: `True`.
- Helper result target was unavailable at collection time: `True` from `tmp/wifi/v2138-qcacld-fwclass-feeder-handoff/v2137-handoff/test-v1393-helper-result.stdout.txt`.
- The feeder internal counters are therefore unavailable in this capture, but `test-wlan0` plus dmesg prove native `wlan0` creation.

## Interpretation

- V2138 actively tests whether the V2136 fallback request can be satisfied by userspace feeding the observed QCACLD firmware_class node from the read-only vendor source.
- This is a bounded sysfs firmware_class fallback data path, not a firmware file, EFS, partition, GPIO, PCIe, or HAL mutation.
- V2138 reached real native `wlan0`, so the next gate is a dedicated connectivity handoff rather than more firmware_class request classification.
- If INI feed succeeds without wlan0, the next unit should target the next observed firmware request or the post-INI QCACLD startup state rather than returning to AP-side producer captures.

## Steps

- `pre-version` rc `0` ok `True` evidence `host/pre-version.txt`
- `pre-selftest` rc `0` ok `True` evidence `host/pre-selftest.txt`
- `pre-flags` rc `0` ok `True` evidence `host/pre-flags.txt`
- `arm-clean-dsp-flag` rc `0` ok `True` evidence `host/arm-clean-dsp-flag.txt`
- `cleanup-leftover-clean-dsp-flag` rc `0` ok `True` evidence `host/cleanup-leftover-clean-dsp-flag.txt`
- `post-selftest` rc `0` ok `True` evidence `host/post-selftest.txt`
- `post-status` rc `0` ok `True` evidence `host/post-status.txt`
- `post-flags` rc `0` ok `True` evidence `host/post-flags.txt`

## Safety

- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.
- No firmware/partition file writes, EFS writes, tracefs write, sysrq, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, QMI payload send, `tftp_server` ptrace, module load/unload, or driver bind/unbind was run.
- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.
- Mutation scope: V2137 rollbackable test-boot flash-handoff, read-only `sda29` mount at `/mnt/vendor`, temporary `firmware_class.path` restore-proven write, namespace-local RFS bridges/tmpfs mirrors, one gated `/sys/kernel/boot_wlan/boot_wlan` write after FW_READY, and bounded firmware_class fallback `loading`/`data` writes only for observed QCACLD files.
