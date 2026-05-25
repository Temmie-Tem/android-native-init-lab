# Native Init V839 Post-V838 Trigger Classifier Plan

## Goal

V839 is a host-only classifier that selects the next Wi-Fi gate after V838 ruled
out the simple service-notifier listener timing explanation.

## Current Basis

- V833 Android positive-control proves the same bounded listener can observe
  WLAN-PD `UP`; raw state is `0x1fffffff`.
- V838 proves native lower-only listener registration happens before service
  `74` and remains open through service `74` + `5s`, but WLAN-PD remains
  `UNINIT`.
- V700 proves provider-first CNSS retry can run with `vendor.qcom.PeripheralManager`
  visible and without the prior CNSS Binder failure, but it did not include the
  prearmed WLAN-PD listener.

## Implementation

- Read only existing manifests and transcripts.
- Compare Android V833, native V838, and provider-first V700.
- Reject unchanged repeats of V838 lower-only and V700 provider-first gates.
- Select the smallest combined next gate:
  provider-first CNSS retry plus V838-style prearmed WLAN-PD listener.

## Success Criteria

- No device command or live mutation is executed.
- Android reference path proves WLAN-PD/WLFW/`wlan0`.
- V838 proves listener timing is closed.
- V700 proves provider-first CNSS retry reached the post-Binder gap.
- The selected next gate keeps Wi-Fi HAL, scan/connect, DHCP, routes, and
  external ping blocked.

## Hard Gates

- No service-manager or daemon start in V839 itself.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP, route change, or external ping.
- No `esoc0` open.
- No `wlan.ko` load/unload.
- No boot image write, partition write, or custom kernel flash.

## Expected Branch

If all input evidence is consistent, V840 should combine provider-first CNSS
retry with the prearmed service-notifier listener. The outcome to watch is
WLAN-PD `UP` first; WLFW/BDF/`wlan0` remains observational, not a permission to
scan/connect yet.
