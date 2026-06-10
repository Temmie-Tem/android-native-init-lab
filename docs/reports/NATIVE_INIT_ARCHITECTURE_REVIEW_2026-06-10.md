# Native Init 아키텍처/구조 분석 보고서 (2026-06-10)

분석 대상: `workspace/public/src/native-init/` 소스 클로저와
`workspace/public/src/scripts/revalidation/` 빌드 체인.
분석 방법: 빌드 모델 역추적 + 소스 정적 분석(컴파일 경계, dispatch, 모듈
경계, 죽은 코드 식별). 디바이스 실행은 하지 않음.

---

## 1. 한 줄 결론

런타임 코드(모듈 레이어 + 명령 dispatch + Wi-Fi 서브시스템)는 **구조적으로
건강하다**. 문제는 코드 자체가 아니라 그 코드를 **둘러싼 두 개의 누적 레이어**다:
(1) PID1 main 변환 단위에 박제된 ~4,700줄의 폐기된 연구 스캐폴딩,
(2) 빌드 스크립트가 서로를 import 해서 전역을 덮어쓰는 monkeypatch 상속 타워.
둘 다 "기능"이 아니라 "관성"이며, 지금 시점(Wi-Fi end-to-end 완료)이 이 빚을
청산하기에 가장 좋은 시점이다.

---

## 2. 빌드 모델 (먼저 이해해야 나머지가 읽힌다)

### 2.1 컴파일 구조: 하이브리드 unity + module

PID1 바이너리는 두 종류 소스로 만들어진다.

- **유니티 TU 1개**: `init_v725_fasttransport.c` 가 9개 `v319/*.inc.c` +
  `v724/90_main.inc.c` 를 `#include` → 하나의 ~13,000줄 변환 단위.
- **개별 모듈 45개**: `a90_*.c` 중 `int main(` 없는 파일 전부
  (`glob("a90_*.c")` 후 main 보유 4개 제외). 각각 별도 .o 로 컴파일 후 링크.

컴파일 플래그(전부):
```
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra <-D...> -o init *.c
```
- `-std=` 없음 → GNU 방언 암묵 의존.
- `-Werror` 없음 → 경고가 빌드를 막지 못함(유니티 TU 특성상 `-Wextra`
  경고가 다량 발생해도 무시됨).
- `-flto` / `-ffunction-sections -Wl,--gc-sections` 없음 → 모듈 45개가
  사용 여부와 무관하게 **전부** 바이너리에 링크됨(직접 `*.c` 링크라 .o는
  무조건 포함). 죽은 모듈의 dead-strip이 일어나지 않음.
- 단일 invocation 전체 재컴파일 → 증분 빌드 없음. 현재 규모(~26k줄)에선
  견딜 만하지만 모듈이 늘수록 선형 악화.

### 2.2 버전 식별 주입 (이건 잘 되어 있음)

`a90_config.h` 의 `INIT_VERSION "0.9.68" / INIT_BUILD "v724"` 는 **stale
기본값**이고 전부 `#ifndef` 가드가 있다. 실제 식별자는 빌드 시
`-DINIT_VERSION="0.9.259" -DINIT_BUILD="v2187-..."` 로 주입되어 헤더 값을
덮어쓴다. 충돌·재정의 경고 없음. 식별자 흐름은 깔끔하다.
다만 **소스만 읽으면 현재 버전을 알 수 없다**(헤더가 거짓을 말함)는 함정이
있다 — config.h 기본값을 현재 baseline과 일치시키거나 주석으로 "build-time
override" 명시 필요.

### 2.3 빌드 스크립트 상속 타워 (가장 심각한 구조 문제)

빌드 스크립트는 두 세대로 갈린다.

- **1세대 (포크)**: `build_native_init_boot_v724.py` →
  `_v725_fasttransport.py` 는 `run/sha256/pid1_sources/build_init/
  build_ramdisk/build_boot_image/verify_markers/main` 을 통째로 복붙한
  포크다. 공통 로직이 두 곳에 중복.
- **2세대 (monkeypatch)**: v726 이후 모든 스크립트가 직전 버전을 모듈로
  import 하고 그 **모듈 전역을 런타임에 덮어쓴다**. 실제 v2187 코드:
  ```python
  for key, value in replacements.items():
      v2182.v2178.v2176.v2174.v2169.v726.set_arg(args, key, value)
  helper_builder = (
      v2182.v2178.v2176.v2174.v2169.v726.v2168.prev2137.prev2135.prev2133
      .prev2131.prev2129.prev2127.prev2120.prev2112.prev2108.prev2106
      .prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038
  )
  ```
  즉 v2187을 빌드하려면 **20여 단계 import 체인 전체가 메모리에 살아있고
  올바른 순서로 전역 변이를 받아야** 한다. 한 중간 버전을 지우거나 시그니처를
  바꾸면 하류 전부가 깨진다. 디버깅 시 "이 값이 어디서 세팅됐나"를 추적하려면
  20개 모듈을 거슬러 올라가야 한다.

