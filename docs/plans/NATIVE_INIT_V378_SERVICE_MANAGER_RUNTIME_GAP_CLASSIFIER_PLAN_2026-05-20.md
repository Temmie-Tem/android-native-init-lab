# V378 Service-Manager Runtime Gap Classifier Plan

## Summary

- 목표는 V376 approved service-manager start-only run의 `runtime-gap`을 host-only로 분류하는 것이다.
- V378은 device mutation을 하지 않고 V376 evidence만 읽어 첫 번째 actionable blocker를 고정한다.
- 현재 V376 evidence는 `servicemanager`와 `hwservicemanager`가 모두 `SIGABRT`로 종료했고, stderr는 Binder driver open 실패를 가리킨다.
- HAL start-only approval packet은 runtime-gap 분류/수정 전까지 만들지 않는다.

## Implementation

- 새 classifier: `scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py`
- 입력 기본값:
  - `tmp/wifi/v376-approved-run-20260520-022612/manifest.json`
- 명령:
  - `classify`: 실제 V376 evidence를 분류한다.
  - `regression`: synthetic cases로 분류 matrix를 검증한다.

## Decision Model

- no approved V376 manifest: `service-manager-runtime-gap-classifier-awaiting-v376`
- V376 is not runtime-gap: `service-manager-runtime-gap-classifier-not-needed`
- missing observation files: `service-manager-runtime-gap-classifier-missing-observations`
- unsafe postflight: `service-manager-runtime-gap-classifier-unsafe-postflight`
- Binder open failure in all targets: `service-manager-runtime-gap-binder-devnode-required`
- property runtime missing without Binder failure: `service-manager-runtime-gap-property-runtime-required`
- unknown pattern: `service-manager-runtime-gap-manual-review`

## Current Technical Basis

- V376 stderr:
  - `Binder driver '/dev/binder' could not be opened.  Terminating.`
  - `Binder driver could not be opened. Terminating.`
- Current read-only Binder feasibility refresh:
  - evidence: `tmp/wifi/v378-current-binder-devnode-feasibility-20260520-023057/`
  - decision: `binder-devnode-plan-ready`
  - candidates: `/dev/binder c 10 81`, `/dev/hwbinder c 10 80`, `/dev/vndbinder c 10 79`
- Existing V292 open-only smoke already proved temporary devnodes can be created/opened/removed safely.
- Kernel binderfs documentation confirms Binder devices can be private per binderfs instance, but V378 does not mount binderfs or allocate Binder devices: https://www.kernel.org/doc/html/v5.1/filesystems/binderfs.html

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py

python3 scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py \
  --out-dir tmp/wifi/v378-service-manager-runtime-gap-classifier-regression-$(date +%Y%m%d-%H%M%S) \
  regression

python3 scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py \
  --out-dir tmp/wifi/v378-service-manager-runtime-gap-classifier-live-$(date +%Y%m%d-%H%M%S) \
  classify

python3 scripts/revalidation/wifi_binder_devnode_feasibility.py \
  --out-dir tmp/wifi/v378-current-binder-devnode-feasibility-$(date +%Y%m%d-%H%M%S) \
  --expect-version "A90 Linux init 0.9.61 (v319)" \
  run
```

## Acceptance

- Regression passes without device commands/mutations.
- Live classify returns `service-manager-runtime-gap-binder-devnode-required`.
- Current Binder metadata refresh confirms candidate major/minor values.
- Next work is helper-private Binder devnode provisioning, not HAL start.
