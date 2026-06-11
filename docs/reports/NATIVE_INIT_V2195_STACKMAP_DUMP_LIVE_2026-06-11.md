# Native Init V2195 Stackmap Dump Live Probe (2026-06-11)

대상: A90 native boot, 현재 `0.9.261 (v2189-security-p0-stage-fix)` 계열.
V2193 `bpf_get_stackid()` probe를 확장해, 반환된 stack id에 대해
`BPF_MAP_LOOKUP_ELEM` 으로 stack trace map value를 userspace에서 직접 읽었다.

범위: BPF 관측 검증만 수행했다. Wi-Fi 연결, credential, DHCP, external ping,
cgroup attach, `probe_write_user` 실행, 커널/펌웨어/파티션 쓰기는 수행하지 않았다.
바이너리는 `/cache/bin/a90_bpf_helper_probe` 에 임시 배포했다.

---

## 1. 결론

V2195는 P1의 첫 부분을 통과했다.

- `bpf_get_stackid()` runtime hit 뒤 stackmap value lookup이 성공했다.
- stack id `122` 에서 non-zero frame 6개를 회수했다.
- 회수된 6개 frame 전부 `0xffffff...` 형태의 kernel VA다.
- `/proc/kallsyms` 는 `kptr_restrict=4` 로 주소가 전부 `0` 이지만,
  stackmap value에는 raw KASLR-slid address가 노출됐다.

따라서 V2193의 “stackmap index 반환”은 V2195에서
“stackmap raw kernel IP 회수”로 승격한다.

아직 완료하지 않은 부분:

- raw IP를 symbol name으로 매핑하는 단계는 미완료다.
- 현재 repo에서 발견된 `tmp/wifi/v1331-esoc-disasm/vmlinux.raw` 는 실제 vmlinux가
  아니라 kernel config text라 symbol map으로 사용할 수 없다.
- 다음 P1b는 이 boot와 일치하는 `System.map` 또는 unstripped `vmlinux` 확보 후,
  stackmap IP를 `symbol + offset` 으로 변환하는 것이다.

---

## 2. Helper 변경

소스: `workspace/public/src/native-init/helpers/a90_bpf_helper_probe.c`

추가:

- `--dump-stackmap`
- `STACK_DEPTH=127`, `STACK_MAX_ENTRIES=128`
- `get_stackid` runtime hit 후 `stack_map[last_stackid]` lookup
- summary line:
  `stackmap_dump requested=1 lookup_ok=1 stackid=... depth=... nonzero=... kernelish=...`
- frame line:
  `stack_ip index=N value=0x... kernelish=1`

기본 실행은 기존 V2193와 동일하게 load-only다. Stackmap dump는
`--allow-attach --dump-stackmap` 을 모두 명시해야만 실행된다.

빌드:

```sh
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra \
  -o workspace/private/runs/kernel/v2195-stackmap-dump-20260611-203700/a90_bpf_helper_probe \
  workspace/public/src/native-init/helpers/a90_bpf_helper_probe.c
aarch64-linux-gnu-strip \
  workspace/private/runs/kernel/v2195-stackmap-dump-20260611-203700/a90_bpf_helper_probe
```

SHA-256:

```text
78510396cf15ef7eff41d4217291e2b1619bd1d7a90d4020ac7bd697c2e76696
```

---

## 3. Live 결과

### 3.1 Check-only

```text
a90_bpf_helper_probe v2195
allow_attach=0 allow_cgroup_attach=0 duration_sec=1 dump_stackmap=0 verbose=1
probe name=get_current_task load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
probe name=get_stackid load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
probe name=probe_write_user_loadonly load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only_not_attached_not_executed
probe name=cgroup_skb_pass load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
result=v2195-helper-capability-probe-complete
```

판정:

- 기본 경로는 attach 없이 load-only.
- `probe_write_user` 는 여전히 load-only, not attached, not executed.
- cgroup program은 load-only. cgroup attach는 시도하지 않았다.

### 3.2 Stackmap dump

