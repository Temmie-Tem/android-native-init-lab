# V2291 Kernel Security Recon: FastRPC Stage-B reachability gate + Unit A result

Date: 2026-06-12
Scope: host/source review plus one read-only live Unit A liveness check. No device write,
no flash, no reboot, no devnode, no ioctl, no `mmap(2)`, no DSP invoke, no payload, no
trigger. This report corrects Stage-B ordering and records the liveness gate result; it
does **not** authorize Stage-B execution. Stage-B execution still requires the exact
approval phrase defined in V2289.
Baseline: resident rollback checkpoint `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`.

## Why this report exists

V2289 left two candidate B2 shapes to choose between: a naive crash-only one-shot
(no reflash) and an `slub_debug`-instrumented one-shot (diagnostic, reflash). Before
choosing, a source review of the FastRPC invoke path found that **both shapes sit
downstream of an upstream reachability gate that V2284-V2289 never checked**: the DSP
`rpmsg` channel must be live (`rpdev != NULL`), or every INVOKE/INIT fails *before*
reaching the vulnerable free path. So "naive vs slub_debug" is the wrong first
question. The first question is whether the vulnerable path is reachable at all under
bare native init.

## Decisive source finding: the UAF is gated behind a live DSP channel

Confirmed in `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/char/adsprpc.c`:

- The CVE-2024-43047-class UAF site is `put_args()` (`adsprpc.c:1719`), which walks the
  DSP-returned `fdlist` and calls `fastrpc_mmap_free(mmap, 0)` (`adsprpc.c:1756-1764`)
  without the public `dma_handle_refs` guard (V2284 confirmed the guard is absent).
  `adsprpc.c:1003` is a separate `fastrpc_mmap_create()` error-cleanup free, not the
  DSP-returned `fdlist` free.
- `put_args` is reached only at the **end** of `fastrpc_internal_invoke()`:
  `get_args` (`:2012`) → `fastrpc_invoke_send` (`:2025`) → `wait_for_completion` for the
  DSP response (`:2033`/`:2035`) → `put_args` (`:2052`).
- `fastrpc_invoke_send` (`:1858`) reaches `rpmsg_send(channel_ctx->rpdev->ept, ...)`
  (`:1901`) only after `VERIFY(err, !IS_ERR_OR_NULL(channel_ctx->rpdev))`; if `rpdev` is
  NULL it returns `-ECONNRESET` (`:1895-1901`).
- The INIT path first calls `fastrpc_channel_open(fl)` (`:2117` → `:3356`), which
  `VERIFY(err, NULL != me->channel[cid].rpdev)` and returns `-ENOTCONN` if NULL
  (`:3369-3375`).
- `rpdev` is set **only** in `fastrpc_rpmsg_probe()` (`:2910`), which runs when the DSP
  glink/rpmsg edge (`cdsp`/`adsp`/`dsps`/`mdsp`) probes — i.e. when remoteproc has brought
  a DSP up and its rpmsg channel is connected. The probe logs
  `adsprpc: fastrpc_rpmsg_probe: opened rpmsg channel for <subsys>`.
- `FASTRPC_IOCTL_GETINFO` can set `fl->cid` and allocate `fl->sctx` (`:3502-3546`)
  without proving `rpdev` liveness. It can prepare local file/session state, but it does
  not remove the later `rpdev` gate in INIT/INVOKE.

Implication:

- If no DSP rpmsg channel is live under native init (no Android remoteproc/PIL
  bring-up), then:
  - **naive B2** → `-ENOTCONN`/`-ECONNRESET` before `put_args`; the UAF is never exercised.
  - **slub_debug B2** → identical; poisoning is irrelevant because the free path is
    never reached.
- Even if `send` somehow did not error, `wait_for_completion` waits for a DSP response
  that never arrives → at best the userspace-interruptible wait (`:2035`) returns an
  error, at worst a hang — still no `put_args`.

So neither candidate B2 reaches the bug unless the DSP channel is live first.

## Stage-B reachability ladder (FastRPC)

