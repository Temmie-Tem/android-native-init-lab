# Native Init 아키텍처 구조 선택지와 목표 구조 (2026-06-10)

이 문서는 **앞으로 어떤 구조로 갈 것인가**(구조 종류 메뉴 + 목표 구조 결정 +
로드맵)를 다룬다. **현재 상태 진단 + 청소 계획**은 동일 일자의
[`NATIVE_INIT_ARCHITECTURE_REVIEW_2026-06-10.md`](NATIVE_INIT_ARCHITECTURE_REVIEW_2026-06-10.md)
가 담당하며, 이 문서는 그 위에 얹힌다.

- 리뷰 문서: "런타임 모듈/dispatch 레이어는 건강하다. 주변 관성(죽은 스캐폴딩,
  빌드 monkeypatch 타워)을 제거하라." → **선행 청소(필수)**.
- 이 문서: "관성을 제거하며, **무엇을 최종 목표로 잡고 지금은 무엇을 할지**를
  정한다." → **방향·로드맵**.

이 문서가 말하는 "분리"는 모듈 레이어 재설계가 아니라 **배포 경계(프로세스
경계)** 의 이동이다. 코드 품질이 아니라 장애 반경·공격 표면·빌드 정체성·학습을
다룬다.

---

## 0. 결론 먼저 (이 문서의 합의)

- **렌즈를 명확히 한다**: 같은 코드라도 *production 신뢰성*으로 최적화하면
  "쪼개지 말고 빼라"가 답이고, *학습*으로 최적화하면 "의도적으로 쪼개라(리스크가
  곧 커리큘럼)"가 답이다. **이 프로젝트는 학습 최적화다.** 실패가 싸다(TWRP +
  known-good fallback)는 점이 이 선택을 정당화한다.
- **최종 목표 = 부팅 오케스트레이션.** 정석 OS의 형태(얇은 PID1 + 별도 데몬 +
  **선언적 의존 순서** + 마일스톤)로 수렴한다. 정전(canonical) 산출물은
  `main()`의 직선 부팅 시퀀스를 **선언적 테이블 + 작은 resolver**로 외재화한
  미니 init.rc/systemd.
- **근시일 = 기능 구현 위주.** 오케스트레이션은 "순서 관계를 가진 여러 서비스"가
  있어야 의미가 있다. 기능 구현 = 나중에 오케스트레이션할 **원재료를 모으는
  일**이며, 그게 쌓여야 진짜 경계가 드러난다. 기능 먼저가 미루기가 아니라
  **올바른 순서**다.
- **단, 두 페이즈가 충돌 안 하게 §10의 위생 규칙 3개를 지킨다.**
- **물리 프로세스 분리는 기본값 "보류"** — §6의 3축을 다 통과하고 크래시 증거가
  있을 때만, 컴포넌트 단위로, fallback 보장하에. 빅뱅 재아키텍처 금지.

---

## 1. 지배 원칙

- PID1의 본래 책무는 좁다 — 자식 reap, 세션/프로세스그룹 설정, 부트스트랩,
  시그널 앵커, 감독. 그 외 기능을 PID1에 넣는 건 "잘못된 자리".
- **PID1이 얇아야 하는 이유는 미학이 아니라 강제다**: 죽으면 커널이
  `Attempted to kill init`로 패닉하는 **유일한 프로세스**. 그래서 "다른 데서 돌
  수 있는 건 전부 다른 데서" — 회복 불가 프로세스에 코드를 최소만 싣는 위험
  집중 관리.
- 환원불가 코어(위임 불가): ① 고아 reap(커널이 PID1로 재부모화), ② 절대 종료
  금지, ③ 부트스트랩 0번째 단계(매니저 존재 전 mount/dev/env), ④ 시스템 시그널
  앵커. 이 프로젝트의 "core 클러스터"가 여기 해당.
- 따라서 구조 선택 = **단순성/성능(상주 모놀리식) ↔ 신뢰성·격리·학습(프로세스
  분리)** 의 트레이드오프.

---

## 2. 결정적 제약: `-static`

빌드는 `aarch64-linux-gnu-gcc -static`(glibc 정적 링크)다. 구조 선택지를 좁힌다.

- **정적 glibc는 `dlopen`이 사실상 불가** → 동적 공유 라이브러리 플러그인(§3
  옵션 5)은 `-static` 유지 시 **탈락**.
