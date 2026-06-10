# Codex 보안 스캔 결과 분류·해결 계획 (2026-06-10)

## 0. 이 문서의 목적

원본 스캔: `workspace/private/raw-logs/security/codex/2026-06-10/codex-security-findings-2026-06-10T02-46-26.267Z.csv`
(Codex Cloud Security, 613건, 전부 `status=new`, 자동분류·resolution 없음)

스캐너가 **5/12~6/10 전체 커밋 히스토리를 커밋 단위로** 훑은 결과라, 같은 취약점 클래스가
수백 개의 일회성 스크립트에 흩어져 중복 계상돼 있다. 이 문서는 각 finding을 **현재 코드베이스/커밋과
대조**해 (1) 아직 유효한지, (2) 어느 작업 단위에 속하는지, (3) 어떤 순서로 풀지를 정리한다.

핵심 결론 먼저:
- **613건 중 실제 활성 코드에 대한 건 15건**(직접) + 116건(아카이브→활성 마이그레이션, 재검토 필요).
- 나머지 **482건은 2026-06-07 워크스페이스 reorg에서 삭제된 `stage3/`·루트 `scripts/` 경로**에 대한 것.
  코드는 `workspace/public/archive/`에 보존돼 있으나 **활성 빌드/런타임에 포함되지 않음 → 조치 불요(close as stale)**.
- 활성 15건 중 **HIGH 2건은 이미 V2188/V2189 보안 하드닝 커밋(`be5c54e4`)으로 수정 완료**.
- 즉시 손봐야 할 **현재 유효 활성 건은 약 11건**이고, 호스트 브리지/전송 3건이 최우선.

이번 패치 기준 처리 상태:
- **Unit A/B/C/D 및 Tier 2 핵심 패턴 조치 완료.**
- V2189 source build PASS: `boot_sha256=f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51`,
  `helper_sha256=a4ef028aee167ab6a66b17389ade37427e85647d18e45270634f666b8efe1a44`.
- 로컬 targeted rescan PASS: `docs/security/scans/SECURITY_FRESH_SCAN_V2189_2026-06-10.md`
  (`PASS=10`, `WARN=1`, `FAIL=0`). 남은 WARN은 의도된 trusted-lab local root-control boundary.

## 1. 전체 분포

| 구분 (disposition) | high | medium | low | info | 합계 | 의미 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **ACTIVE** (활성 `workspace/public/src/` 직접 지목) | 3 | 8 | 2 | 2 | **15** | 우선 검증·처리 대상 |
| **MIGRATED** (구 경로 지목, basename이 활성 빌드로 이동) | 15 | 60 | 23 | 18 | **116** | 활성 헬퍼/하네스 재검토 필요 |
| **ARCHIVE** (코드가 `workspace/public/archive/`에만 존재) | 56 | 259 | 69 | 95 | **479** | 비활성, 조치 불요 |
| **DELETED** (완전 삭제) | 0 | 0 | 1 | 2 | **3** | 조치 불요 |

> 검증 근거: `git ls-files` 기준 루트 `stage3/`, `scripts/`, `mkbootimg/`는 추적/파일시스템 모두 부재
> (reorg 커밋 `ae6bbacf`로 삭제, archive로 이전). 활성 경로는 `workspace/public/src/`.

### 반복되는 취약점 클래스 (제목+본문 키워드, 중복 허용)

