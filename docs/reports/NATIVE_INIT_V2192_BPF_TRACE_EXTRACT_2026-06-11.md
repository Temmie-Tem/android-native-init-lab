# Native Init V2192 Parametric eBPF Trace Extractor (2026-06-11)

## Result

- decision: `v2192-bpf-trace-extract-validated`
- pass: `true`
- type: 디바이스 read-only 관측 엔진 빌드 + 온디바이스 검증. 플래시·파티션
  쓰기·재부팅·Wi-Fi 트리거 없음.
- 목표: V2191 한계맵의 **master observe chain**(eBPF + `bpf_probe_read` 임의
  커널 읽기)을 **단일 데이터구동 도구**로 구현하고 디바이스에서 실동작 검증,
  체인 확장 경로를 확정.
- 채널: native-init `0.9.261 (v2189-security-p0-stage-fix)` 시리얼 브리지 +
  a90ctl. 바이너리 배포는 NCM USB 링크(표준 `192.168.7.0/24` 게이트 서브넷)를
  통한 `tcpctl install`(netcat+dd, SHA 검증). 디바이스 식별자(serial/MAC)는
  본 문서에서 redaction.
- 선행: [V779/V780 BPF 로더 빌드·배포](NATIVE_INIT_V779_BPF_LOADER_BUILD_2026-05-25.md),
  [V781 BPF idle attach](NATIVE_INIT_V781_BPF_IDLE_ATTACH_2026-05-25.md),
  [V2191 커널 능력 한계맵](NATIVE_INIT_V2191_KERNEL_CAP_LIMIT_MAP_2026-06-11.md).

## 산출물

| 항목 | 값 |
| --- | --- |
| 소스 | `workspace/public/src/native-init/helpers/a90_bpf_trace_extract.c` |
| 빌드 | `aarch64-linux-gnu-gcc -static -Os -Wall -Wextra` (경고 0), strip |
| 빌드 증거 | `tmp/wifi/v2192-bpf-extract-build/` |
| ELF | ARM aarch64, static, INTERP 없음, 마커 `a90_bpf_trace_extract v2192` |
| 배포 경로 | `/cache/bin/a90_bpf_trace_extract` |
| 배포 SHA256 | `3f8510175ef0f7f7ac0564acd396f0fd82367e90a9095e1bcf61c2312b8f10ee` |
| 의존성 | 없음 — libbpf/LLVM 불사용, BPF 바이트코드 런타임 직접 emit |

## 엔진 설계 (데이터구동 단일 바이너리)

타깃·읽기·출력이 전부 플래그라 **재타깃에 재컴파일이 불필요**하다. BPF 프로그램은
파라미터에서 `bpf_insn` 배열로 런타임 조립한다.

| 축 | 옵션 | 비고 |
| --- | --- | --- |
| 타깃 | `--event GROUP:EVENT` | `/sys/.../id`·`/format` 런타임 resolve |
| Tier-1 read | `--field NAME` / `--field-raw OFF:SIZE` | ctx 스칼라; offset/size는 format 파일에서 |
| Tier-2 read | `--deref CTXOFF:o1,o2,…:SIZE` | `bpf_probe_read` 포인터 추적 (RKP-safe) |
| 출력 | `--mode sample\|freq\|stream` | ARRAY stats / HASH 분포 / perf_event_array + per-cpu perf buffer 시계열 |
| 게이트 | 기본 `--check-only`, attach는 `--allow-attach` | read-only, tracefs write 없음, wifi 무관, duration bound |

### 오프셋 출처 결정 (BTF 없음 → 두 경로)

- `CONFIG_DEBUG_INFO_BTF` 부재(`DEBUG_INFO=y`만, DWARF) → **CO-RE 불가**.
- **Tier-1**: 트레이스포인트 BPF prog의 ctx 레이아웃 = `format` 파일의 필드
  오프셋. 즉 **format이 커널별 정확한 자기기술** → 오프셋 지식 0.