- 그러므로 **"모듈 분리" = "별도 프로세스 바이너리"** 가 유일한 수단. *분리* = *spawned-helper*.
- 프로젝트는 **이미 이 패턴을 절반 쓴다**: ramdisk가 PID1과 별개로 빌드·동봉하고
  PID1이 `/bin`에서 실행하는 helper —
  `a90sleep / a90_cpustress / a90_longsoak / a90_rshell / a90_tcpctl /
  a90_usbnet / busybox / toybox`. `cpustress`·`longsoak`은 **PID1 상주본과
  `/bin` helper본이 중복 존재**한다. 즉 분리 권고는 새 패턴 도입이 아니라
  **시작된 패턴의 마무리**다.

---

## 3. 구조 종류 메뉴 (목적별 · 장단점)

| # | 구조 | 결함격리 | 빌드/디버그 단순성 | 보안 표면 | `-static` 호환 | 비고 |
| --- | --- | :---: | :---: | :---: | :---: | --- |
| 1 | 순수 모놀리식 (현재) | ✗ | ◎ | 큼 | ◎ | 초기 단계용 |
| 2 | 모듈러 모놀리식 (논리분리·물리1) | ✗ | ○ | 중 | ◎ | core+wifi 상주 |
| 3 | Supervisor + spawned helper | ◎ | △ | 작음 | ◎ | 데몬 분리 |
| 4 | 마이크로커널형 / 메시지패싱 | ◎◎ | ✗ | 작음 | ◎ | 과함(채택X) |
| 5 | dlopen 동적 플러그인 | ○ | △ | 중 | ✗ | static이라 탈락 |

- **1 순수 모놀리식**: IPC 0·단일 blob·in-process 디버그(◎). 결함 격리 0(한
  모듈 segfault=init 패닉), 전 코드가 TCB, 빌드 정체성이 `glob`에 묶임.
- **2 모듈러 모놀리식**: 논리 경계·헤더 인터페이스 + in-process 디버그 유지.
  "마이크로서비스 이점의 ~80%는 독립 배포가 아니라 논리 경계에서." 결함 격리는
  여전히 0. 모듈 레이어는 이미 이 수준 근접 — 빠진 건 명시적 source manifest와
  dispatch 유니티 TU 모듈 승격.
- **3 supervisor+helper**: helper가 죽어도 PID1 생존·reap·재시작, TCB 축소,
  `-static` 호환 유일 분리 수단(이미 부분 적용). spawn/IPC 배선·ramdisk 수↑·
  단일 blob 단순성 상실. **순서/의존 관리는 별도 책임**(§5).
- **4 마이크로커널형**: 최고 격리지만 메시지패싱 오버헤드+복잡도 최고. 단일
  디바이스 연구 init엔 과도. 채택 안 함.
- **5 dlopen**: `-static`에서 불가. 채택 안 함.

---

## 4. 정석 OS는 어떤 형태인가 (참조)

실제 OS(Linux/systemd · Android · 고전 Unix)는 한 형태로 수렴한다.

- **커널(모놀리식) ≠ 유저스페이스(데몬 분리).** 두 축은 별개. 유저스페이스는
  모든 정석 OS가 **서비스마다 별도 데몬**으로 쪼갠다 — "표준 관행".
- **PID1은 오케스트레이션·매니징만**, 실제 작업은 데몬에 위임. systemd조차 PID1은
  매니저일 뿐 resolved/networkd/logind/udevd는 전부 별도 프로세스. Android는
  init이 `.rc` 서비스 정의로 healthd/logd/storaged/servicemanager/vold/netd/
  zygote를 시작.
- **부팅 순서 = 선언적 데이터.** Android `.rc`(`service`/`class`/`on <trigger>`/
  `class_start`), systemd unit(`Wants=`/`Requires=`/`Before=`/`After=`) + `.target`
  동기화 지점. **순서를 C로 직조하지 않는다** → non-deterministic 부팅 버그 제거 +
  독립 서비스 병렬 시작.
- **마일스톤으로 결합 완화.** 서비스가 서로에게 직접 의존하지 않고 마일스톤
  (target/class)에 붙어 N×N 결합을 N×(소수)로 낮춤.

