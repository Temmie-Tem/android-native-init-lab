# Goal: autonomous native-init frontier loop (Codex)

Drive the A90 native-init project forward one **bounded V-iteration at a time** using
the proven cycle below. This file says WHAT to pursue; **`AGENTS.md` says HOW — its
safety invariants and flash gates are binding and override any sub-goal.**

> Running mode note: this loop is intended to run unattended (incl. Codex bypass).
> Because it can flash a real device with no human in the loop, every device step MUST
> obey the flash gates in `AGENTS.md` (rollback precondition, post-flash health check,
> auto-rollback, no cascading bad flashes). When in doubt, STOP and report — never guess.

## North star — priority-ordered tracks (T1 → T2 → T3)

Pursue the **highest tier that still has a meaningful, safely-actionable next step**.
Drop to the next tier only when the current one is *impossible* or *meaningless* (criteria
below). Re-evaluate the tier each iteration; you may climb back up if new evidence reopens
a higher tier.

**T1 (primary) — kernel observation.** Extend what is *observable* on the locked RKP
kernel via sanctioned read paths: the V2192–V2221 line — BPF/perf read probes, the slide
solver / exact symbolization (resume at the V2214 perf-event register-frame sampler:
raw `ctx->pc` kernel-text anchor to collapse the V2197 four-candidate slide ambiguity),
uprobe/tracepoint observation, and mapping the observe/control envelope. Mostly read-only
(`/cache/bin` helper + bounded attach) — usually **no flash needed**, lower risk.

**T2 (fallback) — WLAN native-init.** Advance the WLAN bring-up / boot baseline (latest
promoted = **V2237 supplicant terminate-poll**): e.g. connect robustness, network detail
surface, or bounded lifecycle/soak evidence. Device/flash steps obey the `AGENTS.md`
flash gates.

**T3 (fallback) — self-directed.** When T1 and T2 are both exhausted/meaningless, pick the
next best step anywhere on the current frontier from the state docs.

**Drop-tier criteria** — leave a tier when the next step would need a kernel-write
primitive / RKP bypass / exploit (out of scope), needs hardware/data not available, is
blocked with no new independent oracle after exhausting non-conflicting evidence, or only
re-confirms already-established facts (diminishing returns). **When you change tier, record
the trigger** (what made the higher tier impossible/meaningless) in that iteration's report
before proceeding.

Read at the START of every iteration (then apply the tier policy above):
- `CLAUDE.md` (current state + safety),
- `docs/overview/PROJECT_STATUS.md`,
- the newest `docs/reports/NATIVE_INIT_V*.md` (a few; include the latest kernel-track
  V21xx reports when on T1),
- `git log --oneline -15`.

## The cycle (repeat)

1. **STATE** — read the docs above; identify current baseline, last result, open thread.
2. **SELECT** — choose the single most appropriate next sub-goal: small, bounded, one
   V-iteration on the current frontier. Assign the next run/build identity per
   `docs/operations/VERSIONING_POLICY.md` (keep run ID / init version / build tag / SHA
   axes separate).
3. **DESIGN** — short plan; web research allowed when it helps; ground claims in kernel
   source (`tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`) or docs.
4. **IMPLEMENT** — focused change in canonical `workspace/public/src/...` paths only.
5. **STATIC VALIDATE** — `py_compile` touched Python; cross-compile touched C with
   `aarch64-linux-gnu-gcc` and verify with `file`; `git diff --check`.
6. **DEVICE** (only if the sub-goal needs a new boot artifact) — build via the checked
   build script, record SHA256, flash via `native_init_flash.py`, reboot, run the
   serial-bridge health check (`a90ctl version` / `status` / `selftest`), then the bounded
   functional validation this sub-goal calls for. On any failure → auto-rollback per
   `AGENTS.md`.
7. **REPORT** — write `docs/reports/NATIVE_INIT_VNNNN_<purpose>_<date>.md`: redacted,
   metadata-only, no secrets/binaries.
8. **COMMIT** — one sub-goal per commit; scoped `git add` of the touched public paths +
   the report; never `-A`. Message per project convention.
9. **REPEAT** → back to STATE.

## Stop conditions

- Device unreachable after an auto-rollback → STOP, leave an incident report.
- The same sub-goal fails twice → STOP or shelve it and move on; do NOT retry-loop.
- No sub-goal is safely actionable without the operator → STOP with a note.

## Sub-goal seeds (optional; the loop may pick others from state)

**T1 — kernel observation (try first):**
- After V2249 live: the helper-started tail sampler hook works, but V2249 is
  not a baseline promotion candidate. The rollbackable test boot reached
  `wlan0-ready`, emitted `tail_perf_regs_codeword_sampler.started=1`, finished
  `after_fwclass_feeder` with `output_exists=1`, captured `668` perf samples,
  and the V2216 parser accepted an exact per-boot codeword slide with `512/512`
  PC matches and `507/507` LR/LR-4 matches. The V2247 post-FWREADY whitelist
  scorer returned `0/512` target hits, but this is not yet a path-negative:
  the helper log had `samples occupied=668 printed=512 capacity=1024`, so 156
  occupied ring entries were not printed. Next live unit (V2250): keep the same
  V2237 route and V2249 hook placement, set the tail sampler `print_limit` to
  `1024` (or otherwise emit every occupied ring entry), re-score with V2247,
  then only if hits remain zero treat CPU-clock sampling as missing the narrow
  firmware_class/qcacld tail and switch to a more target-specific observable.
