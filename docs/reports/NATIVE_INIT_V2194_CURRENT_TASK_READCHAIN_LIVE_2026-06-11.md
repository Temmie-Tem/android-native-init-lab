# Native Init V2194 current_task Read-Chain Live Probe (2026-06-11)

대상: A90 native boot `0.9.261 (v2189-security-p0-stage-fix)`.
목적: V2192 `bpf_probe_read` Tier-2 read engine과 V2193 `bpf_get_current_task()`
앵커를 한 프로그램으로 결합해 `task_struct` 최소 그래프를 live로 읽을 수 있는지
검증한다.

범위: read-only BPF tracepoint 관측. Wi-Fi, credential, DHCP, external ping,
파티션/펌웨어/커널 쓰기, `probe_write_user`, cgroup attach 없음.

---

## 1. 결론

V2194는 P0 합성 갭을 통과했다.

- `bpf_get_current_task()` 로 얻은 `task_struct *` 에서 `pid/tgid/cred/comm`을
  `bpf_probe_read`로 읽었다.
- helper 기준값 `bpf_get_current_pid_tgid()`, `bpf_get_current_uid_gid()`,
  `bpf_get_current_comm()` 과 비교해 live hit를 확인했다.
- `cred`는 `real_cred == cred` 포인터 쌍까지 요구해 단순 zero/invalid read false
  positive를 제거했다.

최종 판정:

```text
decision=v2194-current-task-readchain-pass
```

---

## 2. 산출물

| 항목 | 값 |
| --- | --- |
| 소스 | `workspace/public/src/native-init/helpers/a90_bpf_current_task_probe.c` |
| 마커 | `a90_bpf_current_task_probe v2194` |
| 빌드 | `aarch64-linux-gnu-gcc -static -Os -Wall -Wextra`, strip |
| 배포 경로 | `/cache/bin/a90_bpf_current_task_probe` |
| 최종 SHA256 | `de8bc49427febcc04148ae0463aead35dd4a5403091ff28266411dd5fe7227b7` |

설계:

- 기본은 attach 없음.
- `--allow-attach` 를 줘야 `sched:sched_switch`에 attach 한다.
- scan mode: 후보 offset 범위를 live로 훑고 hit 상위 후보를 출력한다.
- fixed mode: `--comm-off/--pid-off/--tgid-off/--cred-off` 를 지정해 한 번에 pass/fail을
  판정한다.

---

## 3. Live Evidence

### 3.1 후보 탐색

초기 전체 scan은 장시간 출력 때문에 a90ctl END marker를 놓쳤지만, 부분 결과에서
핵심 후보가 나왔다.

```text
candidate rank=1 kind=comm off=2144 total=2 hits=2
candidate rank=1 kind=pid off=1704 total=25 hits=25
```

좁은 pid/tgid 재검증:

```text
scan kind=pid start=1704 end=1708 step=4 dwell_ms=100
candidate rank=1 kind=pid off=1704 total=59 hits=34 last0=8 last1=8
candidate rank=2 kind=pid off=1708 total=60 hits=34 last0=1 last1=1

scan kind=tgid start=1704 end=1708 step=4 dwell_ms=100
candidate rank=1 kind=tgid off=1708 total=70 hits=38 last0=1 last1=1
candidate rank=2 kind=tgid off=1704 total=64 hits=36 last0=1 last1=1
```

좁은 comm/cred 재검증:

```text
scan kind=comm start=2080 end=2184 step=8 dwell_ms=20
candidate rank=1 kind=comm off=2144 total=23 hits=23 last0=0 last1=0

scan kind=cred start=2080 end=2184 step=8 dwell_ms=20
candidate rank=1 kind=cred off=2136 total=28 hits=28 last0=0 last1=0
```

소스 선언 순서와 일치한다.

```text
real_cred -> cred -> comm[TASK_COMM_LEN]
cred_off=2136, comm_off=2144
```

### 3.2 최종 fixed pass

명령:

