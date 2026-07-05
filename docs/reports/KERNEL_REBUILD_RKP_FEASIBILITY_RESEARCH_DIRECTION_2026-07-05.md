# Kernel-Rebuild / RKP Feasibility — Research Direction (Potential Long-Term Driver)

- Date: `2026-07-05`
- Type: feasibility analysis + strategic framing (conceptual; no device action, no exploit detail)
- Origin: operator discussion during the server-distro D-harden phase
- Status: **exploratory direction, NOT chartered work.** Recorded so it can seed a future epic.
- Safety note: conceptual only. No raw kernel pointers, KASLR slides, secrets, or exploit
  primitives are recorded here. Any future device work stays inside the existing safety
  invariants (boot-partition-only flashes, download-mode preserved, forbidden partitions
  never touched).

## 1. Why this exists

The server-distro endgame runs on the **stock, frozen Samsung kernel 4.14.190** (native-init on top,
never replacing the kernel). The design (Decision E) accepts the frozen-kernel residual risk as
acceptable for a single-admin tunnelled server because containment (seccomp + outbound-only tunnel +
network isolation) shrinks the surface without needing a rebuild.

A recurring limitation keeps surfacing (e.g. Debian-eye hardware inventory: `NET_NS/PID_NS/USER_NS/
UTS_NS/IPC_NS=missing`, `VETH=n`, `OVERLAY_FS=n`): the frozen kernel blocks **real containers/namespaces,
overlayfs, WireGuard kernel module, and CVE patching**. This report captures the finding that a kernel
rebuild is **difficult, not proven impossible**, and frames it as a possible long-term direction.

## 2. Key correction: "difficult" ≠ "impossible"

Earlier framing treated kernel rebuild as effectively walled. That was an overstatement. Broken down:

| Sub-problem | Real status |
| --- | --- |
| Kernel **source** | Public (opensource.samsung.com). Not a blocker. |
| **Compile** it | Fiddly (toolchain/config), but clearly possible. |
| Match vendor **drivers/DTB/config** so hardware boots | Hard (out-of-tree drivers; e.g. Wi-Fi often breaks on naive rebuilds) — this is the real practical friction. |
| **AVB / secure boot** accepting a modified image | Already bypassed — native-init boots custom boot images today. Not the wall. |
| Custom boot **flash infra** | Already works (byte-patched kernels boot). Not the wall. |
| **RKP / RKP_CFP** accepting a rebuilt kernel | The perceived crux — but a documented community path exists (see §3). |

Conclusion: rebuild on the A90 is **untested + high-effort + carries a soft-brick iteration cost**, not a
proven physical impossibility.

## 3. The RKP crux — documented community path

Web research (July 2026) shows the custom-kernel community routinely boots rebuilt Samsung kernels by
**disabling RKP/KDP at kernel-config time** and recompiling:

```
CONFIG_UH=n            # micro-hypervisor (uH) integration
CONFIG_RKP=n           # Real-time Kernel Protection
CONFIG_KDP=n / CONFIG_KDP_CRED=n / CONFIG_KDP_NS=n   # Kernel Data Protection
CONFIG_DEFEX=n
CONFIG_PROCA=n / CONFIG_FIVE=n
CONFIG_RKP_TEST=n / CONFIG_KDP_TEST=n
```

Why it works: RKP setup is **kernel-driven** — the kernel calls into the EL2 hypervisor to enable
protections. With `CONFIG_UH=n` the kernel never registers, so even though the EL2 monitor is loaded by
the bootloader it does not engage kernel protection, and the kernel boots. Real-world confirmation:
KernelSU issue #260 ("kernel panic due to RKP and KDP") is resolved by disabling exactly these configs.

**Snapdragon (A90 = SM8150) specific:** RKP is embedded in the **QHEE (Qualcomm Hypervisor Execution
Environment)** in the `hyp` partition (extractable from `BL_*.tar`). The kernel-side `CONFIG_UH/RKP=n`
approach still applies (kernel simply doesn't register with QHEE's RKP).

## 4. Reverse-engineering angle (source + binary)

The user's instinct — "we have the source AND the compiled kernel, diff them to analyse the closed
parts" — is correct and is **already how this project analyses the kernel**:

- **Source ↔ shipped-binary diff** (Ghidra + BinDiff/Diaphora, compile source with matching config as a
  reference) recovers: the real build config / which `#ifdef`s are on, the **build-time-injected CFP
  (ROPP/JOPP) instrumentation** sites (absent from vanilla source → they pop out in the diff), symbol
  names on the stripped binary, and the kernel→hypervisor call sites. This project already used
  source-informed binary analysis for KASLR slide, `printk` offsets, the `num_pwrlevels` anchor, etc.

- **The genuinely closed part is NOT in the kernel source:** the RKP *enforcement logic* lives in a
  **separate binary** — `uh.bin` (GREENTEA header, obfuscated) / the Snapdragon `hyp`/QHEE image. To
  understand what RKP actually enforces you must RE that hypervisor binary directly (Ghidra on the hyp),
  which source↔kernel-binary diffing cannot reach. Public reference RE already exists (Impala Labs,
  dayzerosec).

