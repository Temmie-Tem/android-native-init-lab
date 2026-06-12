# Goal: autonomous native-init forward loop (Codex)

Drive the A90 native-init project forward one **bounded V-iteration at a time** using
the proven cycle below. This file says WHAT to pursue; **`AGENTS.md` says HOW — its
safety invariants and flash gates are binding and override any sub-goal.**

> Running mode note: this loop is intended to run unattended (incl. Codex bypass).
> Because it can flash a real device with no human in the loop, every device step MUST
> obey the flash gates in `AGENTS.md` (rollback precondition, post-flash health check,
> auto-rollback, no cascading bad flashes). The operator accepts that a boot failure may
> need a manual TWRP/download-mode recovery in the morning — **but that acceptance covers
> the boot partition ONLY.** Forbidden partitions (efs/sec_efs/modem/RPMB/keymaster/
> vbmeta/bootloader) are NOT TWRP-recoverable = permanent brick, and remain absolutely
> off-limits regardless. When in doubt, STOP and report — never guess.

## North star — priority-ordered tracks (T1 → T2 → T3)

Pursue the **highest tier that still has a meaningful, safely-actionable next step**.
Drop to the next tier only when the current one is *saturated* or *meaningless* (criteria
below). Re-evaluate each iteration; you may climb back up if new work appears.

**T1 (primary) — analyzer / harness regression test suite (host-only, NO flash).**
This is the original goal and is barely started: only `path_safety` of the 12
`workspace/public/src/harness/a90harness/` modules has tests, and the 124 revalidation
scripts are untested. Each iteration, pick **one** untested unit — an `a90harness` module
(`bundle`/`device`/`evidence`/`failure`/`gate`/`module`/`observer`/`runner`/…) or a
cohesive cluster of revalidation-script logic — and write representative + edge/reject
tests under `tests/` using the `tests/_loader.py` import helpers. Validate with
`python3 -m unittest discover -s tests -p 'test_*.py'` and `py_compile` (see `tests/GOAL.md`
for the runner contract + coverage checklist). This track is **fully host-only**: no device,
no creds, no flash, no approval gates — the ideal unattended overnight work. Done-signal:
the unit has accept + reject/edge tests passing; coverage delta recorded. Stay here until
the meaningful units are genuinely covered.

**T2 (fallback) — native-init / WLAN baseline improvement (device; flash authorized).**
When T1 is saturated, or when you have a concrete device-validatable improvement, advance
the native-init baseline beyond `0.9.272`. Candidates: the parked **WLAN structural epic**
(a supervised long-lived `wpa_supplicant` + event subscription — ctrl-iface events +
netlink — replacing spawn-per-connect polling), or **`a90_wifi.c` (~3156 lines)**
modularization / dead-code reduction. Do DESIGN → IMPLEMENT → STATIC VALIDATE host-side
autonomously; the DEVICE step (flash + validate) **is authorized** and MUST obey the
`AGENTS.md` flash gates.
- **Validation ceiling — Wi-Fi creds are ABSENT.** `wifi connect`/`dhcp`/`ping` (the N=3
  both-band functional check) cannot run. Device validation = boot + `version` / `status`
  / `selftest fail=0` + non-creds surfaces only (`wifi status`, `wifi scan`). Do NOT block
  waiting for creds; record full Wi-Fi functional validation as a **parked human
  checkpoint** in the report. Do NOT promote a new safety/rollback baseline on boot-health
  alone — **`v2237` stays the rollback target.**

**T3 (fallback) — self-directed (host-only preferred).**
Build reproducibility / tooling hardening (e.g. mkbootimg round-trip verification,
build-script robustness), or another concrete frontier unit from the state docs. Prefer
host-only, safe units.

**Drop-tier criteria** — leave a tier when its meaningful units are genuinely covered/done,
it needs hardware/data not available (e.g. creds for full Wi-Fi validation), it is blocked
with no safe next step, or it would only re-confirm established facts (diminishing returns).
**When you change tier, record the trigger** in that iteration's report.