**`-static` 보정**: 정석 풀스택(systemd+D-Bus, Android binder)은 풍부한 IPC
전제. 이 프로젝트는 데몬 간 통신이 파일/파이프/소켓 → **D-Bus 이전 고전 Unix /
Android 네이티브 데몬 + runit/s6식 감독 + 작은 선언적 순서 계층**이 가장 가까운
정석 모델. 학습 목적이면 systemd의 D-Bus·cgroup·socket-activation 복잡도 없이
"순서를 데이터로 제어한다"의 알맹이만 배운다.

→ **목표 구조 = (우리가 도출한 2+3 하이브리드) + (빠진 조각: 선언적 의존 순서).**

---

## 5. 분리의 숨은 비용 (신중해야 하는 이유)

분리는 결함을 *없애는* 게 아니라 *교환*한다. 모놀리식의 "모듈이 in-process로
죽으면 패닉" 한 가지 위험이 사라지는 대신, **새 결함 클래스가 생기고 상당수가
PID1 안에서 돈다**:

1. **IPC/직렬화 결함** — in-process 호출은 실패할 수 없지만, 프로세스 경계는 연결
   실패·부분 read/write·버전 skew·교착을 새로 만든다. 새 코드 = 새 버그.
2. **자원 소유권 경합** — fb/KMS·evdev. helper가 DRM master 쥔 채 죽으면
   블랙스크린·입력 먹통 등 오늘은 불가능한 고장.
3. **감독/재시작 결함** — 크래시 루프·재시작 폭주·reap 순서·"죽었는데 모름".
   하필 PID1에 산다.
4. **역결합(최악)** — PID1이 helper 응답을 **동기 대기**하면 멈춘 helper가 PID1을
   hang. 깔끔한 크래시를 hang으로 악화.

추가로 **마이그레이션 자체가 회귀 벡터**(건강하던 코드를 옮기는 행위).

**그리고 "순서"가 공짜에서 설계 대상으로 승격된다.** 지금 부팅 경로는 단일
프로세스 직선 코드라 순서·준비성·의존이 "10번째 줄이 20번째 줄보다 먼저"로 공짜
보장된다. 분리하면 readiness 신호·선행조건 재확인·의존 그래프를 **명시**해야 한다.
조사 결론: **supervision ≠ dependency management**(runit/s6은 감독만, 순서는 s6-rc).
즉 부팅시점 컴포넌트를 분리한다는 건 systemd-unit/s6-rc가 존재하는 그 미니 의존
계층을 직접 떠안는다는 뜻 — 모놀리식이 직선 main()으로 공짜로 주던 것.

**최악 시나리오**: 부팅 경로가 optional helper를 동기 대기하면 `shell_loop()` 도달이
지연/차단 → **부팅 중 시리얼로도 안 닿는 디바이스**.

→ 신뢰성 순이득 = (없앤 in-process 위험) − (새 seam/소유권/감독 위험 +
마이그레이션 회귀). **자동으로 +가 아니다.**

---

## 6. 분리 적합도 3축 테스트

물리 분리는 **세 축을 다 통과할 때만**. 학습 렌즈에서도 우선순위 판별에 쓴다.

1. **좁고 비동기인 인터페이스** (seam이 작다).
2. **실제로 자주 죽는다는 증거** (없앨 standing 위험이 크다).
3. **부팅 경로 밖 + on-demand 단명** (순서를 안 건드린다).

| 클러스터 | ①좁은 인터페이스 | ③부팅경로 밖 | 판정 |
| --- | :---: | :---: | --- |
| D/E (진단·소크·테스트앱) | ○ | ○ (shell에서 호출) | **분리 1순위** (②증거制) |
| UI/C (autohud) | ✗ (fb/input 결합) | ✗ (부팅경로) | 논리 경계까지만 |
| netservice / wifi-autoconnect | △ | ✗ (부팅경로) | 상주 |
| core + wifi | ✗ (넓고 핫) | ✗ | **상주 확정** |

D/E는 이미 `/bin/a90_longsoak`처럼 "사용자가 명령하면 spawn"이라 부팅 순서를 안
건드린다. UI는 autohud가 부팅 경로에 박혀 분리=순서 수술 강제.

---

## 7. 공유(공통화) 결정 heuristic

공유 코드의 긴장 = **DRY(재사용) ↔ 변경 증폭(한 곳 바꾸면 의존부 다 패치)**.
통증의 세기는 "공유하느냐"가 아니라 "어떻게 공유하느냐"로 갈린다.

