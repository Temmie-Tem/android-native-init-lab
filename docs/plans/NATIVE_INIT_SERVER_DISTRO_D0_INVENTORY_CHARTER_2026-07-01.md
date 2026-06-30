# Server Distro Endgame — D0 Inventory & Host-Prep Charter

- Date: 2026-07-01
- Parent design: `docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md` (decisions A–E locked).
- Milestone: **D0** (roadmap §7). Goal: pin the facts D1–D4 depend on, and stage the host-side
  build inputs, **without committing to any device-modifying step**.
- Split: this charter has a **host-now** track (conflict-free, runnable today) and a
  **device-live** track (read-only, deferred to a window when the autonomous A90 loop is quiesced —
  V2631 separation rule; the loop is currently running live REPL call-proof flashes).

## A. Device-live inventory (READ-ONLY, deferred to a quiet loop window)

Run only when the autonomous loop is not flashing. All commands are read-only; **no** mkfs, mount
changes, or writes. Capture to a private run dir (`workspace/private/runs/server-distro/d0-<ts>/`),
do not commit raw output. Pre-vetted command set:

| # | Question | Command (native-init serial `cmdv1x` or busybox) | Why it matters |
| --- | --- | --- | --- |
| 1 | SD present + size/free | `df -h` / `/bin/busybox df -h` | C.1 SD loop-image fit (rootfs ~1–2 GB) |
| 2 | SD block device + fs | `/bin/busybox blkid` ; `cat /proc/partitions` | where the loop image lands |
| 3 | `userdata` block dev + size | `ls -l /dev/block/by-name/userdata` ; `cat /proc/partitions` | C.2 reformat target identity + size |
| 4 | partition-by-name map | `ls -l /dev/block/by-name/` | confirm only `userdata` is the C.2 target; everything else forbidden |
| 5 | current writable mounts | `cat /proc/mounts` | what native-init already mounts rw (staging spots) |
| 6 | busybox applets present | `/bin/busybox --list` | which coreutils exist for chroot bring-up (losetup, mount, chroot, switch_root, mkfs?) |
| 7 | loop/dm support | `ls /dev/loop* /dev/mapper 2>/dev/null` ; `cat /proc/filesystems` | C.1 loop-mount + ext4 availability in this kernel |
| 8 | kernel net/namespace knobs | `zcat /proc/config.gz 2>/dev/null \| grep -E 'NAMESPACES\|SECCOMP\|VETH\|TUN\|EXT4\|OVERLAY'` (if present) | feasibility of E.3 seccomp/netns, tun for tunnel, ext4, overlay |
| 9 | tun device | `ls -l /dev/net/tun 2>/dev/null` | D-public tunnel client (wireguard-go/cloudflared need /dev/net/tun) |
| 10 | RAM / cpu | `cat /proc/meminfo` ; `nproc` | service sizing |

Classification deliverable: a short table of {SD free, userdata dev+size, ext4+loop available
y/n, chroot/switch_root applets present y/n, /dev/net/tun present y/n, seccomp/netns config y/n}.
That table gates D1 (chroot MVP) readiness.

## B. Host-now staging (conflict-free; runnable today)

### B.1 Debian aarch64 rootfs builder
- **Prerequisite (system change, needs operator sudo):** install `debootstrap` + `qemu-user-static`
  and register the aarch64 binfmt handler. Host is x86_64, none present, no binfmt registered.
  This is the one host-now item that is NOT a no-op; flag before running.
- Plan: a reproducible builder script under
  `workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py` that runs
  `debootstrap --arch=arm64 --foreign` (+ `qemu-aarch64-static` second stage) into
  `workspace/private/builds/server-distro/debian-aarch64-rootfs/`, installs `dropbear`
  (MVP SSH) and minimal tooling, locks default credentials, and produces an ext4 loop image
  `debian-aarch64-<ts>.img` for SD staging. Output is private/gitignored; record only
  size + SHA-256 in the run report.
- Init-agnostic for D1: image runs `dropbear` directly; no distro init chosen yet (§3 defers
  systemd-vs-sysvinit to switch_root / D3).

### B.2 Tunnel client acquisition (D-public prep)
- Fetch `cloudflared` **linux-arm64** static binary (glibc) and `wireguard-go` arm64 build into
  `workspace/private/builds/server-distro/tunnel/`; record SHA-256. Do not configure/run; this is
  just staging the artifact for D-public. Cloudflare account/tunnel token creation is a separate
  later step (not in D0).

### B.3 No device action in track B
Nothing in B touches the A90. It is pure host build/download. It can proceed fully in parallel
with the autonomous loop.

## C. Exit criteria for D0

D0 is done when:
1. The device-live inventory table (§A) is captured and classified (one quiet-window pass).
2. A Debian aarch64 rootfs ext4 image (§B.1) exists privately with recorded size + SHA-256, with
   `dropbear` installed and default credentials locked.
3. `cloudflared`/`wireguard-go` arm64 binaries (§B.2) are staged privately with recorded SHA-256.

Then D1 (chroot MVP: push the §B.1 image to SD, `losetup` + `mount` + `chroot`, run a static
binary) is unblocked — and D1's first live step waits for the same quiet-loop window.

## D. Safety / separation

- §A is read-only; §B is host-only. No forbidden-partition access, no mkfs in D0 (the `userdata`
  reformat is D4 only). Carry all invariants from the parent design §8.
- **V2631**: do not run §A while the loop flashes. §B has no such constraint.