- After V2248: do not try to run the V2216 perf regs/codeword sampler only
  after native boot if the goal is the post-FWREADY qcacld/HDD tail. The source
  route calls `append_post_fw_ready_boot_wlan_trigger(stdout_buf)`, holds 8 s,
  then runs post-trigger samplers and
  `append_qcacld_firmware_class_fallback_feeder(..., "after_boot_wlan_trigger",
  30000)` inside `a90_android_execns_probe`; host-side post-boot attachment can
  miss the tail. The next live unit (V2249) should package or embed the V2216
  exact-slide perf regs/codeword sampler, launch it from a compile-gated helper
  child before the `boot_wlan` write, keep it alive at least 45 s through the
  firmware_class feeder, store output under
  `/cache/native-init-v2249-tail-perf-regs-codeword.log`, then score with
  `a90_kernel_v2247_tail_pc_lr_scorer.py`.
- After V2247: tail PC/LR scoring infrastructure exists.
  `a90_kernel_v2247_tail_pc_lr_scorer.py` consumes a per-boot exact-slide
  perf regs/codeword summary plus the V2246 whitelist and scores `ctx_pc`,
  `ctx_lr`, and `ctx_lr-4`; the V2216 generic CPU-clock negative control had
  exact slide `0x84ef4`, `62/62` PC codeword matches, and `0` tail hits. The
  next meaningful live T1 unit is a tail-window perf regs/codeword capture
  around the post-FWREADY firmware_class/qcacld-HDD path, then run the V2247
  scorer on that capture.
- After V2246: the post-FWREADY tail live-sampling whitelist is source-backed:
  `_request_firmware`, `request_firmware`, `qdf_file_read`, `qdf_ini_parse`,
  `cfg_parse`, `hdd_context_create`, and `wlan_hdd_pld_probe` all map to stock
  kallsyms plus source definitions. Do not reuse a numeric slide across boots or
  treat next-symbol deltas as function sizes on the RKP/CFP/JOPP kernel.
- After V2245: the V2233 `wlan0-ready` delta is the downstream post-FWREADY
  tail, not WLFW/QMI order: V2229/V2231 have `tail_absent`, while V2233 executes
  `boot_wlan`, feeds `wlan/qca_cld/WCNSS_qcom_cfg.ini` through firmware_class,
  catches the qcacld/HDD `_request_firmware -> request_firmware -> qdf_file_read
  -> qdf_ini_parse -> cfg_parse -> hdd_context_create -> wlan_hdd_pld_probe`
  worker stack, then reaches ICNSS register/cfg/mode/ini completion and `wlan0`.
  Do not re-run PerMgr/WLFW/QMI ordering.
- After V2244: V2229/V2231/V2233 have identical semantic WLFW/QMI edge sets:
  nine edges per run, four strong and five marker edges, with no weak/missing
  semantic rows. Do not spend another T1 iteration re-proving WLFW/QMI order
  unless new evidence contradicts this.
- After V2243: helper-owned `a90*` event interpretation now has a public
  semantic layer. Use
  `workspace/private/runs/kernel/v2243-user-uprobe-semantic-classifier-20260612-113113/summary.json`
  for event role / instruction class / alignment / confidence. Key events have
  no low-confidence rows; non-key `needs_manual_context` rows must be rechecked
  against private context before supporting strong conclusions.
- After V2242: all checked `a90*` helper static offsets map to executable user-ELF
  `LOAD` segments. Treat `group` as the log surface and `object` as the ELF identity:
  `periph_*` offsets belong to `libperipheral_client.so` (`a90periph`), not
  `cnss-daemon`. Use
  `workspace/private/runs/kernel/v2242-user-elf-offset-context-20260612-112444/private_instruction_context.json`
  for bounded private instruction-context lookups; do not publish raw
  bytes/disassembly.
- After V2241: `a90*` user-space code-path identity is `runtime_probe_ip =
  per-run_load_bias + helper_static_uprobe_offset`. Parse offsets from
  `a90_android_execns_probe.c`, require one page-aligned load bias per `(run, object)`,
  and use stripped user-ELF disassembly around those offsets if finer instruction
  context is needed.
- After V2240: V2216/V2217 exact-slide symbolization is valid for kernel canonical
  PC/LR samples and kernel function-pointer anchors only. Do not apply the kernel slide
  to `a90cnss`/`a90libqmi`/`a90pmsrv` user-space trace-uprobe `__probe_ip`; use event
  names plus stable relative user-space offset signatures instead. If finer `a90*`
  names are needed, build a user-ELF ASLR/base mapper rather than extending the kernel
  System.map slide solver.
- After V2239: use `docs/reports/NATIVE_INIT_V2239_SCALAR_UPROBE_TIMELINE_CONTRACT_2026-06-12.md`
  as the merge contract before new boot-window observers. Do not retry
  cfg80211/PIL/QRTR static-tracepoint object-chain dereference from trace records; those
  records are scalarized. Use static tracepoints for scalar lifecycle correlation,
  helper-owned `a90*` tracefs records for WLFW/QMI edge sequencing, and exact-slide
  live-register sampling for code-path identity.

**T2 — WLAN native-init (if T1 blocked):**
- Network detail surface + remaining test-script cleanup (CLAUDE.md "Active work").

**Any tier — safe filler (no device):**
- **Host-only regression harness** — `tests/GOAL.md`. Ideal between device iterations.
