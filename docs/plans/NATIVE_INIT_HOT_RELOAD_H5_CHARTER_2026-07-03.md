# Native Init Hot-Reload Ladder — H5 Charter + Fast-Build Feasibility (operator, 2026-07-03)

Operator-chartered next bounded unit for the **dev-velocity infra side-quest**. This file says
WHAT the loop should pursue next; `AGENTS.md` safety invariants + flash gates remain binding and
override any sub-goal here.

## Where the ladder stands (H0–H4 DONE, live-proven, all rolled back to v2321 `fail=0`)

Hot-reload = replace PID1 (`/init`) in place via `execve()` with **no reboot / no reflash**. It is the
*apply* half of the fast dev loop; it is **ephemeral** (the boot partition is unchanged; a real reboot
reverts to the flashed init).

| Rung | Cycle | Result |
| --- | --- | --- |
| **H0** | V3363 | `reload INIT-RELOAD-EXECVE <path> <sha>` replaces PID1 via execve; serial by-id never disappears (no USB re-enum, no reboot). Re-exec'd init re-ran the FULL boot path and errored on already-live subsystems (`autohud SETCRTC EACCES`, `netservice NCM start EIO`). |
| **H1** | V3364 | `A90_RELOADED` env-gated fast path in `main()` (compiled `v724/90_main.inc.c`): on reload, skip splash + skip re-init of already-live services. Clean (0 SETCRTC / 0 NCM errors) + **2.18 s** reload→shell. Normal boot byte-identical (all guards `if (!a90_reloaded)`). |
| **H2** | V3365 | A **genuinely changed** init ELF reloaded → version flips `0.11.125 → 0.11.126` with no reboot. Proves changed code takes effect across reload. Residual: `BOOT ERR storage E16`, tcpctl/autohud stopped. |
| **H3** | V3366 | Storage residual fixed — reloaded init adopts the existing rw SD mount (no `E16` fallback). Residual: autohud/tcpctl still stopped. |
| **H4** | V3367 | `tcpctl-adopt` — reload restores the tcpctl control plane (NCM reused, USB gadget reconfigure skipped, existing listener adopted). `tcpctl=running`, host `ping`→`pong`, `selftest fail=0`. |

**After H4 the reloaded init has: no reboot + changed code + clean SD storage + serial + tcpctl control
plane.** The one remaining gap is the **display/HUD (autohud) + rshell**, deliberately skipped since H1
because the re-exec'd init's `autohud SETCRTC` hit `EACCES` (the pre-reload PID1 held DRM master).

## H5 — full-service refresh across reload (autohud/HUD + rshell)

**Goal:** make a hot-reloaded init a *full* service refresh — restore the on-panel HUD (autohud) and
rshell after `reload`, WITHOUT a reboot and WITHOUT crossing the display bright-line.

**Technical approach (bounded — pick the safest that works; the panel + DRM/KMS pipe are ALREADY UP,
held by the pre-reload init, so this is a DRM-MASTER HANDOFF, NOT a panel bring-up):**
- **Option A (adopt — mirror H4's tcpctl-adopt):** the reloaded init *adopts* the existing KMS/CRTC/mode
  state and resumes drawing to `/dev/dri/card0` instead of running a fresh `SETCRTC`/modeset. An
  "autohud-adopt" path analogous to `tcpctl-adopt`.
- **Option B (master drop/reacquire):** pre-reload init `DROP_MASTER` before `execve` (or inherit the
  card fd) so the new init `SET_MASTER` + resumes the existing mode without re-running modeset.
- **rshell:** restart the listener (cheap, no display) — likely straightforward like tcpctl-adopt.

**Hard guardrails (bright-line — from `AGENTS.md`/memory):**
- **NO panel re-init from scratch** (no DSI panel bring-up), **NO PMIC/regulator/GDSC/backlight/GPIO
  power writes.** H5 is DRM-master handoff + KMS-state re-adopt ONLY, on an **already-lit** panel.
- If restoring the HUD requires ANY panel re-init or power write → **STOP, out of bounds; do NOT force
  it.**
- Standard flash gates stay ON: v2321 rollback precondition, pinned + readback SHA, post-flash health,
  auto-rollback to v2321, **fails-twice-on-the-same-approach → STOP and write a report**.

**Acceptance (either outcome closes the epic):**
- **PASS:** post-reload `autohud: running` (clean adopt) with the HUD visibly updating on the panel
  (operator eye-confirm or a device-side liveness marker), `rshell` running, `selftest fail=0`, rollback
  to v2321 `fail=0`.
- **CLEAN-CLOSE (equally acceptable, NOT a failure):** if DRM-master handoff cannot restore the HUD
  within the bright-line (i.e. it would need a panel re-init), record **"hot-reload is control-plane-only
  by design (serial + tcpctl); HUD/display refresh requires a real flash/reboot"** and CLOSE the
  hot-reload epic at H4. The tool is already fully useful for init-code dev iteration without the HUD.

**Deliverable:** V3368 source-build (`0.11.129`, `v3368-hot-reload-autohud`) + live H5 (PASS or
clean-close record), then rollback to clean v2321. Report to `docs/reports/`.

## Fast-build — proven-feasible drop-in (operator host-only, 2026-07-03) — NOT part of H5

Measured host-only on the real `build_init` sources (`aarch64-linux-gnu-gcc -Os`, 59 TUs, 22 cores):

- Current build compiles all 59 TUs in **one serial `gcc` call = 12.78 s** (22 cores idle, no `.o`
  caching).
- **Splitting into per-TU `gcc -c` in parallel + link is BYTE-IDENTICAL** to the one-shot build (same
  stripped SHA256 `9dd782d4…`, LTO not used → TU split changes nothing) → **zero behavioral risk,
  pure drop-in**. Wall time **12.78 → 5.03 s** (2.5×; bounded by the single giant main TU `init_v724.c`
  ≈ 4.5–5 s).
- **Incremental (`.o` cache by mtime):** change one standalone `a90_*.c` module → recompile only it +
  relink = **0.11 s**. Change the main TU (`init_v724.c`/its `.inc.c` include chain) → **4.47 s** (single
  giant TU is the hard floor; not broken without a `.inc.c` split refactor — out of scope).

Combined with hot-reload the real inner loop is **~5 s (module change)** / **~10 s (main change)** vs the
old ~2–3 min flash cycle = **12–30×**. Productizing fast-build = wire parallel + `.o` caching into
`build_init` (host-only, no device); it is a **separate infra follow-up**, do NOT bundle it into H5.

## Not in scope

Self-write-as-default, prefix-only self-write, non-v2321 self-flash candidates, raw `dd`/fastboot,
non-boot partitions — all still gated (see `FAST_SELF_DD_BOOT_FLASH_TOOL_DESIGN_2026-07-02.md`). TWRP
stays the default recovery path.
