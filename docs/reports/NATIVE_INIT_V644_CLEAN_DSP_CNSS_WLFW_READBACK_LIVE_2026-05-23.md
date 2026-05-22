# Native Init V644 Clean-DSP CNSS/WLFW Readback Live Report

- date: `2026-05-23 KST`
- status: `failed-safe/advanced`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_clean_dsp_cnss_wlfw_readback_v644.py`
- arm evidence: `tmp/wifi/v644-arm-clean-dsp-20260523-071222/`
- prerequisite evidence: `tmp/wifi/v644-prereq-retry-20260523-071329/`
- preflight evidence: `tmp/wifi/v644-preflight-20260523-071520/`
- live evidence: `tmp/wifi/v644-live-20260523-071610/`

## Scope

V644 replayed the V598-class CNSS-including lower companion path on top of a
fresh V641 clean-DSP boot.

Executed:

- V641 one-shot clean-DSP arming and reboot;
- `mountsystem ro`;
- V401 SELinuxfs mount;
- current-boot V490 policy load into `tmp/wifi/v644-v490-current-run/`;
- firmware mount + `subsys_modem` holder;
- lower companion window:
  `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon`;
- WLFW QRTR nameservice readback for service `69` instances `0/1`;
- reboot cleanup.

Not executed:

- ADSP/CDSP/SLPI boot-node writes after V641 boot-window proof;
- `esoc0` open;
- `boot_wlan`/`qcwlanstate` writes;
- service-manager, Wi-Fi HAL, `wificond`, supplicant, or hostapd start;
- scan/connect/link-up, Wi-Fi credential use, DHCP, route change, or external
  ping.

## Result

The raw manifest decision is inherited from the V596 base fail-safe path:

```text
decision: v596-modem-holder-companion-kernel-warning
pass: False
reason: kernel WARNING/reference mismatch appeared during live window
```

The V644-specific marker classification is:

```text
service_notifier_180=1
service_notifier_74=1
kernel_warning=5
qmi_server_connected=0
wlan_pd=0
wlfw_start=0
bdf=0
wlan0=0
```

So the effective V644 label is:

```text
v644-service-notifier-advanced-with-kernel-warning
```

## Key Evidence

| item | result |
| --- | --- |
| native cleanup after run | boot OK; selftest `pass=11 warn=1 fail=0` |
| V641 clean-DSP state | armed one-shot boot; timeline entries `28/32` before V644 |
| V401 | `toybox-selinuxfs-mount-live-executor-run-pass` |
| V490 | `v490-selinux-policy-load-proof-pass` |
| helper | v104 SHA `f811c18d1a9af92f5ca9fadcfd4dbd94593318240744a0c86d0419280bbea019` |
| preflight | `v644-clean-dsp-cnss-wlfw-readback-preflight-ready` |
| companion order | `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` |
| child count | `6` |
| holder | `holder_started=True`; `mss_after_holder=ONLINE` |
| `mss_after_companion` | `ONLINE` |
| `mdm3_after_companion` | `OFFLINING` |
| helper result | `companion-window-pass` |
| WLFW readback | service `69` instances `0/1` both end-of-list; `qmi_attempted=0` |

Marker timeline tail:

```text
QRTR RX
QRTR TX
sysmon-qmi modem/slpi/cdsp/adsp
service-notifier 180
service-notifier 74
WARNING at kernel/power/qos.c:616 pm_qos_add_request
```

## Interpretation

V644 is the first native clean-DSP run in this branch to publish both
service-notifier `180` and `74`. That is a real advancement toward the Android
lower Wi-Fi path.

The run is still not safe to build on directly because the service `74`
publication is immediately followed by a `pm_qos_add_request` kernel warning.
That warning class was previously associated with unsafe direct DSP boot-node
paths, but V644 did **not** write DSP boot nodes during the live phase. The
warning now needs a narrower attribution:

```text
clean-DSP state + CNSS-including companion + service 74 publication
  -> pm_qos warning
```

The next blocker is not HAL/credential/scan/connect. It is the post-service
`74` safety boundary and why WLAN-PD/WLFW still do not appear before the
warning/cleanup boundary.

## Cleanup

The runner used reboot cleanup. The reboot command naturally lacked an END
marker once reboot began, but the post-reboot wait observed v641 and a healthy
status. Manual post-run `bootstatus` also showed:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok ... ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Next Gate

Proceed to V645 as a host-only warning attribution classifier:

1. compare V644 service `74` timing against V638/V619/V642/V627 warning and
   non-warning windows;
2. determine whether the warning is tied to service `74`, CNSS child startup,
   audio/DSP deferred probe, or the clean-DSP boot-window state;
3. do not repeat V644 live or attempt HAL/qcwlanstate/scan/connect until the
   warning boundary is classified.
