# V375 Execns Helper v12 Deploy / Preflight Plan

## Summary

- 목표는 V374에서 빌드한 `a90_android_execns_probe v12`를 native runtime의 `/cache/bin/a90_android_execns_probe`로 배포하고, V373 service-manager start-only preflight를 다시 통과 가능한 상태로 만드는 것이다.
- 이 단계는 helper 배포까지만 허용한다. `servicemanager`, `hwservicemanager`, Wi-Fi HAL, CNSS, scan/connect/link-up은 시작하지 않는다.
- `/cache/bin` 쓰기가 포함되므로 `run`은 exact approval phrase, `--apply`, `--assume-yes`가 모두 맞을 때만 진행한다.

## Approval Phrase

```text
approve v375 deploy execns helper v12 only; no daemon start and no Wi-Fi bring-up
```

## Implementation

- 새 host executor: `scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py`
- 기본 local artifact:
  - `tmp/wifi/v374-a90_android_execns_probe-v12/a90_android_execns_probe`
  - expected SHA-256: `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`
- 기본 remote target:
  - `/cache/bin/a90_android_execns_probe`
- 전송 경로:
  - NCM `192.168.7.2`
  - device `toybox netcat` + `dd` receive
  - host `tcpctl_host.py install` 패턴 재사용

## Guardrails

- `plan`: bridge/device command 없음.
- `preflight`: read-only native state, local helper hash/string, host NCM ping만 확인.
- `run` without exact phrase: device write 없음.
- approved `run`: helper install/verify와 V373 preflight 재실행만 수행.
- 명시적 금지:
  - service-manager family process start
  - Wi-Fi HAL/wificond/supplicant/hostapd/CNSS/diag start
  - Wi-Fi scan/connect/link-up, credential, DHCP, routing
  - Android partition write, firmware mutation, rfkill write, driver bind/unbind

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py \
  scripts/revalidation/wifi_service_manager_start_only_smoke.py \
  scripts/revalidation/tcpctl_host.py

python3 scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py \
  --out-dir tmp/wifi/v375-plan-smoke \
  plan

python3 scripts/revalidation/wifi_execns_helper_v12_deploy_preflight.py \
  --out-dir tmp/wifi/v375-preflight-$(date +%Y%m%d-%H%M%S) \
  preflight
```

## Acceptance

- local v12 helper hash and marker pass.
- native `status`/`selftest` clean.
- host NCM ping to `192.168.7.2` pass.
- current remote helper is either already v12 or approved run installs it.
- post-deploy V373 preflight no longer blocks on `helper-service-manager-mode`.
- daemon start remains a separate V373 approval step.
