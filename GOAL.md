# Goal: autonomous native-init frontier loop (Codex)

Drive the A90 native-init project forward one **bounded V-iteration at a time** using
the proven cycle below. This file says WHAT to pursue; **`AGENTS.md` says HOW — its
safety invariants and flash gates are binding and override any sub-goal.**

> Running mode note: this loop is intended to run unattended (incl. Codex bypass).
> Because it can flash a real device with no human in the loop, every device step MUST
> obey the flash gates in `AGENTS.md` (rollback precondition, post-flash health check,
> auto-rollback, no cascading bad flashes). When in doubt, STOP and report — never guess.

## North star

Advance the project's **current** frontier as recorded in the living state docs — it is
deliberately not hardcoded here. Each iteration re-reads state and picks the next best step.

Read at the START of every iteration:
- `CLAUDE.md` (current state + safety),
- `docs/overview/PROJECT_STATUS.md`,
- the newest `docs/reports/NATIVE_INIT_V*.md` (a few),
- `git log --oneline -15`.

Frontier at setup time (confirm from the docs, do not assume): native-init WLAN bring-up /
boot baseline; latest promoted baseline = **V2236 strict Wi-Fi connect**.

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

- **V2236 strict-connect terminate-race**: replace the blind 500 ms post-`TERMINATE`
  sleep with a bounded poll until the old supplicant is gone + SIGKILL escalation
  (see the connect path in `workspace/public/src/native-init/a90_wifi.c`).
- Network detail UI + remaining test-script cleanup (per CLAUDE.md "Active work").
- **Host-only regression harness** — `tests/GOAL.md`. No device; ideal safe filler
  between device iterations.