- **L0** devnode open — DONE (V2287: `adsprpc-smd` openable `O_RDWR` once materialized).
- **L1** DSP channel live (`rpdev != NULL`) — **UNKNOWN; this is the new gate.** Read-only checkable.
- **L2** local session/cid setup and INIT/attach constraints. `GETINFO` can create
  local `sctx` before L1, but any INIT/attach path that sends work to the DSP still
  calls `fastrpc_channel_open()` first. Signed-PD/domain policy also applies
  (`:2127`/`:2265` "untrusted app trying to attach" rejects).
- **L3** INVOKE round-trips the DSP and returns an `fdlist`.
- **L4** `put_args` → `fastrpc_mmap_free` without the `dma_handle_refs` guard → UAF.

Neither naive nor slub_debug B2 reaches L4 unless L1 holds.

## Unit A — DSP-channel liveness pre-check (do FIRST; read-only recon; no exact phrase)

Same safety class as V2286: read-only metadata only. No devnode, no vulnerable command
family, no ioctl. Through the existing serial bridge collect:

- `/sys/class/remoteproc/*/state` and `.../name` — is any `adsp`/`cdsp`/`slpi`/`mdsp`
  subsystem `running`?
- `/sys/bus/rpmsg/devices/` and `/sys/class/rpmsg/*` presence.
- a bounded `/dev/kmsg` (or native dmesg surface) grep for
  `opened rpmsg channel for` and remoteproc bring-up lines, only if readable without
  destabilizing the device.

Classify L1 as one of:

- `dsp-channel-live` — a DSP subsystem is `running` AND an rpmsg probe / channel is
  observed → the FastRPC invoke path is reachable; proceed to Unit B.
- `dsp-channel-down` — no running DSP / no rpmsg channel → INVOKE/INIT will
  `-ENOTCONN`/`-ECONNRESET`; the FastRPC trigger is unreachable under native init as-is.

Evidence goes to `workspace/private/runs/security/`; a metadata-only report is committable.

## Branch on Unit A result

- **If `dsp-channel-down` (the expected result under bare native init):**
  - The FastRPC UAF is not reachable without first bringing the DSP up (remoteproc start
    + glink edge), which is a large, risky, separate subsystem action — outside the
    one-shot, crash-only B2 envelope and not recommended as a toe-dip.
  - Re-rank trigger surfaces by *reachability*: **Binder** UAF classes are self-contained
    in-kernel (no coprocessor round-trip) and `/dev/binder` is openable (V2287) → Binder
    becomes the more reachable in-kernel trigger surface than FastRPC when the DSP is down.
    KGSL is also self-contained but its open path is blocked (V2287).
  - Recommended: either (a) **STOP** the FastRPC trigger path (recon is complete and
    strong) and, if continuing, re-triage **Binder** with the same host-only rubric
    (code present + post-2023 UAF fix-marker diff + reachability); or (b) explicitly
    charter DSP bring-up as its own large unit (not a one-shot; not recommended now).
- **If `dsp-channel-live`:**
  - naive B2 (Unit B) has a real chance to reach L3/L4; proceed under the exact phrase.

## Unit A live result

Private read-only evidence:

- `workspace/private/runs/security/v2291-fastrpc-dsp-liveness-20260612-224503/a90ctl_dsp_liveness.txt`

Preflight:

