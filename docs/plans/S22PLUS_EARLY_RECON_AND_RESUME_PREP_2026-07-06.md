# S22+ (SM-S906N) — Early Recon & Resume-Prep Map

- Date: `2026-07-06`
- Type: host-only recon + strategic framing + resume checklist (NO device action)
- Purpose: pre-stage the slow "early / no-feel" part of the S22+ target so that, when the operator
  returns to it, work can start immediately instead of re-fogging from zero (as it did on day-1 A90).
- Status: **prep only, NOT chartered.** S22+ stays parked until the operator explicitly picks it as the
  next target. The A90 server-distro epic is CLOSED; this document is the on-ramp for the eventual pivot.
- Safety note: conceptual + host-only. No secrets, no device serials, no exploit primitives. Any future
  device work obeys the same safety invariants as A90 (forbidden partitions never touched, download-mode
  preserved, boot-partition-only flashes).

---

## 0. One-paragraph orientation (read this first when you come back)

S22+ is **not a harder A90 — it is a freer A90.** On A90 the platform was adversarial (locked-ish boot,
frozen monolithic 4.14 kernel, RKP you had to do acrobatics *inside*). On S22+ the platform cooperates:
**bootloader already unlocked**, **GKI 5.10 kernel is standardized + rebuildable**, and — the headline
finding below — **the stock kernel already ships the container/VPN primitives A90's 4.14 lacked.** The
"no feel" fog is just "no map yet," and this document is the map. The muscle you built on A90 (boot
unpack, partition sense, kernel analysis, the recoverable-envelope discipline) transfers directly.

---

## 1. Device profile (consolidated, read-only recon 2026-06-30)

| Axis | Value |
| --- | --- |
| Model | **Galaxy S22+ 5G `SM-S906N`** (Korean) |
| SoC | **Qualcomm SM8450 = Snapdragon 8 Gen 1** (platform `taro`, Adreno 730, Vulkan 1.3) |
| RAM | 8 GB LPDDR5 |
| Android | **15** (SDK 35), build `S906NKSS7FYG8`, security patch 2025-08-01 |
| Kernel | **5.10.226-android12-9 (GKI)**, aarch64, Toybox |
| Bootloader | **UNLOCKED** (`ro.boot.flash.locked=0`, `vbmeta.device_state=unlocked`, `verifiedbootstate=orange`, `oem_unlock_allowed=1`, `warranty_bit=0` — Knox **not yet** tripped) |
| Root | **Unrooted** (release-keys, `ro.debuggable=0`, no su) |
| Partition scheme | **A-only + dynamic partitions** (super=sda29) |
| boot | `sda25` — **NO `init_boot`; the generic ramdisk lives inside `boot`** |
| vendor_boot | `sda27` (vendor ramdisk + DTB/DTBO) |
| recovery | separate partition |
| vbmeta | `vbmeta` / `vbmeta_system` |
| vm-bootsys | `sda28` — Samsung **protected VM / pKVM** image |
| Treble | on, VNDK 31 |
| Flash tool | download mode + **odin4** (same tool family as A90) |

---

## 2. HEADLINE FINDING — GKI 5.10 already has what A90's 4.14 lacked

The whole reason A90's server-distro leaned on seccomp + userspace tunnels + `.text` byte-patching was
that **stock 4.14 lacked container/namespace/overlay/VPN primitives** (`VETH=n`, `OVERLAY_FS=n`,
`USER_NS`/namespaces limited, no in-kernel WireGuard). On the Android **`android12-5.10` GKI base**
(what S906N is built from), the generic `gki_defconfig` shows:

