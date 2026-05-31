# Native Init Versioning

Updated: `2026-05-31`

두 개의 독립된 버전 축을 쓴다. 자세한 규칙은
`docs/operations/VERSIONING_POLICY.md`를 따른다.

| 축 | 형식 | 올리는 시점 |
|---|---|---|
| 숫자 버전 | `MAJOR.MINOR.PATCH` (예: `0.9.68`) | 실제 boot image가 디바이스에 flash될 때 |
| 사이클 태그 | `vNNN` (예: `v724`, `V1253`) | host 도구·커밋·계획/리포트 등 모든 진행 단계 |

- 숫자 버전은 **boot image 정체성**이다. flash가 없으면 올리지 않는다.
- `vNNN`은 **진행 추적용**이다. host-only 작업·리포트·실험 게이트마다 자유롭게 증가한다.
- boot image를 빌드할 때, 그 시점의 **최신 `vNNN`을 이미지에 박아** 표기한다 →
  `A90 Linux init 0.9.68 (v724)`. 이후 사이클이 올라가도 재flash 전까지 박힌 태그는 유지된다.

## Current

- 현재 디바이스 빌드(flash): `A90 Linux init 0.9.68 (v724)`
- 공식 숫자 버전: `0.9.68`
- 박힌 빌드 태그: `v724`
- boot image: `stage3/boot_linux_v724.img`
- known-good fallback: `stage3/boot_linux_v48.img`
- 직전 rollback: `stage3/boot_linux_v261.img` (0.9.60)
- 현재 진행 사이클: **V1253** (native Wi-Fi bring-up; PMIC power-surface write-gate)
- 소스 루트: `stage3/linux_init/init_v724.c` + 모듈 `stage3/linux_init/a90_*.c/h`
- creator: `made by temmie0214`

`v724`(0.9.68) 이후 V725–V1253 사이클은 모두 host-only 연구이며 디바이스를 재flash하지
않았다. 그래서 디바이스 표기는 여전히 `0.9.68 (v724)`이고 연구 사이클만 V1253까지 진행됐다.

## Version Format

```text
A90 Linux init 0.9.68 (v724)
                ^^^^^^  ^^^^
                숫자    박힌 사이클 태그(빌드 시점 최신)
```

## Rules

- `MAJOR`: 구조/호환성이 크게 바뀌는 업데이트 (rootfs/service 구조, command 호환성, 부팅/저장소 전략)
- `MINOR`: 기능/능력 추가 (USB NCM, TCP control, netservice, app menu, storage manager 등)
- `PATCH`: 작은 수정·안정화·화면/문구 조정
- `vNNN`: 진행 사이클. boot image flash가 동반되면 그 사이클 태그를 숫자 버전에 박는다.

## Two-axis history

`v81`(0.8.12)–`v159`(0.9.59) 구간은 사이클과 flash가 사실상 **1:1**로 움직였다(매
사이클이 곧 boot image 릴리스). `v159` 이후 native Wi-Fi 연구기에 들어서며 두 축이
**분리**됐다: 숫자 버전은 실제 flash에서만 올랐고, 사이클은 독립적으로 진행됐다.

분리기 실제 flash 릴리스:

| 숫자 | 박힌 태그 | date | 요약 |
|---|---|---|---|
| `0.9.68` | `v724` | 2026-05-24 | qrtr-ns boot hook; service-locator ~4.4s (현재 디바이스 빌드) |
| `0.9.67` | `v641` | 2026-05-23 | firmware-backed boot-window proof |
| `0.9.66` | `v631` | 2026-05-23 | per-node SSCTL boot proof |
| `0.9.65` | `v630` | 2026-05-23 | sibling SSCTL boot proof |
| `0.9.61` | `v319` | 2026-05-19 | native serial transfer append |
| `0.9.60` | `v261` | 2026-05-19 | PID1 orphan/zombie reaper |

`0.9.0`–`0.9.59`(1:1 안정화기)와 `0.8.x` 이하 전체 per-release 이력은 `CHANGELOG.md`를
정식 기준으로 한다. `vNNN` 진행 사이클(특히 V160 이후 Wi-Fi 연구)은 `CLAUDE.md`와
`docs/plans/`, `docs/reports/`를 기준으로 한다.

## Local Artifact Retention

- 보존: 현재 `v724`, 직전 rollback `v261`, known-good fallback `v48`
- 정리 대상: 그 외 ignored `stage3/boot_linux_v*.img`, `stage3/ramdisk_v*`, compiled `stage3/linux_init/init_v*`
- 정리 도구: `python3 scripts/revalidation/cleanup_stage3_artifacts.py --execute`
- 리포트의 artifact hash와 tracked source는 유지되므로 오래된 local binary는 필요 시 재생성한다.

## 1.0.0 Criteria

`1.0.0`은 아직 아껴 둔다. 권장 기준:

- serial/NCM/TCP 제어 경로 장기 안정화
- 화면/버튼만으로 recovery/poweroff/status 확인 가능
- safe storage 정책과 복구 경로 문서화
- `/cache/bin` 도구와 runtime service 운용 정책 정리
- known-good fallback 유지
