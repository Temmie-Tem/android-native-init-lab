# Native Init V831 Early Service-notifier Listener Plan

## Goal

Move the V830 listener earlier in the lower companion window to determine
whether `msm/modem/wlan_pd` briefly transitions to `UP` and then returns to
`UNINIT`, or whether it never reaches `UP` in the native lower window.

## Basis

- V829 proved service-locator returns `msm/modem/wlan_pd` instance `180` for
  `wlan/fw`.
- V830 proved service-notifier `66/46081` accepts `REGISTER_LISTENER`, but the
  current state at end-of-window is `uninit`.
- Android reference evidence has `mss=ONLINE`, `mdm3=ONLINE`, WLAN-PD, WLFW,
  BDF, and `wlan0`; native lower windows still have `mdm3=OFFLINING`.

## Implementation

- Bump exec namespace helper to `a90_android_execns_probe v128`.
- Keep the same explicit gate: `--allow-service-notifier-listener-probe`.
- Change listener timing from late-window to early-window:
  - start lower companion children;
  - capture `net_after_spawn`;
  - discover service-notifier endpoint `66/46081`;
  - send one `REGISTER_LISTENER` request for `msm/modem/wlan_pd`;
  - keep the socket open for a bounded indication window before cleanup.
- Increase service-notifier endpoint readback to `10s` and response/indication
  observation to `15s`.

## Guardrails

- No service-manager, Wi-Fi HAL, wificond, supplicant, scan, connect, link-up,
  DHCP, route, external ping, or credentials.
- No `esoc0` open, qcwlanstate write, bind/unbind, driver override, module
  load/unload, boot image write, partition write, or custom-kernel flash.
- Cleanup reboot remains the live boundary.

## Commands

```bash
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v831-execns-helper-v128-build/a90_android_execns_probe

python3 scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py \
  --out-dir tmp/wifi/v831-service-notifier-early-listener-plan-check \
  plan

python3 scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py \
  --out-dir tmp/wifi/v831-service-notifier-early-listener-preflight \
  preflight

python3 scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py \
  --out-dir tmp/wifi/v831-service-notifier-early-listener-run \
  run
```

## Decision

- `state-up`: route next gate to WLFW service `69/1` and ICNSS firmware-ready
  observation.
- `state-not-up`: treat WLAN-PD online trigger as the active blocker and avoid
  HAL/connect retries.
- `no-response`: re-check service-notifier endpoint timing before widening.