Important: **to merely boot a rebuild you do not need to RE the hypervisor** — `CONFIG_UH/RKP=n` suffices.
Hypervisor RE is only needed for the harder goals: keeping RKP *on* while modifying the kernel, or
finding RKP vulnerabilities.

## 5. The tradeoff — rebuild converts risk, it does not delete it

"If rebuild works, the frozen-kernel risk is gone" is only partly true. It is a **trade**, not a free win:

| Axis | Frozen (current) | Rebuild + actively maintained |
| --- | --- | --- |
| Patch kernel CVEs | ❌ cannot | ✅ can (ongoing effort) |
| RKP / KDP hardening | ✅ present | ❌ lost (disabled to boot) |
| Containers / namespaces / WireGuard | ❌ | ✅ |
| Maintenance burden | none | **continuous** (track CVEs, rebuild, reflash) |
| Base kernel age | 4.14 (frozen) | still 4.14 (patchable, not modern) |
| Vendor blobs (Wi-Fi/modem FW, TZ, bootloader) | frozen | **still frozen** |
| Rebuild-introduced instability | n/a | possible (driver bring-up) |

Net: a rebuilt + maintained kernel moves the risk profile toward **"an ordinary, self-maintained Linux
server"** (which is not zero risk) — plus an old 4.14 base and unchanged vendor blobs. For a *hardening*
goal, keeping RKP on and byte-patching + seccomp may stay more coherent; for a *capability* goal
(containers/WG/modern features), rebuild is the path. **It is a choice between tradeoffs, not the removal
of risk.**

## 6. Brick-risk reality (why experiments are affordable)

Kernel-rebuild experiments confined to the **boot partition** are **soft-brick only** (recoverable):
- Samsung **Download Mode (Odin)** lives at the bootloader/SBL level, ahead of the kernel. A kernel that
  fails to boot just panics/hangs → enter download mode → Odin-flash a stock boot image → recovered.
- Hard-brick lives elsewhere: bootloader / `vbmeta` / `pit` (partition table) / `efs` / RPMB, plus the
  **anti-rollback (ARB)** counter (bumped only by bootloader/firmware flashes, not kernel-in-boot).
- Rule for any future attempt: **boot-partition-only, download mode preserved, never touch the forbidden
  partitions, do not bump ARB.** Then the worst realistic outcome is an Odin reflash, not a dead device.

This is exactly why the project's "recoverable envelope" already pre-authorises boot-partition flashes.

## 7. If this becomes an epic — suggested first steps (host-only / low-risk first)

1. **Host-only firmware recon:** locate and extract the A90 `hyp`/QHEE (`uh.bin`) from the stock
   `BL_*.tar` / boot chain; confirm version; stage under `workspace/private/` (do not commit the blob).
2. **RE reconnaissance** of that hyp binary using the public Impala Labs / dayzerosec roadmap — map the
   RKP command interface and what it enforces (understanding-only).
3. **Off-device test build:** compile the Samsung 4.14 source for SM-A908N with `CONFIG_UH/RKP/KDP=n` in
   a build VM; assess how far a bootable image gets and enumerate the driver/DTB gaps (esp. Wi-Fi). **No
   flash** in this step.
4. **Only then**, if justified, a single gated boot-only flash of a rebuilt kernel (download-mode
   preserved, stock boot staged for rollback) — treat as a soft-brick-tolerant experiment.
5. Note the **natural platform for real rebuild** is the already-bootloader-unlocked **S22+ (SM-S906N,
   5.10 GKI)**, where rebuild/boot is far more tractable than A90 4.14 — A90 = "extreme within
   constraints", S22+ = "free expansion".

## 8. Sources (web, July 2026)

- Impala Labs — *A Samsung RKP Compendium*: https://blog.impalabs.com/2101_samsung-rkp-compendium.html
- Impala Labs — *Attacking Samsung RKP*: https://blog.impalabs.com/2111_attacking-samsung-rkp.html
- dayzerosec — *Reversing Samsung's H-Arx Hypervisor (Part 1, 2025)*: https://dayzerosec.com/blog/2025/03/08/reversing-samsungs-h-arx-hypervisor-part-1.html
- Google Project Zero — *Lifting the (Hyper)Visor: Bypassing Samsung's RKP*: https://projectzero.google/2017/02/lifting-hyper-visor-bypassing-samsungs.html
- XDA — *How to compile Samsung kernel source to a bootable image*: https://xdaforums.com/t/how-to-compile-samsung-kernel-source-to-a-bootable-image-for-android-14-devices.4701072/
- KernelSU — issue #260, *kernel panic on samsung due to RKP and KDP*: https://github.com/tiann/KernelSU/issues/260

## 9. One-line takeaway

Kernel rebuild on the A90 is **not proven impossible** — the RKP crux has a documented `CONFIG_UH/RKP=n`
rebuild path, and the closed enforcement logic (hyp `uh.bin`) is already partly RE'd publicly. But
rebuild **trades RKP hardening + a maintenance burden for patchability + containers**, on a still-old
4.14 base with unchanged vendor blobs. It is a **strategic alternative direction** (best suited to the
unlocked S22+ GKI target), not a strict requirement for the frozen-kernel server — recorded here as a
possible long-term project driver.