## Read at the START of every iteration

- **this `GOAL.md`** — re-read it every iteration; the contract may be updated mid-run,
  so never rely on a cached copy from session start,
- `AGENTS.md` (binding safety/flash gates),
- `CLAUDE.md` (current state + safety),
- `tests/GOAL.md` (the host-only harness sub-goal detail) when on T1,
- the newest `docs/reports/NATIVE_INIT_*.md` (a few),
- `git log --oneline -15`.

## The cycle (repeat)

1. **STATE** — read the docs above; identify current baseline, last result, open thread.
2. **SELECT** — choose the single most appropriate next sub-goal: small, bounded, one
   V-iteration on the current frontier. Assign the next run/build identity per
   `docs/operations/VERSIONING_POLICY.md` (keep run ID / init version / build tag / SHA
   axes separate).
3. **DESIGN** — short plan; web research allowed when it helps; ground claims in source or
   docs.
4. **IMPLEMENT** — focused change in canonical `workspace/public/src/...` / `tests/` paths
   only.
5. **STATIC VALIDATE** — `py_compile` + `python3 -m unittest discover -s tests -p
   'test_*.py'` for touched Python; cross-compile touched C with `aarch64-linux-gnu-gcc`
   and verify with `file`; `git diff --check`.
6. **DEVICE** (only if the sub-goal needs a new boot artifact) — build via the checked
   build script, record SHA256, flash via `native_init_flash.py`, reboot, run the
   serial-bridge health check (`a90ctl version` / `status` / `selftest`), then the bounded
   non-creds validation this sub-goal calls for. On any failure → auto-rollback per
   `AGENTS.md`. T1 sub-goals skip this step entirely.
7. **REPORT** — write `docs/reports/NATIVE_INIT_VNNNN_<purpose>_<date>.md` (or a `tests/`
   coverage note for T1): redacted, metadata-only, no secrets/binaries.
8. **COMMIT** — one sub-goal per commit; scoped `git add` of the touched paths + the
   report; never `-A`. Message per project convention; end with the Co-Authored-By line.
9. **REPEAT** → back to STATE.

## Stop conditions

- Device unreachable after an auto-rollback → STOP, leave an incident report.
- The same sub-goal fails twice → STOP or shelve it and move on; do NOT retry-loop.
- No sub-goal is safely actionable without the operator → STOP with a note (but T1 is
  almost always safely actionable, so this should be rare).

## Anti-churn guard (low-value *success* streaks)

The "fails twice → stop" rule does not catch *successful* but low-information work. Guard:

- If the last **3+ iterations** were host-only metadata / inventory / runner / cleanup /
  audit work with **no new tested behavior and no device validation**, treat that theme as
  **exhausted** and force a tier re-evaluation toward substantive work.
- A new test file that actually exercises previously-untested behavior is substantive (not
  churn). Mechanical sweeps with no new assertions are churn — **batch** them into one
  iteration, never one-V-per-item.
- Never let one theme justify its own next iteration ("previous left a backlog" is not a
  reason to continue past the streak limit).

## Out of scope / do not reopen

- **Kernel-security recon and kernel-observation phases are CLOSED.** See
  `docs/reports/NATIVE_INIT_KERNEL_SECURITY_RECON_PHASE_CLOSE_CHECKPOINT_2026-06-13.md`.
  Do NOT re-triage FastRPC/Binder/KGSL, build trigger/exploit/UAF helpers, attempt any
  memory-corruption trigger, do heap spray/reclaim, or flash `slub_debug`/debug-cmdline
  images. No exploit development.
- **KGSL `/dev/kgsl-3d0` open-block** is a human-gated investigation, NOT a loop unit (live
  open hangs). Leave it.
- **No doc / metadata / inventory cleanup as a track** (anti-churn trap).
- **Never reopen** external SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO paths for internal `wlan0`.
