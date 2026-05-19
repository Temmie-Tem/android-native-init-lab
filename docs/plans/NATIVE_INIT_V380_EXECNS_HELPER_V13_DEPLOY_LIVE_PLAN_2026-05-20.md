# V380 Execns Helper V13 Deploy + Start-Only Live Plan

## Summary

- Baseline native build remains `A90 Linux init 0.9.61 (v319)`.
- V380 deploys `a90_android_execns_probe v13` to `/cache/bin/a90_android_execns_probe` and reruns the bounded service-manager start-only smoke.
- Scope remains narrow:
  - deploy one helper binary
  - start only `servicemanager` and `hwservicemanager` under bounded helper control
  - no Wi-Fi HAL start
  - no scan/connect/link-up/credential/DHCP/routing

## Execution Boundary

- V13 deploy approval phrase:
  - `approve v380 deploy execns helper v13 only; no daemon start and no Wi-Fi bring-up`
- Service-manager start-only approval phrase:
  - `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`
- NCM host setup may require sudo/TTY. If unavailable, use serial `appendfile + uudecode` fallback for helper deployment.

## Expected Outcomes

- Remote helper SHA matches the V379 artifact.
- Helper usage reports `a90_android_execns_probe v13`, `service-manager-start-only`, and `--allow-service-manager-start-only`.
- Private Binder nodes are visible inside the helper namespace:
  - `/dev/binder` `c 10 81`
  - `/dev/hwbinder` `c 10 80`
  - `/dev/vndbinder` `c 10 79`
- If service-manager still exits, classify the next runtime gap before HAL work.

## Guardrails

- No global native `/dev/binder` creation.
- No Android partition writes.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, CNSS, scan/connect, DHCP, routing, or credential operations.
- Postflight must show no lingering service-manager processes and no Wi-Fi links.

## Next

- If start-only passes, move to HAL-readiness approval packet.
- If it remains a runtime gap, classify the blocker and plan the smallest private runtime repair.