```sh
/cache/bin/a90_bpf_current_task_probe \
  --allow-attach \
  --dwell-ms 100 \
  --pid-off 1704 \
  --tgid-off 1708 \
  --cred-off 2136 \
  --comm-off 2144
```

결과:

```text
a90_bpf_current_task_probe v2194
allow_attach=1 start=0 end=4096 dwell_ms=100 cred_uid_off=4 cred_euid_off=20
fixed kind=comm off=2144 total=53 hits=52 last0=0 last1=0
fixed kind=pid off=1704 total=75 hits=43 last0=1 last1=1
fixed kind=tgid off=1708 total=59 hits=33 last0=1 last1=1
fixed kind=cred off=2136 total=64 hits=64 last0=0 last1=0
decision=v2194-current-task-readchain-pass
```

판정:

- `task->comm` read-chain: pass.
- `task->pid` read-chain: pass.
- `task->tgid` read-chain: pass.
- `task->cred->uid/euid` read-chain: pass.

---

## 4. 보정 사항

### 4.1 task_struct randstruct

커널 config에서 `CONFIG_GCC_PLUGINS`가 꺼져 있다.

```text
# CONFIG_GCC_PLUGINS is not set
```

따라서 `__randomize_layout`/`randomized_struct_fields_start`는 실질적으로 비활성이다.
그래도 V2194는 소스 offset만 믿지 않고 live helper 값과 비교해 offset을 검증했다.

### 4.2 cred false-positive 제거

초기 cred scan은 invalid pointer read가 0으로 남아 root uid 0과 우연히 맞는 false
positive를 만들 수 있었다. 최종 helper는 다음을 모두 요구한다.

- `probe_read(task + off)` 성공.
- `probe_read(task + off - 8)` 성공.
- `cred == real_cred`.
- `probe_read(cred + uid_off/euid_off)` 성공.
- `uid == euid == bpf_get_current_uid_gid() & 0xffffffff`.

이 기준에서 `cred_off=2136`이 통과했다.

---

## 5. 능력맵 갱신

V2194 이후 상태:

| 능력 | 상태 |
| --- | --- |
| V2192 record-pointer Tier-2 `bpf_probe_read` | 확정 |
| V2193 `current_task` 앵커 | 확정 |
| V2194 `current_task -> task_struct scalar` read-chain | 확정 |
| V2194 `current_task -> cred -> uid/euid` read-chain | 확정 |
| stackmap raw address dump / symbolization | 아직 미구현 |
| kernel write / `probe_write_user` execution | 미수행, 금지 유지 |
| cgroup-BPF attach | cgroupfs 미마운트로 미확정 |

즉 “부품은 입증됐고 조립만 남음” 상태에서, 핵심 조립인
`current_task + probe_read offset-chain`은 완료됐다.

---

## 6. Next

P1: stackmap value dump + symbolization.

- V2193의 `stackid=122`에서 stackmap value를 userspace로 lookup.
- raw address가 실제로 회수되는지 확인.
- `System.map`/vmlinux 또는 kallsyms-derived symbol map과 매칭.
- WLAN/QRTR/cfg80211 tracepoint에만 적용한다.

P2: WLAN/cfg80211 object-chain read.

- tracepoint record pointer → wiphy/wireless_dev/net_device → driver private 방향.
- 각 offset은 소스 기반 후보 + V2194 방식의 live 교차검증으로만 승격.

---

## 7. Safety

- `/cache/bin` 임시 배포만 수행.
- tracepoint attach는 `--allow-attach` 명시 + 100ms dwell fixed run.
- BPF helper는 `bpf_probe_read`, `get_current_task`, `get_current_pid_tgid`,
  `get_current_uid_gid`, `get_current_comm`, map lookup만 사용.
- `probe_write_user` 없음.
- cgroup attach 없음.
- Wi-Fi/scan/connect/DHCP/routes/external ping 없음.
- 파티션/펌웨어/커널 쓰기 없음.