| Config | GKI 5.10 base | A90 4.14 (for contrast) | Meaning |
| --- | --- | --- | --- |
| `CONFIG_NET_NS` | **=y** | limited | network namespaces |
| `CONFIG_OVERLAY_FS` | **=y** | **n** | overlay/union fs (container images) |
| `CONFIG_VETH` | **=y** | **n** | virtual eth pairs (container networking) |
| `CONFIG_BRIDGE` | **=y** | — | software bridge |
| `CONFIG_TUN` | **=y** | — | tun/tap (VPN, `/dev/net/tun`) |
| `CONFIG_CGROUPS` | **=y** | — | resource control |
| `CONFIG_WIREGUARD` | **=y (in-kernel)** | **absent** | WireGuard *without* userspace wireguard-go |
| `CONFIG_SECURITY_SELINUX` | **=y** | y | MAC present (Android SELinux) |
| `CONFIG_NAMESPACES` | **=y** | partial | base namespace support |
| `CONFIG_USER_NS` | **not set (off)** | off | the one gap — see below |
| `CONFIG_SECURITY_APPARMOR` | not set | absent | use SELinux, not AppArmor |
| `CONFIG_SECCOMP` | not listed in defconfig* | present | *almost certainly on in shipped kernel |

\* `CONFIG_SECCOMP`, `CONFIG_PID_NS`, `CONFIG_UTS_NS`, `CONFIG_IPC_NS` are **not listed in the generic
defconfig because they sit at their Kconfig default (`=y` when `NAMESPACES=y`)** or are forced by a
required Android config fragment. So "absent from defconfig" here means "left at default-on," **not**
"disabled." The authoritative source is the *shipped* S906N config (see §7 first rung), not this generic
base — Samsung layers its own fragments (adds RKP/KDP/PROCA/FIVE/DEFEX and may flip specific options).

### 2.1 Strategic consequence

