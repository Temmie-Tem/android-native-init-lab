# Server Distro Endgame — D0 Host-Staging Result

- Date: 2026-07-01
- Unit: D0 track B (host-now staging), §B.1 + §B.2.
- Charter: `docs/plans/NATIVE_INIT_SERVER_DISTRO_D0_INVENTORY_CHARTER_2026-07-01.md`
- Design: `docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md`
- Device action: **none** (host-only; conflict-free with the autonomous A90 loop).

## What ran

Host: Ubuntu 26.04 x86_64. Installed `debootstrap`, `qemu-user-binfmt`, `binfmt-support`
(aarch64 binfmt registered with flags `POF`, interpreter `/usr/bin/qemu-aarch64`).

### B.1 — Debian aarch64 rootfs + ext4 image
Builder: `workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py`
(reproducible; one `sudo` run; `debootstrap` → in-chroot customize via binfmt → `mke2fs -d`).

- Suite/arch: Debian 12 **bookworm** / **arm64** (glibc 2.36, conservative for the 4.14.190 kernel).
- Packages: `minbase` + `dropbear-bin openssh-client ca-certificates iproute2 iputils-ping nano less procps`.
- rootfs tree (private): `workspace/private/builds/server-distro/debian-bookworm-arm64-rootfs` — 269 MiB.
- ext4 image (private): `debian-bookworm-arm64-20260701-024412.img` — 2.0 GiB, label `A90ROOT`,
  SHA-256 `210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc`.
- Hygiene (design E.6): **root password LOCKED** (`root:!*`), no SSH keys installed; stage marker
  `/etc/a90-server-distro-stage` records the unconfigured state.

**Key compatibility finding:** `/bin/ls` in the rootfs is `ELF aarch64 … for GNU/Linux 3.7.0`.
The bookworm glibc runtime minimum kernel is **3.7.0**, which the stock **4.14.190** kernel
satisfies. This de-risks the "glibc-on-old-kernel" concern for the D1 chroot MVP with on-disk
evidence (not just expectation).

### B.2 — Tunnel client staging
- `cloudflared` linux-arm64 (official latest release): static Go ELF aarch64, 36,980,327 bytes,
  SHA-256 `59816ce9b16db71f5bc2a86d59b3632a96c8c3ee934bde2bc8641ee83a6070eb`, staged at
  `workspace/private/builds/server-distro/tunnel/cloudflared-linux-arm64`.
- `wireguard-go`: deferred — no official prebuilt binary (build-from-source). Design picks
  Cloudflare Tunnel first; WG is the later "full ownership" upgrade, staged when needed.

All private artifacts (rootfs, image, cloudflared) are gitignored; only metadata/SHA recorded here.

## Status vs D0 exit criteria

- §C.2 (Debian rootfs ext4 image with dropbear + locked creds): **DONE** (B.1).
- §C.3 (cloudflared arm64 staged): **DONE** (B.2; wireguard-go intentionally deferred).
- §C.1 (device-live read-only inventory table): **PENDING** — track A, deferred to a quiet window
  when the autonomous A90 loop is not flashing (V2631 separation). The loop is currently running
  live REPL call-proof flashes.

## Next

When the loop is quiesced, run the §A read-only inventory (SD free, `userdata` dev+size,
loop/ext4 availability, chroot/switch_root applets, `/dev/net/tun`, seccomp/netns config) to
complete D0 and unblock D1 (push the §B.1 image to SD, `losetup` + `mount` + `chroot`).