| 클래스 | 건수 | 활성 코드 잔존 여부 |
| --- | ---: | --- |
| 심링크/TOCTOU 경쟁 (root chown·chmod·write 싱크, 예측가능 `/tmp`·`/cache`) | 172 | **일부 활성** (bridge repair-dirs, wificfg 읽기경로, ping/HUD는 완화됨) |
| 무제한 read / 리소스 고갈 (DoS) | 83 | **일부 활성** (`evidence.py` 하네스) |
| raw DIAG/MAC/네트워크 식별자 리포트 유출 | 54 | **일부 활성** (wifi status, V2172 리포트) |
| 셸/커맨드 인젝션 (artifact export, readelf, manifest 경로) | 27 | 대부분 아카이브 스크립트 |
| 아티팩트 해시 위조/자기신고 신뢰 | 27 | 대부분 아카이브, 활성 flash는 핀 SHA로 보완됨 |
| 미검증 boot 아티팩트 flash | 22 | 활성 `native_init_flash.py`는 `--expect-sha256` 추가로 보완됨 |
| 노출된 serial bridge | 4 | 아카이브 |
| wpa_supplicant UID 미강등 | 1 | 활성 경로 재확인 권장 |

> 시사점: 활성 코드 처리는 "파일 단위"보다 **클래스 단위 패턴 수정**이 효율적이다. 예) 신뢰 디렉터리
> 부모 전체를 `O_NOFOLLOW`로 검증하는 패턴(이미 `a90_wifi.c`에 도입된 `wifi_verify_root_exec_parents`)을
> wificfg 읽기경로·HUD reader에 재사용하면 다수 잔여 건이 한 번에 닫힌다.

---

## 2. Tier 0 — 이미 해결됨 (검증 완료, 재오픈 불필요)

보안 하드닝 커밋 `be5c54e4 "Harden native Wi-Fi staging and pinned flash validation"`
(보고서: `NATIVE_INIT_V2188_SECURITY_P0_HARDENING_SOURCE_BUILD_2026-06-10.md`,
`...V2189_SECURITY_P0_STAGE_FIX_*`, 베이스라인 승격 `cd89f5c2`)이 다음을 닫았다.

