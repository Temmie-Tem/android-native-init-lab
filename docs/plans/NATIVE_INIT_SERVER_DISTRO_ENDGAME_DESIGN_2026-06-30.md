# Native-Init Server Distro Endgame — Architecture & Design

- Date: 2026-06-30
- Status: DESIGN LOCKED (decisions A–E confirmed by operator). Implementation not started.
- Scope: A90 5G `SM-A908N` first; the Stage-1 layer is intended to be ~portable to S22+
  (`SM-S906N`) later (see `memory/project_s22plus_future_target`).
- Device action in this doc: none. This is a host-only planning artifact.

## 0. Endgame Vision

Turn the A90 from a "native-init hardware demo" into a **self-contained, remotely
administered, internet-reachable headless server appliance**:

- Boots on the stock Samsung Android kernel (4.14.190) with our custom static `/init` as PID 1.
- Brings all needed hardware up through the proven native-init vendor glue
  (audio ACDB → `/dev/msm_audio_cal`, Wi-Fi qcacld / SoftAP, GPU KGSL / DRM-KMS, USB gadget, display).
- Then hands off to a **familiar distro userspace** (Debian) so the device can be used like any
  Linux server: SSH login, package manager, web services.
- Exposed to the public internet **without opening any inbound port** on the device, via an
  outbound-only tunnel terminated at a hardened edge.

The motivation is a multipurpose personal lab/server, so the design optimizes for **operator
familiarity and remote administration**, not minimal footprint.

## 1. Two-Stage Architecture

The system is split into two layers that share **one kernel** (the stock kernel we already boot):

### Stage 0 — Native-init (device-specific, already built)
PID 1 responsibilities, all proven in this project:
- Boot the stock kernel, mount early filesystems, set up the console/serial control surface.
- Wake hardware through vendor glue that has no mainline path: audio (ACDB calibration replay
  into `/dev/msm_audio_cal`), Wi-Fi (qcacld built into the stock kernel; SoftAP via
  `wpa_supplicant mode=2` + `udhcpd`), GPU (KGSL-direct, DRM/KMS to `/dev/dri/card0`),
  USB gadget (NCM/ACM/mass-storage), display panel.
- Expose those as **kernel-level device nodes** (`/dev/snd/*`, `/dev/dri/card0`, `wlan0`,
  `/dev/msm_audio_cal`, gadget configfs, …) — the same nodes a normal Linux userspace expects.

Stage 0 is **device-specific** and is the hard, already-done part. The vendor glue
(ACDB/qcacld/KGSL) stays NATIVE on any distro — it is the bridge to the SoC.

### Stage 1 — Distro userspace (portable, to be built)
A standard Debian rootfs that runs **on top of** Stage 0. Because both stages share the same
kernel, Stage 1 talks to hardware through Stage 0's already-materialized device nodes — there
is no second driver stack. Stage 1 owns:
- Service management, package manager (`apt`), users/auth, SSH, web stack, the tunnel client.

Stage 1 is **~100% portable**: the same rootfs artifact and handoff mechanism move to the S22+
unchanged; only Stage 0 (the device-specific glue) is re-done per device.

> Mental model: **postmarketOS / Halium "from native-init UP, not HAL DOWN."** We do not emulate
> Android HALs; we expose raw kernel nodes from PID 1 and put a normal distro on them.

## 2. Decision A — Handoff Mechanism: `chroot` → `switch_root`

CONFIRMED. Staged in two risk-separated steps that reuse the **same rootfs artifact**; only the
entry mechanism and "who is PID 1" change.

