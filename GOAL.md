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
- Resume the slide solver: build/run the **V2214 perf-event register-frame sampler** —
  per-CPU `PERF_COUNT_SW_CPU_CLOCK`, read raw `ctx->pc` (off 256) + `ctx->regs[30]` live
  LR (off 240) as un-ROPP'd kernel-text anchors; `exclude_user=1 exclude_idle=1`,
  ~1 ms period. Harvest the kernel `ctx->pc` set and solve the unique KASLR slide
  (collapse the V2197 four-candidate ambiguity). Read-only BPF; no flash.
- After V2238: do not retry cfg80211/PIL/QRTR static-tracepoint object-chain
  dereference from trace records; those records are scalarized. Use static tracepoints
  for scalar lifecycle correlation, helper-owned `a90*` tracefs records for WLFW/QMI
  edge sequencing, and exact-slide live-register sampling for code-path identity.

**T2 — WLAN native-init (if T1 blocked):**
- Network detail surface + remaining test-script cleanup (CLAUDE.md "Active work").

**Any tier — safe filler (no device):**
- **Host-only regression harness** — `tests/GOAL.md`. Ideal between device iterations.
