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

### Active epic — Internal audio (ADSP/Q6) feasibility research

**Prior epics CLOSED:** WLAN events at V2312; USB gadget control **layer ①** at V2315; USB
**device identity** at V2316–V2321 (real serial redacted to `A90NATIVE001`; host-visible
descriptor `A90-LNX` / `A90 Linux ARM64` via fixed-length kernel **rodata** patches); **USB
named multi-LUN mass-storage identity** at V2322 (`0.9.286`, U-A single named LUN) and V2323
(`0.9.287`, U-B `lun.0`+`lun.1` → host SCSI models `A90-INTERNAL`/`A90-SD`, FAT labels
`A90INTERNAL`/`A90SD`). Rollback target `v2321` (`0.9.285`); `v2237`/`v48` remain deeper
fallbacks. USB U-C (real SD / internal read-only exposure) stays **DEFERRED**. ②adb-over-ffs and
③HID/BadUSB remain separate follow-on USB epics — **do not start them here.**

**Active epic: determine whether the internal speaker/headphone audio path can be driven under
native init, and — only if a safe path exists — produce sound.** This is a *research / feasibility*
epic: like the kernel-security recon phase, **"NON-VIABLE under native init" is an acceptable,
valuable outcome** if that is where the evidence lands. Do not force a result.

**Grounded starting facts (from the 2026-06-14 session research; re-verify, do not trust blindly):**
- **HW:** codec `wcd934x`/`wcd9360` on **SLIMbus** + **4× `wsa881x`** smart amps on **SoundWire**;
  *all* audio routes through the **ADSP (Q6 DSP)** — you cannot poke the speaker directly.
- **Two Linux audio architectures:** (a) **downstream techpack** (proprietary `msm-pcm-q6`/APRv2 +
  ACDB + Qualcomm audio HAL — what *this* device actually uses); (b) **mainline** `q6afe`/`q6asm`/
  `q6routing` + mainline `wcd934x`/`wsa881x` (postmarketOS). **(b) needs a mainline kernel we do
  NOT run → swapping the kernel is out of scope + brick-risky → (b) is REJECTED up front.**
- **Our stock 4.14 kernel (verified):** the ADSP **PIL/remoteproc node is present** in DTS
  (`qcom,firmware-name = "adsp"`, `sm8150.dtsi:1718`), but `sound/`, `techpack/audio`, the APR bus,
  and all q6 ASoC drivers are **stripped from the open-source drop**. We boot the **stock kernel
  image unchanged**, so its built-in/vendor audio drivers + ADSP firmware + ACDB are **ABI-matched**
  → the only realistic path is **(a): reuse stock vendor blobs**, not a rebuild.
- **The two real walls:** ① does native init ever **bring the ADSP up** (stock Android init does the
  PIL load; we do not)? ② **Qualcomm audio HAL + ACDB calibration**. Lighter hope to test:
  **tinyalsa + tinymix(`mixer_paths*.xml`) direct** on the ASoC card, *bypassing* the full HAL.