**평가**: 이건 "버전별 재현 빌드를 보존하려는" 의도는 이해되지만, 상속을
파이썬 import 부작용으로 구현한 안티패턴이다. 새 baseline마다 스크립트가 1개씩
영구 추가되어 활성 50개 / 아카이브 **2,041개**가 쌓였다.

---

## 3. 런타임 소스 구조 (여기는 양호)

### 3.1 모듈 레이어 — 건강함

`a90_*.c` 45개는 `a90_<도메인>` 네이밍, 대응 헤더, 명확한 단일 책임을
가진다(storage/runtime/console/hud/kms/input/wifi/netservice/...). 헤더가
공개 API 표면을 좁게 정의하고, 예로 `a90_wifi.c`(2,935줄)는 **가변 파일
스코프 전역이 사실상 0개** — 상태를 `a90_wifi_*_snapshot` 구조체로 주고받아
캡슐화가 좋다. 이 레이어는 그대로 유지·확장할 가치가 있다.

### 3.2 명령 dispatch — 건강함

`v319/80_shell_dispatch.inc.c` 의 `command_table[]` 는
`{ name, handler, usage, flags, group }` 테이블 드리븐이고, `a90_shell.c` 가
제네릭 루프로 조회한다. 새 명령 추가가 테이블 한 줄 + thin `handle_*` 래퍼로
끝나는 깔끔한 구조. if-else 사슬 아님.

### 3.3 main() 부팅 경로 — 건강함

`v724/90_main.inc.c:6164` 의 `main()` 은 선형·가독적이다:
base mount → cache → runtime root → helper/userland 인벤토리 →
ACM gadget → ttyGS0 → console attach → autohud → netservice → rshell →
Wi-Fi autoconnect → `shell_loop()`. 각 단계 실패 처리·로깅·타임라인 기록이
일관적이다.

---

## 4. 구조적 문제 (우선순위순)

### P0 — `v724/90_main.inc.c` 의 죽은 연구 스캐폴딩 박제

6,476줄 파일의 실제 구성:

| 구간 | 라인 | 상태 |
| --- | --- | --- |
| 라이브 헬퍼 + main() | ~1,750줄 | 컴파일·실행됨 |
| **`#ifdef A90_WIFI_TEST_BOOT` 블록 (866–5590)** | **4,724줄** | **활성 빌드에서 컴파일 아웃** |

`A90_WIFI_TEST_BOOT` 는 **어떤 활성 빌드 스크립트에서도 정의되지 않는다**.
즉 `v1393_*`(248회), `v1664_pcie1_clock_vote_*`(62), `v641_*`(60),
`v1511_*`/`v1633_*`/`v1661_*`/`v1477_*` 등 RC1 윈도우 샘플러·PCIe 클럭 보트·
IRQ 스냅샷·eSoC 프로브 전부가 **전처리기로 제거된다**. 바이너리는 안 커지지만,
소스는 CLAUDE.md·메모리가 "moot(무관)"으로 명시한 폐기된 modem/PCIe/eSoC
추적 코드를 PID1 핵심 파일에 그대로 이고 있다. 읽는 사람은 4,700줄을
스크롤해야 main()에 도달한다.

추가로 **컴파일 아웃이 아니라 실제로 링크·호출되는 죽은 실험**도 있다:
- `v724_run_qrtr_servloc_boot_once()` (main:6370 호출)
- `v641_run_sibling_ssctl_once()` (main:6371 호출)
- `v726_start_wifi_lifecycle_modem_owner_once()` (`-DA90_WIFI_LIFECYCLE_MODEM_OWNER=1` 로 컴파일 인)

이들은 `/cache` 플래그 파일이 없으면 즉시 return 하므로 기본 동작은
no-op이지만, **PID1 부팅 경로에 실제로 코드가 들어가 있고 호출된다**. Wi-Fi가
독립 경로로 해결된 지금 이 modem/qrtr/ssctl 트리거는 존재 이유가 사라졌다 —
잔존 위험(부팅 경로 복잡도·오작동 표면)만 남는다.

### P1 — 빌드 스크립트 monkeypatch 타워 (2.3 참조)

20+ 단계 import-and-mutate 체인. 활성 50 / 아카이브 2,041개. 새 baseline마다
영구 누적되는 구조. 유지보수·디버깅·신규 진입 비용이 매 사이클 증가.

### P2 — 죽은 파일 / 잘못된 식별자