```text
a90_bpf_helper_probe v2195
allow_attach=1 allow_cgroup_attach=0 duration_sec=1 dump_stackmap=1 verbose=1
probe name=get_current_task load_ok=1 attach_ok=1 runtime_ok=1 load_errno=0 attach_errno=0 count=343 last=1 detail=tp_id=58
probe name=get_stackid load_ok=1 attach_ok=1 runtime_ok=1 load_errno=0 attach_errno=0 count=433 last=122 detail=tp_id=58
stackmap_dump requested=1 lookup_ok=1 stackid=122 depth=127 nonzero=6 kernelish=6 errno=0 detail=ok
stack_ip index=0 value=0xffffff8009a42334 kernelish=1
stack_ip index=1 value=0xffffff8009a42334 kernelish=1
stack_ip index=2 value=0xffffff8009a429d8 kernelish=1
stack_ip index=3 value=0xffffff800819ad8c kernelish=1
stack_ip index=4 value=0xffffff800819adf0 kernelish=1
stack_ip index=5 value=0xffffff80081131f4 kernelish=1
probe name=probe_write_user_loadonly load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only_not_attached_not_executed
probe name=cgroup_skb_pass load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
result=v2195-helper-capability-probe-complete
```

판정:

- `sched_switch` tracepoint id는 `58`.
- 1초 window에서 `get_stackid` 433회 hit.
- 마지막 stack id `122` 에서 stackmap lookup 성공.
- nonzero frame 6개 모두 kernel address 형태.

### 3.3 Symbol visibility

```text
kptr_restrict=4
0000000000000000 t _head
0000000000000000 T _text
0000000000000000 T _stext
0000000000000000 T __exception_text_start
0000000000000000 T do_undefinstr
```

판정:

- `/proc/kallsyms` 는 raw address를 제공하지 않는다.
- 그러나 stackmap value lookup은 raw kernel IP를 제공한다.
- 이로써 stackmap은 `kptr_restrict` 로 가려진 kallsyms 주소와 별개 경로의
  address 관측면으로 분류한다.

### 3.4 Selftest

```text
selftest: pass=11 warn=1 fail=0 duration=51ms entries=12
```

---

## 4. 능력맵 갱신

| 능력 | V2194 이후 | V2195 이후 |
| --- | --- | --- |
| V2193 `bpf_get_stackid` runtime | 확정 | 확정 |
| stackmap raw value dump | 미구현 | **확정** |
| raw kernel IP 회수 | 미확정 | **확정** |
| kallsyms 주소 노출 | 차단 확인 | 차단 유지 (`kptr_restrict=4`) |
| raw IP symbolization | 미구현 | 미완료, symbol map 필요 |
| kernel write / `probe_write_user` execution | 금지 유지 | 금지 유지 |
| cgroup-BPF attach | 미확정 | 시도 안 함 |

V2195의 의미는 “콜스택 symbolization 완료”가 아니라,
`BPF_MAP_TYPE_STACK_TRACE` value가 raw kernel IP를 userspace로 회수할 수 있음을
실측으로 확정한 것이다.

---

## 5. 다음 단계

P1b 상태:

- V2196에서 OSRC kernel build로 `vmlinux`/`System.map`은 생성했지만, live boot의
  stock kernel SHA와 새 `Image` SHA가 달라 정확 심볼화 authority로는 사용할 수 없었다.
- V2196에서 `timer:timer_start`의 `function` field raw pointer anchor는 live로
  회수했다.
- 따라서 남은 blocker는 BPF capability가 아니라 **bit-exact matching stock symbol
  map**이다. 단일 slide anchor는 그 map이 live kernel과 같은 layout이라는 전제가
  있을 때만 충분하다.

다음 exact gate:

- stock `UNCOMPRESSED_IMG`/raw Image kallsyms parser를 복구해 현재 boot와 같은
  `System.map`을 생성한다.
- 그 map으로 V2195 stack IP와 V2196 timer function anchors를 다시 symbolization 한다.

P2: WLAN/cfg80211 object-chain read.

- stack symbolization이 된 뒤, WLAN/QRTR/cfg80211 tracepoint에 적용한다.
- oracle 없는 구조체는 source offset 후보 + 구조 불변식으로만 승격한다.

---

## 6. Safety

- `/cache/bin` 임시 helper 배포만 수행.
- tracepoint attach는 `--allow-attach` 명시 + 1초 bounded run.
- `probe_write_user` 는 load-only, not attached, not executed.
- cgroup attach는 수행하지 않았다.
- Wi-Fi scan/connect, credential, DHCP, route, external ping 없음.
- selftest `fail=0`.
---

## 7. V2197 Update

The matching stock symbol map blocker noted above was closed in V2197 by parsing
the embedded kallsyms tables from the live stock kernel wrapper. The V2195 stack
IP set now maps under the stock map, but slide identity remains provisional;
timer anchors still need separate callback-entry validation before they are used
as slide authority.

See `docs/reports/NATIVE_INIT_V2197_STOCK_KALLSYMS_SYMBOLIZATION_2026-06-11.md`.
