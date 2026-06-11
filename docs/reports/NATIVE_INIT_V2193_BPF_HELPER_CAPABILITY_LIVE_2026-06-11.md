# Native Init V2193 BPF Helper Capability Live Probe (2026-06-11)

대상: A90 native boot, 현재 v2187/0.9.259 계열 베이스라인 위에서 별도 helper
`a90_bpf_helper_probe v2193` 를 `/cache/bin/` 에 임시 배포해 실행했다.

범위: 읽기/관측 능력 확장 가능성 확인. Wi-Fi, 네트워크 연결, credential, DHCP,
외부 ping, 커널/펌웨어/파티션 쓰기는 수행하지 않았다.

---

## 1. 결론

V2193 live probe 기준으로 BPF 기반 관측 확장은 실사용 가능하다.

- `bpf_get_current_task()` helper 35: **load + tracepoint attach + runtime OK**.
- `bpf_get_stackid()` helper 27: **load + tracepoint attach + runtime OK**.
- `bpf_probe_write_user()` helper 36: **load-only OK**, map gate 기본값 0이라 실행하지 않음.
- `BPF_PROG_TYPE_CGROUP_SKB`: **program load OK**, attach는 `/sys/fs/cgroup` 미마운트라 현재 네임스페이스에서 미확정.

즉, locked/RKP 환경에서도 tracepoint 기반 `current_task` 앵커와 stackmap 콜스택
수집은 확인됐다. 커널 메모리 쓰기 벽을 깨는 증거는 없고, `probe_write_user` 는
“로드 가능하지만 실행 금지” 상태로만 분류한다.

---

## 2. Helper 추가

소스: `workspace/public/src/native-init/helpers/a90_bpf_helper_probe.c`

설계:

- 기본 실행은 check-only, attach 없음.
- `--allow-attach` 를 줘야 `sched:sched_switch` tracepoint 에 attach 한다.
- `--duration SEC` 는 1~5초로 clamp 한다.
- `probe_write_user` 는 ARRAY map gate 뒤에 둔다. verifier 는 helper 경로를
  검증하지만 map 기본값이 0이므로 helper call 경로는 실행되지 않는다.
- `--allow-cgroup-attach` 는 임시 cgroup attach만 시도한다.

빌드:

```sh
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra \
  -o tmp/wifi/v2193-bpf-helper-probe-build/a90_bpf_helper_probe \
  workspace/public/src/native-init/helpers/a90_bpf_helper_probe.c
aarch64-linux-gnu-strip tmp/wifi/v2193-bpf-helper-probe-build/a90_bpf_helper_probe
```

최종 배포 해시:

```text
269360965596b0a567116553808b6bb1b2dc25074699b6f090a79e06acf296d3
```

---

## 3. Live 결과

### 3.1 Check-only

```text
a90_bpf_helper_probe v2193
allow_attach=0 allow_cgroup_attach=0 duration_sec=1 verbose=1
probe name=get_current_task load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
probe name=get_stackid load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
probe name=probe_write_user_loadonly load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only_not_attached_not_executed
probe name=cgroup_skb_pass load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
result=v2193-helper-capability-probe-complete
```

판정:

- 세 trace/helper 후보와 cgroup skb program 모두 로드 가능.
- `probe_write_user` 는 load-only 판정이다. 실행하지 않았고 실행하면 안 된다.

### 3.2 Tracepoint attach/runtime

```text
a90_bpf_helper_probe v2193
allow_attach=1 allow_cgroup_attach=0 duration_sec=1 verbose=1
probe name=get_current_task load_ok=1 attach_ok=1 runtime_ok=1 load_errno=0 attach_errno=0 count=440 last=1 detail=tp_id=58
probe name=get_stackid load_ok=1 attach_ok=1 runtime_ok=1 load_errno=0 attach_errno=0 count=398 last=122 detail=tp_id=58
probe name=probe_write_user_loadonly load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only_not_attached_not_executed
probe name=cgroup_skb_pass load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
result=v2193-helper-capability-probe-complete
```

판정:

- `sched:sched_switch` tracepoint id는 `58`.
- 1초 동안 `get_current_task` 440회, `get_stackid` 398회 카운트.
- stack id 마지막 값은 `122`; stackmap 경로가 실제로 값 반환.

