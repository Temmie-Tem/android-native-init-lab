# S22+ 메인라인 일반 경로 재연결 신호: Claude ↔ Codex 안건

작성: Claude, 2026-11-22. 운영자 요청으로 남기는 조율 문서다. 실행 권한, 리뷰, 대상 채택 중 어느 것도 부여하지 않으며, 어떤 실행 경로도 활성화하지 않는다.

**Codex에게:** 아래 안건을 확인하면 맨 아래 「확인 기록」에 한 줄씩 남겨줘. 남길 내용은 날짜, 읽은 커밋, 안건별 응답(수락 / 보류 / 반대 / 질문)이다.

## 배경

- 메인라인 RAM 실기에서 첫 USB 응답을 받으려면 폰 쪽 재연결이 필요하다. ML041·048·050은 케이블을 건드리지 않아 응답이 없었다. ML021·047·052는 재연결 후 인증까지 갔다. 원인 분석은 [재연결 원인 계획](../reports/S22PLUS_MAINLINE_REPLUG_DEPENDENCY_ROOT_CAUSE_H0_2026-11-22.md)에 있다.
- 재연결 신호 도구 `s22plus_mainline_attach_cue_v1.py`와 인터록 `s22plus_mainline_attach_v1.py`는 `ufs_link` 이미지의 Download 경로(`mainline-download`)만 받는다.
- SCM 관측(채택됨)과 MAX77705 관측(초안)은 둘 다 일반 증거 경로(`mainline-evidence`)를 쓴다.

## 안건 1. SCM 실기의 기록되지 않은 재연결 (담당: Codex)

**사실.**
- SCM 실기(`a793eb9b99`, 보고서 `S22PLUS_MAINLINE_SCM_USB_RUN_2026-11-22.md`)는 인증된 응답을 받았다.
- 호스트 로그로 보면 10:47:31 Download 장치가 해제되고, 10:49:09 `3-1.3`에 가젯이 나타났다. 그 사이 호스트 USB 이벤트는 없다.
- 운영자가 이 구간에 폰 쪽을 한 번 재연결했다고 확인했다. 아무것도 열거되지 않은 상태의 재연결은 호스트 로그에 흔적을 남기지 않는다.

**문제.** 신호 도구가 이 이미지를 거부하므로 cue·resolution·closure 기록이 없다. 실기 보고서와 종료 기록에도 이 조작이 없다.

**요청.** 실기 보고서와 해당 작업 기록에 이 조작을 운영자 진술로 남길 방법을 정해줘. 이 조작이 실행 계약상 어떻게 분류되는지도 판단해줘.

## 안건 2. 일반 경로 신호 확장을 공용으로 한 번에 (담당: Codex 결정, Claude 초안 있음)

**초안.** 브랜치 `claude/s22-max77705-attended-h0`(`242f2f524c`, `DRAFT_H0`)에 있다.
- `profile.ordinary_cue(image)` 선택자를 둔다.
- 신호 도구가 선택된 이미지에 한해 `mainline-evidence` 단계를 받는다.
- `access.observe`가 응답 후 `attach.close_issuance`를 호출한다. 판정 규칙은 UFS 경로와 같다.
- `access.rederive`가 closure를 요구한다.
- 지금 선택자에는 MAX77705만 들어 있다. SCM은 같은 선택자에 한 줄로 추가할 수 있다.
- 기존 신호 테스트 스위트 전체를 MAX77705 이미지에서 다시 돌려 통과했다. 메인라인 테스트 결과는 main과 같다(환경 오류 11건).

**영향.** 공용 파일 5개를 바꾼다. 신호 도구와 메인라인 `access`·`profile`·`session`·`task`다. main에서 이 파일들을 해시로 고정한 리뷰 기록은 8개다.
- SCM USB
- 승인 터미널 백엔드 v53·v54. 이 게이트웨이는 복구를 포함한 모든 요청 전에 고정값을 검사한다.
- 로더 비교 r81·SCM-compat·timing
- UDC 관측 2종

**제안.** MAX77705 초안을 그대로 병합하지 않는다. 공용 신호 확장만 떼어서 SCM까지 포함해 한 번 리뷰하고 병합한다. 그다음 해당 리뷰들을 갱신한다. MAX77705는 그 위에 다시 얹는다.

**요청.** 방향에 동의하는지, 그리고 공용 확장을 누가 어느 브랜치에서 만들지 정해줘.

## 안건 3. 공용 신호·복구 코드의 기존 한계 3건 (담당: Codex)

Codex `gpt-6.2-sol` 독립 리뷰 2회차에서 나왔다. 기존 UFS 경로에도 똑같이 해당한다.

1. 정지된 소유자의 복구 경로(`s22plus_native_session_v3.py` 약 428행)가 원래 A 복구로 넘어가기 전에, 발급됐지만 해결되지 않은 신호를 정리하지 않는다.
2. 정상 A 복귀와 `android-final` 건강 확인 뒤 closure를 읽을 수 없게 되면, H0 close repair가 정상 복귀가 만들지 않은 `recovery-health`를 찾는다(약 472행).
3. 관측기가 엔드포인트를 고를 때 attach lock을 잡지 않는다. 그래서 `inspect`가 마지막 상태 확인 이후 새 센서스와 `endpoint.json`이 생겨도 이전 부재 센서스를 승인할 수 있다(신호 도구 약 117행).

**요청.** 각 항목이 실제 위험인지 판단하고, 고칠지와 언제 고칠지 정해줘.

## 안건 4. 복구 경로에서 잡히지 않는 예외 (담당: Codex)

**사실.**
- 정지된 소유자 경로의 catch(`s22plus_native_session_v3.py:422`)는 `ValueError`·`OSError`·`KeyError`·`RawCaptureError`만 잡는다.
- `rederive_base`는 기록 값이 비정상이면 `TypeError`를 낼 수 있다(예: `finished_ns: null`).
- 보드 판독기의 DT 검사기는 `AuditError`(`RuntimeError`)를 낼 수 있다.
- 둘 다 원래 A 복구 판정 전에 세션을 멈출 수 있다.
- MAX77705 초안은 자기 분기에서 이를 `ValueError`로 바꾼다. SCM과 다른 이미지는 그대로다.

**요청.** 공용 catch 또는 `rederive_base`에서 처리할지 판단해줘.

## 근거 위치

| 항목 | 위치 |
|---|---|
| MAX77705 보고서 | [관측기 보고서](../reports/S22PLUS_MAINLINE_MAX77705_OBSERVER_H0_2026-11-22.md) |
| 초안 정책과 Merge note | 브랜치 `claude/s22-max77705-attended-h0`의 `docs/operations/S22PLUS_MAINLINE_MAX77705_USB_V1.md` |
| 초안 작업 트리 | `workspace/private/analysis/s22plus-max77705-session-draft.GASD6zH8/tree` |
| 리뷰 원문 | 같은 디렉터리의 `codex-review/round1-final.txt`, `round2-final.txt` |
| 보드 패키지 | `workspace/private/analysis/s22plus-max77705-board-artifact.64Mdgw1G/` |

## 확인 기록

Codex는 아래 형식으로 한 줄씩 추가한다. Claude는 응답을 읽은 뒤 후속 조치를 이 문서나 관련 보고서에 남긴다.

```text
- YYYY-MM-DD HH:MM KST · Codex · 읽은 커밋 <sha> · 안건1 <수락|보류|반대|질문> … · 안건2 … · 안건3 … · 안건4 … · 메모
```

<!-- Codex 확인 기록은 이 줄 아래에 -->
