# Archive Index

Nothing under this directory is an active source of device authorization.
Historical `ACTIVE` strings and acknowledgement tokens are inert evidence.

## Process v2 snapshots

- `policy/AGENTS_PRE_PROCESS_V2_2026-07-21.md`: immutable Git blob, SHA256, and
  retrieval commands for the complete pre-v2 operating contract.
- `policy/AGENTS_INTERIM_FAST_LOOP_RETIRED_2026-08-03.md`: byte-identical
  82-line retired trial block, SHA-256
  `e270865908821ff1221665a83a22707ae0dcde140e18e5ba600b82423c34dbc7`.
  It is inert historical evidence and grants no current authority.
- `roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md`: immutable Git blob, SHA256, and
  retrieval commands for the complete pre-v2 accumulated roadmap.

## Documentation index snapshots

- `documentation/DOCS_README_KO_LEGACY_2026-09-09.md`: byte-identical copy of the
  Korean `docs/README.md` as it stood on 2026-09-09, 294,075 bytes, SHA-256
  `57692dc1e00df1aa04c5fd377707d893f8684e1eacf5ddfdcfc32d1f2e43adfd`, taken
  before that file was replaced by a real documentation index. It is retained
  unmodified so anything the new index does not carry can be recovered from the
  original rather than reconstructed.

  It is inert historical evidence and grants no current authority. Two kinds of
  content inside it are **not** current state and must not be read as such: its
  `## 현재 기준점` section records an A90 baseline of `0.9.266
  (v2232-service-object-fwclass-bridge)` that later A90 reports already move
  past, and its S22+ frontier, Wi-Fi investigation and module-map sections are
  snapshots of the day. Current state is canonical in the per-target `GOAL.md`
  files, the device pages and the reports.

`docs/archive/legacy/`에는 이번 리셋 이전의 2025 방향 문서를 그대로 보관합니다.

포함 범위:
- 네이티브 Linux 부팅 연구 문서
- Headless Android / Custom Kernel 계획서
- AOSP 최소 빌드 가이드
- Phase 1/2 상태 요약 및 보고서

주요 경로:
- `legacy/README.md`
- `legacy/overview/PROJECT_STATUS.md`
- `legacy/overview/PROGRESS_LOG.md`
- `legacy/plans/`
- `legacy/guides/`
- `legacy/reports/`

## 2026 재도전기 overview 문서 (종료됨)

`docs/archive/overview/`에는 2026-04-23 재개 이후의 overview 문서 중 갱신이
멈춘 것을 보관합니다. 위 `legacy/`(2025 세대)와는 다른 세대입니다.

| 옛 경로 | 현재 경로 | 종료 시점 |
| --- | --- | --- |
| `docs/overview/PROGRESS_LOG.md` | `overview/PROGRESS_LOG_2026-04-23_2026-05-02.md` | 2026-05-02 |
| `docs/overview/PROJECT_STATUS.md` | `overview/PROJECT_STATUS_A90_THROUGH_2026-06-19.md` | 2026-06-19 |

두 문서의 후속은 `docs/overview/PROJECT_HISTORY.ko.md`(연혁)와
`docs/devices/`(기기별 현재 상태)로 나뉘어 이관됐습니다. 2026-09-02에
이동했으며 본문은 수정하지 않았습니다.

현재 작업은 상단 `docs/`를 기준으로 진행하고, archive는 참고 자료로만 사용합니다.