- **Tier-2**: ctx의 포인터를 따라 커널 구조체로 들어가는 offset은 **커널 소스
  (`workspace/private/inputs/kernel_source/.../Kernel/`) + config 유도 후
  온디바이스 교차검증**. (예: `struct timer_list` → 아래 검증.)

## 온디바이스 검증 매트릭스

| 능력 | 타깃 | 결과 |
| --- | --- | --- |
| Tier-1 scalar / sample | `sched:sched_switch` `next_pid` (off56,sz4) | count=783, last=2507, avg=652 (타당 pid) — `extract-pass` |
| Tier-1 scalar / freq | 〃 | 값 분포(`value=0`=idle 우세, 커널스레드 클러스터) — `extract-pass` |
| Tier-1 scalar / stream | 〃 | `stream_cpus=8`, next_pid 원시 시계열 방출 — `extract-pass` |
| **Tier-2 deref / probe_read** | `timer:timer_start` `timer->expires` (`8:16:8`) | record.expires와 동일 jiffy 윈도 — `extract-pass` |
| format 자동 resolve | `--field next_pid` | `off=56 size=4` (format과 일치) |
| 안전 게이트 | 기본 `--check-only` | `attach_attempted=0` |

### Tier-2 교차검증 (offset 정당성)

`timer:timer_start` 레코드는 `void *timer`(ctx@8)와 `unsigned long expires`(ctx@24)를
모두 보유. 소스 `struct timer_list`: `entry`(hlist_node 16B) → **`expires`@offset 16**.

- Tier-1 `record.expires`(ctx@24): `last=4304065331`, avg≈4.2937e9 (32-bit jiffies).
- Tier-2 `timer->expires`(`deref 8:16:8`): `last=4304065582` → **동일 jiffy 윈도**.
- freq 분포: 절대다수가 `4304050xxx`/`4304068407(count=28)` 클러스터로 Tier-1과 일치.
  소수 거대값(`7.8e18` 등)은 "never"급 특수 timer의 실제 expires outlier —
  offset 오류라면 `last`도 어긋났을 것이므로 **offset 16 정당** 확정.
- 함의: `bpf_probe_read`는 잘못된 offset이어도 **폴트 없이 쓰레기를 읽음** →
  Tier-2 offset은 항상 소스 + 교차검증 필수.

## 구현 중 고친 2건

1. **HASH/PERF map `EPERM`** — BPF map 메모리가 이 커널에서 `RLIMIT_MEMLOCK`
   회계 대상. ARRAY(1엔트리)는 통과했으나 HASH(다엔트리)가 거부됨. 시작 시
   `setrlimit(RLIMIT_MEMLOCK, RLIM_INFINITY)`(root) 추가 + hash 엔트리 2048로.
2. **`BPF_PROG_LOAD` `EINVAL` at log_level=0** — 이 4.14 커널은 `log_level=0`인데
   `log_buf`를 넘기면 `EINVAL`(V781에서 본 quirk). 비-verbose 경로에서 log_buf를
   비우도록 수정 → `--verbose` 없이 sample/freq/stream 전부 로드.

## 능력 확장 분석 — 체인으로 어디까지

### Tier-2 = 범용 임의 커널 읽기 프리미티브

`bpf_probe_read(ptr+offset)` 동작 입증의 의미는 timer 하나가 아니다. **커널
메모리의 포인터 하나(앵커)만 쥐면 거기서 도달 가능한 객체 그래프 전체가 읽힌다.**
RKP는 쓰기만 막고 읽기는 막지 않으므로 합법. V2191 가설(닫힌 kcore/devmem을 읽기
체인으로 회수)이 실측 확정됨.

### 앵커 출처

| 앵커 | 도달 대상 | 4.14 가용 |
| --- | --- | --- |
| 레코드 포인터(timer/work/sock/skb/netdev/file…) | 해당 서브시스템 객체 트리 | ✅ (입증) |
| `bpf_get_current_task()` (helper 35) | **현재 실행 task_struct** | ✅ V2193 런타임 확정 |

