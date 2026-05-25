# Native Init V837 Timestamped Service-notifier Hold Plan

## Goal

V837 tests the remaining timing gap after V836: whether the corrected
`msm/modem/wlan_pd` service-notifier listener is open through the service `74`
post-window where Android later reaches WLAN-PD / WLFW.

## Current Basis

- V829 proved service-locator `GET_DOMAIN_LIST wlan/fw` returns
  `msm/modem/wlan_pd`, instance `180`; pd-mapper empty-domain is closed.
- V830/V831 proved the service-notifier listener request model is accepted.
- V833 Android positive-control proved the same listener model can return
  `UP`.
- V835 proved the best native lower window still returns `UNINIT`.
- V836 selected timestamped listener hold as the next narrow gate before any
  wider Wi-Fi stack action.

## Implementation

- Build helper `a90_android_execns_probe v129`.
- Add listener timing fields:
  - `send_before_ms`
  - `send_after_ms`
  - `first_response_ms`
  - `first_indication_ms`
  - `close_ms`
  - `hold_ms`
- Reuse the V835 lower window:
  - clean-DSP arm-only proof
  - current V401/V490 prep
  - firmware mounts
  - `subsys_modem` holder
  - `qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon`
- Parse dmesg timestamps for service `74`, WLAN-PD, WLFW, BDF, and `wlan0`.

## Success Criteria

- Helper v129 is deployed and verified by SHA-256.
- The bounded listener request is sent only to service-notifier `66/46081`.
- The run records listener send/response/close timestamps.
- The run records service `74` timestamp from dmesg.
- The classifier distinguishes:
  - listener not open at service `74`;
  - listener open through service `74` + `5s` with no indication;
  - late WLAN-PD indication;
  - too-short hold.

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

If the listener is open through service `74` + `5s` and still receives no
indication, timing is no longer the primary explanation. The next gate should
classify the Android-only explicit WLAN-PD state-up trigger, likely below HAL
and before scan/connect.