- **Out of scope inside this epic:** modem/**call** audio and the `q6voice` daemon (separate, harder,
  and touches the CP/modem boundary) — **speaker/headphone *playback only*.**

Staged units, one V-iteration each. **AUD-0 and AUD-1 are host-only and loop-safe.** **AUD-2 and
beyond touch the ADSP / device audio — a NEW device-risk domain — so they are HARD operator-gated:
the loop must STOP and request explicit operator go before any on-device ADSP activation or audio
write.** Even when gated-in, device steps stay inside the boot-partition-only + recoverable envelope;
ADSP subsystem-restart is recoverable, but forbidden-partition rules remain absolute.

- **AUD-0 — host-only inventory & decision basis.** From the stock AP/`vendor` image (extract
  host-side; treat as proprietary, keep under `workspace/private/`, never commit), enumerate: audio
  `.ko` modules, the **`adsp` firmware** image, **ACDB** `.acdb` files, `mixer_paths*.xml`,
  `audio_platform_info*.xml`, and the audio-HAL libs. Decide: are the audio drivers **built into the
  boot kernel image** we already flash, or separate vendor `.ko`? Map the exact bring-up chain.
  **Deliverable:** a feasibility report answering *"is a tinyalsa-direct (no full HAL) path plausible,
  or is the full Qualcomm HAL+binder stack mandatory?"* If mandatory → recommend **CLOSE as
  NON-VIABLE** (document, like the kernel-security recon close) and stop the epic.
- **AUD-1 — host-only ADSP/remoteproc path analysis.** Confirm the remoteproc/PIL node, the firmware
  search path, the minimal driver load order, and *how* (in principle) a PID-1 native init would
  trigger the ADSP load via sysfs `remoteproc` state. No device action. **Deliverable:** the precise,
  reviewable device-step plan that AUD-2 would run.
- **AUD-2 — DEVICE, OPERATOR-GATED — ADSP liveness probe (no audio yet).** Only after explicit
  operator go: under native init, read `remoteproc` state, attempt the (recoverable) ADSP subsystem
  load, and observe whether an ALSA card / `/dev/snd` materializes. Success = "DSP comes up + card
  appears," nothing more.
- **AUD-3 — DEVICE, OPERATOR-GATED — first tinyalsa playback attempt.** Only after AUD-2 passes and a
  fresh operator go: load the speaker route via `tinymix`/`mixer_paths.xml` and push a test PCM with
  `tinyplay`. First actual sound test.

**Latest audio route-delta planning state (V2369):** V2362 selected Android route-delta
capture as the next speaker-route measurement and designed it host-only. The measurement should boot
normal Android, use Android framework `AudioTrack` playback through AudioFlinger/vendor HAL, capture
`tinymix -D 0 --all-values` before/during/after, then roll back to V2321 and diff `SEC_TDM_RX_0` /
`WSA_CDC_DMA_RX_0` / `RX INT7` / `COMP7` / `Spkr` controls offline. This is the clean path to learn
Android's actual speaker route without guessing native smart-amp writes. V2364 closed the checked
flash-helper gap by adding `native_init_flash.py --post-flash-target android-adb`, Android
boot-complete polling, optional Magisk root check, and `--expect-android-magic` while preserving the
default native-init serial verification path. V2365 added a host-only dry-run planner for the future
route-delta runner: it verifies the pinned Android boot candidates and V2345 `tinymix`, emits the
checked-helper Android flash/stage/snapshot/playback/rollback command plan, and confirms the archived
Android boot image must be sealed to a private `0600` copy before helper use. V2366 added
`A90AudioRouteStimulus.java` plus a private-output builder. V2368 staged a private Temurin JDK +
Android SDK toolchain and built the DEX at `workspace/private/builds/audio/v2366-android-route-stimulus/A90AudioRouteStimulus.dex` (SHA256 `95c27a152acee5c57d634e03436f72166999f5fd809d772f8f6414a3f9dc2b57`, mode `0600`);
V2365 dry-run with that DEX now reports `live_ready=True`. V2369 converted the planner into an
exact-gated live runner: it creates a run-local `0600` Android boot copy, boots Android through the
checked helper, stages only `tinymix` + the AudioTrack DEX, captures baseline/active/post snapshots,
starts the stimulus in the background so active `tinymix` reads occur during playback, then reboots
Android to recovery and flashes V2321 without incorrectly claiming a native-bridge origin. The
operator text `exact route-delta approval.` is **not** the exact gate and no live run was executed in
V2369. Do not attempt internal speaker playback,
native `tinymix set`, PCM playback open/write, `tinyplay`, or Android route-delta live capture until
a fresh exact route-delta gate is provided. V2363 and V2367 repeated the already-passed
AUD-3C read-only tinyalsa inventory at operator request: V2334 again materialized `/dev/snd`
(`61` nodes), `tinymix`/`tinypcminfo` read-only queries returned `rc=0`, and rollback to
V2321 ended with `selftest fail=0`; V2367 private evidence is
`workspace/private/runs/audio/v2349-tinyalsa-inventory-20260615-025616/`. These were
reproducibility replays and did not change the next frontier.

**Validation:** AUD-0/AUD-1 are host-only — `py_compile`/unittest for any harness code, no flash,
no device. AUD-2/AUD-3 (if gated-in) every iteration: boot-only flash, pinned SHA, post-boot health
check (`version`/`status`/`selftest fail=0`), USB control channel returns, auto-rollback to `v2321`
on any failure (`v2237`/`v48` deeper fallbacks). Bump init beyond the current validated artifact;
`vNNNN-purpose` tag. **If AUD-0 lands on "full HAL mandatory," close the epic with the evidence
rather than grinding.**

**T1 (now SATURATED) — analyzer / harness regression test suite (host-only, NO flash).**
As of 2026-06-13 the 12 `workspace/public/src/harness/a90harness/` modules and all 124 revalidation
scripts have accept + reject/edge tests (**964 tests green**). **This tier is covered — do NOT grind
it.** The overnight run already over-extended here onto frozen one-shot build wrappers and
closed-phase analysis scripts (low marginal value, an anti-churn violation in spirit). Only touch T1
to add a regression test for a **real bug you actually hit**, batched into a single commit — never
resume per-script coverage sweeps.

**T2 (fallback) — native-init / WLAN baseline improvement (device; flash authorized).**
Do not enter T2 from this closed-loop file without a fresh operator direction. If selected later,
advance the native-init baseline from the current V2312 test baseline with DESIGN → IMPLEMENT →
STATIC VALIDATE host-side, then DEVICE validation through the `AGENTS.md` flash gates. Wi-Fi
credentials may be available under `workspace/private/secrets/`; never log their values.

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