트레이스포인트는 모든 프로세스 문맥에서 발화 → 고빈도 포인트에 붙으면 시간이
지나며 **시스템의 거의 모든 task**를 만난다. `task_struct`에서:
`cred`(uid/gid/캡빌리티), `mm`(VMA/pgd), `files`(fd→file→inode/path),
`nsproxy`(net/pid/mnt/user ns), `real_parent`(프로세스 트리). →
**임의 프로세스의 자격증명·메모리지도·열린파일·네임스페이스를 시스템 전역 수동 읽기.**

### 배율기

- **KASLR 무력화/심볼화**: 구조체의 함수 포인터(timer->function, file_operations,
  sk_prot…)는 커널 텍스트 주소. 소스를 보유하므로 누출 포인터→심볼 역매핑 →
  익명 포인터를 "어느 드라이버의 어느 핸들러"로 식별, 그래프를 이름 붙은 그래프로 승격.
- **콜스택**: `bpf_get_stackid`(helper 27, 4.14 존재; `get_stack`(67)은 4.18이라
  **부재** → stackmap 방식 우회) → 발화 시점 커널 콜스택 + 심볼맵 = 라이브 콜그래프.
  V2193에서 `sched_switch` 런타임 `stackid=122` 반환까지 확인됐다. 단, stackmap
  value의 raw address dump는 아직 안 했으므로 `kptr_restrict` 우회 raw 주소 회수는
  다음 검증 항목이다.

### 관측 천장 vs 제어 벽

| 면 | 상태 |
| --- | --- |
| **관측** | 임의 커널 읽기 + current_task 앵커 + 콜스택 + 심볼화 ⇒ 커널 자료구조가 인코딩한 거의 모든 것(프로세스/cred/메모리맵/fd/소켓/netdev·드라이버/타이머/워크큐/런큐/ns/콜스택). **닫힌 kcore·devmem을 읽기 체인이 회수.** |
| **제어** | 좁게만 확장. `bpf_probe_write_user`(36, 존재하나 게이트/taint) = 현재 task **유저메모리 쓰기**; cgroup-BPF = 네트워크 **정책 결정**. `bpf_override_return`(58)은 KPROBES off라 **불가**. **커널 메모리 쓰기는 RKP/무모듈/무devmem으로 벽 유지.** |

### 미션 체인 (관측, 모뎀 쓰기경로 무접촉)

- **WLAN**: cfg80211/mac80211 트레이스포인트(V2191 카탈로그 cfg80211=162) →
  wiphy/wireless_dev/net_device → 드라이버 private(icnss/cnss) → 펌웨어 핸드셰이크·
  레귤러토리·링크 상태.
- **모뎀/전송**: qrtr/ipa/mhi/gsi → QMI/전송 상태 구조체.
- **전력**: regulator/clk/genpd → struct regulator/clk(enable_count/rate/voltage) =
  WLAN 게이팅 전력 트리.

## 확장 로드맵 (V2193 live delta 반영)

| 팔 | 종류 | 구현 | 패턴 |
| --- | --- | --- | --- |
| Tier-1/Tier-2 read | 관측 | **완료(본 V2192)** | — |
| ① `get_current_task` 앵커 | 관측 | **런타임 확정(V2193)** — emitter에 deref base=`R0=task` 분기 + 플래그 필요 | 다음 P0 |
| ② `get_stackid` 콜스택 | 관측 | **런타임 확정(V2193)**, **raw stackmap value dump 확정(V2195)** — 심볼화는 symbol map 필요 | 다음 P1b |
| ③ `probe_write_user` | **제어** | **verifier load 확정(V2193)** — map-gated load-only, 실행 보류 | 별도 안전 게이트 |
| ④ cgroup-BPF 정책 | **제어** | **program load 확정(V2193)** — attach는 cgroupfs 미마운트로 미확정 | 별도 도구/승인 |

