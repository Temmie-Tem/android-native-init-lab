# Native Init V642 Clean-DSP Lower Companion Live Report

- date: `2026-05-23 KST`
- status: `pass/diagnostic`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_clean_dsp_lower_companion_v642.py`
- evidence: `tmp/wifi/v642-live-20260523-070145/`
- decision: `v642-lower-modem-readiness-only`

## Scope

V642 reused the V641 clean firmware-backed ADSP/CDSP/SLPI state and ran only a
bounded lower modem/QRTR observer.

Executed live actions:

- read-only firmware mount setup through the existing V596/V584 path;
- `subsys_modem` holder with reboot cleanup;
- Android-order lower companion start-only window:
  `qrtr_ns,pd_mapper,rmt_storage,tftp_server`;
- dmesg/rpmsg/QRTR/process/state capture;
- reboot cleanup back to `A90 Linux init 0.9.67 (v641)`.

Not executed:

- ADSP/CDSP/SLPI boot-node writes;
- `boot_wlan`/`qcwlanstate` writes;
- CNSS, service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, credential use, DHCP, route change, or external ping.

## Result

```text
decision: v642-lower-modem-readiness-only
pass: True
reason: advance=['qrtr_tx', 'sysmon_qmi'] service_notifier=0
next: compare V642 against V641/V619 and choose next lower publication trigger
```

## Key Evidence

| item | result |
| --- | --- |
| current native after cleanup | boot OK; selftest `pass=11 warn=1 fail=0` |
| V641 clean-DSP preflight | pass after proof log + timeline + rpmsg check |
| helper | v104 deployed and accepted by V642 preflight |
| current-boot V490 | `v490-selinux-policy-load-proof-pass` |
| holder | `holder_started=True`; `mss_after_holder=ONLINE` |
| QRTR gate | `qrtr_rx=True` in `0.529s` |
| companion order | `qrtr_ns,pd_mapper,rmt_storage,tftp_server` |
| child count | `4` |
| helper result | `companion-window-pass` |
| postflight safety | `all_postflight_safe=True`; `all_observable=True` |
| `mss_after_companion` | `ONLINE` |
| `mdm3_after_companion` | `OFFLINING` |
| reboot cleanup | v641 version seen and post-reboot status healthy |

Marker counts:

| marker | count |
| --- | ---: |
| `qrtr_rx` | 1 |
| `qrtr_tx` | 1 |
| `sysmon_qmi` | 4 |
| `service_notifier` | 0 |
| `wlan_pd` | 0 |
| `qmi_server_connected` | 0 |
| `wlfw` | 0 |
| `bdf` | 0 |
| `wlan_fw_ready` | 0 |
| `wlan0` | 0 |
| `kernel_warning` | 0 |

## Interpretation

V642 is a useful positive step but not a Wi-Fi bring-up gate yet.

Compared with V641 armed proof, the lower modem path now advances from clean
DSP PIL/rpmsg state to:

```text
QRTR RX -> QRTR TX -> sysmon-qmi
```

However, the missing boundary is still:

```text
service-notifier 180/74 -> WLAN-PD -> WLFW/BDF -> wlan0
```

`mdm3` remains `OFFLINING`, and no service-notifier/WLAN-PD/WLFW marker
appeared. CNSS/HAL/scan/connect remain premature.

## Cleanup

The runner used reboot cleanup. The reboot command naturally lost its END
marker while rebooting, but the post-reboot wait observed the expected v641
version and healthy status. A separate `bootstatus` check after the run showed:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok ... ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Next Gate

Proceed to a host-only V643 comparison/classifier before another live retry:

1. compare V642 against V598/V619/V625/V627 to isolate why this clean-DSP path
   has QRTR TX/sysmon but no service-notifier;
2. specifically classify the remaining `mdm3=OFFLINING` and missing
   service-notifier publisher relationship;
3. keep CNSS/HAL/scan/connect blocked until service-notifier/WLAN-PD or WLFW
   markers advance.
