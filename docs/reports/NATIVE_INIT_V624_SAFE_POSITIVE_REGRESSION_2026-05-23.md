# Native Init V624 Safe Positive Regression Report

- date: `2026-05-23 KST`
- status: `classified`; Wi-Fi external ping is **not** complete
- runner: `scripts/revalidation/native_wifi_safe_positive_regression_classifier_v624.py`
- evidence: `tmp/wifi/v624-safe-positive-regression-classifier/`
- decision: `v624-safe-positive-nondeterministic-precondition-gap`

## Scope

V624 is host-only. It compares V598, V606, V608, V609, V619, V622, and V623
evidence.

No device command, boot write, partition write, sysfs write, DSP boot-node
write, daemon start, service-manager start, Wi-Fi HAL start, QRTR/QMI payload,
scan/connect/link-up, credential, DHCP, route change, or external ping was
executed.

## Result

```text
decision: v624-safe-positive-nondeterministic-precondition-gap
pass: True
reason: V598 is the only warning-free native partial service-notifier positive, but exact helper-version replays lost it; V619's broader DSP path is unsafe. The next safe gate should replay/observe the V598-class path from a fresh native boot with stronger pre/post state capture, not add new blind daemons.
next: V625 should implement a bounded fresh-boot V598-class replay/observer with no DSP boot-node writes, no service-manager, no HAL, no scan/connect, and expanded precondition capture
```

## Evidence Matrix

| subject | classification | evidence | next |
| --- | --- | --- | --- |
| V598 positive | safe partial native positive | `service_notifier=1`; `kernel_warning=0`; `boot_node_written=no`; order=`qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon` | can seed next safe replay, but not Wi-Fi bring-up |
| V606/V608 | same baseline no longer reproduces | notifier `0/0`; warnings `0/0` | current-boot/precondition or timing instability |
| V609 | no-CNSS lower observer insufficient | no notifier with `qrtr_ns,rmt_storage,tftp_server,pd_mapper` | no-CNSS window is weaker than V598 |
| V619 | unsafe DSP boot-node path | notifier `0`; `pm_qos` warning `21`; boot nodes written | do not repeat ADSP/CDSP/SLPI boot-node writes |
| Android V622 | full lower target | service-notifier `180/74`, WLAN-PD, QMI, firmware-ready, `wlan0` present | native must advance from partial `180` to stable `180/74` + WLAN-PD |

## Interpretation

The safest native positive path remains V598-class:

```text
subsys_modem holder
  -> qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon
  -> service-notifier 180 only
  -> no direct DSP boot-node writes
  -> no kernel warning
  -> no service-manager/HAL/scan/connect
```

However, V606 and V608 replayed that class and did not reproduce
service-notifier `180`. That means the next live work should not add new daemon
targets. It should capture why the same safe class is nondeterministic:
current-boot state, timing, pre/post subsystem values, QRTR/service-locator
state, and companion timing.

## Next Gate

Proceed to V625 as a bounded fresh-boot V598-class replay/observer:

1. reboot/refresh into native and verify v319 health;
2. run the V598-class no-service-manager/no-HAL/no-scan replay;
3. avoid direct ADSP/CDSP/SLPI boot-node writes;
4. capture pre/post subsystem state, QRTR/sysmon/service-locator,
   service-notifier `180/74`, WLAN-PD, WLFW/BDF, and kernel warnings;
5. reboot cleanup and verify native health after the window.

If service-notifier `180` returns, the next gate should extend toward `74` and
WLAN-PD. If it remains absent, classify the missing current-boot precondition
before any CNSS/HAL or Wi-Fi connect attempt.
