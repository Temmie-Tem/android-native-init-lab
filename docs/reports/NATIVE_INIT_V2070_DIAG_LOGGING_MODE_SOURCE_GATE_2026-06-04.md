# Native Init V2070 DIAG Logging-Mode Source Gate

## Summary

- Cycle: `V2070`
- Decision: `v2070-diag-wlan-pd-memory-device-design-ready-host-pass`
- Label: `diag-wlan-pd-memory-device-design-ready`
- Pass: `True`
- Type: host/source-only safety gate; no device boot, flash, or live DIAG mutation.
- Reason: V2059 closed the cnss-daemon PerMgr register/vote candidate, V2067 proved WLAN PD logging support can be queried, and V2069 proved DCI target masks alone still produce no payload; the remaining low-cost modem-side observability option is a bounded WLAN-PD-only memory-device DIAG session.

## Closed Input

| area | current evidence | conclusion |
| --- | --- | --- |
| PerMgr | V2059 `cnss_client=True`, `libperipheral=True`, `pm_service=True`, `wlanmdsp=0` | native already performs the AP-side cnss-daemon register/connect/server-accept path |
| passive DIAG | V2052 zero useful modem payload | do not repeat passive `/dev/diag` |
| query-only PD logging | V2067 `DIAG_IOCTL_QUERY_PD_LOGGING` for `DIAG_CON_UPD_WLAN` succeeded | WLAN PD logging feature/diag-id support is observable after the native lower-window PD registration |
| DCI target masks | V2069 set/cleared three WLAN log codes and three WLAN events, `payload=0`, `wlanmdsp=0` | DCI masks without switching DIAG logging mode do not expose the producer |

## Source Findings

| finding | source | implication |
| --- | --- | --- |
| `DIAG_IOCTL_SWITCH_LOGGING` is ioctl `7`; `DIAG_IOCTL_QUERY_PD_LOGGING` is ioctl `39` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/include/linux/diagchar.h:46` | the helper can use the same packed ABI already used by V2067 for query-only |
| user request modes are `USB_MODE=1`, `MEMORY_DEVICE_MODE=2`, `CALLBACK_MODE=6`, `PCIE_MODE=7` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/include/linux/diagchar.h:29` | use `MEMORY_DEVICE_MODE`, not USB/PCIE |
| WLAN PD user mask is `DIAG_CON_UPD_WLAN=0x1000`; local device mask is `DIAG_MSM_MASK=0x1` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/diag/diagchar.h:78` and `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/diag/diagchar.h:301` | constrain the session to the local WLAN user-PD only |
| switch requires nonzero `peripheral_mask` and `device_mask` | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/diag/diagchar_core.c:1897` | reject any live run if either field is not exactly bounded |
| PD switch first resolves the WLAN PD diag-id and owning peripheral from the kernel diag-id list | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/diag/diagchar_core.c:1908` | live code must wait for `QUERY_PD_LOGGING` success before attempting `SWITCH_LOGGING` |
| memory-device session creation is per-PID and rejects overlapping sessions | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/diag/diagchar_core.c:1383` | a single helper-owned fd/process can contain and later release the session |
| data from a memory-device session wakes the owning client and is read back from the same `/dev/diag` fd | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/diag/diag_memorydevice.c:205` and `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/diag/diagchar_core.c:3689` | no AP-side strace, QRTR matrix, QMI send, or external logger is required |
| normal close path clears the PID session, resets WLAN PD logging state, and switches the owned mask back to the transport default | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/diag/diagchar_core.c:479` | cleanup should be fd/process-close based, not a hard-coded USB/PCIE restore |

## Bounded Live Design

| step | exact constraint |
| --- | --- |
| open | private rootfs `/dev/diag` only, nonblocking reads after arm |
| wait gate | poll `DIAG_IOCTL_QUERY_PD_LOGGING` with `pd_mask=DIAG_CON_UPD_WLAN` until success or a short timeout after native `wlan_pd` registration |
| switch | one `DIAG_IOCTL_SWITCH_LOGGING` with `req_mode=MEMORY_DEVICE_MODE`, `peripheral_mask=DIAG_CON_UPD_WLAN`, `pd_mask=DIAG_CON_UPD_WLAN`, `device_mask=DIAG_MSM_MASK` |
| mask scope | reuse the V2069 three WLAN log codes and three WLAN events only; no broad masks |
| read scope | read the same `/dev/diag` fd for memory-device records, decode offline, and correlate only to TFTP/cascade markers |
| cleanup | clear V2069 DCI target masks if armed, call `DIAG_IOCTL_DCI_DEINIT` if DCI was registered, then close the DIAG fd/process and let `diag_close_logging_process()` restore the owned mask to the current transport default |
| rollback | standard V724 rollback and selftest `fail=0` |

## Rejection Criteria

- If `QUERY_PD_LOGGING` never succeeds, do not call `SWITCH_LOGGING`; label `diag-wlan-pd-query-never-ready`.
- If `SWITCH_LOGGING` returns `-EINVAL` with no session, do not retry broadly; label `diag-wlan-pd-switch-rejected`.
- If memory-device reads produce payload, decode offline; do not add AP-side strace/QRTR matrix in the same boot.
- If memory-device reads still produce no payload and `wlanmdsp=0`, the remaining path is active modem DIAG logging-mode/mask beyond this bounded AP session or a modem-side DIAG transport design.
- Do not issue a hard-coded `USB_MODE` or `PCIE_MODE` restore in the live helper; if explicit restore becomes necessary, source-confirm and gate it separately.

## Safety

- This cycle did not run a live boot, flash, DIAG ioctl, QMI send, AP-side strace, QRTR matrix, passive DIAG replay, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, PMIC/GPIO/GDSC/regulator write, forced RC1/case, fake ONLINE, or sda29 write.
- The proposed live unit remains internal-modem/WLAN-PD scoped and uses rootfs-private nodes plus namespace-local bridges only.
- The proposed live unit must not switch USB/PCIE/global modem logging, must not use broad masks, and must not proceed if the WLAN PD query gate is absent.
