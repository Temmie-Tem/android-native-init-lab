# Native Init V798 PIL Code Gap Classifier Report

## Result

- decision: `v798-modem-pil-complete-service-notifier-mdm3-gap-classified`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_pil_code_gap_classifier_v798.py`
- evidence: `tmp/wifi/v798-pil-code-gap-classifier/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pil_code_gap_classifier_v798.py
python3 scripts/revalidation/native_wifi_pil_code_gap_classifier_v798.py --out-dir tmp/wifi/v798-static-plan-check plan
python3 scripts/revalidation/native_wifi_pil_code_gap_classifier_v798.py run
```

V798 was host-only. It did not execute any device command.

## Evidence Summary

| Signal | Result |
| --- | --- |
| source enum | `include/soc/qcom/subsystem_notif.h` |
| tracepoint source | `include/trace/events/trace_msm_pil_event.h` |
| V797 captured events | `8` |
| V797 firmware field | `modem` |
| V797 code mapping | `2=SUBSYS_BEFORE_POWERUP`, `6=SUBSYS_PROXY_VOTE`, `3=SUBSYS_AFTER_POWERUP`, `7=SUBSYS_PROXY_UNVOTE` |
| modem PIL sequence | complete `BEFORE_POWERUP` + proxy vote/unvote + `AFTER_POWERUP` |
| Android mdm3 | `ONLINE` |
| Native V797 mdm3 | `OFFLINING -> OFFLINING -> OFFLINING` |
| Android service-notifier `74/180` | present |
| Native V797 service-notifier | absent |
| Native V797 service `69` / `wlan0` / wiphy | `0 / false / false` |

Mapped V797 sequence:

```text
before_send_notif code=2 SUBSYS_BEFORE_POWERUP  fw=modem
after_send_notif  code=2 SUBSYS_BEFORE_POWERUP  fw=modem
before_send_notif code=6 SUBSYS_PROXY_VOTE      fw=modem
after_send_notif  code=6 SUBSYS_PROXY_VOTE      fw=modem
before_send_notif code=3 SUBSYS_AFTER_POWERUP   fw=modem
before_send_notif code=7 SUBSYS_PROXY_UNVOTE    fw=modem
after_send_notif  code=7 SUBSYS_PROXY_UNVOTE    fw=modem
after_send_notif  code=3 SUBSYS_AFTER_POWERUP   fw=modem
```

## Classification

V798 removes one ambiguity: native is not blocked because modem PIL
notifications are absent. V797 captured the complete modem power-up notification
path and the proxy vote/unvote cycle.

The remaining gap is after modem power-up notification and before the Android
service-notifier/WLAN-PD chain:

```text
native modem PIL power-up sequence complete
  -> mss ONLINE
  -> sysmon-qmi modem present
  -> mdm3 still OFFLINING
  -> service-notifier 74/180 absent
  -> service 69 / WLFW / BDF / wiphy / wlan0 absent
```

Android reaches the corresponding service-notifier `74/180`, WLAN-PD, ICNSS-QMI,
BDF, firmware-ready, and `wlan0` path. Therefore another blind `boot_wlan`,
CNSS daemon, service-manager, HAL, scan/connect, or custom-kernel retry is not
the next best move.

## Safety

- Host-only classifier; no device command executed.
- No service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes,
  external ping, raw `esoc0`, bind/unbind, module load/unload, boot image write,
  partition write, reboot, or custom kernel flash.
- No Wi-Fi secret material written to tracked output.

## Next

V799 should classify the service-notifier/root-PD state gap around the already
tested lower window. The target is to prove whether ICNSS registers
service-notifier handles for the WLAN-PD domains and whether root-PD service
`74/180` can be observed or queried in native without widening to HAL,
scan/connect, credentials, DHCP, external ping, raw `esoc0`, or custom kernels.
