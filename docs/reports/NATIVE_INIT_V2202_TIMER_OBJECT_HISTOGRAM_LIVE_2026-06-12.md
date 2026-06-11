# Native Init V2202 Timer Object Histogram Live Capture (2026-06-12)

대상: A90 native boot `0.9.261 (v2189-security-p0-stage-fix)` stock kernel,
read-only BPF `timer:timer_start` object histogram path.

목적: V2201의 단일-filter capture 한계를 줄이기 위해, `timer_start.function`별
HASH row를 만들고 각 row에 timer object discriminator를 누적한다. 이 run은 raw
function pointer별 `(count, timeout, obj_data_delta, flags, comm, stackid)`를 동시에
비교한다.

범위: live read-only capture only. Helper deploy to `/cache/bin`, BPF tracepoint attach,
row/stack map readback, post selftest. Flash/reboot, Wi-Fi action, `probe_write_user`,
cgroup attach, kernel/firmware/partition write 없음.

---

## 1. 결론

```text
decision: v2202-timer-object-histogram-captured
run: workspace/private/runs/kernel/v2202-timer-object-histogram-20260612-010308
selftest: fail=0
rows_total: 11
```

V2202는 V2201의 object read-chain을 top-row histogram으로 확장했고 live 통과했다.
결과는 V2199/V2201 해석을 더 정밀하게 갈랐다.

핵심 판단:

- `0xffffff80083108fc`는 여전히 압도적 top row지만, object invariant는
  `obj_data_delta=-16`, `timeout=18000`, `comm=a90_bpf_timer_o`로 고정된다.
- `0xffffff80083108fc`는 RCU no-CB exact authority가 아니다.
- RCU-like row는 별도로 `0xffffff80081db824`에 나타난다: `comm=rcu_preempt`,
  `timeout_min=1`, `timeout_max=1000`, `obj_data`가 RCU-object-like kernel pointer.
- 따라서 V2199의 RCU semantic 자체는 유효한 관측 축이지만, 그것을
  `0xffffff80083108fc`/slide `0x1bcebc`에 묶은 결론은 폐기한다.
- exact symbolization은 계속 금지한다. V2202는 row discrimination을 개선했지만
  raw function pointer를 stock symbol로 확정하지 않는다.

```text
object_histogram: live-pass
v2201_top_row: observer-context-dominated, not RCU
rcu_semantic_row: present as separate raw function 0xffffff80081db824
exact_symbolization: still-forbidden
next_required: source-backed raw-row matcher for top rows, not single dominant pointer naming
```

---

## 2. 산출물

| 항목 | 값 |
| --- | --- |
| Helper | `workspace/public/src/native-init/helpers/a90_bpf_timer_object_histogram.c` |
| Runner | `workspace/public/src/scripts/revalidation/native_kernel_timer_object_histogram_v2202.py` |
| Private run | `workspace/private/runs/kernel/v2202-timer-object-histogram-20260612-010308` |
| Helper SHA256 | `37d157ab5ed5fb8de1039fa731ce8a6677fdf6ba9ebe10b8e2225b05dc7a7a16` |
| Remote install path | `/cache/bin/a90_bpf_timer_object_histogram` |
| Post selftest | `fail=0` |
| Rows | `11 total / 11 printed` |

Command:

```sh
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_kernel_timer_object_histogram_v2202.py \
  --duration 8 --top 16 --dump-stacks
```

---

## 3. Top Rows

Compact row summary:

