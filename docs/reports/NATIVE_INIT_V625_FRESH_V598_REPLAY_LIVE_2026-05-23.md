# Native Init V625 Fresh V598-Class Replay Live Report

- date: `2026-05-23 KST`
- status: `partial-positive/reproduced`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_modem_holder_wlfw_readback_v598.py`
- evidence: `tmp/wifi/v625-fresh-v598-class-live/`
- decision: `v598-wlfw-readback-empty`

## Scope

V625 executed the safe V598-class replay from a fresh native boot. It used:

- helper v100 deployment evidence:
  `tmp/wifi/v625-helper-v100-deploy-run-safe1850/`
- fresh SELinuxfs mount evidence:
  `tmp/wifi/v625-fresh-v401-toybox-selinuxfs-mount-run/`
- fresh V490 policy-load evidence:
  `tmp/wifi/v625-fresh-v490-current-run/`
- V598-class preflight evidence:
  `tmp/wifi/v625-fresh-v598-class-preflight/`

No ADSP/CDSP/SLPI boot-node write, `esoc0` open, service-manager start, Wi-Fi
HAL start, scan/connect/link-up, credential use, DHCP, route change, or external
ping was executed.

## Result

```text
decision: v598-wlfw-readback-empty
pass: True
reason: WLFW QRTR readback reached end-of-list; timeouts=0
next: inspect missing service-notifier/WLAN-PD registration before qcwlanstate/HAL retry
```

## Key Evidence

| item | result | evidence |
| --- | --- | --- |
| native baseline | healthy after cleanup | post-run `version_seen=True`, `status_healthy=True`; manual `bootstatus` shows `fail=0` |
| helper | v100 active | sha256 `916b5c68a3357c79604db4532b457e30fcb9a70c99aaabb6f95519af138abd29` |
| V490 freshness | pass | `fresh=True generated_epoch=1779476401 boot_epoch=1779476371` |
| QRTR readiness | reproduced | `qrtr_rx=1`, `qrtr_tx=1` |
| modem sysmon | reproduced | `sysmon_qmi=1` |
| service-notifier | reproduced | `service_notifier=1`; dmesg shows service `180` |
| WLFW readback | empty | service `69` instances `0/1` both returned end-of-list |
| WLAN-PD/QMI/BDF | absent | `wlan_pd=0`, `qmi_server_connected=0`, `bdf=0` |
| Wi-Fi link | absent | `wlan0=0`, `wlan_fw_ready=0` |
| kernel warning | clean | `kernel_warning=0` |
| cleanup | reboot cleanup completed | reboot command lacks END marker because reboot begins, but post-reboot v319/status were observed |

## Timeline Markers

```text
166.983660  qrtr: Modem QMI Readiness RX
169.359842  qrtr: Modem QMI Readiness TX
169.363353  sysmon-qmi modem SSCTL Connection established
170.084596  service-notifier service 180 Connection established
```

## Interpretation

V625 successfully reproduces the V598 safe partial positive from a fresh native
boot. This is useful because it proves the safe path is not permanently
regressed:

```text
subsys_modem holder
  -> QRTR RX/TX
  -> modem sysmon-qmi
  -> service-notifier 180
  -> WLFW service 69 readback end-of-list
```

The active blocker moved forward from "can we reproduce service-notifier 180?"
to "why do service-notifier 74, WLAN-PD, and WLFW service 69 not publish under
native init?" Since WLFW QRTR readback completed cleanly with end-of-list and no
timeouts, blindly retrying qcwlanstate/HAL remains premature.

`mdm3` remains `OFFLINING` after the companion window, while `mss` is `ONLINE`.
This keeps the lower publication blocker in the `mdm3`/WLAN-PD/service
registration layer, not in Wi-Fi HAL or credential handling.

## Next Gate

Proceed to V626 as a host-only classifier over V598/V625 plus Android V622:

1. compare service-notifier `180`-only native timing against Android
   service-notifier `180/74` + WLAN-PD timing;
2. identify whether service `74`, WLAN-PD, or `mdm3=ONLINE` appears first on
   Android;
3. select a bounded native gate that targets the missing `74`/WLAN-PD
   publication without direct DSP boot-node writes, service-manager, HAL, scan,
   connect, credentials, DHCP, routes, or external ping.
