# Kernel Security Recon Phase — Close Checkpoint (2026-06-13)

Declares the kernel-security recon phase **closed**. All three triaged n-day
candidates were resolved host-only, without ever triggering kernel memory
corruption, flashing a non-checkpoint image, or leaving the v2237 rollback point.
This is a clean, non-destructive termination.

## Termination declaration

> The kernel-security recon phase is **terminated**. Its charter question —
> *"is EL1 (kernel R/W) realistically attemptable via patch-level n-day from this
> native-init environment, within non-destructive scope?"* — is answered **no**
> for all three top candidates, each for a concrete, source-grounded reason. No
> remaining candidate is both reachable from native init and confirmable
> non-destructively. There is no autonomous loop for this phase.

## Charter recap

This phase followed the WLAN/observation close (`v2237` checkpoint). It was
recon-first and explicitly non-destructive: enumerate the stock `4.14.190`
attack surface, triage patch-level n-day feasibility on the owned device, and
decide whether exploitation is warranted *before* any trigger. Exploit
confirmation was always gated as interactive, not an unattended loop.

## Three-candidate triage outcome

| Candidate | Primitive present? | Reachable from native init? | Closure | Reports |
| --- | --- | --- | --- | --- |
| FastRPC / ADSPRPC CVE-2024-43047 (UAF) | yes — `dma_handle_refs` fix-marker absent | **no** — DSP `rpmsg` channel down (`rpdev == NULL`); invoke fails `-ENOTCONN`/`-ECONNRESET` before the free path | unreachable | V2284, V2286–V2291 |
| Binder CVE-2023-20938 / -21255 (UAF) | **no** — `is_failure`-keyed cleanup, both callers balanced; the `failed_at==0 ⇒ release-all` over-decrement does not exist here | yes — normal transaction path proven end-to-end on device | **not vulnerable** | V2285, V2292–V2307 |
| KGSL CVE-2023-33107 (SVM range wrap) | yes — `gpuaddr + size` wrap guard absent | source-reachable via `IOCTL_KGSL_MAP_USER_MEM`, but `/dev/kgsl-3d0` open-blocked under native init; observation needs GPU-side follow-up | runtime-blocked + exploit-dev-gated | V2285, V2287, V2308 |

Each closure is for a different, specific reason: **unreachable** (FastRPC),
**not vulnerable** (Binder), **environment + exploit-dev gated** (KGSL).

## What was established (durable findings)

Capability envelope (from the prior observation phase, carried in):

- exact KASLR slide solved (V2216); BPF read probes, kallsyms recovery under
  `kptr_restrict=4`, CFP/JOPP/ROPP characterization. Hard boundary: ROPP
  full-stack symbolization needs the per-boot RKP key (SYSREGKEY) = out of
  read-only scope.

Runtime reachability facts (not derivable from source — the high-value output):

- native init has no `ueventd`; target `/dev` nodes are absent but can be
  `mknod`'d and opened (FastRPC `adsprpc-smd` `O_RDWR`, Binder `O_RDWR`; KGSL
  `kgsl-3d0` open-blocked / hangs).
- the DSP `rpmsg`/`glink` edges for ADSP/CDSP are **not** live under native init
  (only the modem edge is), so the FastRPC invoke path is gated off.
- the Binder context-manager **uid is locked to 1000** for this boot (a prior
  euid-1000 ctx-mgr lifecycle occurred and exited), so the environment is not a
  pristine Binder context; a uid-1000 registration is required and works.
- Binder is reachable end-to-end on device: devnode → `mmap` → `setresuid(1000)`
  → `BINDER_SET_CONTEXT_MGR` → two-process handle-0 `TF_ONE_WAY` transaction →
  `BR_TRANSACTION` delivered, all with zero memory corruption.

Security determinations:

- this device's Binder is **not vulnerable** to CVE-2023-20938/-21255 (proven,
  not assumed); FastRPC is vulnerable-in-source but **unreachable**; KGSL is
  vulnerable-in-source and source-reachable but **environment/exploit-dev gated**.

## Reusable knowledge & tooling (transferable beyond this device)

- the gate ladder: recon (read-only) → reachability snapshot → devnode-open-only
  → well-formed protocol reachability → (gated) trigger, each with an exact
  scoped approval phrase, static forbidden-symbol scans, benign helpers, and
  build-only-by-default runners.
- working harness: devnode-materialization probes; the BB2 `mmap` and BB-T(-uid)
  two-process Binder helpers; uid-aware child-local `setresuid` drop pattern;
  runner watchdog + private evidence capture under `workspace/private/runs/security/`.
- the doer(codex) + gate(operator) + reviewer(claude, source-verified) loop,
  which caught real analysis errors cheaply via live gates (self-target pid guard;
  the ctx-mgr uid gate).

## Methodology lesson (proven three times)

**Fix-marker absence ≠ exploitability.** A missing public-fix marker proves only
*pre-mitigation*. In all three candidates, the decisive answer came from one more
host-only step past the marker check:

- FastRPC: fix-marker absent, but the invoke path is channel-gated (unreachable).
- Binder: fix-marker absent, but the over-decrement primitive itself is absent
  (the `is_failure` disambiguation already neutralizes it).
- KGSL: fix-marker absent **and** primitive present **and** source-reachable, but
  runtime-open-blocked and exploit-dev-gated.

"Prove it on paper / read-only first" repeatedly made the destructive step
unnecessary.

## Non-destructive outcome

No kernel memory corruption was triggered. No non-checkpoint image was flashed.
No forbidden partition was touched. The destructive-progress bar (question
unanswerable non-destructively **and** the step conclusive **and** recoverable
**and** value proportionate on an EOL device **and** explicitly approved) was
never met — every time, host-only analysis or a benign reachability gate answered
the question first.

## Safety & checkpoint state (unchanged)

- Rollback checkpoint remains `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`,
  resident and healthy: `selftest fail=0` after the last live Binder run (V2306),
  `/dev/binder` and all temporary nodes/helpers removed.
- Image `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`,
  SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`.
  Deeper fallback `boot_linux_v48.img`. TWRP available.

## Reopening criteria

Reopen only if a *new* candidate is shown, host-only, to be **both** reachable
from native init **and** confirmable non-destructively (e.g. an immediate-use UAF
that faults one-shot without reclaim), or if the target environment changes (full
Android userspace, or a deliberately-chartered exploit-development track on a
device whose value justifies it). KGSL remains the one candidate with genuine
residual potential, gated only by the native-init KGSL open-block.

## Decision

> Kernel-security recon phase: **CLOSED**. Triage complete (FastRPC unreachable,
> Binder not vulnerable, KGSL env/exploit-dev gated). v2237 remains the resident
> rollback checkpoint. No further kernel-security unit is chartered.