```text
rank function           count comm             last_timeout min   max   avg   data_delta fn_match exp_match read_err stackid
0    0xffffff80083108fc 1396  a90_bpf_timer_o 18000        18000 18000 18000 -16        1396     1396      0        332
1    0xffffff80081db824 152   rcu_preempt     1            1     1000  154   +281000166072 152   8         0        376
2    0xffffff80081510c4 139   kworker/7:1     95           1     3000  99    -32        139      137       0        143
3    0xffffff8008a1e884 7     init            25           10    370   118   -288       7        0         0        156
4    0xffffff800815b4d4 4     swapper/0       6            6     6     6     -40        4        4         0        228
5    0xffffff800883ed5c 4     crtc_commit:133 500          500   500   500   -32        4        0         0        426
6    0xffffff800889adf4 4     crtc_commit:133 -4294937294  same  same  same  -456       4        0         0        409
7    0xffffff8008291e3c 3     a90_bpf_timer_o 300          296   300   298   -56        3        0         0        35
8    0xffffff80085a42ac 2     kworker/2:1     570          570   570   570   -1368      2        0         0        296
9    0xffffff80093508a4 2     mmcqd/0         1000         1000  1000  1000  -960       2        1         0        254
10   0xffffff800935095c 2     mmcqd/0         1000         1000  1000  1000  -1008      2        1         0        217
```

The row value `obj_function_match=count` for every row. Object reads are valid enough to
use `obj_data_delta`, `obj_flags`, and `stackid` as discriminators. `obj_expires_match` is
not expected to match every row because `trace_timer_start()` can run before the object is
updated, and some timer objects are transient or re-armed quickly.

---

## 4. Interpretation

### Top Row: `0xffffff80083108fc`

The top row is stable across V2200/V2201/V2202:

```text
function=0xffffff80083108fc
count=1396
timeout=18000
obj_data_delta=-16
comm=a90_bpf_timer_o
stackid=332
obj_function_match=1396/1396
obj_expires_match=1396/1396
```

This is a strong object signature, but it is not the RCU no-CB signature. V2202 confirms
V2201's conclusion: this row must not be named as `do_nocb_deferred_wakeup_timer` or used
as a slide authority.

### RCU-Like Row: `0xffffff80081db824`

The RCU-like behavior appears as a separate raw function pointer:

```text
function=0xffffff80081db824
comm=rcu_preempt
count=152
last_timeout=1
timeout_min=1
timeout_max=1000
obj_data=0xffffffc178ac0000
stackid=376
```

This fits the qualitative RCU cadence/context far better than the top row. The important
correction is not "RCU was absent"; it is "RCU is not the same raw function pointer that
V2199 mapped from the dominant row".

### Worker Row: `0xffffff80081510c4`

The next high-count row is a kworker row:

```text
function=0xffffff80081510c4
comm=kworker/7:1
count=139
timeout_avg=99
obj_data_delta=-32
obj_expires_match=137/139
```

This row has a stable object signature and should be included in the next source-backed
matcher. It is not enough to resolve exact symbols by count alone.

---

## 5. What Changed Since V2201

| Question | V2201 | V2202 |
| --- | --- | --- |
| Single dominant object captured? | yes | yes |
| Multiple function rows visible? | no | **yes, 11 rows** |
| RCU semantic separable from top row? | no | **yes** |
| Top row exact owner | unresolved | unresolved, but not RCU |
| RCU raw row | not visible | **`0xffffff80081db824`** |
| Exact symbolization | false | false |

V2202 turns the earlier single-pointer ambiguity into a row classification problem. The
next step should match rows to source-backed timer setup patterns by object invariant,
not by one dominant pointer.

---

## 6. Next

Recommended next unit:

1. Build an offline source-backed row matcher for V2202 rows.
   - Input: raw function, timeout range, `comm`, `obj_data_delta`, flags, stack IPs.
   - Candidate sources: `setup_timer`, `timer_setup`, `DEFINE_TIMER`, direct `.function=`.
   - Do not require exact stock symbol names yet.
2. Rank candidates by object pattern:
   - `data == timer - N` style embedded-object signatures.
   - static `DEFINE_TIMER(..., data=0)` signatures.
   - RCU-like `data=rdp` signatures.
   - workqueue/kworker call path signatures.
3. Only after row-to-source pattern is consistent should the symbolization/slide solver
   consume these rows.
4. Keep read-only BPF only. Do not execute `probe_write_user`, cgroup attach, or any
   mutating path.
