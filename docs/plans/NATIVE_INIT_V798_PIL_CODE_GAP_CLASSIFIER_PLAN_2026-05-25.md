# Native Init V798 PIL Code Gap Classifier Plan

## Goal

Map the V797 `msm_pil_event:pil_notif` code payloads to the Samsung OSRC
`enum subsys_notif_type`, then reconcile that modem PIL sequence with the
existing Android/native gap evidence before attempting another live Wi-Fi
trigger.

## Scope

- Read only existing host artifacts:
  - V797 PIL trace payload manifest.
  - V783 Android/native PIL gap manifest.
  - staged Samsung OSRC source files.
- Extract source snippets for:
  - `enum subsys_notif_type`
  - `trace_pil_notif`
  - `subsys_start()` notification order
  - `sysmon-qmi` notification mapping
  - `service-notifier` QMI server connection path
  - ICNSS service-notifier registration path
  - memshare modem `AFTER_POWERUP` callback path
- Produce a host-only decision for the next smallest Wi-Fi gate.

## Hard Gates

- No device command.
- No service-manager or Wi-Fi HAL start.
- No scan/connect, credential use, DHCP/routes, or external ping.
- No raw `esoc0`, bind/unbind, module load/unload, boot image write, partition
  write, reboot, or custom kernel flash.
- No Wi-Fi secret material in tracked output.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pil_code_gap_classifier_v798.py
python3 scripts/revalidation/native_wifi_pil_code_gap_classifier_v798.py --out-dir tmp/wifi/v798-static-plan-check plan
python3 scripts/revalidation/native_wifi_pil_code_gap_classifier_v798.py run
git diff --check
```

## Expected Routing

- If the V797 payload maps to a complete modem `BEFORE_POWERUP` /
  `AFTER_POWERUP` sequence plus proxy vote/unvote, stop treating modem PIL
  notification absence as the blocker.
- If Android has service-notifier `74/180` and WLAN-PD while native still has
  no service-notifier, no service `69`, no wiphy, and no `wlan0`, route the next
  gate to service-notifier registration/root-PD state rather than another blind
  `boot_wlan` or HAL retry.