| 방식 | 재사용 | 바뀌면 ripple | 이 프로젝트 |
| --- | --- | --- | --- |
| 복사/중복 | 0 | 역방향(버그픽스 N번) | 지금 일부(cpustress/longsoak) |
| 공유 .c 를 각 바이너리에 static 링크 | 높음 | **빌드타임**(고른 소비자만 재빌드) | **sweet spot** |
| 공유 .so (동적) | 최고 | 런타임 즉시 전파, ABI 깨지면 전원 | **`-static`이라 불가** |
| 서비스化(IPC 호출) | 코드 결합 최소 | IPC 계약 깨지면 | 부팅경로 분리 시 자연 등장 |

- **`-static` 덕에 spooky action(안 건드린 컴포넌트가 런타임에 조용히 달라짐)이
  구조적으로 불가능.** 공유=빌드타임 결합 → ripple은 항상 "내가 고른 소비자를,
  내가 고른 시점에 재빌드". `helper-vNNN` 축이 "공유코드 vX로 빌드됨"을 기록 →
  결합이 가시적·통제됨.
- **무엇을 공유할지 = "바뀌는 이유"로 묶어라.** 3문항 다 yes일 때만 공유:
  (1) 모든 소비자가 같은 이유로 바뀌나, (2) 안정적인가, (3) 인터페이스가 좁고
  의미가 동일한가. 하나라도 no면 **중복을 견디는 게 정답**("중복이 잘못된
  추상화보다 싸다").
- 대입: **공유** = 로깅·nl80211/netlink 배선(현재 `a90_wifi.c`↔`helpers/a90_nl80211_*.c`
  중복)·draw 프리미티브·링버퍼·config 파서. **공유 마라** = 부팅 순서·정책·
  컴포넌트별 상태머신(각자 자기 이유로 진화).
- **순서 규칙**: Isolate First, Then Share. 공유 먼저 하면 모놀리식 구조 기준
  의존을 박제 → 쪼갤 때 프로세스 경계를 가로질러 재결합(최악 ripple). 격리(중복
  감수) 먼저 → 진짜 공통 표면이 드러난 뒤 안정부만 추출.

---

## 8. 결정: 목표 구조 + 두 렌즈

- **렌즈 = 학습.** production 신뢰성 렌즈에선 "쪼개지 말고 빼라"가 맞지만, 이
  프로젝트는 학습 최적화이고 실패가 싸다(TWRP/fallback). 우리가 §5에서 카탈로그한
  리스크가 학습 렌즈에선 **회피 비용이 아니라 커리큘럼**(readiness·의존 순서·
  supervision·fb/DRM 핸드오프·non-block IPC)이 된다.
- **목표 구조 = 모듈러 모놀리식(core+wifi 상주) + supervisor-helper(데몬 분리) +
  선언적 의존 순서(정석 OS의 빠진 조각).** 4·5는 기각.
- **물리 분리는 §6 3축 + 크래시 증거制로 보류가 기본값**, 컴포넌트 단위·fallback
  보장. core+wifi·부팅경로 컴포넌트는 상주.
- 리뷰 문서와 충돌 없음 — "런타임 모듈 레이어는 재설계 대상 아님"을 지킨다(코드
  그대로, 프로세스 경계만 이동).

---

## 9. 목표 모듈 맵 (현재 PID1 상주 45모듈 / 22,929 LOC)

| 클러스터 | 구성 모듈 | 약 LOC | Disposition |
| --- | --- | ---: | --- |
| **A. Init 코어 / supervisor** | controller, run, runtime, pid1_guard, reaper, service, log, console, cmdproto, util, timeline, shell (+ v319/v724 dispatch 유니티 TU) | ~3.3K | **상주 (환원불가 PID1)** |
| **B. WiFi 미션 스택** | wifi(3140), wificfg(2046), wifiinv(655), wififeas(240), app_wifi(417), app_network(116), netservice(495) | ~7.1K | **상주** (내부 리팩터 대상) |
| **C. UI/디스플레이 스택** | hud(1113), kms(682), input(642), input_cmd(105), draw(329), menu(408) | ~3.3K | 상주, **논리 경계만**(부팅경로·HW결합) |
| **D. 온디바이스 테스트/데모 앱** | app_displaytest(771), app_inputmon(851), app_cpustress(285), exposure(242), sensormap(385), app_about(292), changelog(850), app_log(96) | ~3.8K | **분리 후보(증거制)** + changelog 블롭 트림 |
| **E. 진단/소크/인벤토리** | diag(630), selftest(560), longsoak(662), metrics(329), kernelinv(475), watchdoginv(253), tracefs(249), pstore(224), helper(904) | ~4.3K | **분리 후보(증거制)** → /bin helper |
| **F. 전송/스테이징 스캐폴딩** | storage(697), userland(302), usb_gadget(154) | ~1.2K | 부팅 필수분 상주, dev 전용분 게이트 |

- 분리 시 **이미 /bin helper 있는 중복본부터**(cpustress↔bin/a90_cpustress,
  longsoak↔bin/a90_longsoak) — 동작 변화 없이 상주 코드 감소.
- **changelog(850)** 는 정적 텍스트 블롭 → 바이너리 밖(ramdisk 파일)으로 = 순수 트림.
- LOC는 분리 *후보* 규모이지 즉시 삭제량 아님. 분리는 PID1 TU→helper TU **이동**,
  트림(블롭, execns_probe dead 모드)만 실제 삭제.

---

## 10. 로드맵

```
지금:  기능 구현 (모듈 위생 유지)
  ↓
다음:  부팅 시퀀스 데이터화 (선언적 테이블 + resolver, 아직 분리 X, 위험 0)
  ↓
이후:  증거制 데몬 분리 (§6 3축 통과 + 크래시 증거, 컴포넌트 단위, fallback)
  ↓
마지막: 안정 mechanics 공통화 (§7 heuristic, Isolate First Then Share)
```

병행 (리뷰 문서 청소, 기회 될 때 · 위험 0):
- `--gc-sections`(+`-flto` 검토)로 dead-strip 실측 → PID1 감량폭 = dead-weight.
- 죽은 `A90_WIFI_TEST_BOOT` 스캐폴딩·죽은 `v319/90_main.inc.c` 적출, execns_probe
  dead 모드 트림.
- `glob("a90_*.c")` → per-baseline source manifest.

**근시일 위생 규칙 3개** (기능 구현이 자동으로 목표 모양으로 쌓이게 하는, 비용 0):

1. **새 기능은 좁은 헤더를 가진 모듈로** — main()/전역에 직조 금지(이미 하는 결).
2. **부팅 경로 삽입보다 on-demand 커맨드 우선** — `shell`/`screenapp` 핸들러로 될
   일이면 그렇게. 꼭 부팅 시점에 돌 게 아니면 부팅 시퀀스를 키우지 않는다.
3. **main()의 부팅 시퀀스 = 나중에 외재화할 대상**으로 의식 — 새 하드코드 단계
   하나하나가 미래 오케스트레이션 엔진의 일감. 추가는 최소·명확하게.

---

## 11. 한 줄 결론

**최종 목표는 정석 OS 형태(얇은 PID1 + 데몬 + 선언적 순서)의 부팅
오케스트레이션이고, 지금은 모듈 위생을 지키며 기능 구현에 집중한다.** 물리 분리는
증거制·컴포넌트별·fallback 보장하에 보류가 기본값이며, 혼잡은 우선 빼기로 줄인다.
이 프로젝트는 학습 최적화이므로 분리의 리스크는 회피 대상이 아니라 학습 대상이다.

---

## 출처 (외부 조사)

- PID1 vs service manager 분리 — systemd/systemd#6323
- init vs systemd 책무·LOC 비교 — vivianvoss.net
- Monolithic vs Microkernel — codelucky.com / cloudnativejourney.in
- Modular vs Monolithic — joepie91 gist / DornerWorks(embedded reliability)
- Monolith vs Microservices vs Modular Monolith — ByteByteGo
- 경량 init/supervision(runit/s6/dinit), s6-rc "why" — skarnet.org, linux-magazine.com
- dlopen 동적 플러그인 — ittrip.xyz
- "Isolate First, Then Share" — arXiv:1604.01378
- Android 부팅·init.rc·데몬 구조 — source.android.com/docs/core/architecture, dev.to(larsonzhong)
- systemd units/targets/의존 순서 — dev.to(rijultp), fedoramagazine.org, geeksforgeeks.org
