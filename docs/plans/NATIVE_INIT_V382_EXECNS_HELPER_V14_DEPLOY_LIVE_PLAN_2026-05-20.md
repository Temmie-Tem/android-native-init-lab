# V382 Execns Helper V14 Deploy + Property Runtime Start-Only Plan

## Summary

- Baseline native build remains `A90 Linux init 0.9.61 (v319)`.
- V382 deploys `a90_android_execns_probe v14` to `/cache/bin/a90_android_execns_probe`.
- After deployment, V382 reruns bounded service-manager start-only with:
  - private Binder nodes from v13
  - private property root from the V317 `/dev/__properties__` export
  - private-empty `/data/vendor/wifi/sockets`
- Scope remains narrow:
  - deploy one helper binary
  - start only `servicemanager` and `hwservicemanager` under bounded helper control
  - no Wi-Fi HAL start
  - no scan/connect/link-up/credential/DHCP/routing

## Execution Boundary

- V14 deploy approval phrase:
  - `approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up`
- Service-manager start-only approval phrase:
  - `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`
- NCM host setup may require sudo/TTY. If unavailable, use serial `appendfile + uudecode` fallback for helper deployment.

## Local Prepared State

- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- local artifact: `tmp/wifi/v381-a90_android_execns_probe-v14/a90_android_execns_probe`
- artifact sha256: `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py`
- helper marker: `a90_android_execns_probe v14`

## Expected Outcomes

- Remote helper SHA matches the V381 artifact.
- Helper usage reports:
  - `a90_android_execns_probe v14`
  - `service-manager-start-only`
  - `--allow-service-manager-start-only`
  - `--property-root`
  - `--data-wifi-mode`
- The start-only live run uses:
  - `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`
  - `--data-wifi-mode private-empty`
- If service-manager still exits, classify the next runtime gap before HAL work.

## Guardrails

- No global native `/dev/binder` creation.
- No Android partition writes.
- No mutation of the private property source.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, CNSS, scan/connect, DHCP, routing, or credential operations.
- Postflight must show no lingering service-manager processes and no Wi-Fi links.

## Validation Plan

Local/static:

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py \
  scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py \
  scripts/revalidation/wifi_service_manager_start_only_live_runner.py \
  scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py

python3 scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py plan
python3 scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py preflight
```

Approved deploy:

```bash
python3 scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py \
  --approval-phrase "approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

Approved start-only live smoke:

```bash
python3 scripts/revalidation/wifi_service_manager_start_only_live_runner.py \
  --helper-sha256 f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7 \
  --approval-phrase "approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

## Next

- If both service-manager targets pass cleanly, create a HAL-readiness approval packet.
- If the property/runtime repair changes the runtime gap, classify the new blocker.
- If the same gap remains, inspect whether the runner actually passes `--property-root` and `--data-wifi-mode private-empty` into the v14 helper before adding new runtime repairs.