### 3.3 cgroup attach

```text
a90_bpf_helper_probe v2193
allow_attach=0 allow_cgroup_attach=1 duration_sec=1 verbose=1
probe name=get_current_task load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
probe name=get_stackid load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only
probe name=probe_write_user_loadonly load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=0 count=0 last=0 detail=load_only_not_attached_not_executed
probe name=cgroup_skb_pass load_ok=1 attach_ok=0 runtime_ok=0 load_errno=0 attach_errno=2 count=0 last=0 detail=mkdir_temp_cgroup_failed
result=v2193-helper-capability-probe-complete
```

추가 확인:

```text
/sys/fs/cgroup: dr-xr-xr-x empty directory
/proc/cgroups: cpuset/cpu/cpuacct/schedtune/blkio/memory/freezer enabled, hierarchy 0
/proc/mounts: no cgroup mount
```

판정:

- cgroup skb program load는 가능.
- attach는 `cgroupfs` 미마운트 때문에 대상 cgroup fd를 만들 수 없어 미확정.
- 이 단계에서 cgroupfs mount는 하지 않았다. mount는 제어면 변경이라 별도 승인이 필요하다.

---

## 4. 보정된 해석

이전 가설 중 “helper 35/27/36/CGROUP-SKB 모두 한 줄 테스트로 확정 가능”은
부분적으로 맞았다.

확정:

- helper 35 `bpf_get_current_task`: 사용 가능.
- helper 27 `bpf_get_stackid`: 사용 가능.
- tracepoint attach + runtime map update: 사용 가능.
- BPF map 기반 상태 누적: 사용 가능.

조건부/미확정:

- helper 36 `bpf_probe_write_user`: verifier load는 가능하지만 실행하지 않았다.
  이 프로젝트의 관측 목적에서는 사용하지 않는 것이 맞다.
- cgroup-BPF attach: program load는 가능하지만 현재 boot namespace에 cgroupfs가
  없어 attach 미확정.

유효하지 않은 확대 해석:

- “커널 임의 쓰기 가능”은 여전히 증거 없음.
- “cgroup-BPF 정책 제어 가능”은 attach 대상 mount/fd 확인 전까지 확정 불가.
- “임의 커널 읽기 전체 개방”도 아직 과장이다. V2193가 확정한 것은
  `current_task` 앵커와 stackid 콜스택을 live tracepoint에서 얻을 수 있다는
  점이다. 구조체 offset-chain extractor는 다음 단계에서 별도 구현해야 한다.

---

## 5. 다음 단계

P0: `current_task` 기반 read-chain extractor 를 작게 만든다.

- `sched_switch` 에 attach.
- `bpf_get_current_task()` 로 task pointer 획득.
- 소스/빌드 기준 offset으로 `pid/tgid/comm/cred uid/euid` 정도만 읽는다.
- 유저스페이스 출력은 pid/comm/uid/euid 카운터 수준으로 제한한다.

P1: stackmap symbolization 파이프라인을 만든다.

- stackmap id → raw address list 회수.
- 현재 커널 `System.map`/vmlinux 심볼과 매칭.
- WLAN/QRTR/cfg80211 이벤트에만 적용한다.

P2: cgroup-BPF는 후순위로 둔다.

- 지금 목적은 관측이다.
- cgroupfs mount/attach는 네트워크 정책 제어 성격이 있어 별도 설계/승인 없이
  baseline 경로에 넣지 않는다.

---

## 6. 안전성 판정

V2193 helper는 baseline 기능이 아니라 연구/진단 helper다.

- `/cache/bin` 임시 배포만 수행.
- tracepoint attach는 명시 옵션 + 1초 bounded run.
- `probe_write_user` 는 load-only, not attached, not executed.
- cgroup attach는 실패했고 cgroupfs mount는 하지 않았다.
- Wi-Fi/네트워크 연결/credential/DHCP/external ping 없음.

결론: V2193는 “BPF 관측 확장 가능성”을 live로 열었다. 다음 작업은 Wi-Fi 기능
쪽이 아니라 커널 관측 도구화라면, `current_task` read-chain extractor와
stack symbolization이 실제 ROI가 높다.