### A.1 `chroot` (MVP / proof)
- Native `/init` stays PID 1. The distro runs as a **guest** inside a `chroot` onto the mounted
  rootfs. Non-destructive, fully reversible (just don't enter the chroot).
- Goal: prove **"Debian binaries run on this kernel + `sshd` comes up + SSH login works."**
- Init-agnostic: the chroot MVP runs `dropbear` (or `sshd`) directly, no distro init system needed.
- **Not a security boundary** — chroot is for bring-up proof only, not multiuser isolation.

### A.2 `switch_root` (appliance / persistent)
- `exec switch_root /target $INIT` — the **distro init becomes PID 1**. Native daemons that must
  persist (the vendor-glue keepers) have to survive the handoff (start them before switch, or
  re-exec them as distro services).
- This is the postmarketOS boot.img model.
- Real multiuser security only exists **after** switch_root.

Risk staging: chroot proves binaries+SSH with zero PID-1 risk; switch_root then adds the
PID-1-handoff problem **separately**, so a failure is unambiguous.

## 3. Decision B — Distribution: Debian

CONFIRMED. Trade-off considered:

| Axis | Alpine | **Debian (chosen)** |
| --- | --- | --- |
| libc / init | musl / OpenRC | glibc / systemd (or sysvinit) |
| Size | ~8 MB base | large |
| Fit for a from-scratch bring-up | best (server-native, least friction) | heavier |
| Ecosystem / familiarity | smaller | **huge, familiar `apt`** |

Operator chose Debian for a **comfortable, familiar server**. Notes:
- **Init-system sub-decision deferred** to the switch_root stage. The chroot MVP is init-agnostic
  (runs dropbear directly), so we don't decide systemd-vs-sysvinit until A.2.
- The one real Debian cost is **systemd-on-stock-kernel friction** (worse on 4.14, easier on the
  S22+'s 5.10). Mitigation: use **sysvinit/OpenRC** under Debian if systemd fights the old kernel.
- **B is not a lock-in.** The rootfs is a swappable artifact and Decision A is distro-agnostic;
  we can swap to Alpine later without redoing the handoff.
- SSH: **dropbear** for the MVP → **openssh-server** for the appliance.

## 4. Decision C — Storage

CONFIRMED. Two phases, matching A.1/A.2:

### C.1 chroot proof → **SD card loop image** (non-destructive)
- `/cache` is too small (~200 MB). The **SD card already exists** (used for the video cache).
- Stage the Debian rootfs as a **loop-mounted ext4 image on the SD card**. No partition is
  formatted; fully reversible. This carries the entire chroot MVP.

### C.2 appliance → **reformat `userdata` to plain ext4** (Android disposal)
- `/data` (`userdata`, UFS, ~100 GB+, fast) is the real appliance store.
- **FBE constraint**: native-init replaces Android, so we cannot derive Android's File-Based
  Encryption keys → the existing `/data` contents are unusable → it must be **reformatted to
  plain ext4**. This is the concrete meaning of "abandon Android."
- **Only the `userdata` partition** is reformatted (`mkfs.ext4` on `/dev/block/by-name/userdata`).
  The GPT table and every other partition are untouched; a full Odin firmware flash recovers
  everything. This is the **only sanctioned `/data` destruction** in the project.
- Deferred to the switch_root stage. The chroot MVP rides entirely on SD with no format at all.

> At-rest encryption (LUKS/dm-crypt on the ext4) is an **optional later axis** for physical-theft
> threat only; it is independent of the public-server design and not required for C.2.

## 5. Decision D — External / Public Access

CONFIRMED. Principle: **the device NEVER opens an inbound public port.** All public traffic flows
through an **outbound-only tunnel** to a maintained edge that faces the internet; the frozen
kernel never directly faces the public.

### 3-layer model
```
[ public internet ]
        │  TLS, WAF, DDoS absorbed here
┌───────▼─────────────────────────┐
│ EDGE  (Cloudflare Tunnel / VPS) │  public IP, TLS termination, WAF/DDoS, maintained & patchable
└───────▲─────────────────────────┘
        │  OUTBOUND-ONLY tunnel (device dials out; no inbound port on device)
┌───────┴─────────────────────────┐
│ TRANSPORT  (cloudflared /        │
│  WireGuard / frp / reverse-SSH)  │
└───────▲─────────────────────────┘
        │
┌───────┴─────────────────────────┐
│ DEVICE  Stage0 glue +           │  hardened, deny-by-default, no listening public port
│  Stage1 Debian web app +        │
│  tunnel client                  │
└─────────────────────────────────┘
```

### Recommendation
- **First: Cloudflare Tunnel** (`cloudflared`). Free, CGNAT/mobile-friendly (works behind the
  carrier NAT a phone sits on), TLS + WAF + DDoS at the edge, **zero inbound ports**, and
  `cloudflared` is glibc — reinforcing the Debian choice.
- **Upgrade path: own VPS + WireGuard** for full ownership. Use **`wireguard-go` (userspace)**
  because the stock kernel may lack the WG module.
- **Connectivity caveat**: a public server needs upstream internet via **`wlan0` STA** (join the
  home AP). Running **SoftAP serving + STA upstream on the same radio concurrently** is a qcacld
  concurrency variable — validate before relying on it; otherwise use STA-only upstream and don't
  also serve SoftAP.

Roadmap milestone **D-public** = a `cloudflared` tunnel makes a LAN web service publicly reachable
with zero inbound ports.

## 6. Decision E — Security Model

CONFIRMED. Two parts: standard hygiene (covers the common case) + containment (covers the
frozen-base delta).

### E.1 What works normally
Standard Debian **DAC** (login / `sudo` / file permissions / setuid) is kernel-enforced + standard
userland on plain ext4 — it works exactly like any Debian box. Caveats:
1. The **chroot phase is not a security boundary**; real multiuser security only after switch_root.
2. Android **SELinux MAC is lost** → DAC-only like a normal Debian box (add **AppArmor** for
   optional MAC).
3. The **frozen base = the whole vendor stack** (kernel + Wi-Fi/modem firmware + vendor libs +
   our native-init), not just the kernel.

### E.2 Threat ranking
1. **Web-app vulns** + 2. **credential/exposure** — SAME as any server; normal hygiene + the
   userspace staying `apt`-patchable covers these. The tunnel removes the inbound front door.
3. **Frozen-kernel LPE** — requires a **prior local foothold** (chained, targeted).
4. **Wi-Fi-firmware** (local network).
5. **Physical at-rest** (the LUKS axis).
Items 3–5 are the genuine **frozen-base deltas**, mostly defense-in-depth / local, not the
tunnel-protected front door.

### E.3 Containment (deny-by-default) — the differentiator
We cannot maintain a CVE-tracked custom kernel (firehose + source→binary cost + structural fixes
don't fit `.text` + CFP limits). So instead of *patching*, we **shrink and contain** the surface:
- **seccomp-bpf per service** — the big lever: a compromised service can't even issue the syscalls
  that would reach a built-in kernel bug.
- **Capability drop / namespaces / AppArmor** per service; services run non-root.
- **nftables default-drop** egress/ingress + outbound-only tunnel.
- **Minimal installed services.**
- **Tier-2 `.text` hard-disable** of unused but built-in vulnerable kernel paths (return
  `-EPERM`/`-ENOSYS`). The project has proven Tier-2 static `.text` patching under RKP_CFP
  (NOP→mov, runtime effect, new `bl printk` injection), so unused vulnerable paths can be made
  **unreachable ≈ as-good-as-fixed**. This is our edge over a normal server.
- Honest limit: we can't remove what the workload **needs** (core syscalls/fs/network stack stay
  frozen) — but the tunnel shrinks the network-facing slice to near-zero, leaving a small
  defensible surface for a single-admin tunneled server.

### E.4 Blast-radius containment (because external access is in scope)
Frozen-kernel LPE is **low-probability × high-impact** (full device + LAN pivot). The cheap,
high-ROI mitigation:
- **Network-isolate the device** (VLAN / guest network) so a full compromise **cannot pivot into
  the home LAN**.
- **Minimize sensitive data** on the device; LUKS only if physical theft is in scope.

### E.5 Risk acceptance (operator-confirmed)
For a **single-admin, tunnel-fronted (no inbound), seccomp-sandboxed, deny-by-default,
network-isolated** server, reaching the frozen kernel requires an attacker to **breach remotely
(web-app RCE) AND locally escalate** — a targeted/chained attack against a small surface, not
opportunistic. Residual risk is **acceptable** for this use, conditioned on: keep userspace
`apt`-patched, no public multiuser shell, device on trusted upstream Wi-Fi, network-isolated.
The exception that breaks "low-probability" is a **wormable app-CVE + a public LPE for this exact
kernel** (automatable chain) — mitigated by E.3/E.4, not eliminated.

### E.6 Hygiene to bake into rootfs staging
Strong root password / `PermitRootLogin no` / SSH key-only / admin user + `sudo` / non-root
services / `rw,suid` rootfs (`/tmp nosuid`) / **lock default debootstrap credentials before any
public exposure**.

## 7. Roadmap / Milestones

| ID | Phase | Goal | Device action |
| --- | --- | --- | --- |
| **D0** | recon | Read-only inventory: SD size/free, `/data` block dev + size, native-init writable mounts, busybox applets present. Host-side: stage Debian rootfs + tunnel client prep. | read-only |
| D1 | chroot MVP | Debian rootfs loop image on SD; `chroot` + run a static binary. | non-destructive |
| D2 | SSH-in-chroot | `dropbear` up inside chroot, SSH login over the native-init network path. | non-destructive |
| D3 | switch_root | distro init = PID 1; persistent vendor-glue daemons survive handoff. | non-destructive (SD) |
| D4 | userdata appliance | reformat `userdata`→ext4, move rootfs there, openssh, services. | **userdata reformat** (Odin-recoverable) |
| **D-public** | external | `cloudflared` outbound tunnel publishes a LAN web service, zero inbound ports. | non-destructive |
| D-harden | security | seccomp/AppArmor/nftables/caps per service; Tier-2 `.text` hard-disable of unused paths; network isolation. | non-destructive |

## 8. Safety Invariants (carried from project)

- Never write/flash `efs`/`sec_efs`/`modem`/RPMB/keymaster/`vbmeta*`/`dsp`/`keydata`/`keyrefuge`/
  bootloader/`persist`. The **`userdata` reformat (D4) is the ONLY sanctioned `/data` destruction**,
  and it touches no other partition (GPT table intact; Odin-recoverable).
- Flash only via `native_init_flash.py` (boot only) or `odin4` tar with only `boot.img`.
- No PMIC/regulator/GDSC/GPIO/backlight writes; no from-scratch DSI panel re-init.
- Rollback targets: v2321 (`ca978551…`), v2237 (`b2ea2d26…`), v48; keep TWRP available.
- Do not commit boot images/firmware/ramdisks/binaries/raw logs/credentials/raw kernel pointers.
- **Operator/loop separation (V2631 rule)**: do not touch the A90 device in parallel with the
  autonomous loop. D0+ live recon must wait until the autonomous A90 work is quiesced for that
  window.

## 9. S22+ Portability Note

Stage 1 (Sections 2–6) is device-independent and moves to the S22+ unchanged. Only Stage 0 is
re-done. The S22+ is easier where it matters for Stage 0/handoff: **5.10 GKI** (standard
KernelSU/Magisk root path; the Tier-2 `.text` trick becomes secondary), bigger GPU, more RAM.
It is harder on the security base: newer Knox/RKP + 8450 MTE. Same forbidden-partition lines.
See `memory/project_s22plus_future_target`.