규율: V2193로 helper 후보 ①②③과 cgroup program load는 분류됐다. 다음 P0는
새 capability 발견이 아니라 **V2192 deref engine + V2193 `current_task` 앵커 조립**이다.
제어 팔 ③④는 관측 엔진과 분리하고 별도 안전 결정을 요구한다.

## V2193 상호참조

[V2193 helper capability live probe](NATIVE_INIT_V2193_BPF_HELPER_CAPABILITY_LIVE_2026-06-11.md)
가 본 문서의 후보 팔을 다음처럼 갱신했다.

- helper 35 `bpf_get_current_task`: load + `sched_switch` attach + runtime count 확인.
- helper 27 `bpf_get_stackid`: load + attach + runtime stackid 반환 확인.
- helper 36 `bpf_probe_write_user`: verifier load 통과, map-gated load-only, 미실행.
- `BPF_PROG_TYPE_CGROUP_SKB`: program load 통과, attach는 cgroupfs 미마운트 때문에 미확정.

V2194에서 이 합성 갭은 닫혔다:
[V2194 current_task read-chain live probe](NATIVE_INIT_V2194_CURRENT_TASK_READCHAIN_LIVE_2026-06-11.md)
가 `current_task -> task_struct(pid/tgid/comm)` 및
`current_task -> cred -> uid/euid` read-chain을 live로 검증했다.

V2195에서 stackmap raw address 회수도 닫혔다:
[V2195 stackmap dump live probe](NATIVE_INIT_V2195_STACKMAP_DUMP_LIVE_2026-06-11.md)
가 `stackid=122` value에서 raw `0xffffff...` kernel IP 6개를 회수했다. 남은
관측 갭은 이 boot와 일치하는 `System.map`/unstripped `vmlinux` 기반 심볼화다.

## Safety

- BPF attach: sched/timer 등 **항상 발화하는 안전 트레이스포인트에만**, duration
  bound(≤2s), 종료 시 detach.
- tracefs control write: 없음(읽기·자기기술 format/id만).
- Wi-Fi HAL/서비스 start·scan·connect·DHCP·route·ping: 없음.
- 모뎀/WLAN-PD 트리거: 없음.
- 재부팅/플래시/파티션 쓰기: 없음. EFS/modem/RPMB/keymaster/vbmeta/bootloader 무접촉.
- 배포: `/cache/bin`(런타임 캐시), boot.img 재플래시 없음. NCM 호스트 IP 설정은
  사용자가 수행(sudo).
- 식별자(serial/MAC) redaction. 자격증명/PSK 미로그.

## Next

- ① `get_current_task` 앵커 + `task_struct` 최소 그래프 관측은 V2194에서 완료.
- stackmap raw address 회수는 V2195에서 완료. 다음은 커널 심볼맵 확보
  (`System.map`/unstripped `vmlinux`) → 콜스택 심볼화 파이프라인.
- 미션면 Tier-2 깊이: WLAN(cfg80211→드라이버 private) 구조체 offset 소스 유도·검증.
- ②/③/④는 별도 run으로, 제어 팔은 명시적 안전 게이트와 함께.

## 참조

- [V2191 커널 능력 한계맵](NATIVE_INIT_V2191_KERNEL_CAP_LIMIT_MAP_2026-06-11.md) — 절단선·Breadth 카탈로그.
- [V781 BPF idle attach](NATIVE_INIT_V781_BPF_IDLE_ATTACH_2026-05-25.md) — tracepoint BPF 로드/attach 최초 증명, log_level quirk.
- [V779/V780 BPF 로더 빌드·배포](NATIVE_INIT_V779_BPF_LOADER_BUILD_2026-05-25.md) — static aarch64 빌드·`/cache/bin` 배포 컨벤션.
- 소스: `workspace/public/src/native-init/helpers/a90_bpf_trace_extract.c`.
