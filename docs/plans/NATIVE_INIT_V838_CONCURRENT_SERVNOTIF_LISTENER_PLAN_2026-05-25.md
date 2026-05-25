# Native Init V838 Concurrent Service-notifier Listener Plan

## Goal

V838 closes the V837 timing ambiguity by pre-arming the
`msm/modem/wlan_pd` service-notifier listener before the native lower companion
stack publishes service `74`.

## Current Basis

- V829 proved service-locator `GET_DOMAIN_LIST wlan/fw` returns
  `msm/modem/wlan_pd`, instance `180`.
- V830/V831 proved the service-notifier listener request model is accepted.
- V833 Android positive-control proved the same listener can report `UP`.
- V835 proved the best native lower window still returns `UNINIT`.
- V837 recorded timestamps and proved the in-helper listener was opened about
  `613ms` after service `74`.

## Implementation

- Build helper `a90_android_execns_probe v130`.
- Add `service-notifier-listener-only` mode.
- In listener-only mode, skip namespace setup and run only the bounded
  service-notifier listener probe.
- Keep QRTR lookup armed through an empty nameservice response so the listener
  can wait for the service-notifier endpoint before service `74`.
- Wrap the existing lower companion helper command so it:
  - starts listener-only in the background;
  - runs the existing CNSS-only lower helper in the foreground;
  - stores listener output in `/cache` for post-cleanup collection.

## Success Criteria

- Helper v130 is deployed and verified by SHA-256.
- The listener-only process begins before service `74`.
- The listener registers before or at service `74`, or the run proves why it
  still cannot.
- The listener remains open through service `74` + `5s`.
- The classifier distinguishes:
  - listener process not open at service `74`;
  - process open but REGISTER_LISTENER still post-service `74`;
  - listener open through service `74` + `5s` with no indication;
  - WLAN-PD `UP` indication observed.

## Hard Gates

- No service-manager start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP, route change, or external ping.
- No `esoc0` open.
- No `wlan.ko` load/unload.
- No boot image write, partition write, or custom kernel flash.

## Expected Branch

If the listener is pre-armed and registered through service `74` + `5s` but
still receives no WLAN-PD `UP` indication, the remaining blocker is not timing.
The next gate should classify the missing Android-only explicit WLAN-PD
state-up trigger before any HAL/connect widening.