**On S22+, kernel rebuild is OPTIONAL, not a prerequisite.** Stock GKI already gives:
- **rootful containers** (overlayfs + veth + bridge + netns + cgroups) — Docker/rootful-LXC class,
- **in-kernel WireGuard** (no wireguard-go hack),
- SELinux MAC (instead of the AppArmor A90 wanted but couldn't get).

The **only** genuine container gap is `CONFIG_USER_NS=off` → **no rootless containers / no unprivileged
user namespaces**. That is a *narrower, optional* want, and it is the main thing a kernel rebuild would
buy on S22+ (plus CVE-patchability and RKP removal). Contrast with A90, where rebuild was the *only*
door to containers at all.

**Net:** the S22+ "distro + server" endgame can likely be reached on the **stock kernel via standard
root**, with **zero rebuild** and the container/VPN story that A90 could never have — a much lighter
early path than A90's.

---

## 3. Two candidate S22+ paths (decide after §7 first rung confirms shipped config)

| | Path L — Light: root stock GKI | Path R — Rebuild: custom kernel |
| --- | --- | --- |
| Kernel | stock 5.10 GKI, unmodified | rebuilt from Samsung source, `CONFIG_UH/RKP/KDP=n` (+ `USER_NS=y` if wanted) |
| Root entry | **KernelSU or Magisk-patched `boot.img`** (standard, well-trodden on GKI) | custom kernel in `boot.img` |
| Containers | rootful ✅ (stock configs) | rootful ✅ + rootless (USER_NS) ✅ |
| WireGuard | ✅ in-kernel (stock) | ✅ |
| RKP/KDP | **kept ON** (hardening intact) | disabled (to boot) — trades hardening for control |
| CVE patching | ❌ (stock kernel frozen) | ✅ (you build it) |
| Effort / risk | low; one Knox trip on first custom-boot flash | higher; driver/DTB bring-up + Knox trip + maintenance |
| Best when | goal = distro+server+containers fast, keep hardening | goal = rootless/CVE-patch/RKP-off research |

**Likely recommendation (pending shipped-config confirmation):** start **Path L** — it reaches the whole
A90 endgame *plus real containers* with far less friction, keeps RKP on, and defers the rebuild. Escalate
to **Path R** only for the specific extras it uniquely buys. This mirrors the A90 lesson: keep hardening
on and take the lighter route unless a concrete capability forces the heavier one.

---

## 4. Boot / partition structure (what unpack will show)

- `boot` (sda25): Android boot image — **generic GKI kernel + generic ramdisk** (no separate `init_boot`
  on this model, unlike S23-era). This is the partition you patch for KernelSU/Magisk (Path L) or replace
  with a rebuilt kernel (Path R). **Boot-partition flash = soft-brick-recoverable via download mode.**
- `vendor_boot` (sda27): vendor ramdisk + **DTB/DTBO**. Usually left stock.
- `super` (sda29): **dynamic partitions** (`system`/`vendor`/`product`/`system_ext`/`odm` as logical
  volumes). Treble on. Debian userspace does **not** live here — it lives on external SD or a reformatted
  data partition, exactly like A90 (method transfers).
- `vbmeta` / `vbmeta_system`: AVB metadata. Unlocked bootloader accepts modified images; you may need
  `--disable-verity --disable-verification` when flashing a patched boot. **Never** flash Samsung-signed
  vbmeta variants blindly.
- `vm-bootsys` (sda28): **Samsung protected VM / pKVM** — do not touch; treat as forbidden.
- Forbidden partitions (same lines as A90, never write): `modem` / `efs` / `sec_efs` / `keymaster` /
  `vbmeta_samsung` (Samsung-fused) / `bootloader` (`sboot`/`xbl`/`abl`) / RPMB / `persist` / `vm-bootsys`.

---

## 5. Knox already tripped — one-way door is behind us (2026-07-06 correction)

- **UPDATE 2026-07-06:** the operator reports **Knox is already tripped (long ago)** on this unit — the
  earlier `warranty_bit=0` recon read is superseded. **The one-way decision no longer exists to make;**
  this is pure upside (flash custom `boot`/vbmeta freely, no fresh cost to weigh). Samsung Pay / Secure
  Folder / Widevine-L1 / warranty are already forfeit on this unit → it is effectively a lab/server device.
- Everything else stays **recoverable**: download mode + odin4 + stock firmware reflash recovers any
  boot-partition experiment (soft-brick), provided bootloader/`vbmeta_samsung`/pit/efs/RPMB stay untouched
  and anti-rollback (ARB) is not bumped.

### 5.1 Recovery backstop reality on Android 15 (TWRP vs odin4)

Operator is bringing up TWRP + verifying normal Android boot (2026-07-06). Practical S906N notes:
- **Primary backstop = download-mode + `odin4` + stock firmware `S906NKSS7FYG8`.** On Android 15 the
  community **S22+ Snapdragon TWRP builds are aging/[CLOSED] (Android 12/13 era)**; they boot but
  **`/data` FBE decryption is commonly broken** on A15, so treat TWRP as a *bonus* backup/flash tool, not
  the guaranteed recovery path the way it is on A90. Keep stock firmware staged as the real safety net.
- **vbmeta**: flash `vbmeta_disabled` (verity/verification off) to the USERDATA slot alongside the TWRP
  AP tar in Odin, or a patched/custom boot bootloops on dm-verity.
- **multidisabler**: run it in the TWRP terminal *before* rebooting to system, or stock ROM auto-restores
  stock recovery (TWRP "disappears") and/or re-enforces encryption. This is the usual "TWRP won't stick"
  cause.
- Quick triage: bootloop → vbmeta_disabled missing, or FBE mismatch after multidisabler → `Format Data`
  once (fine on a lab unit); boots but TWRP gone → multidisabler skipped; TWRP up but `/data` encrypted →
  expected A15/TWRP-generation mismatch, still usable for boot/super backup + stock restore.

---

## 6. What transfers from A90 (do not rebuild these)

- **The distro method itself**: native-glue/stock-kernel → Debian userspace → SSH → outbound cloudflared
  tunnel → deny-by-default containment. Proven end-to-end on A90; ~100% portable (only the device-glue
  layer is per-device, and on S22+ that layer is *smaller* because stock root gives more for free).
- **Staged artifacts**: the Debian bookworm/arm64 rootfs builder + image, cloudflared arm64 binary, the
  seccomp-profile approach, the safety/flash-gate machinery. Reuse directly.
- **The Wi-Fi lesson**: on A90, full `switch_root` tore down the vendor WLAN glue → chroot-under-native
  was chosen. On S22+ with stock root the WLAN stack stays owned by stock Android/vendor, so uplink is
  simpler — but re-verify AP+STA concurrency (qcacld) if SoftAP is wanted.
- **Safety discipline**: forbidden-partition lines, recoverable-envelope, no-committed-secrets, Gate-2.

---

## 7. First tractable rungs when S22+ becomes the target (in order)

All early rungs are read-only / low-risk. **Do not trip Knox until the fork decision in rung 3.**

1. **Acquire base materials (host-only, no device):**
   - Official firmware for `SM-S906N` build `S906NKSS7FYG8` (AP/BL/CP/CSC tars) — for stock rollback +
     partition/boot inspection. Stage under `workspace/private/` (never commit).
   - Kernel source for that exact model+build from `opensource.samsung.com` (search `SM-S906N`).
   - `odin4` (Linux) + aarch64 toolchain (or the AOSP/GKI clang for a rebuild later).
   - Unpack `boot.img`/`vendor_boot.img` (existing `mkbootimg` tooling handles GKI v3/v4 headers).
2. **Confirm the SHIPPED kernel config (read-only device, zero risk):** pull `/proc/config.gz` from the
   running S22+ (or read it from the rebuilt-source `.config`) and verify the §2 table against the real
   Samsung-fragmented config — especially `USER_NS`, `SECCOMP`, `OVERLAY_FS`, `VETH`, `WIREGUARD`, and
   which RKP/KDP/PROCA/FIVE/DEFEX are on. This turns the generic-defconfig assumptions into device facts.
3. **Fork decision Path L vs Path R (§3)** from rung-2 facts. Default to **L** unless a rung-2 gap
   (e.g. USER_NS needed) forces R.
4. **Path L bring-up:** patch `boot.img` with KernelSU or Magisk (this is the Knox-tripping flash — the
   first deliberate one-way step), boot, confirm root, then stand up chroot Debian on SD/data (A90 method)
   and validate `unshare`/overlayfs/veth actually work → **first real container on the phone.**
5. **Port the server stack:** Debian rootfs + SSH + cloudflared tunnel + containment, reusing A90 artifacts.
6. **(Optional) Path R later:** off-device rebuild of Samsung 5.10 source with `CONFIG_UH/RKP/KDP=n`
   (+ `USER_NS=y`), enumerate driver/DTB gaps, single gated boot-only flash. Only if rung-2/3 justified it.

**Resume trigger:** when the operator says "S22+ go," start at rung 1 (or rung 2 if firmware already
staged). This document + the two config findings mean no re-fogging — the fork is a decision, not a search.

---

## 8. Open questions to resolve during rungs 1–2 (so they don't surprise you later)

- Exact **shipped** status of `USER_NS` / `SECCOMP` on S906N (generic defconfig says USER_NS off; confirm).
- Which **RKP/KDP/PROCA/FIVE/DEFEX** Samsung fragments are active on this Android-15 build (newer gen than
  A90's; relevant only if Path R).
- `boot` header version (GKI v3 vs v4) and whether a patched boot needs `--disable-verity`.
- **AP+STA / SoftAP concurrency** on SM8450 qcacld (only if the SoftAP server feature is wanted).
- pKVM / `vm-bootsys` interaction — leave untouched; note it exists so it isn't mistaken for a target.

---

## 9. Sources (web, July 2026)

- Android GKI `android12-5.10` `gki_defconfig` (arm64): https://android.googlesource.com/kernel/common/+/android12-5.10/arch/arm64/configs/gki_defconfig
- Android kernel FAQ (GKI): https://source.android.com/docs/core/architecture/kernel/gki-faq
- Building kernels (AOSP): https://source.android.com/docs/setup/build/building-kernels
- Samsung open source (kernel source by model/build): https://opensource.samsung.com
- Companion strategic report: `docs/reports/KERNEL_REBUILD_RKP_FEASIBILITY_RESEARCH_DIRECTION_2026-07-05.md`

## 10. One-line takeaway

S22+ is the **freer** platform: unlocked + GKI 5.10 means the container/VPN primitives A90 never had are
**already in the stock kernel**, so the endgame is reachable by **standard root, no rebuild** (rebuild
becomes an optional extra for rootless/CVE/RKP-off). The only real one-way door is the **Knox trip** on
the first custom-boot flash. When you return: acquire firmware+source (rung 1) → confirm shipped config
(rung 2) → pick Path L (rung 3) → root + first container (rung 4). No fog, just a decision.
