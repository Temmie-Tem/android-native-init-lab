# Native Init V646 Android Post-Service74 Timing Plan

- date: `2026-05-23 KST`
- cycle: `v646`
- scope: host-only classifier
- target: compare Android's normal service `74` → WLAN-PD/WLFW timing against
  V644's service `74` → warning timing

## Background

V644 proved native can publish service `74`, but a `pm_qos_add_request` warning
appeared about `11.789 ms` after service `74`. V645 showed clean-DSP alone and
service `180` alone are warning-free. V646 checks whether Android expects a
longer post-`74` window before WLAN-PD/WLFW/QMI, making the V644 warning a
preemption of the normal path.

## Inputs

- Android timing from V628/V622:
  `tmp/wifi/v628-service74-publisher-classifier/manifest.json`
- Native V644 live:
  `tmp/wifi/v644-live-20260523-071610/manifest.json`

## Guardrails

V646 is host-only and must not contact the device, start any daemon, start Wi-Fi
HAL, scan/connect, use credentials, run DHCP, change routes, or ping externally.

## Success Criteria

V646 passes if it proves:

- Android publishes service `74` quickly after `180`;
- Android waits substantially longer before WLAN-PD/WLFW/QMI;
- V644 hits the warning far earlier than that Android post-`74` window;
- next live work remains blocked until the warning source is classified.

## Next Gate

Expected next gate is V647 warning-source classifier:

- inspect V644/V619 warning call traces and Android non-warning path;
- determine whether the warning is audio deferred-probe, CNSS child timing,
  service `74` callback, or missing Android-side delay/ACK context;
- only then design a safer bounded live retry.
