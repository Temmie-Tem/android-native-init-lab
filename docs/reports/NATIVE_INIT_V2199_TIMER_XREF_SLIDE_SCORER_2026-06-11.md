# Native Init V2199 Timer Xref Slide Scorer (2026-06-11)

대상: A90 native boot `0.9.261 (v2189-security-p0-stage-fix)` stock kernel
symbolization artifacts.

목적: V2198의 `timer-magic + callback-name` 후보를 source xref로 재점수화한다.
핵심은 “이 함수명이 timer 콜백 후보인가”가 아니라 “실제로 `timer_list` API에
연결되고, 그 timer object가 어떤 cadence로 arm 되는가”다.

범위: host-only parser 구현·실행 + 기존 V2198 result 재분석. 새 live device 명령,
flash, reboot, Wi-Fi scan/connect, credential, DHCP/routes, external ping,
`probe_write_user`, cgroup attach 없음.

---

## 1. 결론

V2199는 V2198의 broad callback whitelist보다 훨씬 강한 semantic lead를 만들었다.
하지만 exact slide proof는 아직 아니다.

```text
decision: v2199-provisional-xref-lead-not-authority
reason: source xref scoring produced a lead, but not enough margin for exact symbolization
top_slide: 0x1bcebc
second_slide: 0x1bceb8
```

핵심 판단:

- Dominant timer `0xffffff80083108fc`는 source xref상
  `do_nocb_deferred_wakeup_timer` 계열이 가장 강하다.
- 근거는 `setup_timer(&rdp->nocb_timer, do_nocb_deferred_wakeup_timer, ...)`와
  `mod_timer(&rdp->nocb_timer, jiffies + 1)` 조합이다.
- 즉 V2198의 `key_gc_timer_func` 선두는 source cadence 관점에서 밀렸다.
- 그러나 `0x1bcebc`와 `0x1bceb8`는 같은 callback의 `+0/+4` pair라 margin이 작다.
- 따라서 `exact_symbolization=false` 유지. 다음 proof는 same-boot live caller/stack
  cross-confirm 또는 ROPP/JOPP stack decode가 필요하다.

---

## 2. 산출물

| 항목 | 값 |
| --- | --- |
| Analyzer | `workspace/public/src/scripts/revalidation/a90_kernel_v2199_timer_xref_scorer.py` |
| Input V2198 JSON | `workspace/private/runs/kernel/v2198-jopp-ropp-classifier/result.json` |
| Private JSON | `workspace/private/runs/kernel/v2199-timer-xref-scorer/result.json` |
| Private summary | `workspace/private/runs/kernel/v2199-timer-xref-scorer/result.md` |
| Source input | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source` |

Command:

```sh
python3 workspace/public/src/scripts/revalidation/a90_kernel_v2199_timer_xref_scorer.py \
  --v2198-json workspace/private/runs/kernel/v2198-jopp-ropp-classifier/result.json \
  --source-root tmp/wifi/v766-icnss-qcacld-patch-apply-build/source \
  --out-json workspace/private/runs/kernel/v2199-timer-xref-scorer/result.json \
  --out-md workspace/private/runs/kernel/v2199-timer-xref-scorer/result.md
```

Runtime on host:

```text
real: 0m53.830s
source_files_scanned: 44202
callback_xref_count: 12
```

The scanner excludes `Documentation`, `samples`, `tools`, `usr`, and non-arm64
`arch/*` trees to reduce false positives from non-target source.

---

## 3. Scoring Model

V2199 takes the V2198 `top_timer_candidates` set and adds source-level xref scoring.

Positive evidence:

- callback passed to `setup_timer(...)`, `timer_setup(...)`, or `DEFINE_TIMER(...)`.
- timer object is a struct field, not just an isolated static symbol.
- timer object has `mod_timer(...)` / `add_timer(...)` arm references.
- arm cadence looks frequent, especially `jiffies + 1`.
- callback has a definition and appears in RKP address-taken lists.

Negative or weak evidence:

- callback name exists but no timer API xref.
- magic target maps to non-callback symbols.
- low cadence objects such as daily/five-minute ext4 report timers.
- same callback `+0/+4` pairs remain unresolved by semantic xref alone.

This is intentionally a ranking model, not a proof model.

---

## 4. Top Candidates

V2199 ranking:

```text
0x1bcebc: final=118330, dominant=340
0x1bceb8: final=111360, dominant=320
0xfabf4:  final=67860,  dominant=195
0x1cd5bc: final=60910,  dominant=175
0xfabf0:  final=60900,  dominant=175
```

Top candidate detail:

```text
slide: 0x1bcebc
timer0: 0xffffff80083108fc count=348
symbol: do_nocb_deferred_wakeup_timer+0x0
api: setup_timer
timer leaf: nocb_timer
interval: jiffies_plus_1
notes:
  explicit runtime timer setup
  struct-field timer object
  timer object has arm/delete references
  best interval jiffies_plus_1 score 140
  RCU no-CB per-cpu timer object
```

Closest candidate:

```text
slide: 0x1bceb8
timer0: 0xffffff80083108fc count=348
symbol: do_nocb_deferred_wakeup_timer+0x4
interval: jiffies_plus_1
```

Interpretation:

- The semantic target is likely the RCU no-CB deferred wakeup timer path.
- The remaining ambiguity is mostly entry offset (`+0` vs `+4`), not a completely
  different subsystem.
- This does not yet authorize exact stack symbol names. It only changes the leading
  slide hypothesis.

---

## 5. What Changed Since V2198

| Question | V2198 | V2199 |
| --- | --- | --- |
| Is JOPP magic sufficient? | no | no |
| Is callback-name whitelist enough? | no | no |
| Does source cadence improve the lead? | not implemented | **yes** |
| Leading semantic target | `key_gc_timer_func` by broad whitelist | **`do_nocb_deferred_wakeup_timer`** |
| Slide uniqueness | no | no |
| Exact symbolization | false | false |

The important correction is that `key_gc_timer_func` is a real timer callback, but its
source cadence is weak for the dominant V2196 timer_start frequency. The RCU no-CB
`jiffies + 1` timer is a better semantic fit.

---

## 6. Next

Recommended next unit:

1. Same-boot read-only capture of `timer_start` with `function`, `expires`, `current->comm`,
   and `stackid` for the dominant pointer. This directly asks whether the runtime caller is
   the RCU no-CB path.
2. Keep BPF read-only. Do not execute `probe_write_user`, cgroup attach, or any mutation.
3. If live capture confirms the RCU no-CB caller, use it as a slide cross-check; otherwise
   keep `0x1bcebc` as a semantic lead only.
4. Only move WLAN/cfg80211 object-chain symbolization to exact labels after the slide is
   cross-confirmed. Until then, every resolved symbol must remain `provisional`.

---

## 7. V2200 Follow-Up

V2200 ran the recommended same-boot read-only `timer:timer_start` context capture.
Result: `0xffffff80083108fc` was still the dominant function pointer, but all `1396`
filtered events had `expires - now = 18000` (`timeout_eq1=0`, `timeout_eq18000=1396`).

This contradicts the `jiffies + 1` cadence that made `do_nocb_deferred_wakeup_timer`
attractive in V2199. The function-name lead remains useful, but `0x1bcebc` / `0x1bceb8`
are not exact slide authorities. Keep `exact_symbolization=false` and label downstream
symbols as provisional until V2201 or another independent discriminator resolves the
owner/cadence mismatch.
