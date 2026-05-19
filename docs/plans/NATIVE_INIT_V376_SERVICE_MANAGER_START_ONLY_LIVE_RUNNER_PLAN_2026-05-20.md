# V376 Service-Manager Start-Only Live Runner Plan

## Summary

- 목표는 V375로 배포된 `a90_android_execns_probe v12`를 이용해 V373 service-manager start-only smoke의 실제 실행 본문을 추가하는 것이다.
- 이 단계는 `servicemanager`와 `hwservicemanager`의 bounded start-only 관찰까지만 허용한다.
- Wi-Fi HAL, CNSS, wificond, supplicant, hostapd, scan/connect/link-up, credential, DHCP, routing은 계속 금지한다.
- `run`은 exact approval phrase, `--apply`, `--assume-yes`가 모두 맞을 때만 daemon start를 수행한다.

## Approval Phrase

```text
approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Implementation

- 새 host runner: `scripts/revalidation/wifi_service_manager_start_only_live_runner.py`
- 대상 helper: `/cache/bin/a90_android_execns_probe`
- required helper SHA-256: `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`
- start-only target profiles:
  - `system-servicemanager`
  - `system-hwservicemanager`
- helper mode:
  - `--mode service-manager-start-only`
  - `--allow-service-manager-start-only` only after exact approval
  - `--timeout-sec` bounded to `1..30`

## Guardrails

- `plan`: bridge/device command 없음.
- `preflight`: read-only native state와 helper readiness만 확인한다.
- `run` without exact phrase: bridge/device command 없음.
- approved `run`: service-manager start-only helper calls와 postflight process/network cleanliness check만 수행한다.
- 명시적 금지:
  - Wi-Fi HAL, CNSS, wificond, supplicant, hostapd start
  - Wi-Fi scan/connect/link-up, credential, DHCP, routing
  - rfkill write, driver bind/unbind, firmware mutation
  - Android partition write

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_service_manager_start_only_live_runner.py

python3 scripts/revalidation/wifi_service_manager_start_only_live_runner.py \
  --out-dir tmp/wifi/v376-plan-$(date +%Y%m%d-%H%M%S) \
  plan

python3 scripts/revalidation/wifi_service_manager_start_only_live_runner.py \
  --out-dir tmp/wifi/v376-preflight-$(date +%Y%m%d-%H%M%S) \
  preflight

python3 scripts/revalidation/wifi_service_manager_start_only_live_runner.py \
  --out-dir tmp/wifi/v376-refusal-$(date +%Y%m%d-%H%M%S) \
  run
```

Approved live run requires the exact phrase and flags:

```bash
python3 scripts/revalidation/wifi_service_manager_start_only_live_runner.py \
  --out-dir tmp/wifi/v376-approved-run-$(date +%Y%m%d-%H%M%S) \
  --apply \
  --assume-yes \
  --approval-phrase "approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up" \
  run
```

## Acceptance

- Preflight passes native version/status/selftest checks.
- Remote helper v12 SHA and usage are confirmed.
- `servicemanager` and `hwservicemanager` binaries are visible.
- no existing service-manager family process is running.
- no Wi-Fi link surface is active.
- temporary Binder nodes are not pre-existing.
- no-approval run records approval-required with `daemon_start_executed=false` and no native steps.