- `status`: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`, `selftest fail=0`.
- `selftest verbose`: `fail=0`.

Read-only observations:

- `/sys/class/remoteproc/remoteproc*`: no entries printed by the read-only loop.
- `/sys/bus/rpmsg/devices`: present, but only modem-side channels were listed:
  `qcom,glink:modem.IPCRTR.-1.-1`,
  `qcom,glink:modem.SSM_RTR_MODEM_APPS.-1.-1`,
  `qcom,glink:modem.glink_ssr.-1.-1`, and
  `qcom,glink:modem.rpmsg_chrdev.0.0`.
- `/sys/class/rpmsg`: `rpmsg_ctrl0` for the modem rpmsg char device only.
- `/sys/class/fastrpc`: the FastRPC class/devnodes are registered:
  `adsprpc-smd` = `480:0`, `adsprpc-smd-secure` = `480:1`.
- filtered `dmesg`: no `adsprpc: fastrpc_rpmsg_probe: opened rpmsg channel for <subsys>`
  marker; the only FastRPC line in the bounded tail was the prior V2290 invalid-ioctl
  B1 marker (`bad ioctl: -559038737`).

Post-check:

- `selftest verbose`: `fail=0`.

Classification:

> `dsp-channel-down-for-fastrpc`

The driver/device class is registered and B1 dispatch is live, but no ADSP/CDSP/DSPS/MDSP
FastRPC rpmsg channel is observable in the resident native-init boot. The modem rpmsg
channels prove rpmsg/glink infrastructure exists in general; they do not satisfy the
`gcinfo[cid].rpdev` requirement for FastRPC DSP invoke paths.

## Unit B — naive B2 (blocked unless a later Unit A = `dsp-channel-live`)

The V2289 B2 one-shot, unchanged: one process / one fd, INIT(+attach) then exactly one
INVOKE crafted to walk toward `put_args`; no spray, no reclaim, no retry, no threads;
crash-only classification; helper lives only under `workspace/private/` and is **not
committed**. All V2289 preconditions / abort matrix / outcome taxonomy remain in force.

Diagnostic caveat (V2289 + `.config`): with `CONFIG_KASAN` unset, `CONFIG_SLUB_DEBUG_ON`
unset, and `CONFIG_PAGE_POISONING` unset, freed memory is not poisoned, so a no-fault
result is **inconclusive** (silent UAF), not "not vulnerable." Naive B2 confirms only on
a positive fault (`b2-kernel-warning` / `b2-panic-reboot`).

## Unit C — slub_debug-instrumented B2 (only if Unit B = path-reachable-no-fault)

Make the free path detectable without spray/reclaim:

- `struct fastrpc_mmap` is `kzalloc(sizeof(*map), GFP_KERNEL)` (`adsprpc.c:839`).
  Source-layout estimation on this 64-bit tree gives about 136 bytes, so the expected
  general slab cache is **`kmalloc-192`**. Before any Unit C image is built, confirm
  this with a compile-time `sizeof(struct fastrpc_mmap)` probe against the exact stock
  headers/config; do not rely on the estimate as the only cache selector.
- Build a boot-image variant with `slub_debug=FZPU,kmalloc-192` appended to the kernel
  cmdline (`F` sanity, `Z` redzone, `P` poison, `U` user-tracking). Targeting `kmalloc-192`
  bounds overhead/noise and disables merge for that cache.
- Flash via the checked helper. **This makes the slub_debug image resident and therefore
  leaves the v2237 checkpoint** → rollback to v2237 is a mandatory post-step, and the
  slub_debug boot is a throwaway test image, never a new baseline.
- Verify `/proc/cmdline` actually carries `slub_debug=` after boot (Samsung sboot may
  append/override the boot.img cmdline). If not honored → slub_debug instrumentation is
  infeasible without bootloader cmdline control → abort this branch, do not retry blindly.
- Re-run the same one-shot. A UAF read of the freed map now dereferences poison
  (`0x6b6b…`) → invalid-pointer oops, or an alloc-time poison-overwrite/redzone BUG →
  detectable. Then rollback to v2237; verify SHA256 and `selftest fail=0`.
- slub_debug boot artifacts are private; not committed.

## Safety

- Units B and C are Stage-B execution → still require the V2289 exact approval phrase
  (`Stage B go: FastRPC one-shot crash-only trigger on v2237, no heap spray, no privilege
  escalation, no retry`). Unit A is read-only recon and does not.
- Unit C additionally leaves the v2237 checkpoint resident during the test → checkpoint
  restore is mandatory afterward; the slub_debug boot is disposable.
- All V2289 preconditions, abort conditions, and outcome classification remain in force
  for B and C.

## Decision / recommended order

1. Unit A was run read-only and classified `dsp-channel-down-for-fastrpc`.
2. Do **not** run naive B2 on the current resident native-init boot: it is expected to die
   at `fastrpc_channel_open()` / `fastrpc_invoke_send()` before reaching `put_args`.
3. Do **not** build a `slub_debug` image for FastRPC now: allocator instrumentation cannot
   help when the free path is not reachable.
4. Recommended next branch: stop the FastRPC trigger path at recon/B1/Unit-A, or re-triage
   **Binder** as the more reachable self-contained in-kernel surface.
5. If FastRPC is reopened later, first charter DSP/rpmsg bring-up as its own explicit,
   higher-risk subsystem unit; do not hide that inside Stage B.

Default without the exact phrase remains: no Stage-B trigger.
