# Native Init V831 Early Service-notifier Listener Report

## Result

- decision: `v831-service-notifier-early-listener-state-not-up`
- pass: `true`
- reason: listener registered but state is `uninit`; no state indication arrived
- evidence: `tmp/wifi/v831-service-notifier-early-listener-run-20260525-121658/`
- runner: `scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py`
- helper: `a90_android_execns_probe v128`
- helper sha256: `30a509d500a8c887c1fb43c506c86aa2bf3b450bb770043d91a38a9d11dddfb8`

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py \
  scripts/revalidation/wifi_execns_helper_v128_deploy_preflight.py

strings tmp/wifi/v831-execns-helper-v128-build/a90_android_execns_probe \
  | rg 'a90_android_execns_probe v128|--allow-service-notifier-listener-probe|--qrtr-readback-matrix|early-window'

python3 scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py \
  --out-dir tmp/wifi/v831-service-notifier-early-listener-plan-check \
  plan

python3 scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py \
  --out-dir tmp/wifi/v831-service-notifier-early-listener-preflight \
  preflight

python3 scripts/revalidation/native_wifi_service_notifier_early_listener_probe_v831.py \
  --out-dir tmp/wifi/v831-service-notifier-early-listener-run-20260525-121658 \
  run
```

## Evidence Summary

- phase: `early-window`
- child stack: lower companion start-only, `child_started=6`
- service-notifier endpoint: service `66`, encoded instance `46081`, node `0`,
  port `2`
- request bytes: `31`
- response: QMI result `0`, error `0`
- response current state: `0x7fffffff` / `uninit`
- state indication: not observed
- ACK: not sent because no indication arrived
- cleanup reboot: executed
- post-cleanup health: native build `0.9.68 (v724)`, status `ok`

## Guardrails

- service-manager: not executed
- Wi-Fi HAL: not executed
- scan/connect/link-up: not executed
- credential use: not executed
- DHCP/route/external ping: not executed
- `esoc0`, module load/unload, boot image write, partition write, custom-kernel
  flash: not executed

## Interpretation

V831 removes a timing ambiguity left by V830. The listener was established in
the early lower companion window, but `msm/modem/wlan_pd` still reported
`UNINIT` and never produced a state indication in the bounded observation
window. The active blocker remains the modem/WLAN-PD online trigger, not
service-locator discovery, service-notifier endpoint visibility, or listener
registration.

The next gate should classify the minimal safe path that makes Android set
`mdm3=ONLINE` and WLAN-PD `UP`, while keeping service-manager, Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, and external ping blocked.