- `v319/90_main.inc.c` (321줄): 어디서도 include 되지 않는 **완전한 죽은
  파일** (`init_*.c` 는 `v724/90_main.inc.c` 만 include). 혼동 유발.
- `a90_config.h` 의 INIT_VERSION/BUILD 가 현재 baseline(0.9.259/v2187)과
  불일치 (2.2 참조).
- 1세대 빌드 스크립트(v724↔v725) 함수 복붙 중복.

### P3 — 빌드 위생

`-std=` 미지정, `-Werror` 부재, dead-strip 플래그(`--gc-sections`) 부재,
유니티 TU 때문에 `-Wextra` 경고가 사실상 사장됨. init 한 대 빌드엔 치명적이지
않지만 회귀를 조용히 통과시킨다.

---

## 5. 개선 방향 / 설계 방향

원칙: **런타임 레이어(모듈·dispatch·main)는 건드리지 말고, 그 주변 관성만
제거**한다. 위험 대비 이득이 가장 큰 순서로.

### 5.1 단기 (낮은 위험, 즉시 — 동작 변화 0)

1. **죽은 파일 제거**: `v319/90_main.inc.c` 삭제(또는 archive 이동). 빌드
   영향 0 — 어디서도 include 안 됨.
2. **`A90_WIFI_TEST_BOOT` 블록 적출**: `v724/90_main.inc.c` 866–5590 를
   통째로 `workspace/public/archive/` 의 별도 연구 소스로 이동.
   `init_*.c` 가 include 하는 유니티 TU에서 분리만 해도 main 파일이
   6,476 → ~1,750줄로 줄고 동작은 동일(컴파일 아웃이었으므로).
   → main inc를 `v724/90_main.inc.c`(부팅 경로)와
   `archive/.../wifi_test_boot_research.inc.c`로 물리 분할.
3. **config.h 식별자 정리**: 기본값을 현재 baseline에 맞추거나
   "//build-time `-D` override" 주석 명시.

### 5.2 중기 (빌드 시스템 — 한 번의 집중 작업)

4. **monkeypatch 타워를 데이터 기반 빌드로 교체**. 빌드 스크립트 N개 대신
   **빌드 로직 1개 + baseline 정의 N개(JSON/TOML)**:
   ```
   build_native_init.py --baseline v2187   # 로직은 하나
   baselines/v2187.json                     # init_version, build_tag,
                                            # extra_flags, helper_sha, parent
   ```
   `parent` 필드로 상속을 데이터로 표현(전역 변이 대신 dict merge). 과거
   재현성은 baseline 정의 파일로 보존되고, import 체인은 사라진다. 활성
   스크립트 50 → ~3개.
5. **빌드 위생 추가**: `-std=gnu11`, `--gc-sections`(+`-ffunction-sections
   -fdata-sections`)로 미사용 모듈 dead-strip, 가능하면 모듈 레이어부터
   `-Werror` 점진 적용.

### 5.3 장기 (구조 진화 — 선택)

6. **유니티 TU 해체**: `v319/*.inc.c` 10개를 진짜 `.c` 모듈로 승격해 dispatch
   레이어를 모듈 레이어와 동일한 규칙으로 통일. 그러면 증분 빌드·진짜
   `-Wextra` 효력·심볼 격리가 생긴다. 단, `static` 함수 다수가 TU 경계를
   넘게 되므로 헤더 정리 비용이 있다 — 이득 대비 비용을 보고 결정.
7. **죽은 실험 트리거 정리**: `v724_run_qrtr_servloc_boot_once` /
   `v641_run_sibling_ssctl_once` / `A90_WIFI_LIFECYCLE_MODEM_OWNER` 를
   부팅 경로에서 제거(또는 명시적 `--enable-legacy-modem-probe` 빌드
   옵션 뒤로). Wi-Fi 독립 경로 확정 이후 이 트리거들은 순수 부채다.

---

## 6. 권고 (terse)

- **지금 당장**: 5.1 (1)(2)(3) — 위험 0, main 파일 73% 감량, 동작 불변.
  Wi-Fi가 막 안정화된 지금이 죽은 modem/PCIe 스캐폴딩을 들어낼 최적기.
- **다음 baseline 사이클에서**: 5.2 (4) 빌드 데이터화 — 매 사이클 누적되는
  구조적 출혈을 멈추는 단 하나의 가장 큰 ROI.
- **여유 있을 때**: 5.3 — 필수 아님. 모듈 레이어가 이미 건강하므로 유니티
  해체는 "있으면 좋은" 수준.

런타임 아키텍처 자체는 재설계 대상이 아니다. 재설계가 필요한 건 빌드
파이프라인과 소스에 박제된 연구 잔재뿐이다.
