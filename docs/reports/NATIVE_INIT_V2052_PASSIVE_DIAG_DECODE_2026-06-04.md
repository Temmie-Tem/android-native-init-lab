# Native Init V2052 Passive DIAG Decode

## Summary

- Cycle: `V2052`
- Type: host-only decode of the V2051 passive `/dev/diag` samples; no device boot or live command.
- Decision: `v2052-diag-passive-mask-bootstrap-no-modem-user-data`
- Label: `diag-passive-mask-bootstrap-no-modem-user-data`
- Pass: `True`
- Reason: all decoded passive DIAG samples are diagchar startup mask blocks, not modem USER_SPACE/DCI/PKT payload records
- Evidence: `tmp/wifi/v2052-passive-diag-decode`
- Source manifest: `tmp/wifi/v2051-passive-diag-pre-wlanmdsp-trigger-handoff/manifest.json`

## Decode Matrix

| idx | delta_ms | reported | stored | type | name | mask_bootstrap | modem_payload | prefix_hex |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 000 | 11099 | 4 | 4 | 0x00000001 | MSG_MASKS_TYPE | 1 | 0 | 01000000 |
| 001 | 11099 | 517 | 96 | 0x00000004 | EVENT_MASKS_TYPE | 1 | 0 | 04000000000000000000000000000000 |
| 002 | 11099 | 1577 | 96 | 0x00000002 | LOG_MASKS_TYPE | 1 | 0 | 02000000000000000001e80c00000000 |
| 003 | 11099 | 520 | 96 | 0x00000200 | DCI_EVENT_MASKS_TYPE | 1 | 0 | 00020000000000000000000000000000 |

## Classification

- DIAG bytes reported by V2051: `2618`; decoded samples: `4`.
- Decoded type names: `MSG_MASKS_TYPE, EVENT_MASKS_TYPE, LOG_MASKS_TYPE, DCI_EVENT_MASKS_TYPE`.
- Modem payload record count: `0` (`USER_SPACE_DATA_TYPE`, `USER_SPACE_RAW_DATA_TYPE`, `DCI_DATA_TYPE`, `PKT_TYPE`, or `DCI_PKT_TYPE`).
- TFTP branch remains off-path: mcfg `6`, wlanmdsp `0`, server_check `0`, ota_firewall `0`.
- Read error after startup records: `Bad address`; this is after useful mask-bootstrap classification and does not create a modem payload sample.

## Source Basis

- Local kernel ABI header defines `MSG_MASKS_TYPE=0x1`, `LOG_MASKS_TYPE=0x2`, `EVENT_MASKS_TYPE=0x4`, `USER_SPACE_DATA_TYPE=0x20`, `DCI_DATA_TYPE=0x40`, `DCI_LOG_MASKS_TYPE=0x100`, `DCI_EVENT_MASKS_TYPE=0x200`, and `DCI_PKT_TYPE=0x400` in `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/linux/diagchar.h`.
- Android MSM `diagchar_open()` initializes a new client with mask-ready bits, and `diagchar_read()` emits those mask types before real `USER_SPACE_DATA_TYPE`/DCI data. This matches the V2051 sample sequence.

## Next Gate

- Do not repeat passive O_RDONLY DIAG as a modem-side event capture; it only proved the diag node and startup mask stream.
- The next aligned discriminator must first establish a safe, bounded DIAG mode/query path that can produce `USER_SPACE_DATA_TYPE` or DCI payload records without log-mask writes, or explicitly document that any useful DIAG stream requires an active logging-mode/mask operation before using it.
- Keep the TFTP conclusion intact: native still reaches `wlan_pd` UP and ICNSS QMI but selects only `mcfg.tmp`, with no `server_check`, `ota_firewall`, or `wlanmdsp` request.

## Safety

- Host-only decode; no flash, reboot, shell command, DIAG ioctl, DIAG write, log-mask operation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC, PCIe, GDSC, PMIC, GPIO, or sda29 write was performed.