| finding | 심각도 | 검증 결과 |
| --- | --- | --- |
| DHCP helper script runs from wifi-writable cache dir | high | **FIXED** — `wifi_prepare_runtime_dirs()`가 `/cache/a90-wifi`를 **root 소유(0755,0,0)**로, `/cache/a90-wifi/sockets`만 UID/GID 1010으로 생성([a90_wifi.c:600-608](workspace/public/src/native-init/a90_wifi.c#L600-L608)). udhcpc 스크립트 exec 전 `wifi_verify_root_exec_file()` 호출([a90_wifi.c:1164](workspace/public/src/native-init/a90_wifi.c#L1164),[1187](workspace/public/src/native-init/a90_wifi.c#L1187)). |
| Root exec from Wi-Fi-owned supplicant bundle | high | **FIXED** — `wifi_verify_root_exec_parents()`가 RUNTIME_ROOT부터 모든 상위 디렉터리를 `O_NOFOLLOW`로 열어 `S_ISDIR`·`uid==0`·비그룹/타인쓰기 검증, 파일은 `O_NOFOLLOW`+`S_ISREG`+`uid==0`+비쓰기+exec비트 검증([a90_wifi.c:117-205](workspace/public/src/native-init/a90_wifi.c#L117-L205)). supplicant 기동 전 호출([a90_wifi.c:640](workspace/public/src/native-init/a90_wifi.c#L640),[1777](workspace/public/src/native-init/a90_wifi.c#L1777),[2545](workspace/public/src/native-init/a90_wifi.c#L2545)). |
| Stale mkbootimg paths break boot image builders | info | **FIXED** — `MKBOOTIMG_DIR`가 `workspace/public/src/third_party/mkbootimg`로 갱신됨([build_native_init_boot_v724.py:32](workspace/public/src/scripts/revalidation/build_native_init_boot_v724.py#L32)). |

부분 완화(직접 전제는 사라졌으나 방어심화 미완) — Tier 2 하단 참조:
- **HUD follows untrusted autoconnect result path** (medium): `/cache/a90-wifi`가 root 소유로 바뀌어 UID 1010이
  `autoconnect.result`를 교체하는 **전제가 제거됨 → 실질 완화**. 잔여: `hud_read_key_value_file`는 여전히
  `O_NOFOLLOW`/타입검사 없음([a90_hud.c:32](workspace/public/src/native-init/a90_hud.c#L32)).
- **Root ping log symlink race** (medium): ping 로그 디렉터리가 root 소유 → 심링크 경쟁 전제 제거. 잔여:
  리밸리데이션 스크립트가 `rm -f "$LOG"; >"$LOG"` 셸 리다이렉트를 그대로 사용(호스트측 위생).

---

## 3. Tier 1 — 활성 코드 · 현재 유효 · 즉시 처리

직접 검증으로 **현재 코드에 그대로 존재**함을 확인한 건들. 작업 단위(파일/컴포넌트)로 묶음.

### Unit A — 호스트 브리지/전송 계층 (최우선)
하드닝 커밋이 손대지 않았고 모두 실제로 재현됨. 운영자가 직접 실행하는 신뢰경계라 영향이 큼.

| finding | 심각도 | 검증 | 위치 |
| --- | --- | --- | --- |
| repair-dirs follows symlinks and can chown arbitrary paths | **high** | **STILL VALID** — `chown_tree`가 최상위 `path`에 `is_dir()`(심링크 추종)+`os.walk()` 사용, 최상위 심링크 가드 없음. `follow_symlinks=False`는 최종 객체만 보호. 운영자가 sudo `repair-dirs` 실행 시 임의 root 디렉터리 chown/chmod 가능 | [a90_bridge.py:500-518](workspace/public/src/scripts/revalidation/a90_bridge.py#L500-L518) |
| Unsafe serial command replay on bridge-busy text | medium | **STILL VALID** — `if BRIDGE_BUSY_TEXT in text`(retry) 분기가 `if not allow_retry`(반환)보다 **먼저** 평가됨. unsafe 명령(`writefile`/`mount`/`dd`/`run`)도 busy 문구 포함 출력 시 재전송 → 전송 계약(부분쓰기 후 unsafe 미재실행) 위반 | [a90ctl.py:314-318](workspace/public/src/scripts/revalidation/a90ctl.py#L314-L318) |
| Default NCM repair can persistently alter host networking | medium | **STILL VALID(추정, 미수정)** — cdc_ncm+삼성 VID(04e8)만으로 매칭해 NetworkManager 프로파일을 자동 down/삭제/재생성+autoconnect=yes. USB 가젯→호스트 영속 설정 신뢰경계 침범. 명시적 opt-in·엄격 식별·롤백 필요 | [a90_ncm_transport.py](workspace/public/src/scripts/revalidation/a90_ncm_transport.py) |

권장 처리: (1) `chown_tree` 진입 전 각 대상 최상위 경로에 `path.is_symlink()` 거부 + `os.walk(followlinks=False)` 고정,
실경로가 `workspace/private/` 하위인지 `realpath` 재확인. (2) a90ctl에서 busy 분기를 `allow_retry` 가드 **뒤로** 이동하고
바이트 전송 전 브리지 생성 응답만 정확매칭(부분쓰기 후 unsafe 재시도 금지). (3) NCM repair에 `--repair-host-net` 같은 opt-in 플래그.

처리 결과(2026-06-10, Unit A patch):
- `a90_bridge.py repair-dirs`: `workspace/private/` 하위 lexical 경로만 허용하고, 기존 경로 컴포넌트 중
  symlink가 있으면 생성/수리 전에 거부한다. `chown_tree()`도 최상위 symlink/non-directory를 거부하고
  `os.walk(followlinks=False)`로 고정했다.
- `a90ctl.py`: unsafe command에서 bridge busy text가 반환되면 재전송하지 않고 즉시 실패한다. safe retry allowlist나
  explicit `retry_unsafe`가 있는 경우만 재시도한다.
- `a90_ncm_transport.py`: A90 NCM 후보를 `cdc_ncm + Samsung VID 04e8 + product 6861`로 재검증하고,
  NetworkManager host repair는 기본 비활성으로 바꿨다. 필요 시 `A90_NCM_REPAIR_HOST_NET=1`로만 opt-in하며,
  생성 profile은 `connection.autoconnect=no`이고 다른 active NM connection은 수정하지 않는다.
- 회귀 테스트: `workspace/public/src/scripts/revalidation/security_unit_a_regression.py`
  (`repair-dirs` symlink reject, unsafe busy no-retry, NCM product filter, repair opt-in).

### Unit B — wifi status/config 정보누출 & 검증 게이트

| finding | 심각도 | 검증 | 위치 |
| --- | --- | --- | --- |
| Wi-Fi status leaks unredacted device network identifiers | medium | **PARTIAL/VALID** — `mac_label`/`ip4_label` 마스킹 라벨은 추가됐으나 raw `mac=`/`ipv4=`를 콘솔에 여전히 출력([a90_wifi.c:1743-1749](workspace/public/src/native-init/a90_wifi.c#L1743-L1749)). **공개 경로 docs/ 리포트에 unredacted MAC이 그대로 남아 있음**(`...V2172...md:60`, 안전불변식 위반) → 스크럽 필요 | a90_wifi.c + V2172 리포트 |
| Wi-Fi config status trusts symlinked config roots | medium | **PARTIAL/VALID** — 런타임 스테이징 쓰기경로는 V2188에서 root 소유로 하드닝됐으나, `wifi config status`의 SD config **읽기/검증 경로**는 최종 컴포넌트만 `lstat`+`O_NOFOLLOW` 검사, 중간 디렉터리 심링크 미차단. 이후 autoconnect/connect의 검증 게이트로 재사용되므로 위험 | [a90_wificfg.c:392-422](workspace/public/src/native-init/a90_wificfg.c#L392-L422) |
| Probe executes fixed remote artifacts without transfer validation | medium | **STILL VALID(추정, 미수정)** — `transfer_file()`의 ok/reason 반환을 검사하지 않고 고정 `/cache` 스크립트를 root `run`으로 실행. 전송 실패 시 기존 `/cache` 파일이 root로 실행됨 | [native_wifi_supplicant_dependency_probe.py](workspace/public/src/scripts/revalidation/native_wifi_supplicant_dependency_probe.py) |
| Wi-Fi validation passes despite credential leak flags | low | **STILL VALID** — `classify()`가 version/connect/cleanup/disable_restore/selftest만 게이트, `secret_values_logged`/`credentials_logged`는 출력만 하고 pass 판정에 미반영. 자격증명 누출 회귀를 PASS로 가릴 수 있음 | [native_wifi_v2178_autoconnect_phase_validation.py:79-120](workspace/public/src/scripts/revalidation/native_wifi_v2178_autoconnect_phase_validation.py#L79-L120) |

권장 처리: (B1) `wifi status` 기본 출력은 라벨만, raw 값은 명시적 debug 모드로 한정 + V2172 리포트 MAC 마스킹.
(B2) wificfg 읽기경로에 Unit A/Tier0의 부모 `O_NOFOLLOW` 워크 패턴 이식(또는 `O_PATH`+`openat` 단계별 검증).
(B3) probe에서 transfer 결과 `ok` 확인 후에만 실행. (B4) `classify()`에 `secret_values_logged==0 and credentials_logged==0` 하드 게이트 추가.

처리 결과(2026-06-10, Unit B patch):
- `a90_wifi.c`: `wifi status`, runtime summary, UI status snapshot, DHCP 표시값의 `mac=`/`ipv4=`를 raw 값이 아닌
  `mac_label=xx:..` / `ip4_label=a.b.c.x` 형식으로 통일했다. raw 출력 여부를 `mac_raw_redacted=1`,
  `ip4_masked=1`로 명시한다.
- 공개 리포트: 동일 WLAN MAC이 남아 있던 V2144/V2146/V2172 리포트를 label 형식으로 스크럽했다.
- `a90_wificfg.c`: config/profile/secret 읽기와 profile list scan 전에 절대경로의 각 기존 컴포넌트를 `lstat()`로
  확인해 중간 symlink를 거부한다. status 출력에도 `path_components_safe`를 노출한다.
- `native_wifi_supplicant_dependency_probe.py`: helper/script transfer가 `ok`이고 sha mismatch가 없을 때만
  `/cache` 원격 probe를 실행한다. 실패 시 `supplicant-dependency-probe-transfer-failed`로 종료한다.
- `native_wifi_v2178_autoconnect_phase_validation.py`: `secret_values_logged`/`credentials_logged`가 모두 0일 때만
  PASS 판정한다.
- 회귀 테스트: `workspace/public/src/scripts/revalidation/security_unit_b_regression.py`
  (`v2178` secret gate, probe transfer gate, 공개 V2172 MAC 스크럽).
- 빌드 검증: `build_native_init_boot_v2189_security_p0_stage_fix.py` source build PASS
  (`boot_sha256=f54becb2b720ad198413c2a0089912626ca295c79a96f13e0921cf4f05b39f51`).

### Unit C — phone/lab 도구

| finding | 심각도 | 검증 | 위치 |
| --- | --- | --- | --- |
| Unauthenticated Wi-Fi upload receiver allows LAN DoS | medium | **STILL VALID** — CSV 내 최신 커밋(`d57bccc0`, 6/10 07:35). `0.0.0.0` 리슨, 인증·소스 허용목록·업로드 크기/타임아웃/저장 쿼터·동시연결 한도 전무. LAN 동료 기기가 저장소/스레드 고갈 가능(가용성). 단, 폰측 랩 도구라 디바이스 init 신뢰경계 밖 | [a90_termux_wifi_lab.sh](workspace/public/src/scripts/phone/a90_termux_wifi_lab.sh) |

권장 처리: 루프백/명시적 호스트 바인드, 토큰/소스IP 검증, 업로드당 크기 상한·idle 타임아웃·동시연결 제한.

처리 결과(2026-06-10, Unit C patch):
- `a90_termux_wifi_lab.sh`: 서버 bind 주소를 `A90_WIFI_BIND_HOST`로 명시 가능하게 하고, 토큰을 기본 생성한다.
  HTTP 다운로드는 `?token=` 또는 `X-A90-Wifi-Lab-Token`을 요구한다.
- raw TCP upload는 첫 줄 token prefix를 요구하고, `A90_WIFI_ALLOWED_PEER`, `A90_WIFI_MAX_UPLOAD_MIB`,
  `A90_WIFI_MAX_UPLOAD_CLIENTS`, `A90_WIFI_IDLE_TIMEOUT_SEC`로 소스/크기/동시성/idle timeout을 제한한다.
- 업로드 오류는 스레드 stack trace 대신 구조화된 `upload failed ... error=...` 로그로 남기고 연결을 닫는다.

### Unit D — 빌드/감사 위생 (저위험, 운영 신뢰성)

| finding | 심각도 | 검증 | 위치 |
| --- | --- | --- | --- |
| Default searches now hide live legacy Python imports | low | **STILL VALID** — `ignore`가 `workspace/public/archive/`를 기본 rg/fd 검색에서 제외하나, 활성 진입점이 `add_legacy_revalidation_path()`로 그 트리를 import. 감사 사각지대 | `ignore` + `_workspace_bootstrap.py` |
| Archived V2167 runner fails due to missing bootstrap import | info | **VALID(신뢰성)** — 아카이브 풀러너가 import 시 `_workspace_bootstrap`을 못 찾아 즉시 종료 | `workspace/public/archive/scripts/revalidation/native_wifi_connect_dhcp_google_ping_handoff_v2167.py` |

권장 처리: archive를 import 경로에서 빼거나, 보안 스캔 시 archive 포함하도록 별도 ruleset 명시. V2167 아카이브 러너는 호환 래퍼로 복구하거나 인벤토리에서 deprecated 표기.

처리 결과(2026-06-10, Unit D patch):
- `_workspace_bootstrap.add_legacy_revalidation_path()`는 기본적으로 harness path만 추가하고,
  archive import는 `include_archive=True` 또는 `A90_INCLUDE_ARCHIVE_REVALIDATION=1`일 때만 켠다.
- 실제로 archive V2137 빌더가 필요한 `build_native_init_wifi_test_boot_v2168.py`만 명시 opt-in으로 유지했다.
- 회귀 테스트: `security_tier2_regression.py`가 archive import 기본 비활성/명시 opt-in을 검증한다.

---

## 4. Tier 2 — 활성 빌드 헬퍼/하네스 (재검토 필요, 116건의 핵심)

구 경로(`stage3/...`, `scripts/...`)로 지목됐지만 **basename이 활성 빌드로 마이그레이션**된 파일들.
finding이 가리킨 *옛 버전*과 현재 버전이 다를 수 있어, 단일 활성 파일에 대해 클래스별 재검토가 필요.

| 활성 파일 | 관련 건수 | 성격 | 우선순위 |
| --- | ---: | --- | --- |
| `native-init/helpers/a90_android_execns_probe.c` | 71 (high 5, med 36, low 16, info 14) | Wi-Fi 동반 헬퍼, **V2188 활성 빌드 포함**(`helper-v427`). 클래스: 캐시-쓰기가능 바이너리 root 실행, 예측가능 `/tmp` DHCP 스크립트, 심링크 가능 temp→root chown | **높음** |
| `harness/a90harness/evidence.py` | 5 (무제한 read DoS 포함) | 활성 공용 하네스. "Unbounded evidence file read can exhaust host memory" | 중 |
| `scripts/revalidation/native_init_flash.py` | 10 | 활성 flash 도구. **V2188에서 `--expect-sha256` 핀 검증 추가**됨 → 다수 완화, 잔여만 확인 | 중 |
| `native-init/helpers/a90_mdm_helper_strace_wrapper.c` | 2 | 활성 헬퍼 | 중 |
| `native-init/v319|v724/*.inc.c`, `a90_util.c`, `a90_tcpctl.c`, `a90_config.h`, `serial_tcp_bridge.py`, `a90ctl.py`, `tcpctl_host.py` 등 | 나머지 | 활성 init/스크립트 단편 | 건별 |

권장 처리: 이 묶음은 **finding이 지목한 구 경로가 아니라 현재 활성 파일**을 열어 동일 패턴이 남아있는지
확인하는 방식으로 처리. 특히 `a90_android_execns_probe.c`의 high 5건과 `evidence.py` DoS는 Tier 1 직후 검토.
execns_probe의 캐시-쓰기 root 실행/예측 temp 패턴은 Tier 0에서 `a90_wifi.c`에 도입한
`wifi_verify_root_exec_*` 패턴을 그대로 적용하면 일괄 해소 가능성이 높다.

처리 결과(2026-06-10, Tier 2 patch):
- `a90_android_execns_probe.c`: 예측 가능한 `/tmp/a90-v231-<pid>`와 `udhcpc` 스크립트 경로를
  `mkdtemp()`/`mkstemp()` 기반으로 바꿨다.
- `a90_android_execns_probe.c`: private `cnss-daemon` bind source는 `/cache/bin` 하위, root-owned,
  regular, executable, non-group/world-writable, no setuid/setgid, `O_NOFOLLOW` open 조건을 모두 통과해야 하며
  bind mount는 검증된 `/proc/self/fd/<fd>`를 source로 사용한다.
- `a90_android_execns_probe.c`: supplicant/strace exec 직전에 UID/GID 1010(wifi) + `CAP_NET_RAW/CAP_NET_ADMIN`
  identity contract를 적용해 `/cache` 보조 바이너리가 root 권한으로 실행되지 않게 했다.
- `a90harness.evidence`: 공용 evidence reader를 `read_bounded_bytes/text/json()`로 추가하고, 활성 harness modules는
  symlink/non-regular/초대형 파일을 거부하는 bounded read로 전환했다.
- `a90_ncm_transport.py`: archive validation의 secret scan을 chunk streaming으로 바꾸고, tar member scan 상한을 둬
  업로드 archive 검증이 전체 파일/멤버를 메모리에 올리지 않게 했다.
- 회귀 테스트: `security_tier2_regression.py` (`read_bounded_*` symlink/oversize reject, archive import opt-in).

---

## 5. Tier 3 — 아카이브/삭제 (조치 불요, close as stale)

**479 ARCHIVE + 3 DELETED = 482건.** 2026-06-07 reorg로 삭제된 루트 `stage3/`·`scripts/`의 일회성
Wi-Fi 추적 핸드오프 스크립트(`native_wifi_*_handoff_vNNNN.py`, `init_v73.c` 등)에 대한 것.
코드는 `workspace/public/archive/`에 provenance용으로만 보존, **활성 빌드/런타임에 미포함**.

대표 클래스(아카이브): "VNNNN handoff flashes unverified/unpinned boot artifact"(다수),
"Shell injection in … artifact export/readelf", "Raw modem DIAG bytes captured into reports" 등.
→ 활성 코드에서는 `native_init_flash.py --expect-sha256`, 핀 SHA, 리포트 레닥션으로 이미 패턴이 닫혔으므로
재현 위험 없음.

**예외 1건:** Tier 1 Unit D의 "live legacy imports" 사각지대 때문에, archive 중 활성 import 대상 모듈은
완전 사문(死文)이 아니다. archive를 import 경로에서 제거(Unit D 처리)하면 이 예외도 함께 닫혀
482건 전부를 안전하게 무시할 수 있게 된다.

처리 방법: Codex 콘솔에서 해당 paths가 `stage3/`·루트 `scripts/`인 건들을 일괄 `won't fix (archived / removed in 2026-06-07 reorg)`로 마감.

---

## 6. 해결 순서 (작업 단위 기준)

1. **(완료확인) Tier 0** — V2188/V2189 하드닝으로 닫힌 HIGH 2건 + mkbootimg를 재오픈 목록에서 제외. ✅
2. **(완료확인) Unit A (호스트 브리지/전송)** — `a90_bridge.py` repair-dirs 심링크(high), `a90ctl.py` busy-replay(med), `a90_ncm_transport.py` 자동 repair(med). ✅
3. **(완료확인) Unit B (정보누출·검증게이트)** — `wifi status`/V2172 리포트 MAC 레닥션(med), `a90_wificfg.c` 읽기경로 부모 `O_NOFOLLOW`(med), supplicant probe transfer 검사(med), v2178 classify secret 게이트(low). ✅
4. **(완료확인) Tier 2 핵심** — `a90_android_execns_probe.c` high 패턴 + `evidence.py` DoS + archive validation memory hygiene. ✅
5. **(완료확인) Unit C (phone lab)** — `a90_termux_wifi_lab.sh` 인증/한도/타임아웃. ✅
6. **(완료확인) Unit D (감사 위생)** — archive import 기본 비활성, 필요한 빌더만 명시 opt-in. ✅
7. **Tier 3 일괄 마감** — 482건은 Codex 콘솔에서 `won't fix / archived or removed in 2026-06-07 reorg`로 disposition 처리.

## 7. 부수 메모

- `CLAUDE.md`의 현재 베이스라인 표기는 `v2182-hud-menu-cleanup`이지만, 실제로는 보안 하드닝 이후
  **`v2189-security-p0-stage-fix`(init 0.9.260+)가 승격**(`cd89f5c2`)됨 → 문서 갱신 필요(보안 외 위생 항목).
- 본 문서는 redaction 원칙상 MAC/BSSID/IP 등 식별자를 포함하지 않는다. 원본 CSV·finding URL은
  `workspace/private/raw-logs/security/codex/2026-06-10/`에만 보관한다(공개 경로 승격 금지).
