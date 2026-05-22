# Native Init V637 Service-74 Post-CDSP Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v637`
- scope: host-only classifier
- target: classify why V636 still stops at service-notifier `180` even after
  CDSP is brought online under restored firmware mounts

## Background

V636 combined two safe partial positives:

- V635 restored firmware mounts and made the CDSP boot-node write return
  cleanly, with CDSP reaching PIL/reset/power-clock/`ONLINE`;
- V598/V625/V627 modem-holder path reproduced QRTR RX/TX, modem `sysmon-qmi`,
  and service-notifier `180`.

The composite still did not publish service `74`, WLAN-PD, WLFW/BDF, firmware
ready, or `wlan0`.

## Inputs

- Android V622 same-boot lower-surface manifest;
- V631 per-node sibling SSCTL report;
- V635 firmware CDSP-only live manifest;
- V636 CDSP + V598 composite live manifest.

## Checks

1. Confirm Android reaches SLPI/CDSP/ADSP sibling `sysmon-qmi`, service `74`,
   WLAN-PD, WLFW/BDF, firmware-ready, and `wlan0`.
2. Confirm V631 proved ADSP/SLPI returned and CDSP was the pre-firmware active
   blocking node.
3. Confirm V635 fixed CDSP boot-node timeout under read-only firmware mounts,
   but did not produce `sysmon_cdsp` or service `74`.
4. Confirm V636 preserved clean service `180` reproduction but still missed
   service `74`, WLAN-PD, WLFW/BDF, firmware-ready, and `wlan0`.
5. Keep all HAL/connect/credential/external-ping paths blocked.

## Success Criteria

V637 passes if it classifies one of these outcomes without contacting the
device:

- `v637-service74-needs-sibling-sysmon-not-cdsp-power`
- `v637-service74-post-cdsp-evidence-gap`

If the first outcome is selected, the next live candidate should remain below
HAL/connect: a firmware-backed per-node sibling SSCTL composite observer with
strict timeout, warning, cleanup, and no Wi-Fi bring-up gates.
