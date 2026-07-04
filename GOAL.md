# Goal: autonomous native-init forward loop (Codex)

Drive the A90 native-init project forward one **bounded V-iteration at a time** using
the proven cycle below. This file says WHAT to pursue; **`AGENTS.md` says HOW — its
safety invariants and flash gates are binding and override any sub-goal.**

> Running mode note: this loop runs unattended (incl. Codex bypass) and is **OPERATOR-PRE-AUTHORIZED
> BY PRINCIPLE (2026-06-15)**, not by an enumerated mechanism list. **The rule: the loop MAY
> self-authorize ANY device action that stays inside the "recoverable envelope" — it MUST NOT stop
> merely to ask for human approval, and MUST NOT treat a *new* mechanism as needing fresh approval as
> long as that mechanism stays inside the envelope.** Proceed.
>
> **Recoverable envelope (self-authorize freely):** an action whose only persistent writes are to the
> **boot partition** (via the checked flash helper) or to **runtime / ephemeral / temporary state**,
> AND which is **fully recoverable to `v2321` native init without manual partition repair**. This
> explicitly includes — but is **not limited to** — native-init flashes, ADSP activation,
> `tinymix`/PCM/`tinyplay`, USB-gadget reconfigure (control-channel preserved), booting a pinned
> stock-Android image, **temporary systemless Magisk measurement capsules** (auto-cleaned before
> rollback; writes confined to the Magisk module dir under `/data`; never format/wipe `/data`), and
> all reads/observation. Any future mechanism that meets the envelope test is likewise pre-authorized.
>
> **Bright line — NEVER self-authorize; STOP and report:** (1) any write to a **forbidden partition**
> (efs/sec_efs/modem/RPMB/keymaster/vbmeta/bootloader/dsp/keydata) = permanent brick; (2) raw
> `dd`/fastboot to any non-boot partition; (3) any **PMIC/regulator/GDSC/GPIO power write** (e.g. GPU
> GX-GDSC) — hardware-damage / hard-hang risk; (4) **destructive `/data`** (format/wipe userdata);
> (5) anything **not recoverable to `v2321`** (no known-good rollback image present).
>
> This relaxes only the *human-approval* gate; it does **not** relax the flash-safety machinery —
> every device step still obeys the `AGENTS.md` flash gates (rollback precondition, pinned + readback
> SHA, post-flash health check, **auto-rollback to `v2321`**, no cascading bad flashes); these stay ON
> because they are what makes unattended progress safe (a bad boot self-recovers and the loop
> continues; a disabled rollback would strand the device until morning). Audio writes keep to
> **observed/known-good routes and bounded/low amplitude — no blind smart-amp gain/boost poking**. The
> **"fails twice → stop" and anti-churn guards stay in force** (broad pre-auth removes *parking*, not
> the duty to stop grinding low-information plumbing). The operator accepts that a boot failure may
> need a manual TWRP/download-mode recovery in the morning — **that acceptance covers the boot
> partition ONLY.** When an action would cross the bright line or leave the recoverable envelope, STOP
> and report — never guess.

> **✅ OPERATOR GO (2026-07-04) — D-public is USER-AUTHORIZED and operator-driven; PROCEED.** (Supersedes the
> earlier same-day HOLD, which assumed authorization was pending — it was not.) The user confirmed the
> `D-PUBLIC-LIVE-PUBLISH` go and is actively driving D-public. First live publish (commit `8d25f793`:
> cloudflared quick Tunnel + public URL returning the smoke marker) and the follow-on server/HUD profile
> (`8ebbff49`) were authorized — **no gate was breached.** The loop MAY continue D-public work (quick-Tunnel
> exposure, the no-autoreboot server/HUD appliance profile, loopback smoke/HUD, and further D-public
> build-out) under the user's direction. **Safety machinery still applies (unchanged):** stay in the
> recoverable envelope (boot-partition + runtime state, always recoverable to `v2321`); the
> forbidden-partition / destructive-non-userdata / power-write bright lines are absolute; never commit the
> public URL, tunnel tokens, or credentials (private run dir only); and the D4 userdata guards (PARTNAME
> single-match, `compare_expected`, verified node, GPT-intact) stay ON for any userdata action. **Hygiene
> (advisory, not a halt):** when D-public is idle/unattended, prefer stopping `cloudflared` and/or rolling
> boot back to `v2321`; before a *persistent, always-on public* posture (named tunnel, resident exposed
> profile), fold in D-harden (seccomp/AppArmor/nftables/caps + named-tunnel auth) per design doc D + E §8.

> **🟢 OPERATOR CHARTER (2026-07-04) — read-only DEBIAN-EYE HARDWARE INVENTORY (user-requested). ⏫ DO THIS NEXT,
> BEFORE any further persistent-exposure LIVE rung (WSTA55+).** The user explicitly asked for this; it was not
> picked up while the loop had persistent-exposure-design momentum. Persistent-exposure DESIGN/source (WSTA52/53,
> no live action) may finish, but land the Debian hardware inventory before starting WSTA55+ live leased exposure.
> Capture what the Debian appliance actually sees for hardware, from inside the distro (chroot-under-native-PID1
> is fine — no switch_root needed, no Wi-Fi association needed). NON-DESTRUCTIVE / READ-ONLY: mount the staged
> Debian rootfs (SD image), start no exposure, collect and persist a hardware inventory, cleanup, roll back /
> return to native with `selftest fail=0`. Capture (Debian-side, redacted): `uname -a` (kernel/arch), `lscpu`
> or `/proc/cpuinfo` (core count/model/features), `free -h` + `/proc/meminfo` (MemTotal), `lsblk`/`/proc/partitions`
> (block devices + sizes), `ip -o link` + `ip -o addr` (interface names/state/mtu), `/sys/class/net` + `/sys/class/block`
> presence, `cat /proc/filesystems`, and a bounded `dmesg` HW-line sample. Also record which vendor userspace stacks
> are ABSENT in Debian (audio/ACDB, GPU/KGSL userspace, sensors, modem/RIL, camera, BT) vs the raw kernel nodes that
> exist. **REDACTION (hard):** REDACT MAC/BSSID/IP/gateway/serial/IMEI/MEID/UUID/PARTUUID/hostname/SSID/PSK and any
> routable address from BOTH the committed report AND any public artifact — keep only shapes/counts/models/sizes/kernel-config
> booleans (private run dir may hold fuller detail). Cross-check against the existing native-side D0 inventory
> (`workspace/private/runs/server-distro/d0-device-live-*/inventory_public_summary.json`: cpu_count=8, mem_total≈5.375 GiB,
> ext4/seccomp/tun=y, NET_NS/PID_NS/USER_NS/UTS_NS/IPC_NS=missing, VETH=n, OVERLAY_FS=n) — the Debian view should
> match the shared-kernel facts; note any divergence. Safety machinery unchanged (recoverable envelope → `v2321`,
> forbidden-partition/power bright lines, no committed secrets, D4 userdata guards). DoD = a committed redacted
> Debian-eye hardware inventory report + `selftest fail=0`.

> **🟣 OPERATOR STEER (2026-07-03) — D4C: RESOLVE THE ext2/ext4 FILESYSTEM-TYPE DIVERGENCE BEFORE the
> destructive userdata format.** Gate-2 caught that V3377 "fixed" the V3375 syntax failure by *dropping*
> `-t ext4` from the busybox `mke2fs` argv. BusyBox `mke2fs` with no `-t` makes **ext2 (no journal)**, not
> ext4 — it still mounts and passes functional tests, but it silently breaks locked design decision C
> ("userdata is plain **ext4**") and removes journaling, so an unclean power loss on the always-on
> appliance risks fs corruption + an unbootable server. The `superblock_magic=53 ef` probe does NOT
> distinguish ext2/3/4. **Before D4C live format, consciously choose + REPORT a journaled formatter:**
> (a) *preferred* — the plan's own SHA-pinned e2fsprogs `mkfs.ext4` (D4 plan line 140 / D4B design line
> 119); (b) busybox ext2 then `tune2fs -j` (only with a provenance-pinned, device-proven `tune2fs`);
> or (c) knowingly accept ext2/no-journal, record the power-loss/fsck tradeoff, and do NOT call it "ext4".
> **D4C DoD must verify the ACTUAL on-disk feature set (`has_journal`) of the formatted userdata, not just
> that it mounts.** Detail + options in `docs/plans/SERVER_DISTRO_D4_EXECUTION_BRIEF_2026-07-03.md` §5.
> All existing D4 safety guards (PARTNAME single-match, `compare_expected`, verified major:minor node,
> forbidden-name deny, GPT-intact) stay ON and unchanged; this steer is about filesystem TYPE only.

> **🟣 OPERATOR STEER (2026-07-03) — hot-reload H5 DONE, resume REPL frontier.**
> The dev-velocity infra side-quest (self-dd fast-flash + PID1 hot-reload) is the current thread:
> self-dd F0→F4-live DONE, hot-reload **H0→H5 DONE** (live-proven, all rolled back to `v2321`
> `fail=0`). H5 made a hot-reloaded init a full-service refresh via a **DRM-master handoff**:
> it preserves the already-running HUD child, adopts its pidfile in the reloaded PID1, refreshes
> tcpctl, restarts rshell from the opt-in flag, and refreshes selftest/pid1guard after service adoption.
> Live result/report: `docs/reports/NATIVE_INIT_V3368_HOT_RELOAD_AUTOHUD_H5_LIVE_2026-07-03.md`.
> Hard bright-line held: **no panel re-init, no PMIC/regulator/GDSC/backlight/GPIO power write**.
> **Fast-build is now the PRODUCTIZED DEFAULT** (commit `5f14cd49`): the V1393 build base splits the
> one-shot gcc into cached per-source `.o` (depfile `-MMD` + `source_sha256` + compiler/flags signature
> invalidation; `--init-build-mode one-shot` fallback; `--init-fast-verify-one-shot` SHA-parity guard),
> proven byte-identical (12.78→5.03 s parallel, 0.11 s incremental-module). **The flash-cycle infra epic
> is COMPLETE** (self-dd F0–F4 + hot-reload H0–H5 + fast-build default, all live-proven); resume the
> REPL v2c active epic below (or operator re-charter). Two complementary tools stand: hot-reload
> (init-code, ~2–5 s, ephemeral) + self-dd/TWRP (persistent/kernel, ~50–65 s, reboot-bound).

> **🟣 OPERATOR STEER (2026-07-03) — REPL SHARPENED: drive to a FINISH LINE, not open-ended breadth.**
> REPL v2c productization is DONE + Gate-2 signed off (C2E; 3-oracle byte-identical ground-truth map, C1
> fail-closed strengthened). The post-epic call-proof campaign has reached **SHAPE-SATURATION** — the
> loop's own 2026-07-01 steer already flagged it, and the Nth same-shape proof adds ~0 capability.
> **STOP open-ended same-shape call-proofs (low-information plumbing).** REPL stays the active epic, but
> it is now driven to a DEFINITE close, not perpetual breadth. **DoD to CLOSE the REPL epic:**
> 1. **Complete the ABI-shape matrix — the ONE uncovered shape = struct-pointer-arg / struct-return
>    marshalling.** Prove ONE representative under the packed resident-session harness (a function that
>    takes a `struct *` it fills, or returns a struct by value/pointer; pick a read-only,
>    classifier-SAFE target). After that the ABI matrix is CLOSED — **no more same-shape breadth for ANY
>    shape**, scalar/borrowed/owned-buffer/string/time all included.
> 2. **A FINITE observation-bundle set (assemble these, then STOP):** (a) kernel-vitals, (b) procfs/sysfs
>    live reader via the VFS-read keystone, (c) SoC-fingerprint [done], (d) **hardening-posture** = the
>    server-distro **D-harden** surface — read-only enumeration of which built-in kernel attack-surface
>    paths exist, for later hard-disable (see
>    `docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md` §6 E.3). Once these exist as
>    first-class REPL surfaces the instrument is COMPLETE — do not keep inventing new bundles.
> 3. **RETIRE-SUBSUMED stays in force:** never prove a getter whose value is readable via a `/proc`/`/sys`
>    node; reserve individual call-proofs for no-file-node targets or a genuinely-new ABI shape only.
> 4. Optional remainder only = U2 ergonomics + a one-page tool runbook, and ONLY if it improves real
>    usability — not a reason to keep the epic open.
> **When 1 + 2 are met the REPL epic CLOSES** (loop HALTS at the boundary; operator re-charters — the
> server-distro endgame is the standing next epic). **HARD (unchanged, do NOT loosen):** C1 fail-closed
> resolution, the call-safety classifier (DENY / behavior-changing tiers stay DENY — **never relax a
> tier to reach a struct/state target**), the rollback-to-v2321 gate, the recoverable envelope,
> fails-twice→STOP, **PACKED resident sessions only (reject <2-target sessions)**, and raw
> pointers/slide out of commits.

> **🟣 OPERATOR STEER (2026-07-03) — REPL FINISH-LINE CLOSED.**
> The remaining ABI-shape gap is now closed by the live `current_kernel_time64()` return-pair proof:
> a narrow call-pair v1-repl companion image captured same-call x0/x1 and proved the arm64
> `struct timespec64` aggregate-return contract (`x0=tv_sec`, `x1=tv_nsec`) against
> `ktime_get_real_seconds()` anchors. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_CURRENT_KERNEL_TIME64_RETURN_PAIR_2026-07-03.md`.
> The finite observation bundle set required above is also already present as first-class VFS-read
> surfaces: `kernel-vitals`, generic `/proc`/`/sys` reader, `soc-fingerprint`, `boot-config`, and
> `hardening-posture`. Therefore the REPL epic's close criteria are met. **STOP adding REPL
> same-shape breadth or new observation bundles.** Optional work is limited to the already-chartered U2
> ergonomics / one-page runbook if it directly improves operator usability; otherwise the next major
> work requires an operator re-charter, with the server-distro endgame remaining the standing next epic.

> **✅ OPERATOR GATE-2 SIGN-OFF (2026-07-03) — REPL epic CLOSE accepted; 2 residuals deferred.**
> Independently verified. **DoD #1 (struct-return) is genuinely met:** `current_kernel_time64` returns a
> 16-byte `struct timespec64` in x0/x1 per the arm64 PCS — a real aggregate-register-return mechanism,
> distinct from a scalar-x0 return AND from the already-proven caller-provided pointer-out result slots;
> the call-pair image flashed with matching readback SHA, captured same-call `x0=tv_sec`/`x1=tv_nsec`
> inside the `ktime_get_real_seconds` anchor window, rolled back to v2321 `fail=0`. **DoD #2 bundles are
> REAL implemented `vfs-bundle` surfaces** (confirmed in `a90_repl.py` `VFS_READ_BUNDLES`: `boot-config`,
> `hardening-posture`, `kernel-vitals`, `soc-fingerprint`), not claims. **The Tier-2 kernel-instrument
> (REPL) epic is CLOSED.** Two residuals — both correctly DEFERRED, neither a reason to reopen REPL:
> - **ABI residual (minor/known):** the x0/x1 ≤16-byte aggregate return is proven; the **>16-byte x8
>   indirect-sret** return and a **struct-pointer ARG the callee fills** remain unproven. Most kernel
>   functions use pointer-out params (already covered), so this is a known small gap — reopen only on
>   demand, do NOT grind it now.
> - **D-harden residual → belongs to the server-distro epic:** the `hardening-posture` bundle reads 6
>   `/proc/sys/kernel/*` hardening sysctl *values* (`kptr_restrict`, `dmesg_restrict`,
>   `perf_event_paranoid`, `modules_disabled`, `randomize_va_space`, `unprivileged_bpf_disabled`). The
>   fuller D-harden **attack-surface enumeration** (which built-in kernel interfaces/paths to hard-disable
>   for deny-by-default containment) is a server-distro containment-design task done against the real
>   threat model there — NOT open-ended REPL bundle breadth.
> **Standing next epic = the server-distro endgame** (`docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md`;
> design A–E locked, D0 host-staging done, device-live inventory pending). Loop halts pending operator re-charter.

> **🟣 ACTIVE NEXT EPIC (operator-chartered 2026-07-03) = SERVER-DISTRO ENDGAME.**
> The Tier-2 REPL epic is CLOSED (above). The single active epic is now the server-distro endgame:
> A90 native-init → Debian userspace → SSH → a public web service via an **outbound** Cloudflare tunnel.
> **Full spec (decisions A–E, roadmap D0→D-harden, safety §8) is LOCKED in
> `docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md` — read that doc; it is the spec.**
> D0 host-staging (Debian rootfs + `cloudflared`) is already DONE; the epic resumes at the D0 device-live
> half. The just-finished hot-reload + fast-build infra accelerates the native-init (Stage-0) glue work.
>
> **▶ FIRST BOUNDED UNIT = D0 device-live read-only inventory.** On the resident device, capture
> READ-ONLY (no writes, no mounts, no format):
> - SD card total size + free space, and its mountpoint/fs under native init;
> - `/data` (userdata) block-device path + size — **identify only, do NOT mount or format**;
> - native-init writable mounts (where a rootfs loop image could live);
> - on-device busybox applet inventory — especially `losetup`/`mount`/`chroot`/`switch_root`/
>   `mkfs.ext4`/`tar`/`unshare` presence (decides what D1+ can rely on vs must be staged).
> Then roll back to v2321, `selftest fail=0`. **DoD:** a private inventory record sufficient to size the
> D1 SD loop image and pick the rootfs mount. This is read-only recon; it unblocks D1 (chroot MVP).
>
> **HARD guardrails (design §8 + project invariants):** forbidden partitions NEVER
> (efs/sec_efs/modem/RPMB/keymaster/vbmeta/dsp/keydata/keyrefuge/bootloader/persist); **the D4 userdata
> reformat is the ONLY sanctioned /data destruction and is a SEPARATE, LATER, explicitly-gated unit —
> D0–D3 are all non-destructive / SD-based and must NOT touch userdata**; flash only via
> `native_init_flash.py` (boot only) or `odin4` with only `boot.img`; no PMIC/regulator/GDSC/GPIO/
> backlight, no from-scratch panel re-init; rollback v2321 + keep TWRP; recoverable envelope +
> fails-twice→STOP; keep rootfs/binaries/credentials/raw pointers out of commits. **Operator/loop
> separation (V2631):** the autonomous loop owns D0+ device-live work and commits; the operator (Claude)
> does Gate-2 verification + host RE + GOAL.md steering — no parallel device/coding work.

> **✅ STATUS (2026-07-03) — D0 device-live read-only inventory DONE.**
> Codex ran the D0 device-live half on resident v2321 with read-only serial observations only:
> no flash, no mount change, no format, no `/data` mount, and final standalone
> `selftest pass=11 warn=1 fail=0`. Private run:
> `workspace/private/runs/server-distro/d0-device-live-20260702T200338Z/`.
> Report:
> `docs/reports/SERVER_DISTRO_D0_DEVICE_LIVE_READONLY_INVENTORY_2026-07-03.md`.
> D0 facts now pinned: SD `/mnt/sdext` ext4 has ~50.4 GiB free; `userdata` is
> `/dev/block/sda33` (`PARTNAME=userdata`, ~110.42 GiB) and was identified only;
> D1 tooling has `losetup`/`mount`/`chroot`/`switch_root`/`tar`/`unshare`, ext4 and loop kernel
> support are present, but `/dev/loop*` nodes are absent and must be materialized/proven in D1;
> `CONFIG_TUN=y` but `/dev/net/tun` is absent for later D-public. Host D0 staging was already done
> (`SERVER_DISTRO_D0_HOST_STAGING_2026-07-01.md`), so **D0 is complete**.
> **NEXT bounded unit = D1 chroot MVP**: use the staged Debian ext4 image on SD, do the first
> non-destructive loop/mount/chroot/static-binary proof, and keep `userdata` untouched.

> **✅ OPERATOR GATE-2 + ▶ D1 CHARTER (2026-07-03) — D0 accepted; next unit = D1 chroot MVP.**
> D0 verified by operator: read-only throughout (no flash / mount change / format / `userdata` write),
> resident stayed v2321 `selftest fail=0`, inventory complete and informative. Pinned facts carried into
> D1: rootfs target = **`/mnt/sdext`** (SD, ext4, rw, ~50 GiB free — the 2 GiB Debian image fits);
> **`userdata=/dev/block/sda33` stays UNTOUCHED**; busybox has `losetup`/`mount`/`chroot`/`switch_root`/
> `tar`/`unshare`; ext4 + loop kernel support present BUT **`/dev/loop*` nodes are ABSENT**; `mkfs.ext4`
> absent (not needed — image is pre-built); `VETH=n`/`OVERLAY_FS=n` (noted for D-harden later).
>
> **▶ NEXT BOUNDED UNIT = D1 chroot MVP (non-destructive, SD-only, NO flash):** on the resident
> native-init device —
> 1. Stage the pre-built Debian ext4 image
>    (`workspace/private/builds/server-distro/debian-bookworm-arm64-20260701-024412.img`, SHA
>    `210fc1f9…`, 2 GiB) onto **`/mnt/sdext`** via the established device push channel.
> 2. **Materialize a runtime loop node** (the D0-identified gap): `mknod /dev/loop0 b <loop-major> 0`
>    with the loop major from `/proc/devices`, or prove `losetup -f` / `mount -o loop` auto-handles it.
> 3. `losetup` + `mount` the image ext4 rw (or `mount -o loop`) at an SD-backed mountpoint.
> 4. `chroot` in and run a known Debian binary (e.g. `/bin/busybox` / `/bin/ls` / `cat /etc/debian_version`
>    / `uname -a`) to prove the portable Debian userspace EXECUTES on the stock 4.14 kernel, live.
> 5. Clean up: exit chroot, `umount`, `losetup -d`, remove materialized loop nodes.
> **DoD:** a known Debian binary runs inside the loop-mounted chroot; cleanup leaves no dangling
> mount/loop; device recoverable to v2321 (a reboot clears all D1 runtime state, the SD image is inert).
> Unblocks D2 (dropbear SSH inside the chroot).
>
> **Guardrails:** all runtime / SD-only (no boot flash, no partition write, no forbidden partitions);
> **`userdata` NEVER touched** — the D4 reformat is the only sanctioned `/data` destruction and is a
> separate, later, explicitly-gated unit; no PMIC/regulator/GDSC/GPIO/backlight/panel writes; recoverable
> to v2321; **fails-twice on the same loop/mount/chroot approach → STOP + report** (do not force
> loop-node/mount hacks); keep the rootfs image / binaries / credentials out of commits; scoped
> `git add` + a `docs/reports/` report.

> **🟣 OPERATOR STEER (2026-07-03) — server-distro non-destructive D-ladder: PROCEED CONTINUOUSLY, do NOT
> halt per-rung.** D0→D3 are all non-destructive, SD-based, and fully recoverable to v2321, and their
> designs are already fixed in the design doc — so do NOT stop at each rung boundary to wait for an operator
> re-charter (that cadence is too slow, and it is what kept stalling the loop). **Run the non-destructive
> ladder continuously:** when a rung passes (commit + `docs/reports/` report + device recoverable to v2321),
> **self-charter and immediately begin the next rung per the design doc** — D1 chroot MVP → D2 dropbear SSH
> in chroot → D3 `switch_root` PID1 handoff — keeping each rung individually bounded (its own commit/report,
> its own clean recoverable state). Every non-destructive rung is inside the recoverable envelope and is
> already self-authorized by the top-of-file pre-authorization. **HALT and wait for the operator ONLY at:**
> (1) **D4** (userdata reformat = destructive `/data` disposal — HARD gate; needs explicit operator
> authorization; NEVER self-authorize); (2) a genuine **fails-twice** blocker on the same approach; (3) a
> real **design ambiguity/decision** not resolvable from the design doc; (4) **D-public** first live tunnel
> exposure (external-facing — operator confirms before publishing). The operator Gate-2-verifies each passed
> rung ASYNCHRONOUSLY via periodic nudge-checks and intervenes only if a rung drifts or goes off-spec — you
> do NOT wait for that verification to proceed to the next non-destructive rung.

> **✅ STATUS (2026-07-03) — D1 chroot MVP DONE.**
> Codex staged the prebuilt Debian Bookworm arm64 ext4 image on SD at
> `/mnt/sdext/a90/runtime/debian-bookworm-arm64-20260701-024412.img` (SHA-256
> `210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc`), materialized runtime
> `/dev/loop0` from loop major `7`, mounted the image at `/mnt/sdext/a90/runtime/distro-root`,
> entered the chroot, and executed known Debian binaries. Live proof reported Debian `12.14`,
> `stage_marker=present`, `A90D1_CHROOT_DONE`, cleanup mount absent, cleanup loop node absent,
> final v2321, and final selftest `fail=0`. Report:
> `docs/reports/SERVER_DISTRO_D1_CHROOT_MVP_2026-07-03.md`. No flash, no format, no forbidden
> partition write, and `userdata=/dev/block/sda33` stayed untouched. Persistent D1 residue is limited
> to the inert SD image.
>
> **▶ NEXT BOUNDED UNIT = D2 SSH-in-chroot (non-destructive, SD-only, NO flash):** reuse the same
> SD-backed Debian image, mount/chroot it, start `dropbear` directly inside the chroot, and prove SSH
> login over the native-init USB/NCM path. Use temporary key-only credentials under
> `workspace/private/runs/server-distro/`; do not commit keys, host keys, raw transcripts, or
> credentials. Bind/listen only on the local native-init/NCM path for this proof; do NOT expose a
> public tunnel (D-public remains an explicit later gate). Cleanup must stop `dropbear`, unmount,
> detach/remove runtime loop nodes, leave no dangling mount/process, keep resident v2321
> `selftest fail=0`, and keep `userdata` untouched. **DoD:** a host SSH command authenticates with
> the temporary key to the chrooted dropbear and returns a bounded marker command from Debian.

> **✅ STATUS (2026-07-03) — D2 SSH-in-chroot DONE.**
> Codex reused the SD-backed Debian image from D1, mounted/chrooted it, generated per-run temporary
> SSH material under `workspace/private/runs/server-distro/`, temporarily configured key-only root
> auth inside the chroot, started chrooted `dropbear` with password auth and forwarding disabled,
> and proved host SSH login over the native-init USB/NCM path with `A90D2_SSH_MARKER`,
> Debian `12.14`, and `stage_marker=present`. Cleanup restored `etc/shadow`, removed temporary SSH
> files, stopped dropbear, unmounted/detached the loop device, and a separate postcheck proved no
> mount, loop node, dropbear process, or D2 SSH listener remained. Final v2321 selftest stayed
> `fail=0`. Report: `docs/reports/SERVER_DISTRO_D2_SSH_IN_CHROOT_2026-07-03.md`. No flash, no
> format, no forbidden partition write, no public tunnel exposure, and `userdata=/dev/block/sda33`
> stayed untouched.
>
> **▶ NEXT BOUNDED UNIT = D3 switch_root PID1 handoff (non-destructive, SD-only):** prove the
> distro-root handoff path using the same SD image, with native-init/vendor-glue control preserved
> enough to observe success and recover to v2321. D3 may require a checked boot artifact or
> hot-reloadable native-init glue because `switch_root` is PID1-sensitive; do the static design gate
> first and keep the unit bounded. **DoD:** the device enters the SD-backed distro root through the
> `switch_root` path, emits an unambiguous Debian-side marker, preserves the required native-init
> control/recovery path, then returns/reboots/rolls back to v2321 with `selftest fail=0`. If the
> exact PID1/control-preservation design is ambiguous, STOP and write the design note instead of
> improvising.

> **🟡 D3 STATIC GATE STOP (2026-07-03) — design decision required before live `switch_root`.**
> Static gate found the staged Debian rootfs has no real PID1 candidate: no `/sbin/init`, no
> `/usr/sbin/init`, no `/lib/systemd/systemd`, no `/etc/inittab`; installed packages include
> `init-system-helpers` and `sysvinit-utils`, but not `sysvinit-core`, `systemd-sysv`, `openrc`, or
> `runit`. This matches the design's deferred init-system sub-decision at A.2. A live D3 attempt would
> either improvise `/bin/sh`/ad-hoc PID1 (not the promised "distro init = PID1") or replace native-init
> PID1 without an explicit observation/recovery control path. Per the D-ladder steer, this is a real
> design ambiguity, so the loop STOPS before live D3. Report:
> `docs/reports/SERVER_DISTRO_D3_SWITCH_ROOT_STATIC_GATE_2026-07-03.md`. Recommended next charter:
> choose the D3 init system (likely `sysvinit-core` over systemd for the stock 4.14 kernel), choose
> whether D2-style dropbear survives the handoff or distro init starts it, then build a checked
> non-destructive handoff unit that can emit a Debian-side marker and recover/reboot to v2321.

> **✅ OPERATOR GATE-2 (D2 accepted) + ▶ D3 DESIGN DECISION + CHARTER (2026-07-03).** D1 and D2 verified
> Gate-2 clean (non-destructive/SD-only, `userdata` untouched, resident v2321 `selftest fail=0`, keys/creds
> kept out of commits; D2 proved key-only SSH into the chrooted Debian over the NCM path). The D3 static-gate
> STOP was the correct call — a real design ambiguity. **Operator resolves it:**
> - **① Init system = `sysvinit-core`** (NOT systemd for this first handoff): lowest-friction PID1 on the
>   stock Android 4.14 kernel (no cgroup2/logind/dbus friction); systemd is a deferred later-optional upgrade.
> - **② Observation/control path = `dropbear` started EARLY by sysvinit** (an rc/inittab entry), reachable
>   over the **persisted native-init NCM path**; the rc script must (re)assert the NCM interface IP/route so
>   the host can SSH in AFTER the handoff and read the D3 marker (`/proc/1/comm`=`init`, `debian_version`),
>   proving distro-init-as-PID1.
> - **③ Recovery backstop = a MANDATORY bounded UNCONDITIONAL auto-reboot** scheduled by the D3 rootfs init
>   as its FIRST action (background `sleep <90-180s>; reboot -f` or equivalent). The device MUST self-return
>   to resident **v2321** within that window regardless of whether SSH/observation succeeds; the boot
>   partition stays v2321 (untouched), so a manual power-cycle is the ultimate backstop. This mandatory
>   auto-reboot is what keeps D3 inside the recoverable envelope.
> - **④ Handoff mechanism = a checked native-init helper / hot-reloadable PID1 path** that SHA/path-verifies
>   the SD Debian image, prepares/moves the `/proc` `/sys` `/dev` mounts, then `switch_root <distro-root>
>   /sbin/init`. SHA-check BEFORE the pivot.
>
> **▶ NEXT BOUNDED UNIT = D3 switch_root PID1 handoff, in two parts:** (a) HOST-ONLY rootfs update — install
> `sysvinit-core` into the Debian image + add the early-`dropbear` rc entry, the NCM-IP reassert, the
> mandatory bounded auto-reboot, and a Debian-side D3 marker; rebuild/re-stage the SD image (new SHA, keep
> it out of commits). (b) LIVE handoff — perform the checked `switch_root`, observe the D3 marker over SSH
> (distro init = PID1), let the mandatory auto-reboot return the device to v2321, confirm resident v2321 +
> `selftest fail=0`. **DoD:** Debian `sysvinit` observed as PID1 post-`switch_root` via the NCM SSH marker,
> then automatic recovery to v2321 `fail=0`. **Guardrails:** non-destructive/SD-only, NO flash, `userdata`
> NEVER touched, no forbidden partitions, no PMIC/panel writes; the mandatory bounded auto-reboot is
> REQUIRED (D3 is the riskiest non-destructive rung — PID1 replacement — and must self-recover); keys/creds/
> rootfs/binaries out of commits; fails-twice on the same handoff approach → STOP + report. **After D3, D4
> (userdata reformat) is the HARD operator gate — HALT and get explicit authorization; never self-authorize.**

> **✅ STATUS (2026-07-03) — D3A sysvinit rootfs HOST-ONLY prep DONE.**
> Codex added `workspace/public/src/scripts/server-distro/prepare_d3_sysvinit_rootfs.py`, a `fakeroot`
> host builder that starts from the D1/D2 Debian rootfs, downloads/extracts `sysvinit-core` plus the
> minimal sysv package set, installs an explicit `/etc/inittab` sysinit entry, installs
> `/etc/a90-d3-firstboot`, and builds a private 2 GiB ext4 image labeled `A90D3ROOT`. The firstboot
> script schedules the mandatory bounded auto-reboot as its first action, reasserts the USB-local NCM
> interface, writes `A90D3_MARKER`, and starts key-only dropbear only if the later live runner stages a
> per-run key. Private image:
> `workspace/private/builds/server-distro/d3-sysvinit-20260703T080236Z.img`, SHA-256
> `2ee61172116be7578fddbfcbe491c1c29e3e4c7cf485376191019417c69880c3`; intended SD path:
> `/mnt/sdext/a90/runtime/debian-bookworm-arm64-d3-sysvinit.img`. Report:
> `docs/reports/SERVER_DISTRO_D3A_SYSVINIT_ROOTFS_HOST_2026-07-03.md`. Host-only: no device command, no
> flash, no mount on device, no `switch_root`, no public tunnel, no credentials in artifact, and
> `userdata` untouched.
>
> **▶ NEXT BOUNDED UNIT = D3B live checked switch_root handoff:** add the native-init handoff surface
> that verifies the D3 image SHA/path, prepares/moves `/proc` `/sys` `/dev`, then executes
> `switch_root <distro-root> /sbin/init`. The live runner must stage the D3 image to the intended SD
> path, stage a per-run temporary SSH key into the mounted image, invoke the checked handoff, observe
> `A90D3_MARKER` over SSH after handoff (`/proc/1/comm` should be `init`), then wait for the mandatory
> auto-reboot and confirm resident v2321 `selftest fail=0`. NO flash, NO `userdata`, NO D-public.

> **🟡 D3B FEASIBILITY STOP (2026-07-03) — current `NO flash` charter contradicts PID1 handoff.**
> Static/live command-surface gate showed resident `v2321-usb-clean-identity-rodata` has no
> `reload INIT-RELOAD-EXECVE` command (`reload` returns unknown), and existing `run /bin/busybox
> switch_root` cannot satisfy D3 because BusyBox requires `switch_root` to run as PID1. Therefore the
> current resident cannot execute a real `switch_root <distro-root> /sbin/init` handoff without first
> adding a PID1 command surface, and adding that surface requires either a checked native-init flash or
> first moving to a hot-reload-capable resident — both contradict the current D3B **NO flash** guardrail.
> Report: `docs/reports/SERVER_DISTRO_D3B_SWITCH_ROOT_FEASIBILITY_STOP_2026-07-03.md`. Next charter must
> explicitly choose: (1) allow one checked `native_init_flash.py` boot flash to a D3-capable candidate
> with normal rollback gates and no `userdata`, (2) allow one checked flash to a hot-reload-capable
> resident and then hot-reload D3 glue, or (3) downgrade to a non-PID1 lower rung that is not D3.

> **✅ OPERATOR DECISION + D3B CHARTER AMENDMENT (2026-07-03) — choose OPTION 1: allow ONE checked boot
> flash.** The D3B feasibility stop was correct — the "NO flash" line in the earlier D3 charter was an
> operator over-constraint, not a safety rule, and it made a real `switch_root`→PID1 handoff impossible
> (`switch_root` must run as PID1; resident v2321 PID1 has no such command and no `reload`). **Resolution:
> D3B MAY perform exactly ONE checked boot flash** of a D3-capable native-init candidate via
> `native_init_flash.py`. This is a **boot-partition-only, pinned + readback-SHA, auto-rollback-to-v2321
> flash — already inside the top-of-file recoverable envelope** (identical in kind to every audio/GPU/Wi-Fi
> test-build flash); it is NOT the D4 gate and needs no further approval. **Amended D3B unit:**
> 1. Build a **D3-capable native-init candidate** (next `vNNNN-server-distro-switchroot`, bump init
>    version) that adds a **gated PID1 handoff command** (e.g. `switch-root-to-distro <image> <sha>`):
>    from PID1 it SHA/path-verifies the D3 sysvinit image, loop-mounts it, moves `/proc` `/sys` `/dev`,
>    then `switch_root <distro-root> /sbin/init`. (This same command is the seed of the future D4+
>    appliance auto-handoff, so build it as a real feature, not a throwaway.)
> 2. **ONE checked boot flash** of that candidate (rollback target stays **v2321**).
> 3. Boot it; native-init wakes HW (NCM); stage the D3 image to
>    `/mnt/sdext/a90/runtime/…-d3-sysvinit.img` + a per-run key; run the handoff command → PID1
>    `switch_root` → Debian **sysvinit = PID1**.
> 4. Observe `A90D3_MARKER` / `/proc/1/comm=init` over the NCM SSH path (early key-only dropbear from the
>    D3A firstboot script).
> 5. The D3A **mandatory bounded auto-reboot** returns the device to the flashed candidate; then
>    **rollback-flash to v2321** and confirm `selftest fail=0`.
> **DoD:** Debian sysvinit observed as PID1 after a PID1-driven `switch_root`, then clean recovery to
> resident v2321 `fail=0`. **Guardrails:** exactly ONE D3-candidate boot flash + ONE v2321 rollback flash
> (both checked, boot-only); **`userdata` NEVER touched**; the mandatory auto-reboot is REQUIRED;
> keys/rootfs/binaries/credentials out of commits; fails-twice on the same handoff → STOP + report.
> After D3B passes, continue the ladder toward D4 (now operator-pre-approved, see below); D-public
> remains a separate user gate.

> **✅ STATUS (2026-07-03) — D3B live checked `switch_root` handoff DONE.**
> Codex ran the V3372 D3-capable native-init candidate (`0.11.133`,
> `v3372-server-distro-switchroot-stdio`, SHA
> `09db071ae6bebe538d0f9c6c62f6e86b28a4b1a2a6954f1910f8d189675cc653`) with the usrmerge-fixed D3
> sysvinit image. The runner generated a per-run keyed image, **pre-staged it on SD before candidate
> flash**, and verified the remote SD SHA matched the keyed image SHA
> `3251fcea80bffc0d35e25143786e13b023a7dd25c72d662088d268ef57aa996e`. Live proof observed
> `A90D3_MARKER`, Debian `12.14`, `/proc/1/comm=init`, `/proc/1/exe=/usr/sbin/init`,
> `dropbear_started=1`, `autoreboot_sec=120`, and `userdata=untouched` over NCM SSH after the PID1
> `switch_root`. The mandatory auto-reboot returned to the V3372 candidate with `selftest fail=0`;
> final checked-helper recovery from TWRP restored v2321 (`0.9.285`,
> `v2321-usb-clean-identity-rodata`) with `selftest fail=0`. Report:
> `docs/reports/SERVER_DISTRO_D3B_SWITCHROOT_LIVE_PASS_2026-07-03.md`. The D3B runner now falls back
> from `--from-native` rollback to direct TWRP recovery ADB rollback when recovery is already present.
> **D3B is complete; D4 preflight is now unblocked. D-public remains a separate external-exposure gate.**

> **✅ OPERATOR APPROVAL — D4 userdata reformat PRE-AUTHORIZED (device owner, 2026-07-03).** The operator
> has explicitly approved D4. The loop **no longer HALTS for a separate human approval at D4** — it may
> reformat `userdata` and stand up the persistent appliance as part of the continuous ladder. This is a
> deliberate, irreversible disposal of Android `/data` on this dedicated research device, accepted by the
> owner. **The safety machinery around D4 stays FULLY ON — approval removes only the human-gate stop, not
> the guards:**
> 1. **Precondition — D0→D3 must have PASSED first.** Do NOT reformat `userdata` until the distro stack is
>    proven working (D1 chroot, D2 SSH, **D3 switch_root PID1 handoff live-proven**) on the SD image. No
>    jumping straight to D4.
> 2. **`userdata` (`/dev/block/sda33`) ONLY.** Re-derive the target by `PARTNAME=userdata` at run time
>    (rdev is not stable across boots) and hard-verify it before any `mkfs`. NEVER touch any other
>    partition — `efs`/`sec_efs`/`modem`/RPMB/keymaster/`vbmeta`/`dsp`/`keydata`/`keyrefuge`/bootloader/
>    `persist` stay forbidden; the GPT table stays intact (Odin-recoverable).
> 3. **Recovery preconditions present before the reformat:** v2321 + v2237 + v48 boot images and TWRP
>    available, and the Debian rootfs staged so it can be re-placed onto the new ext4 `userdata`. Verify
>    these in a D4 preflight; abort if any is missing.
> 4. **Bounded + reported:** D4 is still a bounded unit with its own commit/report and a preflight that
>    prints the exact target device/PARTNAME/size before `mkfs`. fails-twice → STOP + report.
> 5. **D-public is a SEPARATE gate, NOT covered by this approval** — first external/tunnel exposure still
>    HALTS for the user. So the loop may now flow D3B → D4 (appliance on `userdata`) and then STOP at
>    D-public.
>
> **🟣 D4 EXECUTION PLAN LOCKED (2026-07-03).** Use
> `docs/plans/SERVER_DISTRO_D4_USERDATA_APPLIANCE_PLAN_2026-07-03.md` as the D4 runbook. D4 is split
> into bounded units: **D4A read-only preflight** (no writes/mounts/format), D4B D4-capable native-init
> surface, D4C `userdata` format+populate, and D4D appliance `switch_root` proof. **Immediate next
> bounded unit = D4A only:** re-derive `PARTNAME=userdata`, print exact target device/PARTNAME/size,
> verify v2321/v2237/v48/TWRP, verify the clean rootfs source, and emit a report with `NO FORMAT
> PERFORMED`. D4C must not run until D4A passes and D4B has a statically validated fail-closed surface.

> **✅ STATUS (2026-07-03) — D4A userdata read-only preflight DONE.**
> D4A ran read-only on resident v2321 and performed **NO FORMAT / NO MOUNT / NO FLASH / NO REBOOT**.
> Authoritative target was re-derived from sysfs `PARTNAME=userdata`: single scan block `sda33`,
> `dev=259:27`, `size=118567645184` bytes (`110.42 GiB`), `ro=0`, not mounted, no forbidden-partition
> collision. Current native-init lacks `/dev/block/sda33` materialization and lacks `mkfs.ext4`, so
> **D4B must provide fail-closed userdata block-node materialization and a known formatter before D4C**.
> Recovery envelope and clean rootfs source passed: v2321/v2237/v48 present, D3 source image SHA
> `6f1960eb4332e1a22d5da1c98e990352c58d80157fbe6286b53ec9fe8ebe59f7`, D3B pass/TWRP evidence present.
> Report: `docs/reports/SERVER_DISTRO_D4A_USERDATA_PREFLIGHT_2026-07-03.md`.
> D4B design/runbook is now pinned at
> `docs/plans/SERVER_DISTRO_D4B_NATIVE_INIT_SURFACE_DESIGN_2026-07-03.md`: authoritative target discovery
> is sysfs `PARTNAME=userdata`, by-name is optional cross-check only, D4B must materialize a private
> `/dev/block/a90-userdata` node from verified `MAJOR:MINOR`, and formatter choice must be proven
> (`mkfs.ext4` staged/bundled or device-proven BusyBox `mke2fs -t ext4`) before D4C.
> **NEXT bounded unit = implement/build D4B native-init fail-closed surface**; D4C remains disallowed until
> D4B static validation and candidate health pass, and D-public remains a separate later gate.

> **✅ STATUS (2026-07-03) — D4B native-init source/build DONE.**
> Codex implemented the D4B command surface in native-init and built `V3373`:
> `A90 Linux init 0.11.134 (v3373-server-distro-userdata-appliance)`, boot SHA
> `78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d`.
> Added commands: `userdata-appliance-preflight`, `userdata-appliance-format`,
> `userdata-appliance-populate`, and `switch-root-to-userdata`. All require
> `SERVER-DISTRO-D4-USERDATA-APPLIANCE`; mutating commands re-derive sysfs
> `PARTNAME=userdata`, compare caller-pinned `devname/dev/sectors`, and materialize
> `/dev/block/a90-userdata` from verified `MAJOR:MINOR` only after identity passes.
> Source/build validation passed, but this unit performed **NO FLASH / NO REBOOT / NO FORMAT / NO MOUNT**.
> Report: `docs/reports/NATIVE_INIT_V3373_SERVER_DISTRO_D4B_USERDATA_APPLIANCE_SOURCE_BUILD_2026-07-03.md`.
> Execution brief: `docs/plans/SERVER_DISTRO_D4_EXECUTION_BRIEF_2026-07-03.md`.
> **NEXT bounded unit = D4B candidate-health validation**: confirm rollback/TWRP preconditions, flash the
> exact V3373 artifact only through `native_init_flash.py`, verify `version`/`status`/`selftest`, run only
> device-side `userdata-appliance-preflight`, and roll back to v2321 unless D4C starts immediately under
> the destructive runbook. D4C remains disallowed until this candidate-health gate passes and the formatter
> path is device-proven.

> **✅ STATUS (2026-07-03) — D4B candidate-health LIVE PASS, rolled back cleanly.**
> Codex flashed the exact V3373 artifact through `native_init_flash.py`, TWRP/recovery ADB came up,
> remote SHA and boot readback SHA both matched
> `78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d`, and the candidate booted as
> `A90 Linux init 0.11.134 (v3373-server-distro-userdata-appliance)` with `selftest fail=0`.
> The only D4B live command executed was read-only `userdata-appliance-preflight`, after auto-menu
> hide/retry. It passed with `target.source=partname-scan`, `target.devname=sda33`,
> `target.dev=259:17`, `target.sectors=231577432`, `target.size_bytes=118567645184`, `target.ro=0`,
> `target.mounted=0`, `target.node_exists=0`, and `node_materialized=0`.
> No format, no populate, no `switch-root-to-userdata`, and no userdata node materialization occurred.
> v2321 rollback then used the checked helper; boot readback SHA matched
> `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`, final version was
> `0.9.285 (v2321-usb-clean-identity-rodata)`, and final `selftest fail=0`.
> Report:
> `docs/reports/NATIVE_INIT_V3374_SERVER_DISTRO_D4B_CANDIDATE_HEALTH_LIVE_2026-07-03.md`.
> D4A saw the same `sda33` target as `dev=259:27`, while V3373 saw it as `259:17`; therefore D4C must
> treat `target.dev` as a **same-session guard only** and must parse/pass the live preflight major:minor
> from the same candidate session before any mutating command. **NEXT bounded unit = D4C entry prep**:
> prove or add a non-destructive formatter probe, prepare/stage a SHA-pinned rootfs tarball under
> `/mnt/sdext/a90/runtime/`, then re-enter V3373 and run fresh same-session preflight before the
> destructive format. D-public remains a separate later gate.

> **✅ STATUS (2026-07-03) — D4C entry formatter-probe source/build DONE; live still pending.**
> Codex added `userdata-appliance-formatter-probe` and built `V3375`:
> `A90 Linux init 0.11.135 (v3375-server-distro-userdata-formatter-probe)`, boot SHA
> `460fbbc137478695c9271a80fd9e0e5dedb96975ee9e69bd6b67c9a72db1ecdb`.
> The probe is non-destructive: it accepts only an approved `/mnt/sdext/a90/runtime/` regular-file path,
> creates a bounded 4-64 MiB probe file, runs the same BusyBox `mke2fs -t ext4 -F -L A90D4PROBE`
> formatter path, verifies the ext4 superblock magic, unlinks the probe file, and reports
> `userdata_touched=0`. Mutating userdata commands are unchanged and still require fresh same-session
> `PARTNAME=userdata` preflight identity. Static validation passed, but this unit performed **NO FLASH /
> NO FORMAT / NO USERDATA TOUCH**. Report:
> `docs/reports/NATIVE_INIT_V3375_SERVER_DISTRO_D4C_FORMATTER_PROBE_SOURCE_BUILD_2026-07-03.md`.
> **NEXT bounded unit = D4C entry live prep**: prepare/stage the rootfs tarball under SD runtime, flash
> exact V3375 through `native_init_flash.py`, run candidate health, run read-only preflight plus
> formatter-probe only, then roll back to v2321 unless the destructive D4C format starts immediately.

> **✅ STATUS (2026-07-03) — D4C rootfs tarball staging runner documented/static-validated; live staging still pending.**
> Codex added `workspace/public/src/scripts/server-distro/prepare_d4c_userdata_rootfs_tarball.py`, a
> non-destructive host runner that requires resident v2321 and `selftest fail=0`, verifies the clean D3
> sysvinit rootfs markers, creates a deterministic root-owned tar stream under `workspace/private/runs/`,
> uploads it to `/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar`, and verifies the remote SHA. It does
> **NO FLASH / NO FORMAT / NO USERDATA TOUCH** and does not call `mkfs`, `mke2fs`,
> `userdata-appliance-format`, or `switch-root-to-userdata`. Static validation passed:
> `py_compile` plus `tests.test_prepare_d4c_userdata_rootfs_tarball`.
> Report:
> `docs/reports/SERVER_DISTRO_D4C_ROOTFS_TARBALL_STAGING_RUNNER_2026-07-03.md`.
> **NEXT bounded unit = D4C entry live prep**: run the tarball staging runner on clean v2321, then flash
> exact V3375, run candidate health, read-only `userdata-appliance-preflight`, and
> `userdata-appliance-formatter-probe` only, then roll back to v2321 unless destructive D4C starts
> immediately under the D4 runbook.

> **✅ STATUS (2026-07-03) — D4C rootfs tarball LIVE STAGED; no flash/userdata touch.**
> `prepare_d4c_userdata_rootfs_tarball.py` ran on clean resident v2321 and ended on v2321 with
> `selftest fail=0`. It created
> `workspace/private/runs/server-distro/d4c-rootfs-tarball-20260703T121035Z/a90-d4c-userdata-rootfs.tar`
> from the clean D3 sysvinit rootfs, verified required entries (`/sbin`, `/usr/sbin/init`,
> `/etc/debian_version`, `/etc/inittab`, `/etc/a90-server-distro-stage`), and staged it to
> `/mnt/sdext/a90/runtime/a90-d4c-userdata-rootfs.tar`. Host and remote SHA both equal
> `0875b8bd6e58298f644735e5d7ee12c0286e3057a7744b05064fc34829412603`; size is `268349440` bytes.
> The unit performed **NO FLASH / NO FORMAT / NO USERDATA TOUCH**. Report:
> `docs/reports/SERVER_DISTRO_D4C_ROOTFS_TARBALL_STAGING_LIVE_2026-07-03.md`.
> **NEXT bounded unit = V3375 formatter-probe live proof**: confirm rollback/TWRP preconditions, flash
> exact V3375 through `native_init_flash.py`, verify candidate health, run read-only
> `userdata-appliance-preflight` plus `userdata-appliance-formatter-probe` only, then roll back to v2321
> unless destructive D4C starts immediately.

> **🟡 STATUS (2026-07-03) — V3375 formatter-probe LIVE FAILED SAFELY; rollback clean.**
> Exact V3375 flashed through `native_init_flash.py` with remote SHA and boot readback SHA matching
> `460fbbc137478695c9271a80fd9e0e5dedb96975ee9e69bd6b67c9a72db1ecdb`. Candidate booted as
> `A90 Linux init 0.11.135 (v3375-server-distro-userdata-formatter-probe)` with `selftest fail=0`, and
> read-only `userdata-appliance-preflight` passed for `sda33`, same-session `target.dev=259:17`,
> `target.sectors=231577432`, `target.mounted=0`, `node_materialized=0`. The SD regular-file
> formatter probe then failed before any userdata action because device BusyBox `mke2fs` rejects
> `-t ext4` (`mke2fs: invalid option -- 't'`). A same-session SD syntax probe proved
> `/bin/busybox mke2fs -F -L A90D4PROBE <file> 16384` writes ext superblock magic `53 ef`; loop mount
> probing failed due missing loop setup and is not proof for the real block-partition path. All SD probe
> files were removed, no `userdata-appliance-format`/populate/switch-root ran, no userdata node was
> materialized, and rollback to v2321 completed with final `selftest fail=0`.
> Report:
> `docs/reports/NATIVE_INIT_V3376_SERVER_DISTRO_D4C_FORMATTER_PROBE_LIVE_FAIL_2026-07-03.md`.
> **NEXT bounded unit = formatter syntax fix candidate**: update the D4 formatter/probe command surface
> away from BusyBox `-t ext4`, build a new candidate, and re-run only preflight plus formatter-probe
> before any destructive D4C format/populate.

> **✅ STATUS (2026-07-03) — V3377 formatter syntax fix source/build DONE; live pending.**
> Codex updated the D4 formatter/probe surface to stop using unsupported BusyBox `-t ext4`. The
> non-destructive probe now runs `mke2fs -F -L A90D4PROBE <probe-image> <KBYTES>` and logs `kbytes=...`;
> the destructive format path now runs `busybox mke2fs -F -L A90D4ROOT /dev/block/a90-userdata`, still
> behind same-session `PARTNAME=userdata` identity checks. Built artifact:
> `A90 Linux init 0.11.136 (v3377-server-distro-userdata-formatter-fix)`, boot SHA
> `65575d4166896d9ffd4e38594ac1776583b6087c5ff79c8eebb140ea07a15dfd`, init SHA
> `5af53b0b2c2352768457604c6f65445ca8a12674445573bb6725e6f702dfbe26`.
> Static validation passed: `py_compile`, 12 relevant unittest cases, V3377 build, `file`, `sha256sum`,
> and image string checks. This unit performed **NO FLASH / NO FORMAT / NO USERDATA TOUCH**. Report:
> `docs/reports/NATIVE_INIT_V3377_SERVER_DISTRO_D4C_FORMATTER_FIX_SOURCE_BUILD_2026-07-03.md`.
> **NEXT bounded unit = V3377 formatter-fix live proof**: confirm rollback/TWRP preconditions, flash exact
> V3377 through `native_init_flash.py`, verify candidate health, run read-only preflight plus
> `userdata-appliance-formatter-probe` only, then roll back to v2321 unless destructive D4C starts
> immediately.

> **🟡 STATUS (2026-07-03) — V3377 formatter-fix LIVE FAILED SAFELY; rollback clean.**
> Exact V3377 flashed through `native_init_flash.py` with remote SHA and boot readback SHA matching
> `65575d4166896d9ffd4e38594ac1776583b6087c5ff79c8eebb140ea07a15dfd`. Candidate booted as
> `A90 Linux init 0.11.136 (v3377-server-distro-userdata-formatter-fix)` and status showed
> `selftest fail=0`; read-only `userdata-appliance-preflight` passed for `sda33`, same-session
> `target.dev=259:30`, `target.sectors=231577432`, `target.mounted=0`, `node_materialized=0`.
> The corrected formatter-probe reached `formatter=busybox-mke2fs ... kbytes=16384` but failed with
> `execve(/bin/busybox): Bad address` because `probe_argv` did not reserve a final NULL terminator after
> adding the KBYTES argument. The SD probe file was removed, no format/populate/switch-root ran, no
> userdata node was materialized, and rollback to v2321 completed with valid final status
> `selftest fail=0`. Report:
> `docs/reports/NATIVE_INIT_V3378_SERVER_DISTRO_D4C_FORMATTER_FIX_LIVE_FAIL_2026-07-03.md`.
> **NEXT bounded unit = formatter argv fix candidate**: extend `probe_argv` for
> `<probe-path>, <KBYTES>, NULL`, rebuild, and re-run only preflight plus formatter-probe before any
> destructive D4C format/populate.

> **✅ STATUS (2026-07-03) — V3379 formatter argv fix source/build DONE; live pending.**
> Codex extended `probe_argv` so the formatter-probe argv now has `<probe-path>, <KBYTES>, NULL` instead
> of overwriting the final NULL. Built artifact:
> `A90 Linux init 0.11.137 (v3379-server-distro-userdata-formatter-argv-fix)`, boot SHA
> `a58c07bca01c74ba97653a7cd3d3681788674fa8a6eb912a4fe64a84fb42112e`, init SHA
> `c6b8e498ac6fde11b0ac61ef34bb0a995930dd816e0a6dd5af7207b5442b547e`.
> Static validation passed: `py_compile`, 16 relevant unittest cases, V3379 build, `file`, `sha256sum`,
> and image string checks. This unit performed **NO FLASH / NO FORMAT / NO USERDATA TOUCH**. Report:
> `docs/reports/NATIVE_INIT_V3379_SERVER_DISTRO_D4C_FORMATTER_ARGV_FIX_SOURCE_BUILD_2026-07-03.md`.
> **NEXT bounded unit = V3379 formatter argv-fix live proof**: confirm rollback/TWRP preconditions, flash
> exact V3379 through `native_init_flash.py`, verify candidate health, run read-only preflight plus
> `userdata-appliance-formatter-probe` only, then roll back to v2321 unless destructive D4C starts
> immediately.

> **✅ STATUS (2026-07-03) — V3379 formatter argv-fix LIVE PASS; rollback clean.**
> Exact V3379 flashed through `native_init_flash.py` with remote SHA and boot readback SHA matching
> `a58c07bca01c74ba97653a7cd3d3681788674fa8a6eb912a4fe64a84fb42112e`. Candidate booted as
> `A90 Linux init 0.11.137 (v3379-server-distro-userdata-formatter-argv-fix)` and status showed
> `selftest fail=0`. Slow-input read-only preflight passed for `sda33`, same-session `target.dev=259:36`,
> `target.sectors=231577432`, `target.mounted=0`, `node_materialized=0`. The non-destructive
> formatter-probe passed with `formatter=busybox-mke2fs`, `kbytes=16384`, ext magic `53ef`, `cleanup=ok`,
> and `userdata_touched=0`. No format/populate/switch-root ran, no userdata node was materialized, and
> rollback to v2321 completed with final status `selftest fail=0`. Report:
> `docs/reports/NATIVE_INIT_V3380_SERVER_DISTRO_D4C_FORMATTER_ARGV_FIX_LIVE_PASS_2026-07-03.md`.
> **SUPERSEDED NEXT (operator steer, 2026-07-03): do not enter destructive D4C with this BusyBox
> formatter path.** It proves ext-family magic only; it does not prove a journaled ext4 filesystem.

> **✅ STATUS (2026-07-03) — D4C e2fsprogs toolroot staged for journaled formatter path; no flash/userdata touch.**
> On clean v2321, Codex extracted the staged D3 rootfs tarball into
> `/mnt/sdext/a90/runtime/d4c-format-toolroot` and verified the journaled formatter toolchain on-device:
> `mke2fs` SHA `92721c9a402ba8015ec6321acffaac187ce32fd2772a54690b46dfe94b8f6589`,
> `dumpe2fs` SHA `6e22ed6668e336a891621de3e18b8915e56545351c20c06bafb6682ac1de9aae`,
> `tune2fs` SHA `f4bd3a7e56772236ec0dd8f6a4c5fa2b9dfa52cf70d2af0fa1eb50cfeafa34ad`;
> `mkfs.ext4 -> mke2fs`, Debian `12.14`, and the D3 stage marker are present. Final v2321 status still
> shows `selftest fail=0`. Report:
> `docs/reports/SERVER_DISTRO_D4C_E2FSPROGS_TOOLROOT_STAGING_2026-07-03.md`.
> **NEXT bounded unit = V3381 journaled formatter surface**: add a native-init e2fsprogs formatter-probe
> and format command that require SHA-pinned `/mnt/sdext/a90/runtime/d4c-format-toolroot`, prove
> `mkfs.ext4`/`mke2fs` plus `dumpe2fs` non-destructively on an SD regular file, and make D4C DoD verify
> actual on-disk `has_journal` before any destructive format/populate.

> **✅ STATUS (2026-07-03) — V3381 journaled formatter source/build DONE; live pending.**
> Codex replaced the D4 formatter implementation behind the existing command names with the staged
> e2fsprogs toolroot: `userdata-appliance-formatter-probe` now requires probe images under
> `/mnt/sdext/a90/runtime/d4c-format-toolroot`, verifies pinned `mke2fs`/`dumpe2fs`/`tune2fs` hashes,
> runs chrooted `mkfs.ext4`, runs `dumpe2fs -h`, checks ext magic, and verifies the `has_journal`
> feature bit before cleanup. `userdata-appliance-format` uses the same journaled formatter path after
> the existing sysfs `PARTNAME=userdata` and same-session `devname/dev/sectors` guards, then verifies
> `has_journal=1` on the real block device before `format=done`. Built candidate:
> `A90 Linux init 0.11.138 (v3381-server-distro-journaled-formatter)`, boot SHA
> `c99be26deb3ca872de444e1f34ab602938a68381fe84c338bf29ead7ed9f1c4f`. Static validation passed:
> `py_compile`, 20 D4 unittest cases, AArch64 build, required-string audit, `file`, and `sha256sum`.
> Report:
> `docs/reports/NATIVE_INIT_V3381_SERVER_DISTRO_D4C_JOURNALED_FORMATTER_SOURCE_BUILD_2026-07-03.md`.
> **NEXT bounded unit = V3381 journaled formatter live proof**: confirm rollback/TWRP preconditions,
> flash exact V3381 through `native_init_flash.py`, verify candidate health, run read-only preflight
> plus non-destructive `userdata-appliance-formatter-probe` against
> `/mnt/sdext/a90/runtime/d4c-format-toolroot/tmp/<probe>.img`, then roll back to v2321 unless
> destructive D4C starts immediately under the runbook.

> **✅ STATUS (2026-07-03) — V3381 journaled formatter LIVE PASS; rollback clean.**
> Exact V3381 flashed through `native_init_flash.py` with remote SHA and boot readback SHA matching
> `c99be26deb3ca872de444e1f34ab602938a68381fe84c338bf29ead7ed9f1c4f`. Candidate booted as
> `A90 Linux init 0.11.138 (v3381-server-distro-journaled-formatter)` and candidate
> `version/status/selftest` showed `selftest fail=0`. Read-only preflight passed for `sda33`,
> same-session `target.dev=259:17`, `target.sectors=231577432`, `target.mounted=0`,
> `node_materialized=0`. The non-destructive formatter-probe ran only on
> `/mnt/sdext/a90/runtime/d4c-format-toolroot/tmp/a90-v3381-live-probe.img`, verified pinned
> `mke2fs`/`dumpe2fs`/`tune2fs` hashes, used `mkfs.ext4 -> mke2fs`, printed `Creating journal`,
> had `dumpe2fs -h` report `Filesystem features: has_journal ...`, and native-init verified
> `formatter-probe=has-journal-ok ... has_journal=1`, `cleanup=ok`, `userdata_touched=0`. No
> format/populate/switch-root ran, no userdata node was materialized, and rollback to v2321 completed
> with final `version/status/selftest` passing and `selftest fail=0`. Report:
> `docs/reports/NATIVE_INIT_V3382_SERVER_DISTRO_D4C_JOURNALED_FORMATTER_LIVE_PASS_2026-07-03.md`.
> **NEXT bounded unit = destructive D4C format+populate** under a fresh same-session preflight:
> flash V3381-or-later by checked helper, re-derive `PARTNAME=userdata`, pass the exact
> `target.devname/dev/sectors` from that session into `userdata-appliance-format`, verify
> `has_journal=1` on real userdata, then populate with the pinned SD rootfs tarball SHA.

> **✅ STATUS (2026-07-03) — D4C destructive format+populate LIVE PASS; V3381 left live for D4D.**
> Codex flashed exact V3381 again through `native_init_flash.py` with remote/readback SHA matching
> `c99be26deb3ca872de444e1f34ab602938a68381fe84c338bf29ead7ed9f1c4f`; candidate health passed
> `version/status/selftest` with `selftest fail=0`. Fresh same-session preflight passed for
> `sda33`, `target.dev=259:17`, `target.sectors=231577432`, `target.mounted=0`, `node_materialized=0`.
> The staged rootfs tarball was rechecked on-device as SHA
> `0875b8bd6e58298f644735e5d7ee12c0286e3057a7744b05064fc34829412603`, size `268349440`. Destructive
> `userdata-appliance-format SERVER-DISTRO-D4-USERDATA-APPLIANCE sda33 259:17 231577432` then created
> `/dev/block/a90-userdata`, ran SHA-pinned e2fsprogs `mkfs.ext4`, printed `Creating journal
> (131072 blocks): done`, `dumpe2fs -h` reported `Filesystem features: has_journal ...`, and native-init
> verified `format=has-journal-ok ... has_journal=1` before `format=done`. Populate then mounted
> `/dev/block/a90-userdata` at `/mnt/a90-userdata-root`, extracted the pinned tarball, verified
> `/sbin/init mode=755`, wrote marker `userdata=appliance-root`, and post-D4C health stayed
> `selftest fail=0`. No switch-root ran yet. Report:
> `docs/reports/SERVER_DISTRO_D4C_USERDATA_FORMAT_POPULATE_2026-07-03.md`.
> **NEXT bounded unit = D4D appliance handoff proof**: run `switch-root-to-userdata` with expected marker,
> observe Debian PID1 and USB-local access, prove root filesystem is userdata, and keep timed
> recovery/rollback available.

> **✅ STATUS (2026-07-03) — D4D appliance handoff LIVE PASS; final rollback clean.**
> Before handoff, Codex installed a per-run SSH public key into the mounted userdata root
> (`authorized_keys` mode `0600`; private key stayed under `workspace/private/run/`) and verified USB/NCM
> host route `192.168.7.1 -> 192.168.7.2` with `0%` ping loss. `switch-root-to-userdata
> SERVER-DISTRO-D4-USERDATA-APPLIANCE userdata=appliance-root` reached `exec_switch_root_now` after
> target/marker/init checks and mount moves. SSH to `root@192.168.7.2:2222` succeeded on the first
> attempt and proved Debian `12.14`, `/proc/1/comm=init`, `/proc/1/exe=/usr/sbin/init`,
> `root_findmnt=/dev/block/a90-userdata ext4 /`, `appliance_marker=userdata=appliance-root`,
> `dropbear_started=1`, and `ncm_addr=192.168.7.2/24`. The firstboot mandatory `autoreboot_sec=120`
> path was observed: native `a90ctl` timed out during Debian PID1, USB serial disappeared/reappeared, and
> V3381 native-init returned with post-autoreboot `selftest fail=0`. Since V3381 promotion is a separate
> decision, Codex rolled boot back through `native_init_flash.py`; v2321 remote/readback SHA matched
> `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`, and final
> `version/status/selftest` passed with `selftest fail=0`. Report:
> `docs/reports/SERVER_DISTRO_D4D_USERDATA_APPLIANCE_HANDOFF_2026-07-03.md`.
> **D4A→D4D requested proof chain is complete.** Remaining work, if desired, is a separate promotion or
> appliance-management decision, not a D4 proof blocker.
>
> **✅ STATUS (2026-07-03 14:52 KST) — D-public no-exposure preflight tooling DONE; live publish still gated.**
> Codex added `workspace/public/src/scripts/server-distro/prepare_dpublic_preflight.py` and report
> `docs/reports/SERVER_DISTRO_DPUBLIC_PREFLIGHT_2026-07-03.md`. The preflight confirmed D4 foundation
> docs are present, the host `cloudflared` linux-arm64 artifact is SHA-pinned
> (`59816ce9b16db71f5bc2a86d59b3632a96c8c3ee934bde2bc8641ee83a6070eb`), and a read-only device check
> saw final v2321 plus `selftest fail=0`. It also confirmed `device_tunnel_artifacts_present=false`,
> `live_publish_ready=false`, `public_exposure_performed=false`, and `device_write_performed=false`.
> **D-public is therefore prepared for a gated next unit, but not live-ready yet.** Before first public
> exposure, choose named tunnel token/hostname vs explicit quick-tunnel mode, stage `cloudflared` and a
> minimal HTTP smoke service into the userdata appliance, boot a D4-capable appliance image, prove outbound
> internet, then require the literal operator gate `D-PUBLIC-LIVE-PUBLISH`.
>
> **✅ STATUS (2026-07-04 00:13 KST) — D-public quick Tunnel LIVE PASS; public URL redacted from git.**
> After the operator sent `D-PUBLIC-LIVE-PUBLISH`, Codex used the existing V3381/D4 userdata appliance,
> staged loopback-only D-public smoke helpers, corrected the proof-only D4D autoreboot firstboot into a
> D-public profile, fixed appliance time and `/etc/hosts`, and launched accountless `cloudflared`
> quick Tunnel against `http://127.0.0.1:8080`. Host public HTTPS curl through the Cloudflare edge returned
> `A90_DPUBLIC_SMOKE_OK`. Cloudflare prechecks passed DNS, UDP/QUIC, TCP/HTTP2, and API reachability.
> Report: `docs/reports/SERVER_DISTRO_DPUBLIC_LIVE_PUBLISH_2026-07-04.md`. The live tunnel was left
> running for operator inspection; the actual URL is stored only in
> `workspace/private/runs/server-distro/dpublic-live-20260703T150145Z/public-url.txt`.
>
> **✅ STATUS (2026-07-04 01:10 KST) — D-public Debian-owned visual HUD LIVE PASS; tunnel still live.**
> Codex added a Debian-side KMS HUD helper
> `workspace/public/src/scripts/server-distro/a90_dpublic_hud.c` and a D-public firstboot profile
> `workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh`.  Live state is Debian PID1
> (`/usr/sbin/init`, Debian `12.14`) with autoreboot disabled, loopback smoke on `127.0.0.1:8080`,
> key-only dropbear on `192.168.7.2:2222`, the existing quick Tunnel still running, and the Debian HUD
> presenting through KMS (`display=1080x2400 connector=28 crtc=133 refresh=2s`).  The firstboot profile
> now recovers DRM ownership from any non-PID1 native `/init` child holding `/dev/dri/card0`, clears stale
> D-public smoke/HUD processes by command line before restart, waits for port/DRM release, ignores smoke
> `SIGPIPE`, and prefixes inherited D3 proof-stage marker fields as `base_*` to avoid status ambiguity.
> Local loopback smoke passed 3/3 and the public quick Tunnel path passed 5/5 with
> `A90_DPUBLIC_SMOKE_OK`; the URL remains private-only.  Report:
> `docs/reports/SERVER_DISTRO_DPUBLIC_BOOT_VISUAL_HUD_2026-07-04.md`.  No flash or rollback was performed
> in this unit; the live Debian appliance/HUD/tunnel were left running for operator inspection.
>
> **✅ STATUS (2026-07-04 01:35 KST) — native switch_root display-owner cleanup SOURCE GATE DONE.**
> Codex implemented the native-side cleanup that should replace the Debian firstboot DRM workaround as
> the primary path: `workspace/public/src/native-init/a90_server_distro.c` now stops tracked
> `A90_SERVICE_HUD`, scans `/proc` for non-self `/init` processes holding DRM fds, terminates those
> owners with bounded `SIGTERM`→`SIGKILL`, and fails closed with `stop=handoff-display-owner` if a
> DRM-owning native child cannot be stopped.  The cleanup runs in both D3 and D4 after root/init
> validation and before `/proc`/`/sys`/`/dev` are moved into the new root.  Static validation passed:
> AArch64 object compile of `a90_server_distro.c` and focused unittest (`12` tests).  Report:
> `docs/reports/SERVER_DISTRO_NATIVE_HANDOFF_DISPLAY_CLEANUP_SOURCE_2026-07-04.md`.  No boot image was
> built/flashed in this unit, and the live Debian appliance/HUD/quick Tunnel were not interrupted.  Next
> live gate, if desired: build a new native candidate identity, flash/hot-reload under normal rollback
> gates, run `switch-root-to-userdata`, and verify Debian no longer has to kill a native `/init` DRM
> holder.
>
> **✅ STATUS (2026-07-04 01:50 KST) — V3383 handoff-cleanup candidate SOURCE BUILD DONE.**
> Codex added `workspace/public/src/scripts/revalidation/build_native_init_boot_v3383_server_distro_handoff_cleanup.py`
> and generated `A90 Linux init 0.11.139 (v3383-server-distro-handoff-cleanup)` at
> `workspace/private/inputs/boot_images/boot_linux_v3383_server_distro_handoff_cleanup.img`, SHA256
> `c2cb74e014c7a3e2121ef50d818e6225d7ab8d042eba75166c77e133f3fd012c`.  Required-string audit confirmed
> the V3383 identity plus `handoff_display service=autohud stop_rc=%d`,
> `handoff_display=done killed=%u rc=%d`, and `stop=handoff-display-owner` are present in the boot image.
> Static validation passed: builder `py_compile`, focused V3383/V3381/native-handoff tests, and marker
> audit.  Report:
> `docs/reports/NATIVE_INIT_V3383_SERVER_DISTRO_HANDOFF_CLEANUP_SOURCE_BUILD_2026-07-04.md`.
>
> **✅ STATUS (2026-07-04 02:20 KST) — V3383 handoff-cleanup LIVE PASS.**
> Codex flashed exact V3383 through `native_init_flash.py`; pushed/readback SHA matched
> `c2cb74e014c7a3e2121ef50d818e6225d7ab8d042eba75166c77e133f3fd012c`, post-boot cmdv1 verify passed,
> and native health was `selftest pass=12 warn=1 fail=0`.  The D4 userdata handoff reached
> `exec_switch_root_now` and proved the new display cleanup path:
> `handoff_display service=autohud stop_rc=0`, three native DRM-owner PIDs terminated, and
> `handoff_display=done killed=3 rc=0`.  Debian came up as PID1 (`/usr/sbin/init`) on
> `/dev/block/a90-userdata` ext4, loopback smoke returned `A90_DPUBLIC_SMOKE_OK`, and the Debian HUD
> reported `display=1080x2400 connector=28 crtc=133 refresh=2s`.  No native `/init` process remained
> after handoff.  Public tunnel was not started in this unit; stale tunnel runtime files from earlier
> runs were ignored and no public URL was committed.  Report:
> `docs/reports/NATIVE_INIT_V3383_SERVER_DISTRO_HANDOFF_CLEANUP_LIVE_2026-07-04.md`.  Device was left in
> the live Debian userdata appliance for operator inspection.
>
> **✅ STATUS (2026-07-04 02:45 KST) — Stage0 hardware contract LOCKED.**
> Codex added `docs/plans/SERVER_DISTRO_STAGE0_HARDWARE_CONTRACT_2026-07-04.md` to narrow the server
> appliance hardware policy.  Default Stage0 boot is now constrained to boot/control, USB ACM/NCM,
> guarded storage/rootfs handoff, optional native boot HUD with mandatory DRM release, and pre-handoff
> health/status logs.  The next required hardware rung is Wi-Fi STA upstream (`wlan0` materialization in
> native, IP/route/tunnel ownership in Debian).  Audio, KGSL/GPU, video/Doom, touch/game input, and stress
> tools are explicit opt-in only; modem/camera/GNSS/NFC/Bluetooth/sensor hubs/Android HAL services are
> not default appliance boot targets.  No device action was performed in this unit.
>
> **✅ STATUS (2026-07-04 03:05 KST) — V3384 Stage0 hardware-contract SOURCE BUILD DONE.**
> Codex added a read-only native command surface: `server-distro [status|hardware-contract]`.  It prints
> `A90DHW` lines for the default active surfaces, Wi-Fi STA next rung, opt-in demo hardware, default-off
> hardware, Debian-owned public tunnel, and safety no-go policy.  V3384 source-build generated
> `A90 Linux init 0.11.140 (v3384-server-distro-hardware-contract)` at
> `workspace/private/inputs/boot_images/boot_linux_v3384_server_distro_hardware_contract.img`, SHA256
> `47890d04219837af3acb96ad8e281ad4eab0ea3a73ae2641e05633d014979178`; `strings` audit confirmed the
> `A90DHW` contract lines are present in the boot image.  Static validation passed: builder/test
> `py_compile`, focused hardware-contract and V3383 handoff tests, AArch64 fast-build compile, required
> string audit, and boot image SHA capture.  Report:
> `docs/reports/NATIVE_INIT_V3384_SERVER_DISTRO_HARDWARE_CONTRACT_SOURCE_BUILD_2026-07-04.md`.
> **NEXT live gate:** checked-helper flash exact V3384, health-check native-init, run
> `server-distro hardware-contract`, verify all expected `A90DHW` lines over cmdv1, then continue to the
> Wi-Fi STA upstream rung.
>
> **✅ STATUS (2026-07-04 03:30 KST) — D-public stale tunnel runtime cleanup SOURCE DONE.**
> Codex tightened the Debian firstboot profile so stale quick-Tunnel state cannot pollute manual-mode
> status.  `a90_dpublic_firstboot.sh` now removes stale `/run/a90-dpublic/cloudflared-*` pid/log/url
> sidecars, kills only matching residual `cloudflared tunnel` processes from old pidfiles, records
> `cloudflared_runtime_cleanup=<reason>`, and runs that cleanup before both quick-Tunnel enabled startup
> and manual `tunnel_started=manual` reporting.  Source/static validation covered shell syntax and
> D-public helper/preflight tests.  No device action, flash, reboot, public tunnel start, or public tunnel
> stop was performed.  Report:
> `docs/reports/SERVER_DISTRO_DPUBLIC_RUNTIME_CLEANUP_SOURCE_2026-07-04.md`.
> **NEXT D-public live check:** on the next appliance boot, confirm manual mode has no cloudflared process,
> marker order includes `cloudflared_runtime_cleanup=manual` before `tunnel_started=manual`, and stale
> `/run/a90-dpublic/cloudflared-*` pid/log/url files are absent.
>
> **✅ STATUS (2026-07-04 03:45 KST) — Wi-Fi STA upstream rung DESIGN LOCKED.**
> Codex added `docs/plans/SERVER_DISTRO_WIFI_STA_UPSTREAM_RUNG_2026-07-04.md` to split the next
> server-appliance hardware rung into ownership-safe steps.  The target is STA-only upstream:
> native init materializes `wlan0` through the already-proven QCACLD/vendor-firmware route, then
> Debian owns long-lived `wpa_supplicant`, DHCP/DNS/default route, and `cloudflared`; USB NCM remains
> the recovery/admin path.  The design explicitly parks SoftAP+STA concurrency, modem/cellular, NAT,
> inbound public ports, and native-owned public tunnel work.  Credentials remain private-only, and
> association gates are blocked rather than failed when credentials are absent.  Static plan tests were
> added under `tests/test_server_distro_wifi_sta_upstream_plan.py`.
> **NEXT implementation unit:** WSTA1 source-only rootfs/firstboot support: add Debian STA client
> packages, add an opt-in `/etc/a90-dpublic/wifi-sta-enable` firstboot helper, and prove the default
> D-public boot still starts no STA and no public tunnel.
>
> **✅ STATUS (2026-07-04 04:10 KST) — WSTA1 Debian STA client SOURCE DONE.**
> Codex added source-only Debian STA upstream support for the D-public appliance.  The rootfs builder now
> includes `wpasupplicant` and `isc-dhcp-client`, stages `/usr/local/bin/a90-dpublic-wifi-sta`, and records
> Wi-Fi STA as private opt-in in `/etc/a90-server-distro-stage`.  The D-public firstboot profile runs the
> helper only when `/etc/a90-dpublic/wifi-sta-enable` exists; otherwise it records
> `wifi_sta_requested=0`, `wifi_sta_started=0`, `wifi_sta_decision=wifi-sta-manual`, and
> `wifi_sta_secret_values_logged=0`.  The helper consumes `/etc/a90-dpublic/wpa_supplicant-wlan0.conf`
> without printing SSID/PSK, starts Debian-owned `wpa_supplicant` + `dhclient`, preserves the USB NCM peer
> route, and records only redacted marker fields.  No device action, flash, Wi-Fi association, DHCP, ping,
> or public tunnel action was performed.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA1_SOURCE_2026-07-04.md`.
> **NEXT gate:** WSTA2 native `wlan0` materialization live check below association, then WSTA3 Debian STA
> association/DHCP/default-route over private credentials only.
>
> **✅ STATUS (2026-07-04 02:20 KST host clock) — WSTA2 runner SOURCE DONE; live preflight blocked before flash.**
> Codex added `workspace/public/src/scripts/server-distro/run_wsta2_native_materialization.py`, a fail-closed
> host runner for the native `wlan0` materialization gate.  The runner defaults to read-only native cmdv1
> probing, can optionally flash the pinned V3384 hardware-contract candidate only through
> `native_init_flash.py`, checks rollback images before any flash request, and refuses to invent a recovery
> path when neither native cmdv1 nor recovery ADB is present.  Static tests cover the V3384 pins, required
> `A90DHW` lines, `wlan0_present` classification, forbidden native worker detection, and below-association
> command surface.  Current live preflight found the Debian appliance reachable over local USB/NCM, but native
> cmdv1 did not return `A90P1 END` and ADB recovery was absent; `--flash-v3384` therefore stopped with
> `wsta2-blocked-no-native-cmdv1-or-recovery-adb` before any flash/reboot.  No Wi-Fi association, DHCP, ping,
> public tunnel, raw write, or device mutation was performed.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA2_RUNNER_2026-07-04.md`.
> **NEXT WSTA2 live gate:** get native cmdv1 or recovery ADB back under the checked recovery envelope, then run
> `run_wsta2_native_materialization.py --flash-v3384 --probe-iftype`.  Only after that passes should WSTA3
> consume private Debian STA credentials.
>
> **✅ STATUS (2026-07-04 02:26 KST host clock) — WSTA3 rootfs pipeline SOURCE/HOST DONE.**
> Codex closed the gap where WSTA1 helper support existed in the generic Debian builder but could be skipped by
> the actual D3/D4 userdata appliance rootfs path.  `prepare_d3_sysvinit_rootfs.py` now stages
> `/usr/local/bin/a90-dpublic-wifi-sta` and `/etc/a90-dpublic`, records Wi-Fi STA as private opt-in in the D3
> stage marker, and leaves `wifi-sta-enable` absent by default.  `prepare_d4c_userdata_rootfs_tarball.py` now
> rejects a rootfs/tarball that lacks the executable STA helper or config directory.  Host validation confirmed
> the older fixed D4C rootfs lacks the helper, then built a new private WSTA-ready image
> `workspace/private/builds/server-distro/d3-sysvinit-usrmerge-wsta-20260704T0225Z.img`
> (`sha256=7adbdcc2f0fd15d4d860532761c767773abcd13d8febf37a7312047adc9f637e`) with
> `wifi_sta_helper.exists=true` and D4C `verify_rootfs=ok`.  No flash, reboot, userdata staging/format,
> Wi-Fi association, DHCP, ping, or public tunnel action was performed.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA3_ROOTFS_PIPELINE_2026-07-04.md`.
> **NEXT:** WSTA2 live still gates WSTA3.  Once native cmdv1/recovery ADB is available and WSTA2 passes, use the
> WSTA-ready private rootfs/image for D4C/D4D and stage private Wi-Fi credentials outside git.
>
> **✅ STATUS (2026-07-04 02:37 KST) — WSTA3 private STA rootfs HOST DONE.**
> Codex added `workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py`, a host-only
> preparer that copies the WSTA-ready D3 sysvinit rootfs into a private run dir, materializes the
> `/etc/a90-dpublic/wpa_supplicant-wlan0.conf` and `/etc/a90-dpublic/wifi-sta-enable` opt-in files from
> the owner-private Wi-Fi env, verifies the D4C rootfs/tarball contract, and writes only redacted summary
> metadata.  A private run produced
> `workspace/private/runs/server-distro/wsta3-sta-rootfs-20260703T173658Z/` with run dir mode `0700`,
> generated/staged config mode `0600`, opt-in marker mode `0600`, tarball mode `0600`, required entries
> present, and summary leak-scan clean for raw SSID/PSK/key/URL/device-id patterns.  The tarball SHA is
> intentionally not reported because the archive contains private STA config.  No flash, reboot, userdata
> staging/format, Wi-Fi association, DHCP, ping, or public tunnel action was performed.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA3_PRIVATE_STA_ROOTFS_2026-07-04.md`.
> **NEXT:** WSTA2 live still gates device use.  Restore native cmdv1 or recovery ADB, run
> `run_wsta2_native_materialization.py --flash-v3384 --probe-iftype`, then consume this private STA rootfs
> only inside a bounded WSTA3 association/DHCP/default-route validation.
>
> **✅ STATUS (2026-07-04 02:50 KST) — WSTA2 native `wlan0` materialization LIVE PASS.**
> Codex recovered native control from the Debian userdata appliance by using the existing USB/NCM-local
> SSH path to perform a normal Debian reboot, then flashed exact V3384 through `native_init_flash.py`
> from native recovery control.  The helper verified remote SHA and boot readback SHA
> `47890d04219837af3acb96ad8e281ad4eab0ea3a73ae2641e05633d014979178`, then V3384 booted with
> `selftest fail=0`.  WSTA2 pass run
> `workspace/private/runs/server-distro/wsta2-native-materialization-20260703T174709Z/wsta2_result.json`
> proved `hardware_contract_ok=true`, `selftest_fail_zero=true`, `wlan0_present=true`, and
> `forbidden_native_workers=[]`.  The iftype probe waited `70444ms`, reached `wlan0_present=1`, created
> and cleaned up the temporary AP iftype, and logged `secret_values_logged=0`; no Wi-Fi association,
> DHCP, ping, AP/DNS/NAT, public tunnel, or credentials were used.  Codex also hardened
> `run_wsta2_native_materialization.py` to hide the native auto-menu and retry once when a read-only
> WSTA2 command gets `rc=-16 status=busy auto menu active`; the patched no-flash rerun
> `workspace/private/runs/server-distro/wsta2-native-materialization-20260703T174947Z/wsta2_result.json`
> returned `wsta2-native-materialization-pass`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA2_LIVE_PASS_2026-07-04.md`.
> V3384 is currently left resident for the next bounded WSTA3 unit; v2321/v2237/v48 rollback images remain
> available.  **NEXT:** WSTA3 live: stage the WSTA3 private rootfs tarball under the SD runtime path,
> refresh/populate userdata with the WSTA3 tarball, switch into Debian, and run Debian-owned STA
> association/DHCP/default-route validation using private credentials only.

> **✅ STATUS (2026-07-04 03:36 KST host clock) — WSTA3 Debian-owned STA LIVE PASS.**
> Codex completed the bounded WSTA3 live unit from resident V3384 without a boot flash.  The live run
> staged a private WSTA3 tarball to SD with secret-derived SHA redacted, formatted/refreshed `userdata`,
> switched into Debian, and iterated until Debian firstboot returned `wifi_sta_decision=wifi-sta-pass`.
> Final redacted markers proved `wifi_sta_wlan0_present=1`, `wifi_sta_wpa_supplicant_rc=0`,
> `wifi_sta_dhcp_rc=0`, `wifi_sta_default_route_router_present=1`, `wifi_sta_default_route_set_rc=0`,
> `wifi_sta_default_route_iface=wlan0`, `ncm_recovery_preserved_after_dhcp=1`, and
> `wifi_sta_secret_values_logged=0`.  Runtime state showed `wlan0` up with a dynamic lease, default
> route via `wlan0`, USB/NCM host route preserved, and `wpa_supplicant`/`dhclient` running.  No public
> tunnel or external ping was used.
>
> Source fixes from the live gaps are now in-tree: `prepare_wsta3_sta_rootfs.py` installs the D-public
> firstboot hook, host-installs or fail-closes missing STA tools, and restores usrmerge links after
> package extraction; `a90_dpublic_wifi_sta.sh` reads the DHCP lease router and explicitly moves
> default route to `wlan0`.  Operational finding: after a native reboot, WSTA3 still needs the WSTA2
> native materialization gate immediately before `switch_root`; otherwise Debian can see
> `wifi_sta_wlan0_present=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA3_LIVE_PASS_2026-07-04.md`.
> **NEXT:** D-public tunnel over Debian STA: boot native, run WSTA2 materialization, switch into WSTA3
> userdata, confirm `wifi-sta-pass`, then start the Debian-owned tunnel path.

> **🟡 STATUS (2026-07-04 04:07 KST host clock) — WSTA4 D-public over STA BLOCKED at STA L3/ARP.**
> Codex reproduced the clean no-flash handoff path from native V3384: WSTA2 materialization passed,
> `switch_root` reached the WSTA3 userdata appliance, Debian firstboot again returned
> `wifi_sta_decision=wifi-sta-pass`, the default route was moved to `wlan0`, USB/NCM recovery stayed
> preserved, and the local D-public smoke endpoint returned `A90_DPUBLIC_SMOKE_OK`.  However, public
> tunnel over STA did **not** pass.  The tunnel path first exposed the appliance clock being stale after
> reboot; after manual clock correction, `cloudflared` still timed out because actual STA upstream L3 was
> absent: gateway ping failed, DNS failed, TCP 443 failed, and neighbor resolution for the STA gateway
> remained incomplete despite WPA completion and DHCP success.  Native V3384 corroborated this with
> `wifi connect-event` timing out with no CONNECT event, `carrier_up=0`, and `rc=-107`.
>
> Source hardening landed for the next D-public boot: firstboot now records bounded tunnel readiness as
> `tunnel_process_alive`, `tunnel_url_observed`, and `tunnel_decision`, while any observed quick Tunnel
> URL is stored only in a root-readable `/run` sidecar and never appended to the public marker.  Final
> device state was native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA4_DPUBLIC_STA_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA5 STA L3/ARP root cause.  Add a true L3 gate to the Debian STA helper, compare the
> V2237/V2312 Wi-Fi-proven lineage against V3384 native client behavior, and only retry D-public tunnel
> after gateway ARP/TCP reachability is proven.

> **✅ STATUS (2026-07-04 04:14 KST host clock) — WSTA5 source L3 gate DONE; live check next.**
> Codex changed the Debian STA helper so DHCP/default-route success alone can no longer return
> `wifi-sta-pass`.  The helper now records bounded L3 markers for gateway ping rc, gateway ARP state,
> gateway ARP resolution, DNS lookup rc, and outbound TCP/443 rc.  Pass now requires `dhclient rc=0`,
> default route on `wlan0`, resolved gateway ARP, successful DNS, and successful outbound TCP/443.
> Failures are split as `wifi-sta-l3-gateway-unreachable`, `wifi-sta-l3-dns-failed`, or
> `wifi-sta-l3-tcp-failed`.  The Debian rootfs builder and private WSTA preparer now include/verify
> `netcat-openbsd` for the TCP probe, and the WSTA plan is updated so WSTA3-style success means true
> upstream reachability rather than DHCP-only routing.  No device action or flash was performed.
> Report: `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA5_L3_GATE_SOURCE_2026-07-04.md`.
> **NEXT:** prepare a fresh private WSTA5 userdata rootfs, run the no-flash WSTA2 materialization gate,
> switch into Debian, and collect the new L3 markers.  Do not retry D-public tunnel until those markers
> prove upstream TCP/443 over `wlan0`.

> **🟡 STATUS (2026-07-04 04:25 KST host clock) — WSTA5 first live attempt INVALID; preparer gap fixed.**
> Codex prepared and staged a WSTA5 rootfs, formatted/populated `userdata`, injected the temporary SSH
> key, switched into Debian, and collected markers.  This boot is **not** a valid WSTA5 L3-gate result:
> the private rootfs preparer had copied the latest firstboot but had not overwritten
> `/usr/local/bin/a90-dpublic-wifi-sta`, so Debian ran the old helper without L3 markers.  The attempt
> ended at old-helper `wifi_sta_dhcp_rc=2`, `wifi_sta_default_route_iface=ncm0`, and
> `wifi_sta_decision=wifi-sta-dhcp-failed`; the new `wifi_sta_l3_*` markers were absent.  It also exposed
> a harmless but real D4C maintenance gap: the SD-runtime formatter toolroot had a stale
> `/dev/block/a90-userdata` node from an older boot minor and correctly failed closed before mkfs; removing
> that SD-runtime node allowed the current preflight identity format to proceed.
>
> Source fix now landed: the WSTA preparer always stages the current repo Wi-Fi STA helper and records
> `latest_helper_staged`/`l3_gate_present`; the helper itself falls back from `nc` to `nc.openbsd` and
> records `wifi_sta_tcp_probe_tool`.  The device was rebooted back to native V3384 with `selftest fail=0`.
> Report: `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA5_PREPARER_GAP_2026-07-04.md`.
> **NEXT:** rerun WSTA5 with a newly prepared rootfs; only that run can answer the L3/ARP question.

> **🟡 STATUS (2026-07-04 04:33 KST host clock) — WSTA5 current-helper live BLOCKED at Debian `wlan0` link-up.**
> Codex rebuilt a fresh WSTA5 private rootfs after the preparer fix; the summary confirmed the current
> helper was staged with `latest_helper_staged=true`, `l3_gate_present=true`, and the `nc.openbsd`
> TCP fallback present.  The no-flash device path then formatted/populated `userdata`, injected the
> temporary SSH key, passed WSTA2 native materialization, switched into Debian, and reached SSH over
> USB/NCM.  The current helper ran, but it never reached DHCP/L3: markers ended at
> `wifi_sta_wpa_supplicant_rc=255`, `wifi_sta_started=0`, and
> `wifi_sta_decision=wifi-sta-wpa-start-failed`.  Direct Debian diagnostics showed the real earlier
> failure: `ip link set wlan0 up` / nl80211 returned `Invalid argument`, leaving `wlan0` down before
> `wpa_supplicant` could initialize.  Source is now hardened so the next boot records
> `wifi_sta_link_set_up_rc=<rc>` and fails as `wifi-sta-link-up-failed` instead of obscuring it as a
> generic wpa start failure.  No boot flash or public tunnel was performed; the device is back on
> native V3384 with `selftest fail=0`.
> Report: `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA5_LINK_UP_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA6 link-up boundary: compare the native materialized interface state against the
> Debian handoff state and find the minimal native cleanup/materialization step that lets Debian run
> `ip link set wlan0 up` successfully, before retrying DHCP/L3 or D-public tunnel.

> **✅/🟡 STATUS (2026-07-04 04:49 KST host clock) — WSTA6 link-up gate LIVE PASS; next blocker is carrier/association.**
> Codex updated the WSTA2 materialization runner so `wlan0_present=1` is no longer enough: it now
> parses native `flags=`, records `needs_iftype_probe`, and requires `wlan0_admin_up=true` before
> declaring the pre-handoff gate passed.  Live no-flash validation on resident V3384 reproduced the
> failing state (`wlan0_present=1`, `flags=0x1002`), ran the existing bounded
> `wifi softap iftype-probe`, got `link_up_rc=0`, and ended with `flags=0x1003`,
> `wlan0_admin_up=true`, and `wsta2-native-materialization-pass`.  Reusing the already populated
> WSTA5 userdata appliance then advanced Debian past the old blocker:
> `wifi_sta_wpa_supplicant_rc=0` and `wifi_sta_started=1`.  It still did not associate:
> `wifi_sta_carrier_up=0`, `wifi_sta_dhcp_rc=2`, `wifi_sta_default_route_iface=ncm0`, and
> `wifi_sta_decision=wifi-sta-dhcp-failed`.  No boot flash, no userdata rewrite, and no public
> tunnel were performed; the device is back on native V3384 with `selftest fail=0`.
> Report: `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA6_LINK_UP_GATE_2026-07-04.md`.
> **NEXT:** WSTA7 association/carrier boundary: collect redacted Debian `wpa_supplicant` state/events
> and compare against the native-good STA path.  Do not retry L3/D-public until carrier is up.

> **✅ STATUS (2026-07-04 05:01 KST host clock) — WSTA7 Debian STA association + L3 LIVE PASS.**
> Codex added a Debian `wpa_cli` control sequence to the opt-in D-public STA helper, matching the
> native-good association path (`DRIVER COUNTRY KR`, scan, enable/select network, reassociate, status)
> and recording only redacted `wifi_sta_ctrl_*` markers.  A freshly prepared WSTA7 userdata appliance
> was formatted/populated through the D4 guarded path, SSH key was injected from private runtime state,
> and the no-flash WSTA2 materialization gate was rerun.  Cleanup alone did not recover a stale
> `flags=0x1002` / `EINVAL` link-up state, but a native reboot followed by WSTA2 iftype-probe
> materialized `wlan0` after ~90s and passed with `wlan0_admin_up=true`.  Debian then reached
> `wpa_state=COMPLETED`, carrier up, DHCP rc=0, default route on `wlan0`, gateway ARP reachable, DNS
> rc=0, TCP/443 rc=0, and `wifi_sta_decision=wifi-sta-pass`; USB/NCM recovery stayed preserved.  No
> public tunnel was started and no public URL was observed.  Device ended back on native V3384 with
> `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA7_WPA_CLI_ASSOC_PASS_2026-07-04.md`.
> **NEXT:** WSTA8 D-public over Wi-Fi: use fresh native boot -> WSTA2 gate -> Debian handoff, then start
> local smoke and the Debian-owned outbound tunnel only after `wifi-sta-pass`; prove the tunnel route is
> `wlan0`, keep NCM admin reachable, and keep the public URL/private network details out of git.

> **🟡 STATUS (2026-07-04 05:50 KST host clock) — WSTA8 Wi-Fi PASS, D-public tunnel BLOCKED at quick API/DNS.**
> Codex staged D-public binaries into a private WSTA rootfs, refreshed `userdata` only through the D4
> guarded formatter/populator, and reran the required fresh native boot -> WSTA2 `iftype-probe` ->
> Debian handoff sequence.  The no-clock Debian appliance reached local D-public readiness and true
> STA L3 pass: `wpa_state=COMPLETED`, carrier up, DHCP rc=0, default route on `wlan0`, gateway ARP
> resolved, DNS rc=0, TCP/443 rc=0, `smoke_started=1`, `hud_started=1`, and
> `wifi_sta_decision=wifi-sta-pass`.  Public tunnel publication did not pass: strict quick URL
> detection saw no generated public URL, `cloudflared` exited on quick-tunnel API POST timeout, and
> device-side OpenSSL showed DNS lookup failure for the API while a host control POST to the same API
> returned HTTP 200.  A transient clock-seeded rootfs attempt was rejected as a regression path because
> it produced empty scans/`DISCONNECTED` and then `wifi-sta-link-up-failed`; do not seed/jump wall clock
> before Wi-Fi.  Source now fixes the quick URL detector so `api.trycloudflare.com` cannot be mistaken
> for a public URL and records `quick-url-dead` if a URL is seen after process exit.  Device ended back
> on native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA8_DPUBLIC_TUNNEL_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA9 device-side DNS/HTTPS/cloudflared diagnostic: keep the WSTA7/WSTA8 no-clock handoff
> sequence, add a small static HTTPS/API POST probe or a pinned curl/wget tool, compare resolver
> behavior for `cloudflare.com` vs `api.trycloudflare.com` before any wall-clock mutation, then retry
> cloudflared only after the API POST is independently proven from the device.

> **🟡 STATUS (2026-07-04 06:25 KST host clock) — WSTA9 API probe BLOCKED at STA/L3 persistence.**
> Codex added a manual Debian-side `/usr/local/bin/a90-dpublic-api-probe` plus opt-in `wget`
> staging for the WSTA rootfs.  The helper does not start `cloudflared`; it records only marker
> booleans/return codes, keeps raw API response files private under `/run/a90-dpublic` with mode
> `0600`, and writes `api_probe_secret_values_logged=0`.  Live WSTA9 refreshed `userdata` through
> the D4 guard, uploaded the SHA-pinned rootfs tarball, injected the private runtime SSH public key,
> rebooted native V3384, reran WSTA2, and switched into the no-clock Debian appliance.  Firstboot again
> reached D-public local readiness and initial Wi-Fi L3 pass: `smoke_started=1`, `hud_started=1`,
> default route on `wlan0`, gateway ARP resolved, DNS rc=0, TCP/443 rc=0, and
> `wifi_sta_decision=wifi-sta-pass`; cloudflared remained manual.  The independent API probe then
> failed before any tunnel retry with `api_probe_dns_control_rc=2`, `api_probe_dns_api_rc=2`,
> `api_probe_tcp_tool=nc.openbsd`, TCP rc=1, wget POST rc=4, OpenSSL POST rc=1, and
> `api_probe_decision=api-dns-failed`.  Follow-up diagnostics showed gateway neighbor degradation and
> numeric external TCP failure; a no-clock manual STA refresh ended with latest markers showing
> `wpa_state=DISCONNECTED`, carrier down, and `wifi_sta_decision=wifi-sta-assoc-failed`.  Therefore
> the current blocker is Debian STA/L3 persistence after the initial pass, not quick URL parsing,
> cloudflared invocation, or wall-clock mutation.  No public tunnel was started.  Device ended back on
> native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA9_API_PROBE_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA10 STA/L3 persistence: add timestamped marker phases so stale pass markers cannot hide
> later disconnects, collect redacted `wpa_cli`/association transitions after firstboot, prove a dwell
> window with stable gateway/DNS/TCP, and only then retry the API probe/cloudflared.

> **🟡 STATUS (2026-07-04 06:45 KST host clock) — WSTA10 STA/L3 dwell BLOCKED after initial pass.**
> Codex added run/phase sequencing to the Debian STA helper (`wifi_sta_run_id` plus ordered
> `wifi_sta_event=<run>:<seq>:<phase>:<uptime_ms>`) and made `wifi-sta-pass` depend on a six-sample
> post-pass dwell window.  Firstboot now gates quick tunnel startup in WSTA mode: if Wi-Fi STA is
> enabled, cloudflared starts only when the latest `wifi_sta_decision=wifi-sta-pass`; otherwise it
> records `tunnel_wifi_sta_gate_*` and keeps tunnel exposure off.  Live WSTA10 used the D4 guarded
> userdata refresh, fresh native V3384 boot, WSTA2 materialization pass, and no-clock Debian handoff.
> The appliance reached initial L3 pass (`wpa_completed=1`, carrier up, DHCP rc=0, default route on
> `wlan0`, gateway ping rc=0, DNS rc=0, TCP/443 rc=0), and dwell samples 1-5 stayed good.  Dwell
> sample 6 failed with `wpa_state=COMPLETED`, carrier up, default route still on `wlan0`, gateway ARP
> still resolved, but DNS rc=2 and TCP not attempted; the final decision was
> `wifi_sta_decision=wifi-sta-dwell-failed`.  A post-failure spot check still showed
> `wpa_state=COMPLETED` and carrier up while DNS/TCP failed, so the next blocker is
> associated-but-L3-degraded behavior, not raw association loss.  Cloudflared was not started, and the
> device ended back on native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA10_DWELL_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA11 associated-but-L3-degraded diagnostic: keep WSTA10 phase/dwell markers, add
> redacted `wpa_cli SIGNAL_POLL`/event samples during dwell, compare gateway ARP vs gateway ping/DNS/TCP
> timing, and only then decide whether a keepalive/reconnect policy is justified.  Do not retry API
> probe or cloudflared until the dwell window passes.

> **🟡 STATUS (2026-07-04 07:02 KST host clock) — WSTA11 signal dwell BLOCKED at gateway reachability.**
> Codex added redacted per-sample `wpa_cli PING` and `SIGNAL_POLL` markers to the Debian STA helper,
> plus first-failure sample/reason classification.  The WSTA private rootfs preparer now records
> `signal_dwell_present`, and tests assert the signal-dwell markers.  Live WSTA11 used the D4 guarded
> userdata refresh, fresh native V3384 boot, WSTA2 materialization pass, and no-clock Debian handoff.
> The first D4 format attempt stopped before formatting on a stale SD e2fs toolroot device node; after
> removing that stale toolroot node only, the guarded format/populate retry passed.  Dwell samples 1-5
> were good with `wpa_state=COMPLETED`, `wpa_cli` control PING rc=0, signal poll rc=0, carrier up,
> default route on `wlan0`, gateway ping rc=0, DNS rc=0, and TCP/443 rc=0.  Sample 6 still had
> `wpa_state=COMPLETED`, `wpa_cli` PING rc=0, carrier up, default route on `wlan0`, and gateway ARP
> resolved, but gateway ping failed first; DNS then failed and TCP/443 was not attempted.  The final
> markers were `wifi_sta_dwell_first_fail_sample=6`,
> `wifi_sta_dwell_first_fail_reason=gateway-ping`, and
> `wifi_sta_decision=wifi-sta-dwell-failed`.  Cloudflared was not started, and the device ended back on
> native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA11_SIGNAL_DWELL_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA12 gateway reachability diagnostic: keep WSTA11 markers, add explicit gateway ping
> count/timing plus neighbor refresh and DHCP lease/router-state comparison around the first
> gateway-ping failure, and only then test a bounded ARP/gateway keepalive candidate if justified.
> Do not retry API probe or cloudflared until the dwell window passes.

> **🟡 STATUS (2026-07-04 07:22 KST host clock) — WSTA12 gateway diagnostics SOURCE DONE; live blocked earlier at Debian scan visibility.**
> Codex added gateway-boundary diagnostics to the Debian STA helper: per-sample gateway ping attempt
> count/success/timing, neighbor state before/after bounded `ip neigh get`, DHCP lease-router match
> booleans, and default-route gateway match booleans.  It also added bounded association retry
> diagnostics so association regressions do not masquerade as gateway failures.  Static validation
> passed (`sh -n`, `py_compile`, 29 focused tests).  Live WSTA12 used native V3384, a fresh WSTA2
> materialization gate, a private WSTA12 rootfs, D4 guarded format/populate, and Debian handoff.  WSTA2
> passed after the default materialization window (`wlan0_wait_elapsed_ms=54634`, `wlan0_present=1`,
> `link_up_rc=0`, `decision=softap-iftype-probe-pass`).  D4 format/populate passed with journaled ext4
> and `userdata=appliance-root`; switch_root reached Debian on retry after display-owner cleanup.
> Debian did not reach the WSTA11 gateway-dwell state: firstboot and a manual rerun both ended at
> `wifi-sta-assoc-failed`.  A hot-patched helper with three bounded association attempts then showed
> `wifi_sta_assoc_attempt_1_scan_results_count=0`,
> `wifi_sta_assoc_attempt_2_scan_results_count=0`,
> `wifi_sta_assoc_attempt_3_scan_results_count=0`,
> `wifi_sta_wpa_completed=0`, `wifi_sta_wpa_completed_attempts=3`, carrier down, and
> `wifi_sta_decision=wifi-sta-assoc-failed`.  No API probe or cloudflared was started, and the device
> ended back on native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA12_GATEWAY_DIAG_ASSOC_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA13 Debian scan visibility boundary: compare native `wlan0` materialization/scan
> readiness against Debian `wpa_cli SCAN_RESULTS` after handoff, capture redacted country/regulatory
> and scan-trigger timing/counts, and do not return to gateway keepalive/API/cloudflared work until
> Debian can reliably see scan results and associate again.

> **🟡 STATUS (2026-07-04 07:36 KST host clock) — WSTA13 scan visibility BLOCKED at Debian link-state boundary.**
> Codex added WSTA13 scan visibility markers to the Debian STA helper: regulatory/country booleans,
> `SCAN` trigger rc, scan-result count, supplicant state, operstate, and carrier for the initial scan
> and each bounded retry scan.  The private rootfs preparer now records `scan_visibility_present`, and
> focused tests still pass.  Live WSTA13 used native V3384, WSTA2 materialization, a private WSTA13
> rootfs, D4 guarded format/populate, and Debian handoff.  WSTA2 first hit stale link-up state, then a
> native reboot plus retry passed with `wlan0_wait_elapsed_ms=100261`, `wlan0_present=1`, `link_up_rc=0`,
> and `decision=softap-iftype-probe-pass`.  D4 format/populate passed with journaled ext4 and
> `userdata=appliance-root`; switch_root reached Debian on retry after display-owner cleanup.  Debian
> scan diagnostics showed `wifi_sta_scan_initial_trigger_rc=0`, but all six initial scan samples had
> `results_count=0`, `wpa_state=DISCONNECTED`, `operstate=down`, and carrier `0`; retry scan windows 1
> and 2 showed the same `trigger_rc=0` plus `final_results_count=0`.  Manual `ip link set wlan0 up`
> followed by three more scans also stayed at count `0` and `operstate=down`.  Final decision:
> `wifi_sta_decision=wifi-sta-assoc-failed`.  No API probe or cloudflared was started, and the device
> ended back on native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA13_SCAN_VISIBILITY_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA14 Debian link-state / scan-engine boundary: add optional `iw` diagnostics if package
> staging allows it, compare sysfs/ip-link state before and after `wpa_supplicant`, and test a bounded
> post-supplicant link-up reassertion only as a diagnostic.  Do not return to gateway keepalive/API/
> cloudflared work until Debian can see scan results and associate again.

> **🟡 STATUS (2026-07-04 08:00 KST host clock) — WSTA14 link-state / scan-engine BLOCKED at Debian WLAN driver state.**
> Codex added WSTA14 diagnostics to the Debian STA helper: `link_snapshot()` sysfs/ip-link markers,
> count-only `iw` probes, and bounded post-supplicant retry relink markers.  The private rootfs
> preparer now installs `iw` and records `linkstate_diag_present` plus `iw_diag_present`; focused
> tests pass.  Live WSTA14 used native V3384, WSTA2 materialization, a fixed WSTA14 private rootfs,
> D4 guarded format/populate, and Debian handoff.  WSTA2 passed with `wlan0_wait_elapsed_ms=93659`,
> `wlan0_present=1`, `link_up_rc=0`, and `decision=softap-iftype-probe-pass`.  Debian then showed
> `iw_present=1`, `iw_dev_info_rc=0`, `iw_phy_present=1`, and `iw_type_managed=1`, but direct
> `iw` scan returned `wifi_sta_reg_after_country_iw_scan_rc=234` and
> `wifi_sta_reg_after_country_iw_scan_bss_count=0`.  `wlan0` stayed administratively UP but not
> running/lower-up (`flags_hex=0x1003`, `flags_up=1`, `flags_running=0`, `flags_lower_up=0`) after
> link-up, after supplicant start, after reassociation, and after both bounded relink attempts.
> Initial and retry scan windows all ended at `final_results_count=0`; final decision was
> `wifi_sta_decision=wifi-sta-assoc-failed`.  No API probe or cloudflared was started, and the
> device ended back on native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA14_LINKSTATE_SCAN_BLOCKED_2026-07-04.md`.
> **🟢 STATUS (2026-07-04 08:12 KST host clock) — WSTA15 native scan boundary PASS.**
> Codex added `run_wsta15_handoff_scan_boundary.py`, a no-flash resident-V3384 runner that
> compares a STA-only native `wifi scan` window against a second scan window after the bounded
> `wifi softap iftype-probe` AP-iftype add/delete proof.  Focused tests pass.  Live WSTA15
> ran from a fresh native reboot on V3384: initial `wifi status` showed `wlan0` missing; the
> STA-only scan window failed three times at `decision=wifi-scan-link-up-failed` /
> `link_up_errno=19`, then attempt 4 passed with `decision=wifi-scan-pass` and
> `scan_result_count=11`.  The AP-iftype probe then passed, and the post-iftype scan passed
> immediately with `scan_result_count=12`.  Final decision:
> `wsta15-native-scan-engine-survives-iftype`; forbidden native Wi-Fi/tunnel workers were absent,
> no association/DHCP/ping/tunnel ran, and post-run `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA15_HANDOFF_SCAN_BOUNDARY_2026-07-04.md`.
> **🟠 STATUS (2026-07-04 08:32 KST host clock) — WSTA16 immediate Debian handoff scan BLOCKED.**
> Codex added a credential-free `--immediate-snapshot-only` rootfs mode and a Debian helper path
> that records link/`iw` state before starting `wpa_supplicant`, DHCP, API probing, or cloudflared.
> Focused tests pass.  Live WSTA16 used the same V3384 resident and an SD-backed image only
> (no boot flash, no userdata format/populate).  A first short native STA-only gate was too early
> after boot and failed six times with `wifi-scan-link-up-failed` / `link_up_errno=19`; the extended
> same-boot gate then passed on attempt 5 with `decision=wifi-scan-pass` and `scan_result_count=11`.
> `switch_root` reached Debian PID1 (`pid1_comm=init`, `dropbear_started=1`).  In Debian snapshot-only
> mode, `wlan0` was present and `ip link set wlan0 up` returned rc `0`, but direct `iw` scan returned
> rc `234` with BSS count `0` both before and after link-up; a delayed manual scan probe also returned
> `Invalid argument (-22)` twice.  Final Debian decision:
> `wifi-sta-immediate-snapshot-scan-failed`; tunnel gate stayed closed; device rebooted back to native
> V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA16_IMMEDIATE_HANDOFF_SCAN_BLOCKED_2026-07-04.md`.
> **🟠 STATUS (2026-07-04 08:48 KST host clock) — WSTA17 handoff materialization BLOCKED.**
> Codex extended snapshot-only mode with redacted rfkill/phy/proc-wireless state and bounded
> materialization branches (`link-cycle`, `managed-reassert`, `rfkill-unblock`).  Focused tests pass.
> Live WSTA17 used SD-backed rootfs only (no boot flash, no userdata format/populate).  Native
> STA-only scan gate passed on attempt 11 with `scan_result_count=11`; handoff reached Debian PID1.
> Debian had `wlan0_present=1`, WLAN rfkill unblocked, `phy_count=1`, and `/proc/net/wireless` row
> present, but immediate direct `iw` scan still returned rc `234`.  The link-cycle branch changed
> flags to down but then `ip link set wlan0 up` returned rc `2`; manual stderr confirmed
> `RTNETLINK answers: Invalid argument`.  Subsequent direct scans returned rc `156` /
> `Network is down (-100)`.  Managed type reassertion returned rc `0` but did not restore link-up;
> rfkill CLI was absent and sysfs rfkill was already unblocked.  Final decision:
> `wifi-sta-handoff-materialization-scan-failed`; tunnel gate stayed closed; device rebooted back to
> native V3384 with `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA17_HANDOFF_MATERIALIZATION_BLOCKED_2026-07-04.md`.
> **🟠 STATUS (2026-07-04 09:01 KST host clock) — WSTA18 handoff control-plane BLOCKED.**
> Codex ran a report-only live diagnostic using the link-down-free WSTA16 snapshot image copied into
> a WSTA18 private run.  Native STA-only scan passed on attempt 11 with `scan_result_count=10`.
> Native focused dmesg showed `cnss_diag` and `cnss-daemon` cld80211 activity plus WLAN FW/driver
> ready before handoff.  After `switch_root`, Debian still had `wlan0_present=1`, phy/rfkill visible,
> and `ip link set wlan0 up` returned rc `0`, but direct `iw scan` returned rc `234` /
> `Invalid argument (-22)`.  Debian post-handoff process snapshot lacked the native vendor WLAN
> userspace (`cnss-daemon`, `cnss_diag`, and related Android/vendor companions); focused dmesg showed
> `firmware down indication`, `PD service down ... Root PD shutdown`, and repeated
> `WMI stop in progress`.  This explains the inherited-but-unusable `wlan0`: the WCNSS/WMI control
> plane is down after full PID1 handoff.  Device rebooted back to native V3384 with `selftest fail=0`.
> Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md`.
> **NEXT:** choose and prototype the ownership model: preserve/relaunch the minimal vendor WLAN
> control-plane set across handoff, or keep Wi-Fi owned by native init and expose it to Debian as a
> bounded service boundary.  Do not spend more rungs on direct Debian `iw`/link toggles.
> **🟢 STATUS (2026-07-04 09:23 KST host clock) — WSTA19 native-owned chroot Wi-Fi boundary PASS.**
> Codex added `run_wsta19_native_owned_chroot_wifi.py`, a no-flash/no-userdata runner that keeps
> native PID1 alive, runs a WSTA2 materialization preflight, mounts the SD-backed Debian image as a
> chroot, starts temporary key-only dropbear, proves host SSH reaches Debian over USB/NCM, and checks
> that native `wifi scan` still works while the Debian chroot is active.  The first same-boot attempt
> correctly exposed the known stale `flags=0x1002` / `SIOCSIFFLAGS EINVAL` state; a fresh native reboot
> plus WSTA2 preflight then passed (`wlan0_wait_elapsed_ms=69042`, `link_up_rc=0`).  Native pre-chroot
> scan passed on attempt 1 with `scan_result_count=9`; Debian chroot SSH returned `debian_version=12.14`
> and the stage marker; native scan during chroot passed on attempt 1 with `scan_result_count=11`;
> cleanup postcheck confirmed mount/loop/dropbear absent; final V3384 `selftest fail=0`.  No association,
> DHCP, ping, API, public tunnel, `switch_root`, boot flash, or userdata path ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md`.
> **NEXT:** build the native-owned service boundary deliberately: keep native init as Wi-Fi owner and
> expose bounded scan/connect/status operations to Debian/chroot consumers.  Full `switch_root` remains
> USB-local/server-only unless the vendor WLAN control plane is explicitly preserved or relaunched.
> **🟢 STATUS (2026-07-04 09:42 KST host clock) — WSTA20 native Wi-Fi service boundary SOURCE/BUILD PASS.**
> Codex added the native-owned `wifi service [status|start|stop|once] <dir>` command surface in
> `a90_wifi.c`: Debian/chroot consumers write a shared `request` file with `seq` + `op=status|scan`,
> and native init writes an atomic redacted `response` file as the WLAN owner.  This rung deliberately
> denies connect/DHCP/ping/public-tunnel operations and records `owner=native-init`.  The V3385 builder
> produced `A90 Linux init 0.11.141 (v3385-wifi-service-boundary)`, boot SHA
> `33fabe5b90cab57c9e538236e2ad8abef28822807de4051cd8b7027053218710`, and fixed the ramdisk overlay
> to drop the immediate previous DOOM engine so the boot image stays within the 64 MiB boot-partition
> limit.  Static source/builder tests pass.  Report:
> `docs/reports/NATIVE_INIT_V3385_WIFI_SERVICE_BOUNDARY_SOURCE_BUILD_2026-07-04.md`.
> **NEXT:** WSTA20 live gate — flash V3385 via `native_init_flash.py`, health-check it, run WSTA2
> materialization, mount the SD-backed Debian chroot, write status/scan requests from Debian, verify
> native-owned responses, then cleanup and leave the device health-checked.
> **🟢 STATUS (2026-07-04 09:53 KST host clock) — WSTA20 native Wi-Fi service boundary LIVE PASS.**
> Codex added `run_wsta20_native_wifi_service_boundary.py` and flashed V3385 through the checked helper
> (candidate SHA `33fabe5b90cab57c9e538236e2ad8abef28822807de4051cd8b7027053218710`, readback matched,
> flash elapsed `62.086s`).  Post-flash V3385 health passed (`selftest fail=0`).  The runner then used
> WSTA2 materialization (`wlan0_wait_elapsed_ms=102064`, `link_up_rc=0`), mounted the SD-backed Debian
> image as a chroot, started temporary key-only dropbear, wrote `status` and `scan` request files from
> Debian, and verified native-owned response files from `wifi service`: status decision
> `wifi-service-status-pass`, scan decision `wifi-scan-pass`, `scan_result_count=9`, `owner=native-init`,
> and redaction/safety fields for credentials/connect/DHCP/public tunnel.  The service stopped cleanly,
> the service dir was removed, chroot/loop/dropbear postcheck was clean, and V3385 remains resident with
> `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA20_NATIVE_SERVICE_BOUNDARY_PASS_2026-07-04.md`.
> **NEXT:** factor a small Debian-side client/helper for this file protocol and decide whether to keep
> D-public over Wi-Fi limited to native-owned status/scan, or add a separate gated native-owned
> connect/association service rung.
> **🟢 STATUS (2026-07-04 10:01 KST host clock) — WSTA21 native Wi-Fi service client SOURCE/HOST PASS.**
> Codex added `/usr/local/bin/a90-native-wifi-service-client` as a Debian-side helper for the WSTA20
> native-owned file protocol.  The helper publishes atomic `seq + op=status|scan` requests, waits for
> matching native responses, requires `version=a90-native-wifi-service-v1` and `owner=native-init`,
> filters output to redacted allowlisted keys, and rejects connect/association/DHCP/ping/public-tunnel
> operations before writing any request.  The WSTA3 private-rootfs preparer and Debian rootfs builder
> now stage the helper alongside the existing D-public Wi-Fi STA helper.  Host validation passed:
> shell syntax, `py_compile`, and 23 unit tests including a subprocess request/response roundtrip.
> No flash, reboot, association, DHCP, ping, public tunnel, userdata, or switch-root action ran.
> Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA21_NATIVE_SERVICE_CLIENT_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA22 live gate — with V3385 resident/native-owned Wi-Fi service, mount the Debian chroot,
> run the new helper from Debian for `status` and `scan`, verify helper decisions/redaction, cleanup,
> and finish with `selftest fail=0`.  Keep connect/association/DHCP/public tunnel as a separate gated
> native-owned service rung.
> **🟢 STATUS (2026-07-04 10:19 KST host clock) — WSTA22 native Wi-Fi service client LIVE PASS.**
> Codex added `run_wsta22_native_wifi_service_client.py` and proved the WSTA21 Debian helper against
> the WSTA20 native-owned service boundary.  No boot flash ran in the passing gate.  The runner
> health-checked resident V3385, verified native pre-service scan (`scan_result_count=8`), mounted the
> SD-backed Debian chroot, temporarily staged `/usr/local/bin/a90-native-wifi-service-client`, started
> native `wifi service`, and executed the helper from Debian.  Helper `status` returned
> `native-wifi-service-client-pass` / `wifi-service-status-pass`; helper `scan` returned
> `native-wifi-service-client-pass` / `wifi-scan-pass` with `scan_result_count=9`,
> `raw_results_redacted=1`, `credentials=0`, and `connect=0`.  Helper staging was removed, service
> stopped, chroot/dropbear/loop cleanup passed, and final V3385 `selftest fail=0`.  Earlier attempts
> also captured the stale WLAN `EINVAL` mode (`trigger_errno=22`, iftype add `errno=22`), and the
> runner now gates on native scan readiness with a bounded native reboot recovery path.
> Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA22_NATIVE_SERVICE_CLIENT_LIVE_PASS_2026-07-04.md`.
> **NEXT:** choose the next rung: either keep D-public Wi-Fi as native-owned status/scan observability,
> or design a separate gated native-owned connect/association/DHCP service with credential/public
> exposure gates.  Do not fold connect/DHCP/public tunnel into the status/scan helper.
> **🟢 STATUS (2026-07-04 10:32 KST host clock) — WSTA23 native Wi-Fi uplink-service SOURCE/BUILD PASS.**
> Codex chose the second rung as a separate service, not an extension of WSTA20 `wifi service`.
> Native init now has a distinct `wifi uplink-service [status|start|stop|once] <dir>` request/response
> surface with version `a90-native-wifi-uplink-service-v1`.  It supports `status` plus token-gated
> `autoconnect`; `autoconnect` requires `confirm=A90_NATIVE_UPLINK_AUTOCONNECT_V1` and delegates to
> the existing native autoconnect/profile path.  Missing or wrong confirm returns
> `wifi-uplink-service-confirm-required`, while public tunnel and external ping execution remain
> denied and response fields keep credentials `private-config-gated` with `secret_values_logged=0`.
> V3386 built as `A90 Linux init 0.11.142 (v3386-wifi-uplink-service-boundary)`, boot SHA
> `9c097e55a2cf1f371ebba581378eeeb058c192147cdf6964d1c6721c7350a55a`, helper SHA
> `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`, from V3385 base
> `33fabe5b90cab57c9e538236e2ad8abef28822807de4051cd8b7027053218710`.  Static source/builder tests
> passed and no device flash, association, DHCP, ping, public tunnel, userdata, or switch-root action
> ran.  Report:
> `docs/reports/NATIVE_INIT_V3386_WIFI_UPLINK_SERVICE_BOUNDARY_SOURCE_BUILD_2026-07-04.md`.
> **NEXT:** WSTA23 live non-credential gate — flash V3386 through `native_init_flash.py`, health-check,
> prove `wifi uplink-service status`, prove `op=autoconnect` without confirm is denied before connect,
> cleanup and finish with `selftest fail=0`.  Full autoconnect/DHCP remains a separate credential-gated
> live unit; do not run connect/DHCP/public exposure in the no-confirm gate.
> **🟡 STATUS (2026-07-04 10:42 KST host clock) — WSTA23 live gate found profile-label redaction gap; V3387 source/build fix PASS.**
> V3386 flashed cleanly through `native_init_flash.py` (`readback_sha256=9c097e55a2cf...`, flash total
> `62.597s`) and booted as `0.11.142` with `selftest fail=0` after one serial resync retry.  The first
> `wifi uplink-service status` request responded with `wifi-uplink-service-status-pass`, but the response
> exposed a profile label value.  No PSK/SSID file contents, association, DHCP, ping, or public tunnel ran,
> but the file-service contract should be stricter because Debian/helper logs are intended to be commit-safe.
> Codex stopped the temporary service and built V3387 to redact profile label values to booleans:
> `autoconnect_profile_present`, `config_profile_present`, and `requested_profile_present`.  V3387 built as
> `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`, boot SHA
> `ebebf4384f408c5cd20630b12cfd94d56d4d484664612b692de986fdecf6da5d`, helper SHA
> `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`.  Report:
> `docs/reports/NATIVE_INIT_V3387_WIFI_UPLINK_SERVICE_REDACTED_SOURCE_BUILD_2026-07-04.md`.
> **NEXT:** flash V3387, then rerun the WSTA23 non-credential live gate: status response must contain only
> profile-present booleans, no profile label values, and no-confirm `op=autoconnect` must return
> `wifi-uplink-service-confirm-required` before connect/DHCP.
> **🟢 STATUS (2026-07-04 10:48 KST host clock) — WSTA23 native Wi-Fi uplink-service LIVE PASS on V3387.**
> V3387 flashed through `native_init_flash.py --from-native` with remote SHA and boot-block readback
> matching `ebebf4384f408c5cd20630b12cfd94d56d4d484664612b692de986fdecf6da5d`; total flash time
> `62.555s`.  Post-boot `version/status` passed and `selftest fail=0`.  Codex started
> `wifi uplink-service` in a temp dir and proved `op=status` returns
> `version=a90-native-wifi-uplink-service-v1`, `owner=native-init`, `connect=0`,
> `dhcp_routing=observed-only`, `public_tunnel=0`, `secret_values_logged=0`,
> `config_profile_present=1`, `autoconnect_profile_present=1`, and
> `decision=wifi-uplink-service-status-pass` without emitting the profile label value.  A no-confirm
> `op=autoconnect` request returned `rc=-13` / `decision=wifi-uplink-service-confirm-required` with
> `connect=confirm-gated`, `dhcp_routing=config-gated`, `external_ping_execution=0`, and
> `public_tunnel=0`.  The service stopped cleanly and final `selftest fail=0`.  No association, DHCP,
> ping, public tunnel, userdata, switch-root, forbidden partition, or raw credential action ran.
> Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA23_UPLINK_SERVICE_LIVE_PASS_2026-07-04.md`.
> **NEXT:** WSTA24 Debian-side uplink-service client/helper for `status` and no-confirm denial proofs.
> Full confirmed autoconnect/DHCP remains parked until a separate credential-gated live unit.
> **🟢 STATUS (2026-07-04 10:56 KST host clock) — WSTA24 Debian uplink-service client SOURCE/HOST PASS.**
> Codex added `/usr/local/bin/a90-native-wifi-uplink-client` as a Debian-side helper distinct from
> the WSTA21 status/scan helper.  It allows only `status` and `autoconnect-no-confirm`; the latter
> writes `op=autoconnect` without a confirm token and expects
> `wifi-uplink-service-confirm-required`.  Confirmed autoconnect, connect, association, DHCP, ping,
> and public tunnel operations are denied before any request file is written.  Output is allowlisted,
> omits profile label values, and always records `native_wifi_uplink_client_secret_values_logged=0`.
> The WSTA3 private rootfs preparer and base Debian rootfs builder now stage the helper at
> `usr/local/bin/a90-native-wifi-uplink-client`.  Host validation passed: shell syntax, `py_compile`,
> and 25 unit tests.  No flash, association, DHCP, ping, public tunnel, userdata, or switch-root ran.
> Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA24_UPLINK_CLIENT_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA24 live gate on resident V3387 — mount Debian chroot, start native
> `wifi uplink-service`, run the helper from Debian for `status` and `autoconnect-no-confirm`, verify
> redaction/denial, cleanup, and finish with `selftest fail=0`.
> **🟢 STATUS (2026-07-04 11:03 KST host clock) — WSTA24 Debian uplink-service client LIVE PASS on resident V3387.**
> Codex added and live-gated
> `workspace/public/src/scripts/server-distro/run_wsta24_native_wifi_uplink_client.py`.  The runner
> required resident `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`, verified baseline
> `selftest fail=0`, refreshed the SD-backed Debian rootfs image to expected SHA
> `210fc1f92d4eb8bf291fb5b362154a29ca2b579a22a0a41cb1aaa89b5b6cb0dc`, mounted the Debian chroot,
> started temporary key-only dropbear, staged `/usr/local/bin/a90-native-wifi-uplink-client`, and
> started native `wifi uplink-service` in a chroot-visible service directory.  From Debian, helper
> `status` returned `native-wifi-uplink-client-pass` / `wifi-uplink-service-status-pass` with
> `owner=native-init`, `credentials=0`, `connect=0`, `dhcp_routing=observed-only`,
> `public_tunnel=0`, and `secret_values_logged=0`.  Helper `autoconnect-no-confirm` returned
> `native-wifi-uplink-client-pass`, native `rc=-13`, and
> `decision=wifi-uplink-service-confirm-required` with `connect=confirm-gated`,
> `dhcp_routing=config-gated`, `external_ping_execution=0`, and `public_tunnel=0`.  Native service
> stop, helper cleanup, chroot/dropbear/loop cleanup, and final V3387 `selftest fail=0` passed.  No
> boot flash, switch-root, userdata touch, association, confirm-token supply, DHCP, ping, or public
> tunnel action ran.  Host validation passed: `py_compile`, focused WSTA24 unit tests (`4 tests`),
> and `git diff --check`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA24_UPLINK_CLIENT_LIVE_PASS_2026-07-04.md`.
> **NEXT:** WSTA25 should be an explicit credential-gated confirmed autoconnect/DHCP design or
> preflight unit.  Keep confirmed association, DHCP, ping, and public tunnel execution parked until
> that unit supplies the confirm token and private credential/public-exposure policy explicitly.
> **🟢 STATUS (2026-07-04 11:10 KST host clock) — WSTA25 confirmed autoconnect gate SOURCE/PREFLIGHT PASS.**
> Codex extended the Debian-side
> `/usr/local/bin/a90-native-wifi-uplink-client` with a WSTA25 `autoconnect-confirmed` operation while
> keeping the default path fail-closed.  The helper now requires both
> `A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED=1` and the exact
> `A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN` before it writes any request file.  Without the allow gate it
> returns `native-wifi-uplink-client-confirmed-disabled`; with allow but no exact token it returns
> `native-wifi-uplink-client-confirm-token-missing`; both cases write no request.  With both gates,
> the helper writes `op=autoconnect` plus the native confirm field and accepts a redacted
> `wifi-uplink-service-autoconnect-pass` response without echoing the token.  Direct
> `autoconnect`, `connect`, `dhcp`, `ping`, public tunnel, and ambiguous `confirmed-autoconnect`
> operations remain denied before request write.  Rootfs staging metadata now records the
> confirmed-autoconnect env gate and fail-closed policy.  Host validation passed: shell syntax,
> `py_compile`, and focused WSTA/native helper/rootfs tests (`32 tests`, `OK`).  No live confirmed
> autoconnect, association, DHCP, ping, routing, public tunnel, boot flash, switch-root, userdata, or
> credential-value logging ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA25_CONFIRMED_GATE_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA25 live confirmed-autoconnect gate remains separate.  It must be explicitly selected,
> supply both helper env gates, collect only redacted native response metadata, and keep DHCP/routing
> plus public exposure as separate gates unless explicitly authorized.
> **🟢 STATUS (2026-07-04 11:17 KST host clock) — WSTA25 confirmed-autoconnect LIVE RUNNER SOURCE/PREFLIGHT PASS.**
> Codex added `workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py`
> as a fail-closed live runner.  By default it exits before bridge/device/chroot work with
> `decision=wsta25-blocked-explicit-live-allow-required`.  A credentialed run now requires
> `--allow-confirmed-live`, `--ack-credentialed-wifi`, and a matching `--confirm-token`; even then,
> the runner starts with a redacted status request and requires native autoconnect readiness
> (`config_profile_present=1`, `profile_valid=1`, `autoconnect_ready=1`, `autoconnect_enabled=1`)
> before sending `autoconnect-confirmed`.  The confirmed helper command is sent through SSH stdin via
> a redacted script executor, so result JSON records `input_redacted=1` and does not store the token in
> the command vector.  Host validation passed: `py_compile`, focused WSTA/helper/rootfs tests
> (`38 tests`, `OK`), `git diff --check`, and a fail-closed dry run (`rc=2`,
> `wsta25-blocked-explicit-live-allow-required`).  No live confirmed autoconnect, association, DHCP,
> routing, ping, public tunnel, boot flash, switch-root, userdata, or credential-value logging ran.
> Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA25_LIVE_RUNNER_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA25 credentialed live can now be executed only by explicitly selecting the live gate and
> providing all runner gates.  Public exposure remains a later separate gate.
> **🟢 STATUS (2026-07-04 11:22 KST host clock) — WSTA25 credentialed live HOST PREFLIGHT PASS.**
> Codex added `workspace/public/src/scripts/server-distro/prepare_wsta25_live_gate_preflight.py` to
> validate the private Wi-Fi env and WSTA25 live runner without contacting the device.  The preflight
> read only redacted credential metadata: env file exists, owner-private mode is true, SSID/PSK are
> present, SSID byte length is `8`, PSK length is `11`, PSK format is `passphrase`, and
> `secret_values_logged=0`.  It verified the live runner has explicit gates, confirm-token arg,
> redacted SSH stdin executor, status readiness gate, and no direct `wifi connect`/`dhcp`/`ping` or
> public tunnel path.  The runner default dry run still returned `rc=2` /
> `wsta25-blocked-explicit-live-allow-required`, and the generated live command template uses
> `--confirm-token <redacted:A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN>`.  Host validation passed:
> `py_compile`, focused preflight tests (`6 tests`, `OK`), broader WSTA/helper/rootfs regression
> (`44 tests`, `OK`), live-gate preflight PASS, and `git diff --check`.  No device contact,
> association, DHCP, routing, ping, public tunnel, boot flash, switch-root, userdata touch, or
> credential-value logging ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA25_LIVE_GATE_PREFLIGHT_2026-07-04.md`.
> **NEXT:** the explicit WSTA25 credentialed live run is now the next gated step.  Public exposure
> remains separate.
> **🟡 STATUS (2026-07-04 11:33 KST host clock) — WSTA25 credentialed live REACHED confirmed request,
> BLOCKED at native scan.**  Codex ran the WSTA25 live runner twice against resident
> `A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)`.  The first run was correctly
> stopped by the readiness gate: native redacted status reported valid config/profile but
> `autoconnect_enabled=0` / `autoconnect_ready=0`, so the confirmed helper was skipped and no
> request was sent.  Codex then ran `wifi autoconnect enable`, which returned
> `wifi-autoconnect-enabled`; follow-up status returned `wifi-autoconnect-ready`.  The second run
> passed the redacted readiness gate and sent `autoconnect-confirmed` through the stdin redaction
> executor (`input_redacted=True`, no token in the command vector), but native init returned
> `wifi-uplink-service-autoconnect-failed` with
> `autoconnect_decision=wifi-autoconnect-scan-failed`, `rc=-22`, `connect_rc=-22`, `dhcp_rc=0`,
> `final_rc=-22`, `carrier_up=0`, `default_route_present=0`, `external_ping_execution=0`,
> `public_tunnel=0`, and `secret_values_logged=0`.  Service stop, helper cleanup,
> chroot/dropbear/loop cleanup, final V3387 check, and final `selftest fail=0` passed.  Codex then
> restored the persistent autoconnect config with `wifi autoconnect disable`
> (`decision=wifi-autoconnect-disabled`) and rechecked `selftest fail=0`.  No boot flash,
> switch-root, userdata formatter action, successful association, DHCP lease, default route,
> external ping, public tunnel, raw credential logging, or confirm-token logging occurred.  Reports:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA25_CONFIRMED_LIVE_SCAN_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA26 should diagnose the scan failure before reattempting confirmed autoconnect.  Keep
> it bounded to scan/link-state evidence: compare direct native `wifi scan` with the
> uplink-service autoconnect path, capture redacted `wpa_supplicant`/`wlan0` state, and do not run
> confirmed connect, DHCP, external ping, or public exposure until the scan blocker is explained.
> **🟡 STATUS (2026-07-04 11:39 KST host clock) — WSTA26 scan-failure diagnostic SOURCE+LIVE
> BLOCKED at native link-up.**  Codex added
> `workspace/public/src/scripts/server-distro/run_wsta26_scan_failure_diagnostic.py` and focused tests
> to diagnose WSTA25's scan failure below association.  The runner prints a public-safe summary by
> default while keeping raw command transcripts private.  Static validation passed (`py_compile`,
> focused WSTA26 unit tests: `5 tests`, `OK`, and `git diff --check`).  Live run against V3387 first
> confirmed fail-closed state (`autoconnect=0`, `decision=wifi-autoconnect-disabled`) and redacted
> Wi-Fi status (`wlan0_present=1`, `operstate=down`, `ipv4=none`, `default_route_present=0`,
> `supplicant.process_count=0`, `ctrl_socket.kind=missing`).  Four direct native `wifi scan` attempts
> all failed before nl80211 trigger with `decision=wifi-scan-link-up-failed`, `link_up_rc=-1`,
> `link_up_errno=22`, `scan_engine_ok=false`, and `scan_has_bss=false`; final `selftest fail=0`
> passed.  This narrows WSTA25's blocker away from Debian helper plumbing / confirm-token delivery and
> back to the stale WLAN materialization state previously seen in WSTA7/WSTA19 (`wlan0` present but
> not administratively bring-up-able).  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA26_SCAN_FAILURE_DIAGNOSTIC_2026-07-04.md`.
> **NEXT:** WSTA27 should restore the known-good materialization precondition on V3387 before
> reattempting confirmed autoconnect: run a safe native materialization/scan gate, require direct
> native scan success, and only then permit the existing WSTA25 confirmed live runner.  Do not send
> another confirmed request until that scan gate passes.
> **🟡 STATUS (2026-07-04 11:43 KST host clock) — WSTA27 materialization preflight SOURCE+LIVE
> BLOCKED; same-boot recovery fails at link-up.**  Codex added
> `workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py` and focused
> tests.  The runner is explicit-live-gated (`--allow-materialization-live`), blocks by default with
> `wsta27-blocked-explicit-materialization-live-allow-required`, prints a public-safe summary by
> default, and never sends a service connect request / DHCP / ping / public tunnel / flash path.
> Static validation passed (`py_compile`, focused WSTA27 unit tests: `6 tests`, `OK`,
> `git diff --check`).  The live run against V3387 confirmed autoconnect remained disabled and
> selftest stayed clean, but the materialization probe returned
> `decision=softap-iftype-probe-link-up-failed`, `wlan0_present=1`, `wlan0_wait_elapsed_ms=0`,
> `link_up_rc=-1`, and `link_up_errno=22`; before/after status stayed `operstate=down`,
> `ipv4=none`, `default_route_present=0`, `supplicant.process_count=0`, and
> `ctrl_socket.kind=missing`.  The runner did not run the scan gate and did not send any confirmed
> request.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA27_MATERIALIZATION_PREFLIGHT_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA28 should be a no-flash controlled reboot/materialization gate for V3387: reboot
> native init, wait for bridge/version/selftest, confirm autoconnect remains disabled, rerun WSTA27,
> and stop unless direct native scan passes.  Confirmed autoconnect remains parked until that scan
> gate is green.
> **🟢 STATUS (2026-07-04 11:53 KST host clock) — WSTA28 no-flash reboot/materialization gate
> PASS.**  Codex added `workspace/public/src/scripts/server-distro/run_wsta28_reboot_materialization_gate.py`
> and focused tests.  The runner is explicit-reboot-gated (`--allow-native-reboot`), blocks by
> default with `wsta28-blocked-explicit-native-reboot-allow-required`, reuses the resident-session
> reboot/bridge-health helpers, adds a post-reboot settle + nested WSTA27 retry for transient native
> health reads, prints a public-safe summary by default, and never flashes / switch-roots / sends a
> service connect request / DHCP / ping / public tunnel path.  Static validation passed
> (`py_compile`, focused WSTA28 unit tests: `5 tests`, `OK`, `git diff --check`).  Live run against
> V3387 rebooted native init without flashing, reacquired bridge health (`version` V3387, `status`
> ok, `selftest fail=0`), then nested WSTA27 passed: before materialization `wlan0_present=0`,
> iftype probe `softap-iftype-probe-pass` with `wlan0_wait_elapsed_ms=106866`, `link_up_rc=0`,
> `link_up_errno=0`, `ap_iftype_add_rc=0`, `ap_iftype_cleanup_ok=1`; direct native scan returned
> `wifi-scan-pass`, `scan_result_count=11`, `scan_engine_ok=true`, `scan_has_bss=true`,
> `trigger_rc=0`, `trigger_errno=0`.  Post-live selftest stayed `fail=0` and autoconnect remained
> disabled.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA28_REBOOT_MATERIALIZATION_GATE_PASS_2026-07-04.md`.
> **NEXT:** retry the WSTA25 confirmed live path only while preserving this scan-green precondition:
> explicitly enable autoconnect, run the existing confirmed live runner, and restore autoconnect
> disabled afterward.  Public exposure remains separate.
> **🟡 STATUS (2026-07-04 11:58 KST host clock) — WSTA29 confirmed retry after WSTA28 still
> BLOCKED at native autoconnect pre-scan.**  Codex enabled autoconnect and reran the existing WSTA25
> confirmed live runner immediately after WSTA28's scan-green pass.  WSTA25 readiness passed
> (`autoconnect_enabled=1`, `autoconnect_ready=1`, config/profile valid, no external ping/public
> tunnel), and the confirmed helper request was sent through the redacted stdin executor.  Native
> response still failed with `native_wifi_uplink_client_native_rc=-22`,
> `decision=wifi-uplink-service-autoconnect-failed`,
> `autoconnect_decision=wifi-autoconnect-scan-failed`, `rc=-22`, `connect_rc=-22`, `dhcp_rc=0`,
> `final_rc=-22`, `carrier_up=0`, `default_route_present=0`, `external_ping_execution=0`,
> `public_tunnel=0`, and `secret_values_logged=0`.  Runner cleanup and final V3387 selftest passed.
> Codex then restored `wifi autoconnect disable`, ran `wifi cleanup`, verified no IPv4/default route
> or supplicant process, and rechecked `selftest fail=0`.  Source inspection confirms
> `wifi_run_autoconnect_sequence` calls `a90_wifi_scan_once(5000)` before the actual connect path and
> treats negative pre-scan rc as terminal `wifi-autoconnect-scan-failed`; WSTA29 therefore narrows
> the remaining blocker to the native autoconnect pre-scan/materialization path, not Debian helper
> transport.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA29_CONFIRMED_RETRY_SCAN_BLOCKED_2026-07-04.md`.
> **NEXT:** WSTA30 should add a same-run pre-confirm scan/materialization guard to WSTA25 so it does
> not send confirmed autoconnect when native scan has already gone stale.  If that proves the state
> goes stale between WSTA28 and WSTA25, the next native build should move materialization recovery
> into `wifi_run_autoconnect_sequence` before pre-scan failure is terminal.
> **🟡 STATUS (2026-07-04 12:06 KST host clock) — WSTA30 pre-confirm scan guard SOURCE+LIVE
> BLOCKED SAFELY before confirmed request.**  Codex added a same-run pre-confirm native scan gate to
> `run_wsta25_confirmed_autoconnect_live.py` and focused WSTA25 tests.  The guard runs only after
> helper status proves redacted autoconnect readiness and before any confirmed helper request is sent;
> if it fails, the runner records `wsta25-blocked-pre-confirm-scan`,
> `helper_confirmed_attempted=false`, and `helper_confirmed.reason=pre-confirm-scan-not-ready`.
> Static validation passed (`py_compile`, focused WSTA25 unit tests: `7 tests`, `OK`,
> `git diff --check`).  Live run against resident V3387 passed the explicit live/token/readiness
> gates, then the pre-confirm `wifi scan 5000` window failed twice with
> `decision=wifi-scan-trigger-failed`, `scan_engine_ok=false`, `scan_has_bss=false`, `cmd_rc=-22`,
> `link_up_rc=1`, `link_up_errno=0`, `ifindex=9`, `netlink_open=1`, `family_id=19`,
> `trigger_rc=-1`, and `trigger_errno=22`.  The confirmed request was not sent.  Service/helper
> cleanup, mount/loop/dropbear postcheck, final V3387 check, and final `selftest fail=0` passed;
> Codex then restored autoconnect disabled state and ran native Wi-Fi cleanup.  No boot flash,
> switch-root, userdata formatter action, successful association, DHCP, default route, external ping,
> public tunnel, raw credential logging, or token logging occurred.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA30_PRE_CONFIRM_SCAN_GUARD_2026-07-04.md`.
> **NEXT:** WSTA31 should move scan/materialization recovery into the native autoconnect path before
> `wifi_run_autoconnect_sequence` treats a pre-scan `-22` as terminal.  Keep the WSTA30 host guard as
> a fail-closed layer, but the connection fix now belongs native-side.
> **🟡 STATUS (2026-07-04 12:22 KST host clock) — WSTA31 V3388 native scan-recovery SOURCE+BUILD+FLASH
> PASS; confirmed live now BLOCKED at connect/carrier, not scan.**  Codex added native
> autoconnect scan recovery in `a90_wifi.c`: on scan failure, native init runs cleanup, the
> bounded AP-iftype add/delete probe, and one rescan before terminal scan failure.  The
> uplink-service response and Debian helper now pass through redacted
> `scan_recovery_*` fields, and WSTA24/25 resident checks accept the V3388 uplink-service lineage.
> V3388 build produced
> `workspace/private/inputs/boot_images/boot_linux_v3388_wifi_autoconnect_scan_recovery.img`
> with SHA `2971367ef2421161ee18a30a2eeb8088fa1a04b377dbfdf208aa9130cfa6d1f9`.  Static
> validation passed (`py_compile`, `sh -n`, focused tests: `25 tests`, C syntax-only with
> `-Wall -Wextra -Werror`, builder build/string audit, `git diff --check`).  Flash gate passed:
> rollback images were present with expected hashes, `native_init_flash.py --from-native` wrote only
> boot, readback SHA matched, V3388 booted, and `selftest fail=0`.  WSTA25 confirmed live was rerun
> with `--skip-pre-confirm-scan-gate` so native recovery could be tested.  The confirmed request was
> sent, but scan failure did not reproduce: `scan_recovery_attempted=0`,
> `scan_recovery_decision=wifi-autoconnect-scan-recovery-not-attempted`.  Native reached connect and
> failed with `autoconnect_decision=wifi-autoconnect-connect-failed`, `connect_rc=-107`,
> `dhcp_rc=0`, `carrier_up=0`, `default_route_present=0`, `external_ping_execution=0`,
> `public_tunnel=0`, and `secret_values_logged=0`.  Cleanup restored autoconnect disabled state,
> ran Wi-Fi cleanup, verified no IPv4/default route/supplicant, and final `selftest fail=0`.
> Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA31_NATIVE_SCAN_RECOVERY_V3388_LIVE_2026-07-04.md`.
> **NEXT:** WSTA32 should expose redacted native connect/carrier diagnostics through autoconnect /
> uplink-service result fields (`wpa_state`, carrier wait rc/elapsed, ctrl socket status, scan/connect
> event summaries) and diagnose the new `connect_rc=-107` blocker.  Recovery branch execution proof
> remains desirable if scan-stale reappears, but the active live frontier has moved downstream.
> **🟡 STATUS (2026-07-04 12:44 KST host clock) — WSTA32 V3389 connect/carrier diagnostics
> SOURCE+BUILD+FLASH PASS; live now BLOCKED at `/cache` ENOSPC before carrier.**  Codex added redacted
> native connect diagnostics to `a90_wifi.c`, carried them through `autoconnect.result`, the native
> uplink-service response, the Debian helper allowlist, and the WSTA live JSON.  V3389 built as
> `A90 Linux init 0.11.145 (v3389-wifi-connect-carrier-diagnostics)` with boot SHA
> `e9eca0744848f51a44690768c4c6335e2867d718acb2cd1afc010c4cb1dc5b4c`; `native_init_flash.py
> --from-native` wrote only boot, verified readback SHA, booted V3389, and health stayed
> `selftest fail=0`.  Confirmed live reached native autoconnect and proved the new diagnostic fields
> end-to-end, but it did not reach carrier: `connect_diag_attempted=1`,
> `connect_diag_decision=wifi-connect-config-prepare-failed`, `connect_prepare_rc=-28`,
> `connect_ctrl_wait_category=not-run`, `connect_ctrl_status_wpa_state=-`, `connect_carrier_wait_rc=0`,
> `external_ping_execution=0`, `public_tunnel=0`, `secret_values_logged=0`.  A metadata-only device
> check showed `/cache` at `Use%=100%`, explaining `-ENOSPC`.  Cleanup restored autoconnect disabled
> state, ran Wi-Fi cleanup, verified no IPv4/default route/supplicant, and final `selftest fail=0`.
> Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA32_CONNECT_CARRIER_DIAGNOSTICS_V3389_LIVE_2026-07-04.md`.
> **NEXT:** WSTA33 should remove the `/cache` ENOSPC blocker before another carrier run.  Prefer
> SD-backed Wi-Fi runtime placement or bounded native Wi-Fi runtime cleanup that never removes
> credential/config sources and only reports redacted metadata.
> **🟡 STATUS (2026-07-04 13:02 KST host clock) — WSTA33 V3390 cache-ENOSPC fallback
> SOURCE+BUILD+FLASH PASS; live now BLOCKED at WPA 4-way handshake completion.**  Codex added a
> bounded native supplicant-config fallback in `a90_wificfg.c`: if the atomic tmp rewrite fails with
> storage pressure, native init rewrites only the existing generated supplicant config in place via
> `O_NOFOLLOW`, with no broad `/cache` deletion.  V3390 built as
> `A90 Linux init 0.11.146 (v3390-wifi-cache-enospc-fallback)` with boot SHA
> `6c9101fa1e5c835e9d3ec0f828bf924089589fc7d56eff9398257f4f29ee2dbf`; checked-helper flash wrote
> only boot, readback SHA matched, V3390 booted, and health stayed `selftest fail=0`.  Confirmed
> live proved WSTA33 moved past the WSTA32 blocker: `connect_prepare_rc=0`,
> `connect_supplicant_start_rc=0`, `connect_ctrl_wait_category=pong`, control scan/enable/select/
> reassociate all returned `0`, `connect_carrier_wait_rc=0`, and
> `connect_carrier_up_at_wait=1`.  The remaining blocker is downstream:
> `connect_diag_decision=wifi-connect-status-not-completed`,
> `connect_ctrl_status_wpa_state=4WAY_HANDSHAKE`, `connect_ctrl_status_completed=0`,
> `connect_rc=-107`, `final_rc=-107`, `external_ping_execution=0`, `public_tunnel=0`, and
> `secret_values_logged=0`.  Cleanup restored autoconnect disabled state, ran Wi-Fi cleanup,
> verified no IPv4/default route/supplicant, and final `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA33_CACHE_ENOSPC_FALLBACK_V3390_LIVE_2026-07-04.md`.
> **NEXT:** WSTA34 should diagnose the WPA 4-way-handshake stall with redacted native wpa-control
> event/status capture and compare it against the earlier known-good Debian WSTA7 association flow.
> Do not log credentials, do not enable public exposure, and keep external ping/tunnel gated off.
> **🟡 STATUS (2026-07-04 13:45 KST host clock) — WSTA34/WSTA35 V3391/V3392 WPA diagnostics
> SOURCE+BUILD+FLASH+LIVE progressed; current blocker is ctrl local abstract socket collision before
> final WPA interpretation.**  V3391 added bounded WPA completion wait plus redacted WPA monitor
> counters/categories, built as `A90 Linux init 0.11.147 (v3391-wifi-wpa-handshake-diagnostics)` with
> boot SHA `11a2685964a93271bac9d2ef34348f2a74a2aa079a3ca46941b731d5f4ed76b3`, and flashed cleanly
> through the checked helper.  Live WSTA34 did not reach WPA diagnostics because `/cache` was still
> full and control socket directory preparation failed: `connect_prepare_rc=-28`,
> `connect_diag_decision=wifi-connect-config-prepare-failed`, `connect_supplicant_spawned=0`,
> `external_ping_execution=0`, `public_tunnel=0`, `secret_values_logged=0`; cleanup restored
> autoconnect disabled, no supplicant/default route, and `selftest fail=0`.  V3392 moved the
> supplicant control directory to `/tmp/a90-wifi/sockets`, built as
> `A90 Linux init 0.11.148 (v3392-wifi-tmp-ctrl-dir)` with boot SHA
> `da2f39b60300497d8957abff77a97764864fd8a6d3de3018bb8e837837c9861c`, and flashed cleanly through
> the checked helper.  Direct `wifi config prepare` then passed with
> `ctrl_interface.dir=/tmp/a90-wifi/sockets`.  Live WSTA35 reached supplicant/control/carrier/WPA
> monitor and bounded WPA wait: `connect_prepare_rc=0`, `connect_ctrl_wait_category=pong`,
> `connect_carrier_wait_rc=0`, `connect_wpa_monitor_attach_rc=0`,
> `connect_wpa_monitor_event_count=56`, `connect_wpa_complete_wait_rc=-110`,
> `connect_wpa_complete_first_state=4WAY_HANDSHAKE`, `connect_wpa_complete_last_state=4WAY_HANDSHAKE`,
> `connect_wpa_monitor_temp_disabled_seen=1`, no connected/auth-reject/assoc-reject/EAP-failure
> category, and final `selftest fail=0`.  However the immediate post-monitor ctrl commands all
> returned `-98`; source inspection shows the likely cause is local abstract ctrl socket names based
> only on `pid + monotonic_millis`, so the persistent monitor socket can collide with one-shot request
> sockets in the same millisecond.  Reports:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA34_WPA_HANDSHAKE_DIAGNOSTICS_V3391_LIVE_2026-07-04.md`
> and
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA35_TMP_CTRL_DIR_V3392_LIVE_2026-07-04.md`.
> **NEXT:** WSTA36 should make native ctrl local abstract socket names monotonic-unique, then rebuild,
> flash, and rerun the same confirmed-autoconnect gate.  Only after `DRIVER COUNTRY`, `SCAN`,
> `ENABLE_NETWORK`, `SELECT_NETWORK`, and `REASSOCIATE` no longer fail with `-98` should the remaining
> 4-way-handshake stall be interpreted as a true WPA/AP/credential/driver condition.
> **🟡 STATUS (2026-07-04 14:01 KST host clock) — WSTA36 V3393 ctrl socket uniqueness
> SOURCE+BUILD+FLASH+LIVE PASS for the `-98` artifact; confirmed autoconnect remains BLOCKED at true
> WPA 4-way completion.**  V3393 adds a process-local sequence to native WPA ctrl local abstract
> socket names, built as `A90 Linux init 0.11.149 (v3393-wifi-ctrl-socket-unique)` with boot SHA
> `ee9d185e831265c47b11939a929ce361d70efc770e746f65d7b2c65884162f79`, and flashed cleanly through
> the checked helper (`63.135s`, readback SHA matched, post-boot `selftest fail=0`).  Live WSTA36
> proves the V3392 collision diagnosis: `connect_ctrl_driver_country_rc=0`,
> `connect_ctrl_scan_rc=0`, `connect_ctrl_enable_network_rc=0`,
> `connect_ctrl_select_network_rc=0`, and `connect_ctrl_reassociate_rc=0` after monitor attach.
> The remaining blocker is downstream and real: `connect_carrier_wait_rc=0`,
> `connect_carrier_up_at_wait=1`, `connect_wpa_monitor_attach_rc=0`,
> `connect_wpa_monitor_event_count=55`, `connect_wpa_monitor_temp_disabled_seen=1`,
> `connect_wpa_complete_wait_rc=-110`, `connect_wpa_complete_first_state=4WAY_HANDSHAKE`,
> `connect_wpa_complete_last_state=4WAY_HANDSHAKE`, `connect_wpa_complete_completed=0`,
> no connected/auth-reject/assoc-reject/EAP-failure category, `external_ping_execution=0`,
> `public_tunnel=0`, `secret_values_logged=0`, and final cleanup/selftest clean.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA36_CTRL_SOCKET_UNIQUE_V3393_LIVE_2026-07-04.md`.
> **NEXT:** WSTA37 should add redacted WPA failure-detail classification around this true
> 4-way-handshake stall: temp-disabled/disconnect reason class, selected-network state,
> key-management/pairwise/group/country summary without SSID/PSK/BSSID, and a same-run comparison
> against the known-good Debian WSTA7 association shape where possible.
> **🟡 STATUS (2026-07-04 14:19 KST host clock) — WSTA37 V3394 WPA failure-detail
> SOURCE+BUILD+FLASH+LIVE PASS; confirmed autoconnect now classified as `WRONG_KEY`, not native
> control-plane failure.**  V3394 carries forward the V3393 ctrl socket uniqueness fix and adds
> redacted WPA failure-detail classifications plus safe ctrl `STATUS` fields.  It built as
> `A90 Linux init 0.11.150 (v3394-wifi-wpa-failure-detail)` with boot SHA
> `471ac301103e27e02bfac7faae3fee850e759218a05ffede1b596c10e5a240a7`, flashed cleanly through the
> checked helper (`62.763s`, readback SHA matched, post-boot `selftest fail=0`), and final cleanup
> again left autoconnect disabled, no IPv4/default route, no supplicant process, and
> `selftest fail=0`.  Live WSTA37 kept the WSTA36 ctrl fix intact:
> `connect_ctrl_driver_country_rc=0`, `connect_ctrl_scan_rc=0`,
> `connect_ctrl_enable_network_rc=0`, `connect_ctrl_select_network_rc=0`, and
> `connect_ctrl_reassociate_rc=0`.  The WPA path still does not complete:
> `connect_diag_decision=wifi-connect-status-not-completed`, `connect_rc=-107`, `final_rc=-107`,
> `connect_carrier_wait_rc=0`, `connect_carrier_up_at_wait=1`,
> `connect_wpa_complete_first_state=4WAY_HANDSHAKE`,
> `connect_wpa_complete_last_state=4WAY_HANDSHAKE`, `connect_wpa_complete_completed=0`, and
> `connect_ctrl_status_completed=0`; public tunnel and external ping stayed disabled and
> `secret_values_logged=0`.  The new fields now classify the reason:
> `connect_wpa_monitor_temp_disabled_reason_class=WRONG_KEY`,
> `connect_wpa_monitor_disconnect_reason_class=15`,
> `connect_ctrl_status_network_selected=1`, `connect_ctrl_status_key_mgmt=WPA2-PSK`,
> `connect_ctrl_status_pairwise_cipher=CCMP`, `connect_ctrl_status_group_cipher=CCMP`,
> `connect_ctrl_status_mode=station`, and `connect_ctrl_status_freq_mhz=5745`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA37_WPA_FAILURE_DETAIL_V3394_LIVE_2026-07-04.md`.
> **NEXT:** WSTA38 should stop probing native transport/control mechanics and reconcile
> credential/AP-side authentication material against the earlier known-good Debian WSTA7 association
> path without logging secrets.  Either refresh/prove the native profile material or identify the AP
> compatibility/security-mode delta; only after `WRONG_KEY` is cleared should DHCP/default-route and
> public uplink exposure be retried.
> **🟢 STATUS (2026-07-04 14:46 KST host clock) — WSTA38 auth-material reconcile PASS;
> stale resident native PSK secret found, restaged, and re-proved with redacted output.**  Codex
> added `workspace/public/src/scripts/server-distro/run_wsta38_auth_material_reconcile.py` and
> focused tests.  The first WSTA38 run classified the WSTA37 `WRONG_KEY` as
> `wsta38-device-psk-secret-mismatch`: host env and the known-good WSTA7 Debian config both had
> SSID length `8` and PSK length `11`, while the resident native device PSK secret length was `10`;
> the native generated PSK matched the device-secret reference, not the host/WSTA7 reference.
> Codex then restaged the native Wi-Fi profile from the current private env with the existing
> profile staging helper (`decision=wifi-profile-stage-pass`, `secret_values_logged=0`) and reran
> WSTA38 after tightening path/profile redaction.  Final result:
> `decision=wsta38-credential-material-consistent`,
> `credential_material_consistent=true`, `device_psk_secret_matches_env=true`,
> `native_psk_hex_matches_python_reference=true`, `native_psk_hex_matches_device_secret_reference=true`,
> no association/DHCP/ping/public tunnel, and `secret_values_logged=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA38_AUTH_MATERIAL_RECONCILE_2026-07-04.md`.
> **🟢 STATUS (2026-07-04 14:46 KST host clock) — WSTA40/WSTA41 V3394
> reboot-materialization + confirmed native autoconnect LIVE PASS.**  Codex updated the WSTA28
> reboot materialization gate to accept the supported native uplink build list instead of only
> V3387, then ran it against resident V3394.  WSTA40 passed:
> `decision=wsta28-reboot-materialization-scan-gate-pass`,
> `checks.post_reboot_health=true`, nested
> `decision=wsta27-materialization-scan-gate-pass`, `wlan0_wait_elapsed_ms=106870`,
> `scan_result_count=12`, `scan_engine_ok=true`, `scan_has_bss=true`, `trigger_rc=0`, and
> `trigger_errno=0`.  After this scan-green state, WSTA41 explicitly enabled autoconnect and reran
> the credential-gated confirmed helper with the confirm token redacted.  It passed:
> top-level `decision=wsta25-confirmed-autoconnect-live-pass`,
> helper `decision=wifi-uplink-service-autoconnect-pass`,
> `connect_rc=0`, `dhcp_rc=0`, `final_rc=0`, `carrier_up=1`,
> `connect_ctrl_status_wpa_state=COMPLETED`, `default_route_present=1`, `nameserver_count=2`,
> `external_ping_execution=0`, `public_tunnel=0`, and `secret_values_logged=0`.  Cleanup restored
> `wifi-autoconnect-disabled`, stopped supplicant, removed IPv4/default route state, and final
> `selftest` returned `fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA40_WSTA41_MATERIALIZATION_CONFIRMED_AUTOCONNECT_PASS_2026-07-04.md`.
> **NEXT:** native Wi-Fi STA uplink is now proven through DHCP on V3394 when starting from the
> reboot/materialization scan-green precondition.  The next rung can retry D-public/public tunnel
> exposure over STA, but only behind the existing explicit public-live gates, with no raw
> SSID/PSK/BSSID/IP/gateway/DNS/token/public URL in committed artifacts.
> **🟢 STATUS (2026-07-04 17:35 KST host clock) — WSTA42 native-owned STA uplink + D-public
> quick Tunnel LIVE PASS.**  Codex added
> `workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py` and focused
> tests.  The runner keeps native init as Wi-Fi owner, mounts Debian only as the chroot service
> surface, requires explicit credentialed Wi-Fi and public-exposure gates, and keeps confirm tokens,
> DNS values, credentials, and the generated public URL out of public artifacts.  After a WSTA28
> reboot/materialization precondition (`scan_result_count=12`, `scan_engine_ok=true`,
> `scan_has_bss=true`), WSTA42 passed on resident V3394: native confirmed uplink passed, default
> route was via `wlan0`, resolver fallback staged usable host resolver entries with values redacted
> (`source=host-resolver`, `nameserver_count=2`), local D-public smoke passed after bringing `lo` up,
> `cloudflared` quick Tunnel produced a redacted URL, and host public HTTPS smoke passed on attempt 3
> with `http_status=200`, `marker_ok=true`, `service_ok=true`, and
> `public_exposure_marker_ok=true`.  Cleanup stopped D-public processes, native service/helper,
> chroot/dropbear/loop; final Wi-Fi status was down/no IPv4/no default route/autoconnect disabled and
> final `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA42_NATIVE_UPLINK_DPUBLIC_TUNNEL_PASS_2026-07-04.md`.
> **NEXT:** promote this from a live proof to an appliance workflow: decide whether WSTA43 should
> automate the WSTA28 scan-green precondition inside the WSTA42 runner, then integrate the native-owned
> uplink + Debian service/HUD path without default public exposure.  Persistent always-on public mode
> remains a separate gate.
> **🟢 STATUS (2026-07-04 17:55 KST host clock) — WSTA43 orchestrated WSTA28→WSTA42
> LIVE PASS.**  Codex added
> `workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py` and
> focused tests.  The runner requires explicit orchestrated-live, native-reboot, public-live,
> credentialed-Wi-Fi, public-exposure, native confirm-token, and public confirm-token gates before any
> device work.  It first runs WSTA28 and stops before public exposure unless scan-green is proven.  Live
> WSTA43 passed: nested WSTA28 returned `wsta28-reboot-materialization-scan-gate-pass`; nested WSTA27
> returned `wsta27-materialization-scan-gate-pass` with `scan_result_count=12`, `scan_engine_ok=true`,
> `scan_has_bss=true`, `trigger_rc=0`, and `trigger_errno=0`.  Then nested WSTA42 passed:
> native uplink confirmed, default route via `wlan0`, resolver ready from native DHCP
> (`nameserver_count=2`, values redacted), local smoke passed, quick Tunnel URL was observed with value
> redacted, and host public HTTPS smoke passed on attempt 2 with `http_status=200`, `marker_ok=true`,
> `service_ok=true`, and `public_exposure_marker_ok=true`.  Cleanup stopped D-public processes,
> native service/helper, chroot/dropbear/loop; final Wi-Fi status was down/no IPv4/no default route/
> autoconnect disabled and final `selftest fail=0`.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA43_ORCHESTRATED_NATIVE_UPLINK_DPUBLIC_PASS_2026-07-04.md`.
> **NEXT:** WSTA44 should move from proof gate to appliance workflow: boot/native init should keep default
> public exposure off, then a controlled operator command/profile should bring up native-owned STA,
> Debian service/HUD, and optional quick Tunnel using the WSTA43 sequence.
> **🟢 STATUS (2026-07-04 16:15 KST host clock) — WSTA44 appliance native-uplink profile
> SOURCE PASS.**  Codex added the Debian-side
> `/usr/local/bin/a90-dpublic-native-uplink-profile` source and stages it through both
> `build_debian_aarch64_rootfs.py` and `prepare_wsta3_sta_rootfs.py`.  The profile is default-off:
> `profile`/`preflight` only records readiness, `autoconnect-confirmed` requires
> `/etc/a90-dpublic/native-uplink-enable` plus the native uplink env confirm gates, and
> `quick-tunnel`/`public-tunnel` does not start `cloudflared`; it records that the WSTA43
> host-orchestrated public sequence is required.  Firstboot now records
> `native_uplink_decision=operator-profile-manual` and `native_uplink_public_default=off` without
> auto-running native uplink or public exposure.  Host validation passed: 37 focused tests,
> `py_compile`, `sh -n`, and `git diff --check`.  No device action, no flash, no Wi-Fi association,
> and no public tunnel ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA44_APPLIANCE_NATIVE_UPLINK_PROFILE_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA45 should add an operator-facing wrapper/menu entry for the WSTA43 sequence that consumes
> this default-off profile, preserving the explicit native-reboot, credentialed-Wi-Fi, and public-exposure
> gates.
> **🟢 STATUS (2026-07-04 16:24 KST host clock) — WSTA45 appliance operator wrapper
> SOURCE PASS.**  Codex added
> `workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py` as the default-off
> operator entrypoint.  Default `preflight` mode validates the WSTA44 profile/menu contract with no
> device action.  `publish` mode delegates to WSTA43 only after explicit
> `--use-native-uplink-profile`, operator-live, native-reboot, public-live, credentialed-Wi-Fi,
> public-exposure, native confirm-token, and public confirm-token gates; WSTA43 gate flags are blocked
> from passthrough so they cannot be smuggled around WSTA45.  WSTA42 now supports
> `--use-native-uplink-profile`, stages `/usr/local/bin/a90-dpublic-native-uplink-profile` into the
> chroot, creates the private `/etc/a90-dpublic/native-uplink-enable` gate only for confirmed
> autoconnect, requires both native-client and profile pass markers, and cleans the staged profile/enable
> file.  WSTA43 forwards the profile flag into WSTA42, and the Debian profile records
> `native_uplink_profile_operator_wrapper=wsta45`.  Host validation passed: 32 focused tests,
> `py_compile`, `sh -n`, default WSTA45 preflight, and `git diff --check`.  No device action, no flash,
> no Wi-Fi association, and no public tunnel ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA45_APPLIANCE_OPERATOR_WRAPPER_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA46 can be the explicit WSTA45 publish live gate, but only with the same deliberate
> native-reboot, credentialed-Wi-Fi, public-exposure, and confirm-token acknowledgements used by WSTA43.
> **🟢 STATUS (2026-07-04 16:33 KST host clock) — WSTA46 WSTA45 profile publish
> LIVE PASS.**  Codex ran the new WSTA45 operator wrapper in `publish` mode with explicit
> `--use-native-uplink-profile`, operator-live, native-reboot, public-live, credentialed-Wi-Fi,
> public-exposure, native confirm-token, and public confirm-token gates.  No boot image was built or
> flashed.  WSTA45 passed with decision `wsta45-appliance-operator-wsta43-profile-pass`; nested WSTA43
> passed; nested WSTA28 scan-green passed; nested WSTA42 passed with
> `use_native_uplink_profile=true`, `native_uplink_profile_staged=true`,
> `native_uplink_profile_confirmed=true`, and `native_uplink_profile_cleanup_ok=true`.  Profile confirmed
> markers included `native-uplink-profile-autoconnect-pass`, `native_uplink_profile_public_default=off`,
> native client pass, native service `wifi-uplink-service-autoconnect-pass`, and `public_tunnel=0` at the
> native service boundary.  D-public over native STA also passed: default route via `wlan0`, resolver ready
> with `nameserver_count=2` redacted, local smoke pass, quick Tunnel URL observed but not committed, and
> host public smoke passed on attempt 4 with `http_status=200`, `marker_ok=true`, `service_ok=true`,
> `public_exposure_marker_ok=true`, and `url_redacted=true`.  Cleanup removed D-public processes, staged
> profile/enable file, helper, service dir, chroot/dropbear/loop state; independent post-run checks showed
> resident v3394 with `selftest fail=0`, `wifi status` down/no IPv4/no default route/no supplicant process,
> and autoconnect disabled.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA46_WSTA45_PROFILE_PUBLISH_LIVE_PASS_2026-07-04.md`.
> **NEXT:** WSTA47 should productize this now-proven profile publish path: tighten run metadata/ended
> timestamps or add a reusable documented operator alias.  Persistent always-on public exposure remains a
> separate gate.
> **🟢 STATUS (2026-07-04 16:39 KST host clock) — WSTA47 operator productization
> SOURCE PASS.**  Codex tightened the proven WSTA45/WSTA42 publish path without another live/public
> run.  WSTA42 now uses `utc_stamp()`/`finish_result()` so terminal gate failures, local image/helper
> failures, final classification, cleanup-finalized results, and top-level runner errors persist
> `ended_utc` consistently.  WSTA45 now exposes a redacted `operator_publish_template` in the menu,
> public summary, and result JSON, and adds `--print-publish-template` for an operator-safe command
> skeleton with `<native-confirm-token>` and `<public-confirm-token>` placeholders.  Host validation
> passed: 17 focused WSTA42/WSTA45 tests, `py_compile`, `--print-publish-template`, and
> `git diff --check`.  No device action, no flash, no native reboot, no Wi-Fi association, and no public
> tunnel ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA47_OPERATOR_PRODUCTIZATION_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA48 should only continue this source/productization track if it adds a concrete operator
> surface, such as a concise committed runbook for the WSTA45 template or a redacted result aggregation
> helper.  Persistent always-on public exposure remains a separate explicit gate.
> **🟢 STATUS (2026-07-04 16:44 KST host clock) — WSTA48 redacted result aggregation
> SOURCE PASS.**  Codex added
> `workspace/public/src/scripts/server-distro/run_wsta48_redacted_result_aggregate.py`, a host-only
> operator helper that reads explicit WSTA result JSON files/directories, recursively discovers
> `wsta*_result.json`, and emits an allowlisted aggregate with counts, decisions, timestamps, elapsed
> seconds, and redacted nested summaries.  It reuses WSTA45/WSTA43 public-summary allowlists and WSTA43's
> WSTA42 summarizer, reduces unknown WSTA files to a narrow decision/check/safety surface, and fail-closes
> if the aggregate contains known confirm-token values, public URL/domain material, public URL scratch
> paths, or obvious Wi-Fi credential assignment strings.  Host validation passed: 22 focused tests,
> `py_compile`, and `git diff --check`.  A source-only smoke over the existing private WSTA46 run produced
> `result_count=5`, `all_pass=True`, and pass decisions for WSTA27/WSTA28/WSTA42/WSTA43/WSTA45 with the
> redaction guard clean; the aggregate output stayed under `workspace/private/runs/` and was not committed.
> No device action, no flash, no native reboot, no Wi-Fi association, and no public tunnel ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA48_REDACTED_RESULT_AGGREGATE_SOURCE_2026-07-04.md`.
> **NEXT:** The source/productization path now has the core operator surfaces.  Continue WSTA only with a
> concrete appliance-level operator runbook/HUD/menu integration or a deliberately gated persistent
> exposure design; avoid another metadata-only cleanup.
> **🟢 STATUS (2026-07-04 16:47 KST host clock) — WSTA49 appliance operator runbook
> SOURCE PASS.**  Codex added
> `docs/operations/A90_WSTA_NATIVE_UPLINK_DPUBLIC_OPERATOR_RUNBOOK.md`, a committed runbook that stitches
> the proven WSTA45/WSTA43/WSTA42/WSTA48 surfaces into one operator procedure: bridge/resident/selftest
> prechecks, WSTA45 host-only preflight, redacted publish-template printing, explicit WSTA45 live publish
> with native-reboot/credentialed-Wi-Fi/public-exposure/confirm-token gates, WSTA48 redacted aggregation,
> independent post-run `status`/`selftest`/`wifi status`, stop conditions, and non-goals.  All live
> examples use `<native-confirm-token>` and `<public-confirm-token>` placeholders and keep private
> aggregate outputs under `workspace/private/`.  Host validation passed: 8 focused WSTA49/WSTA48 tests and
> `git diff --check`; tests verify required command surfaces, placeholder-only live values, absence of
> actual confirm-token constants/public tunnel domain strings/obvious Wi-Fi credential assignments, and
> explicit non-authorization of flashing or always-on public exposure.  No device action, no flash, no
> native reboot, no Wi-Fi association, and no public tunnel ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA49_OPERATOR_RUNBOOK_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA source/productization is now saturated unless the work moves into native/HUD/menu
> integration or a deliberately gated persistent exposure design.  Do not spend another unit on metadata
> cleanup.
> **🟢 STATUS (2026-07-04 16:53 KST host clock) — WSTA50 native menu screenapp
> SOURCE PASS.**  Codex moved the WSTA operator path into the native/HUD/menu surface without adding any
> native public action.  The NETWORK menu now has a `WSTA PUBLISH` item mapped to
> `SCREEN_MENU_WSTA_OPERATOR`/`SCREEN_APP_WSTA_OPERATOR`; `screenapp wsta` and `screenapp dpublic` present
> the same read-only screen.  The screen is rendered by `a90_app_network_draw_wsta_operator()` and shows the
> proven flow (`WSTA45 -> WSTA43 -> WSTA42`), that publish remains host-runbook only, that the native menu
> is display-only/no-connect, and that WSTA48 provides redacted aggregation.  It does not call Wi-Fi command
> handlers, scan/ping collectors, D-public runners, cloudflared, native reboot, or flash paths.  Host
> validation passed: 13 focused WSTA/native screenapp tests, `git diff --check`, and a host-only AArch64
> `build_init` compile/strip to `/tmp/a90_wsta50_init_compile` (warnings were pre-existing unrelated
> native-init warnings).  No device action, no flash, no native reboot, no Wi-Fi association, and no public
> tunnel ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA50_NATIVE_MENU_SCREENAPP_SOURCE_2026-07-04.md`.
> **NEXT:** WSTA now has host wrapper/template/aggregate/runbook plus native menu visibility.  The next
> meaningful WSTA unit should be either a deliberately gated persistent exposure design or live validation
> of the new `screenapp wsta` surface in a boot artifact; avoid another host-only productization-only pass.
> **🟢 STATUS (2026-07-04 17:03 KST host clock) — WSTA51 native menu screenapp LIVE
> PASS.**  Codex built and checked-helper flashed V3395
> (`A90 Linux init 0.11.151 (v3395-wsta-screenapp-live)`,
> boot SHA256 `4d3eb72f20d8a2cf6186b81b7cdcf86c01b68bbc34d9007cc573d0bb19fb0605`) to validate the
> WSTA50 native visual surface in a real boot artifact.  Pre-flash gates passed: current resident
> `status`/`selftest` were clean, v2321/v2237/v48 rollback images were present, and the TWRP recovery
> image/path was confirmed.  `native_init_flash.py --from-native` verified Android boot magic, local
> version marker, local SHA, remote pushed SHA, and boot-prefix readback SHA, then V3395 booted with
> `status=ok` and `selftest fail=0`.  After the expected auto-menu `busy` response, `hide` + settle made
> both `screenapp wsta` and `screenapp dpublic` pass with `screenapp.safety=display-only-explicit`,
> `screenapp.title=WSTA D-PUBLIC`, `screenapp.rc=0`, and `screenapp.presented=1`; post-screenapp
> `status`/`selftest` stayed clean.  No credentialed Wi-Fi association, DHCP, public tunnel, public smoke
> request, userdata format/populate, switch-root, persistent exposure, or non-boot partition write ran.
> Reports:
> `docs/reports/NATIVE_INIT_V3395_WSTA_SCREENAPP_SOURCE_BUILD_2026-07-04.md` and
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA51_NATIVE_MENU_SCREENAPP_LIVE_2026-07-04.md`.
> **NEXT:** WSTA display/productization is now live-proven.  The next meaningful WSTA unit should be either
> a deliberately gated persistent exposure design or a WSTA45 operator publish live run via the WSTA49
> runbook; do not spend another unit on menu/display-only polish.
> **🟢 STATUS (2026-07-04 17:08 KST host clock) — WSTA52 persistent exposure
> DESIGN PASS.**  Codex added
> `docs/operations/A90_WSTA_PERSISTENT_EXPOSURE_DESIGN.md`, a fail-closed design contract for a future
> persistent D-public mode.  The design explicitly defines persistent as a supervised renewable public
> lease, not always-on exposure: `default_state=public-off`, bounded lease TTL, host-gated renewal,
> no boot autostart without a valid private lease, and no committed raw public URL.  It preserves the
> proven flow WSTA45 -> WSTA43 -> WSTA28 -> WSTA42 -> WSTA48, keeps native init as Wi-Fi owner and
> Debian as the service surface, requires explicit credentialed-Wi-Fi/public-exposure acknowledgements
> and private confirm-token sources, and makes success depend on D-public cleanup, tunnel absence,
> smoke absence, native-uplink profile cleanup, helper/chroot/Wi-Fi cleanup, post selftest, and WSTA48
> redaction.  Validation passed: 17 focused WSTA52/WSTA49/WSTA45 tests and `git diff --check`.  No live
> command, flash, native reboot, Wi-Fi association, DHCP, public tunnel, public smoke, userdata action,
> or switch-root ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA52_PERSISTENT_EXPOSURE_DESIGN_2026-07-04.md`.
> **NEXT:** implement WSTA53 source-only: a persistent lease parser and redacted plan generator that is
> fail-closed by default and performs no live action; it should prepare WSTA54 host-only private lease
> artifact generation.
> **🟢 STATUS (2026-07-04 17:12 KST host clock) — WSTA53 persistent exposure plan
> SOURCE PASS.**  Codex added
> `workspace/public/src/scripts/server-distro/run_wsta53_persistent_exposure_plan.py`, a host-only lease
> parser/redacted-plan generator for the WSTA52 persistent exposure design.  It defaults fail-closed,
> performs no live/device action, rejects forbidden nested fields (`raw_public_url`, Wi-Fi identifiers,
> IP/routing/DNS fields, and confirm-token values), enforces `ttl_sec <= 14400`, requires explicit
> credentialed-Wi-Fi/public-exposure acknowledgements and `private` confirm-token source markers, and emits
> a redacted plan with `future_live_allowed=false` plus `wsta54_private_artifact_ready=true` only when the
> source-only lease request is valid.  CLI smoke passed for `--print-template` and a valid redacted plan
> under `workspace/private/runs/server-distro/wsta53-smoke`; no raw public URL or secret value was printed
> or committed.  Validation passed: 13 focused WSTA53/WSTA52 tests, `py_compile`, and `git diff --check`.
> No device command, flash, native reboot, Wi-Fi association, DHCP, public tunnel, public smoke, userdata
> action, switch-root, or external service action ran.  Report:
> `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA53_PERSISTENT_EXPOSURE_PLAN_SOURCE_2026-07-04.md`.
> **NEXT:** implement WSTA54 host-only private lease artifact generation: consume the WSTA53 redacted plan,
> materialize the private lease under `workspace/private/`, and still perform no device action.

## North star — priority-ordered tracks (T1 → T2 → T3)

Pursue the **highest tier that still has a meaningful, safely-actionable next step**.
Drop to the next tier only when the current one is *saturated* or *meaningless* (criteria
below). Re-evaluate each iteration; you may climb back up if new work appears.

### Audio (ADSP/Q6) speaker — DONE ✅ (CORE device-proven + promoted `0.10.0`, 2026-06-19) — now BACKGROUND/optional

Internal-speaker playback works on-device as a self-contained native-init command: `audio play --execute`
runs the integrated worker (adsp boot → `/dev/snd` materialize → global **App Type Config** write → native
ACDB SET replay into `/dev/msm_audio_cal` → route apply → PCM write → cleanup), promoted to init `0.10.0`
(V2811/V2814 audible, V2812 build → V2815 promote). The unlock was the missing global App Type Config write
(numid 3122/3123 → kernel `app_type_cfg[]`, fixing `adm_open bit_width:0→16`); residual `q6asm` ENEEDMORE
(audstrm cal_type 15) is source-confirmed non-fatal. Boot chime, bounded `audio stop`, status/selftest/
screenapp surfaces, and a bundled chime preset all landed across the `0.10.x` line.

**AUDIO IS NO LONGER THE ACTIVE FRONTIER.** Safety still in force: amp ≤ 0.2, no WSA gain/boost / SP-bypass
writes; `v2321` stays the flash-gate rollback target. Magisk remains an Android-side *measurement* capsule
only, never a native-init runtime dependency. Full history (AUD-0 → AUD-5, V2324 → V2815): `CLAUDE.md` +
`docs/reports/` + `docs/operations/VERSIONING_POLICY.md`. Reopen only for an explicit audio polish/feature ask.

### ✅ SUPERSEDED — Video PLAYBACK / Bad Apple / GPU demo ladder — DONE (kept below for history)

> **POINTER (operator, 2026-06-28): Video/GPU AND SoftAP are both CLOSED. The single active epic is now
> `## 🟣 ACTIVE NOW — DELEGATED: Tier-2 Runtime Kernel REPL (v1-repl → v2a)` further down this file.**
> Bad Apple full-song demo, GPU first-light/triangle/compute/accel-2D/monitor/zero-copy rungs, and DOOM
> are all DONE and eye-confirmed; the loop pivoted GPU→SoftAP at V3336; SoftAP S0→S4 is DONE at V3344.
> Do NOT resume Video/Nyan/GPU/SoftAP work — go to the **Runtime Kernel REPL** delegated block. v2a is
> LIVE-PROVEN end-to-end (v1-slide, v1-repl slide/peek/poke/call, kallsyms extractor v2a0, named host
> driver v2a1, recovered-export allocator-backed poke round-trip v2a2). **The ACTIVE NEXT EPIC is now v2c —
> Tier-2 Kernel REPL PRODUCTIZATION (correctness + stability + usability)**; see the `▶ ACTIVE NEXT EPIC =
> v2c` block. v2c's centerpiece is fail-closed resolution (the kallsyms map silently mislabels regions —
> this bit v2a2). v2b "show-buf" bulk peek is superseded by v2c U1's host-side looped `read`. The text below
> is retained as reference history only.

> **🟣 OPERATOR STEER (2026-07-01) — REPL post-epic call-proof: BATCH + SATURATION-STOP + PIVOT.**
> The 95 one-target call-proofs have matured the REPL into a precise, versatile read-only kernel
> instrument on two axes: (a) **ABI-shape coverage** (scalar / result-slot ptr / owned-buffer /
> bounded-string / substring+tokenizer / time-conversion / bitmap+cpumask all proven) and (b)
> **read-only state classes** (time bases, bitmap/cpu topology, SoC/DDR identity, napi/boot-stat).
> That diversity is real but is approaching **shape-saturation** — pure `lib/`/`kernel/time`/
> `kernel/string` helpers are a finite libc-like catalog, and the Nth same-shape variant (e.g. the
> next `kstrtoX`) adds ~0 new capability. Therefore change the selection + cadence policy:
> 1. **BATCH same-shape proofs into ONE `v1-repl` boot session.** The costly/risky step is the
>    flash + rollback, NOT the call (REPL is interactive). Prove several same-session targets per
>    boot, then a single rollback to `v2321`. Keep a per-target proof record; just amortize the
>    flash. This raises throughput and CUTS boot-partition flash cycles.
> 2. **SATURATION-STOP per ABI shape.** Once a shape has a representative proof, STOP enumerating
>    more of that shape (anti-churn applies — same-shape breadth is low-information plumbing).
> 3. **PIVOT selection to UNPROVEN capability:** (a) ABI shapes not yet covered — **struct-pointer
>    arg / struct return** marshalling; (b) read-only **kernel-STATE observation** queries
>    (identity/status/`show`-style) that extend the REPL as a measurement instrument AND feed the
>    server-distro **D-harden** surface-measurement need (which built-in paths to measure / later
>    hard-disable). See `docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md` §6 E.3.
> 4. **KEYSTONE-FIRST + RETIRE-SUBSUMED (2026-07-01 follow-on — this is the map-convergence lever).**
>    Prove the **VFS-read keystone** (`filp_open` + `kernel_read`) *first*; it composes into "read any
>    kernel-visible file live" (`/proc/*`, `/sys/*`, `config.gz`, cmdline). Then **RETIRE — do NOT
>    enumerate — any state-getter whose value is readable via a `/proc`/`/sys` node** (e.g. don't
>    prove `get_max_files` when `/proc/sys/fs/file-max` is readable). Reserve *individual* call-proofs
>    for functions with **no file-node equivalent** or a **genuinely new ABI shape**. Rationale: this
>    shrinks the map that must be built (fewer required entries) instead of proving redundant getters —
>    the useful observation map converges much faster. Composition speeds the map only two ways
>    (same-shape harness reuse + this subsumption); it does NOT make a *new* shape (struct in/out) or
>    the classifier/live-fault analysis cheaper, so spend freed effort only on genuinely new
>    shapes/surfaces. As proven primitives accumulate, prefer assembling **observation bundles**
>    (kernel-vitals, procfs/sysfs reader, SoC-fingerprint, hardening-posture) over lone-function breadth.
> 5. **RESIDENT-SESSION MODE (2026-07-01 follow-on — the flash-cost lever the timing data exposed).**
>    Measured bottleneck is the **boot-partition flash write (~130s/iteration = candidate flash +
>    rollback flash, ~78%), NOT boot (~9-16s) and NOT the calls.** The current harness reflashes
>    v1-repl AND rolls back to v2321 *every unit* = 2 flashes/unit. Restructure to a resident session:
>    **flash v1-repl ONCE → [warm-reboot the resident v1-repl (NO reflash, ~15s) → run one bounded
>    batch → flush each target's result to disk immediately] × N → roll back to v2321 ONCE at session
>    end.** Flash count drops 2N→2. The **warm reboot between batches is MANDATORY** — it resets kernel
>    RAM state so leaked/cumulative allocations (kstrdup/kmemdup etc.) can't accumulate ACROSS batches;
>    a pure no-reboot mega-session (feeding batch after batch to the *same* running kernel) is
>    **FORBIDDEN** (unbounded cumulative-state regime, never validated). Keep per-batch health-check,
>    per-call result flush (so a mid-batch fault loses only the in-flight target + un-run remainder,
>    never completed results, and the faulting call stays attributable/fenceable), and a bounded batch
>    size (~10-30; flash-amortization is steeply diminishing past ~10, risk grows with size). This
>    stays inside the recoverable envelope: v2321 is always available, v1-repl reboots clean, and a
>    batch crash → warm reboot → still-recoverable. The only relaxed convention is "rollback to v2321
>    after every unit" → "rollback at session end"; optionally keep a mid-session v2321 checkpoint every
>    M batches. Re-measure with the run-timing aggregator to confirm the win (expect ~8x+ vs the ~3.5x
>    from in-boot batching alone, since intermediate flashes vanish).
>    Tooling status: `workspace/public/src/scripts/analysis/analyze_repl_run_timing.py` now models this
>    resident-session projection from canonical `events` timelines. With current private evidence
>    (10/52 canonical timelines, `batch_size=10`, `resident_batches=10`, `warm_reboot=15s`) it reports
>    flash count `20→2`, old in-boot batch `28.7s/target`, resident session `15.3s/target`, `18.8x`
>    versus per-unit flash, and `1.9x` versus per-unit in-boot batch. The current mean is conservatively
>    dragged by the intentionally heavy `kernel-vitals` live session (`449.8s`); smaller call-proof
>    batches should move the projection toward the expected `~8x+` practical regime.
>
>    **Implementation status (2026-07-01):** resident-session tooling is now in-tree as
>    `workspace/public/src/scripts/revalidation/a90_repl_resident_session.py`, with
>    per-target flush support added to `a90_repl.py run_call_proof_batch`. The harness uses the
>    checked flash helper only, writes canonical top-level `events` timelines, warm-reboots before
>    each batch, rejects no-reboot `[busy]` warm-reboot paths, and has recovery-direct rollback
>    fallback if native `recovery` disconnects after successfully entering recovery. Host validation
>    passed, and the timing aggregator projects flash `20→2`; after the `sched_clock_cpu` live proof
>    it uses `17` canonical timelines and reports resident-session `13.160s/target`, `20.79x` vs
>    per-unit flash and `2.08x` vs per-unit in-boot batching for `batch_size=10`,
>    `resident_batches=10`. The first promoted target under the harness is now `sched_clock_cpu`:
>    v1-repl flash once, mandatory warm reboot, one bounded batch, per-target flush, and v2321
>    rollback once all passed. Final resident was rolled back to v2321 with `selftest fail=0`.
>    The next target, `get_iowait_load`, extended this path to an owned dual-result-slot ABI and
>    updated the aggregate to `18` canonical timelines out of `66`; projection is now
>    resident-session `13.085s/target`, `21.06x` vs per-unit flash and `2.11x` vs per-unit
>    in-boot batching for the same `batch_size=10`, `resident_batches=10` model. The next target,
>    `thread_group_cputime_adjusted`, extended the same resident-session path to a borrowed
>    `init_task` plus owned dual-`u64` result-slot ABI; the aggregate now uses `19` canonical
>    timelines out of `67` and projects resident-session `13.004s/target`, `21.22x` vs per-unit
>    flash and `2.12x` vs per-unit in-boot batching. The next target,
>    `task_cputime_adjusted`, proved the sibling borrowed-`init_task` plus owned dual-slot ABI where
>    the body performs pinned pre-call `init_task` field reads; the aggregate now uses `20`
>    canonical timelines out of `68` and projects resident-session `12.945s/target`, `21.46x` vs
>    per-unit flash and `2.15x` vs per-unit in-boot batching. The next target, `task_curr`,
>    proved a borrowed-`init_task` leaf boolean current-state reader with a pinned pre-call
>    `task->cpu` field read; the aggregate now uses `21` canonical timelines out of `69` and
>    projects resident-session `12.852s/target`, `21.49x` vs per-unit flash and `2.15x` vs
>    per-unit in-boot batching.
>    The next scalar state target, `get_state_synchronize_sched`, proved a file-node-free
>    RCU-sched state reader with `exact-leaf-export+word-boundary` identity despite zero direct
>    BL xrefs; after the boot-config and SoC-fingerprint VFS bundles, the aggregate now uses
>    `24` canonical timelines out of `72` and projects resident-session `14.5s/target`,
>    `20.9x` vs per-unit flash and `2.1x` vs per-unit in-boot batching.
>    Harness report:
>    `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_RESIDENT_SESSION_HARNESS_2026-07-01.md`.
> 5b. **CORRECTION (2026-07-02 operator, from measured adoption) — PACK THE SESSION; the projection is
>     NOT the measurement.** Adoption check across the private evidence: **30 of 36 resident-session
>     targets ran as `target_count=1, batch_count=1`** single-target sessions; measured **flashes/target
>     = 1.36** (vs the 2.0 per-unit baseline) = only **~1.47x** actual flash reduction — NOT the `~21x`
>     figures quoted above, which are a `batch_size=10, resident_batches=10` MODEL projection, not
>     achieved. A **1-target resident session is STRICTLY WORSE than a plain per-unit flash** (it pays
>     the 2 flashes AND adds a warm reboot for ZERO amortization). Therefore: (a) **do NOT run 1-target
>     (or tiny) resident sessions** — accumulate a queue of eligible proven-safe candidate targets and
>     fill each session toward `max_batch_size` (aim for several batches of ~10-30 per session) so
>     flash-once actually amortizes; if fewer than ~8 targets are queued, keep accumulating rather than
>     spending a flash pair on one. (b) In reports, quote the **MEASURED flashes/target and per-target
>     wall time from the actual session sizes**, and label the `batch_size×resident_batches` numbers
>     explicitly as PROJECTION until real packed sessions match them. The win is real but only
>     materializes when sessions are packed; running the new harness on the old one-target cadence
>     realizes none of it.
>     **Implementation correction landed (2026-07-02):** `a90_repl_resident_session.py` now rejects
>     resident plans with fewer than 2 total targets before any device action. The first promoted
>     packed correction run batched `pid_task` + `find_pid_ns` in one resident session, completing
>     `2/2` targets with `2` flashes (`1.0` flash/target actual) and rolling back to v2321 cleanly.
>     Follow-up correction (2026-07-02): the host REPL result channel now uses `dmesg -c` for both
>     pre-write drain and post-write read, with optional kmsg markers kept off by default after a
>     marker-enabled candidate selftest failed before any batch target ran. The repaired path then
>     completed a real `max_batch_size=30` packed resident session:
>     `workspace/private/runs/kernel/repl-resident-session-dmesg-clear-max30-batch-20260701T183207Z/`,
>     `30/30` targets PASS, `2` flashes total (`0.0667` flash/target actual), measured
>     `437.139s` total (`14.57s/target`), and v2321 rollback clean. This is the first measured
>     max30 run that matches the resident-session projection rather than the old one-target cadence.
>     Additional packed refresh (2026-07-02): a ten-target state/time/memory refresh batch ran under
>     the same `dmesg -c` path:
>     `workspace/private/runs/kernel/repl-resident-session-state-refresh-batch-20260701T184431Z/`,
>     `10/10` targets PASS, `2` flashes total (`0.2` flash/target actual), measured `307.035s`
>     total (`30.70s/target`), and v2321 rollback clean. This was deliberately not a one-target
>     resident session; it confirms the corrected packed cadence while also showing why future
>     live sessions should keep filling toward `max_batch_size=30` when safe targets are queued.
>     Additional packed ABI-family proof (2026-07-02): a 16-target bitmap/cpumask/bit-scan batch
>     proved owned-buffer ABI forms under the repaired path:
>     `workspace/private/runs/kernel/repl-resident-session-bitmap-cpumask-idempotent-poke-batch-20260701T190243Z/`.
>     All `16/16` targets flushed PASS. During the preceding attempt, owned-buffer setup found a
>     host-side reliability gap: `_poke_bytes()` used generic non-replayable `op=2` despite writing
>     deterministic same-value words into proof-owned scratch buffers. Codex added a narrow
>     `poke_runtime_idempotent()` path for `_poke_bytes()` only; arbitrary `poke_runtime()` remains
>     non-replayable. The second attempt proved the batch and rollback flash completed; the pre-fix
>     harness missed `rollback_boot_ready` because rollback `selftest` body fragmented, but a bridge
>     restart plus independent `version/status/selftest` confirmed clean v2321 (`selftest fail=0`).
>     Therefore promote the 16 target-specific proofs and host reliability fixes, but do not count
>     that run as a canonical timing sample.
> **HARD — unchanged, do NOT loosen:** the fail-closed C1 resolution, the **call-safety classifier**
> (DENY / BEHAVIOR-CHANGING tiers stay DENY — never relax a tier to reach a struct/state target),
> the rollback-gate, the recoverable envelope, and "fails-twice → stop" all stay ON. If a candidate
> needs a behavior-changing call to be provable, it is OUT, not a reason to weaken the gate.

## ✅ DONE — REPL packed resident-session PID borrowed-pointer batch — `pid_task` + `find_pid_ns`

> ### ✅ STATUS (2026-07-02 live-proven, packed resident-session mode, rolled back cleanly)
>
> Codex promoted a two-target PID borrowed-pointer batch under the corrected resident-session
> cadence. This is the first promoted run after the operator correction banning one-target resident
> sessions: the harness now refuses single-target resident plans host-side, before any flash.
>
> `pid_task` proves the owned `find_get_pid(1)` PID anchor + scalar `PIDTYPE_PID` -> borrowed
> `task_struct *` path. Static identity: link `0xffffff80080d807c`, export-recovery verified,
> source declaration `extern struct task_struct * pid_task(struct pid *pid, enum pid_type)` at
> `include/linux/pid.h:91`, exact body words, leaf/no in-body BL, next symbol
> `find_task_by_pid_ns` at `+0x30`. Generic gate stays `DENY`; target-specific advisory also
> stays `DENY` because the bounded enum x1 participates in memory-base flow.
>
> `find_pid_ns` proves scalar PID `1` + namespace pointer observed from the owned PID anchor ->
> borrowed `struct pid *` path. Static identity: link `0xffffff80080d7d4c`,
> export-recovery verified, source declaration
> `extern struct pid * find_pid_ns(int nr, struct pid_namespace *ns)` at
> `include/linux/pid.h:118`, exact body words, leaf/no in-body BL, next symbol `find_vpid`
> at `+0x90`. Generic gate stays `DENY`; target-specific advisory is `SAFE-WITH-VALID-PTR`
> because memory flow is attributed to the proof-supplied x1 namespace pointer.
>
> Live packed resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-pid-borrowed-batch-20260701T174344Z/`.
> Result: session `a90-repl-resident-session-pass`, completed targets `2/2`, flash count `2`,
> actual flash amortization `1.0 flash/target`, canonical timeline errors `[]`.
>
> Target results: `pid_task` returned a task whose `task->thread_pid` matched the owned PID 1
> anchor; `find_pid_ns(1, observed_ns)` returned the same PID 1 anchor. Both observed embedded pid
> number `0x1`, both preserved the pid refcount across the borrowed lookup (`6 -> 6`), and both
> restored the anchor with `put_pid` (`-> 5`). Raw runtime pointers and KASLR slide stayed private.
>
> Final rollback health independently confirmed resident `v2321-usb-clean-identity-rodata`,
> `status` BOOT OK, and `selftest pass=11 warn=1 fail=0`. Timing aggregate after this run uses
> `31/79` canonical timelines and projects resident-session `13.749s/target`, `21.50x` vs
> per-unit flash and `2.15x` vs per-unit in-boot batching for the modeled `batch_size=10`,
> `resident_batches=10`; the measured run itself was `2` targets, `2` flashes, `271.358s` total.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_PID_BORROWED_BATCH_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL packed resident-session task lookup proofs + max30 result-channel repair

> ### ✅ STATUS (2026-07-02 live-proven per-target and max30 packed-session pass, rolled back cleanly)
>
> Codex extended the PID borrowed-pointer proof family to task lookup helpers:
> `find_task_by_pid_ns` and `find_task_by_vpid`. Both stay global `DENY` and are only trusted
> through a target-specific proof that first obtains an owned `find_get_pid(1)` anchor, verifies
> the returned borrowed task's `task->thread_pid` against that anchor, confirms the pid refcount
> is unchanged by the borrowed lookup, and balances the owned anchor with `put_pid`.
>
> Static identity for `find_task_by_pid_ns`: link `0xffffff80080d80ac`, source declaration
> `extern struct task_struct * find_task_by_pid_ns(pid_t nr, struct pid_namespace *ns)` at
> `include/linux/sched.h:1785`, exact body words, leaf/no in-body BL, next symbol
> `find_task_by_vpid` at `+0xa0`, direct BL xrefs >= 5. Generic C1 export verification remains
> unavailable, so this is a proof-specific map-entry + exact-words + live-cross-check promotion,
> not a global auto-call promotion.
>
> Static identity for `find_task_by_vpid`: link `0xffffff80080d814c`, source declaration
> `extern struct task_struct * find_task_by_vpid(pid_t nr)` at `include/linux/sched.h:1784`,
> exact body words, leaf/no in-body BL, next symbol `get_task_pid` at `+0xb8`, direct BL xrefs
> >= 49, scalar-flow classifier evidence. Generic gate stays `DENY`.
>
> Two packed resident sessions were run; no one-target resident session was used. First run:
> `workspace/private/runs/kernel/repl-resident-session-task-lookup-packed-batch-20260701T180337Z/`,
> `target_count=13`, `max_batch_size=30`. Flushed PASS targets before the later exception were
> `find_task_by_pid_ns`, `find_task_by_vpid`, `pid_task`, and `find_pid_ns`. The run then failed
> on an older canary: `find_vpid changed pid refcount: anchor=6 after=9`. Rollback-finally
> returned to clean v2321.
>
> Second run after adding a host-side `dmesg` pre-drain:
> `workspace/private/runs/kernel/repl-resident-session-task-lookup-preflush-max30-batch-20260701T181136Z/`,
> `target_count=30`, `max_batch_size=30`. Flushed PASS targets before the later exception were
> `find_task_by_pid_ns`, `find_task_by_vpid`, and `pid_task`. The run then failed on the same
> older PID borrowed-pointer family: `put_pid did not restore anchor pid refcount:
> anchor=6 after_find_pid_ns=6 after_put=8`. Rollback-finally returned to clean v2321.
>
> New target evidence from both packed sessions: `find_task_by_pid_ns` and `find_task_by_vpid`
> each returned a sane task pointer whose `task->thread_pid` matched the owned PID 1 anchor,
> observed embedded pid number `0x1`, preserved the pid refcount across the borrowed lookup
> (`6 -> 6`), and restored the anchor with `put_pid` (`-> 5`). Raw runtime pointers and KASLR
> slide stayed private.
>
> Decision: promote only the two target-specific function-map entries. Do **not** promote either
> packed session as a batch-pass. The packed resident harness preserved per-target flush evidence,
> but the legacy PID borrowed canary refcount/result path is unstable in packed mode; per the
> fails-twice rule, no third live retry was made. Next live unit before another max30 batch:
> harden the A90R result channel / canary accounting, e.g. unique per-op marker or stronger
> `dmesg -c` isolation.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_TASK_LOOKUP_PACKED_RESIDENT_SESSION_2026-07-02.md`.
>
> Follow-up result-channel repair: Codex first tried an opt-in kmsg marker window. The live kernel
> accepts markers only in `6,0,0,-;message` format, but a marker-enabled candidate selftest captured
> marker records without `A90R`, so that attempt ran no batch targets, rolled back cleanly, and was
> not promoted. The default REPL op path was then changed to use `dmesg -c` read-and-clear windows
> without markers.
>
> The repaired default path completed a real max30 packed resident session:
> `workspace/private/runs/kernel/repl-resident-session-dmesg-clear-max30-batch-20260701T183207Z/`.
> Result: `a90-repl-resident-session-pass`, `30/30` targets, `1/1` batch, flash count `2`,
> actual flash amortization `0.0667 flash/target`, timeline errors `[]`, rollback clean. The run
> crossed the previous failure points: `find_vpid`, `find_pid_ns`, and all 30 targets passed.
> Measured total was `437.139s` (`14.57s/target`), close to the resident-session timing model.
>
> Follow-up report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_DMESG_CLEAR_MAX30_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL dmesg-clear packed state/time/memory refresh batch

> ### ✅ STATUS (2026-07-02 live-proven, packed resident-session mode, rolled back cleanly)
>
> Codex refreshed ten already handler-backed state/time/memory targets under the repaired
> `dmesg -c` result channel and the corrected packed resident-session cadence. No one-target
> resident session was used. The queued targets were:
> `can_do_mlock`, `get_avenrun`, `get_ddr_revision_id_1`, `get_ddr_revision_id_2`,
> `is_current_pgrp_orphaned`, `ktime_get_real_seconds`, `ktime_get_seconds`,
> `ktime_get_ts64`, `total_swapcache_pages`, and `vm_commit_limit`.
>
> Static gate: `SAFE-SCALAR=8`, `SAFE-WITH-VALID-PTR=2`, with owned result slots for the
> two pointer-output targets. Dry-run used `target_count=10`, `max_batch_size=30`, existing
> v1-repl candidate SHA
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`, and v2321 rollback
> SHA `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
>
> Live packed resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-state-refresh-batch-20260701T184431Z/`.
> Result: `a90-repl-resident-session-pass`, completed targets `10/10`, completed batches
> `1/1`, flash count `2`, actual flash amortization `0.2 flash/target`, timeline errors `[]`,
> warm reboot before batch, and rollback flashed once at session end.
>
> Target outcomes: all ten targets passed their repeat/read-only contracts. The scalar getters
> returned bool, sane bounded page-count, DDR-revision, or nondecreasing time values in contract.
> `get_avenrun` and `ktime_get_ts64` wrote owned result slots with canaries intact. Raw runtime
> pointers, KASLR slide, and private payloads stayed private.
>
> Timing: canonical timeline had the required event schema. Candidate flash `53.074s`, candidate
> boot/health `42.970s`, warm reboot `19.893s`, live batch `44.934s`, rollback flash `64.213s`,
> rollback boot/health `48.219s`, candidate-start to rollback-ready total `307.035s`
> (`30.70s/target`). Aggregate now uses `35/84` canonical timelines and projects resident-session
> `14.0s/target`, `21.3x` vs per-unit flash and `2.1x` vs per-unit in-boot batching for the modeled
> `batch_size=10`, `resident_batches=10`; this run's measured per-target cost is higher than max30
> because the real queued batch had ten targets.
>
> Final rollback health independently confirmed resident `v2321-usb-clean-identity-rodata`,
> `status` BOOT OK, and `selftest pass=11 warn=1 fail=0`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_STATE_REFRESH_PACKED_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL bitmap/cpumask owned-buffer packed resident-session batch

> ### ✅ STATUS (2026-07-02 live-proven target batch, rollback independently verified clean)
>
> Codex promoted a 16-target bitmap/cpumask/bit-scan packed batch. This is not a `/proc` or
> `/sys` getter batch; it proves owned-buffer ABI forms for the function map:
> `__bitmap_weight`, `__bitmap_complement`, `__bitmap_andnot`, `__bitmap_or`, `__bitmap_set`,
> `__bitmap_clear`, `__bitmap_subset`, `bitmap_alloc`, `bitmap_zalloc`, `find_next_bit`,
> `find_last_bit`, `find_next_zero_bit`, `cpumask_next`, `cpumask_next_wrap`,
> `cpumask_next_and`, and `cpumask_any_but`.
>
> Static gate: `SAFE-SCALAR=2`, `SAFE-WITH-VALID-PTR=14`. Dry-run used `target_count=16`,
> `max_batch_size=30`, existing v1-repl candidate SHA
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`, and v2321 rollback
> SHA `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
>
> First live attempt:
> `workspace/private/runs/kernel/repl-resident-session-bitmap-cpumask-packed-batch-20260701T185601Z/`.
> `__bitmap_weight` flushed PASS, then `__bitmap_complement` stopped before its target call on a
> transient `op=2` result-capture loss while `_poke_bytes()` was filling an owned scratch buffer.
> Rollback-finally returned clean v2321.
>
> Host fix: `_poke_bytes()` now uses `poke_runtime_idempotent()` for deterministic same-value writes
> into proof-owned kmalloc buffers; generic `poke_runtime()` remains non-replayable. Resident health
> checks now retry validation failures such as fragmented `selftest` bodies after a bridge restart.
>
> Second live attempt:
> `workspace/private/runs/kernel/repl-resident-session-bitmap-cpumask-idempotent-poke-batch-20260701T190243Z/`.
> Batch result was `a90-repl-resident-session-batch-pass`, `16/16` targets flushed PASS, all raw
> runtime values private. Rollback flash completed. The pre-fix harness exited nonzero before writing
> `rollback_boot_ready` because rollback `selftest` returned `rc=0 status=ok` with a fragmented body;
> independent bridge restart plus `version/status/selftest` confirmed resident
> `v2321-usb-clean-identity-rodata`, BOOT OK, and `selftest pass=11 warn=1 fail=0`.
>
> Timing for the second attempt until rollback flash done: candidate flash `63.147s`, candidate
> boot/health `43.188s`, warm reboot `33.230s`, batch REPL selftest `32.222s`, live batch
> `465.868s`, rollback flash `65.270s`, candidate-start to rollback-flash-done `704.820s`.
> Because the timeline is missing `rollback_boot_ready`, it is not counted as a canonical timing
> sample. Aggregate after this unit parses `36/86` canonical timelines.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_BITMAP_CPUMASK_PACKED_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL resident-session scalar pid lookup proof — `find_vpid`

> ### ✅ STATUS (2026-07-02 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `find_vpid(1)` as a target-specific scalar PID lookup -> borrowed `struct pid *`
> proof. It composes with the already proven `find_get_pid(1)` owned-ref proof: first obtain an
> owned PID 1 anchor, then prove `find_vpid(1)` returns the same pid pointer without changing the
> observed refcount. This is not a `/proc` or `/sys` getter replacement; it proves a borrowed
> scalar lookup ABI and its refcount behavior.
>
> Static identity is pinned by export recovery and exact body checks: `find_vpid`
> link `0xffffff80080d7ddc`, one export candidate, map/export agreement, JOPP entry,
> direct BL xrefs `14`, leaf/no in-body BL, no pre-call pointer deref, next symbol
> `task_active_pid_ns` at `+0xa8`, source declaration
> `extern struct pid * find_vpid(int nr)` at `include/linux/pid.h:119`, and exact pinned words.
> The anchor `find_get_pid` remains separately pinned at `0xffffff80080d82ec`; cleanup `put_pid`
> remains separately verified at `0xffffff80080d753c`, next symbol `free_pid` at `+0x70`.
>
> The generic gate stays closed: `find_vpid` is an explicit DENY seed with
> `auto_call_allowed=false`, while the target-specific advisory is `SAFE-SCALAR` because the
> function is scalar-only and leaf. `find_get_pid` and `put_pid` remain generic `DENY`; they are
> used only as anchor/cleanup inside the bounded proof.
>
> Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-find-vpid-20260701T171834Z/`.
> Result: `a90-repl-live-call-proof-find_vpid-pass`; `find_get_pid(1)` established an owned PID 1
> anchor, `find_vpid(1)` returned the same pid pointer, embedded pid number was `0x1`, refcount
> moved `6 -> 6 -> 5`, and the single anchor `put_pid` cleanup was attempted and OK. Raw runtime
> pointers and KASLR slide stayed private-only.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Harness summary was `a90-repl-resident-session-pass`, flash count `2`,
> completed targets `1/1`, timeline errors `[]`. Final rollback health independently confirmed
> `v2321-usb-clean-identity-rodata` and `selftest pass=11 warn=1 fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required phase events. This run measured candidate flash `65.037s`, candidate boot/health
> `42.969s`, warm reboot `33.309s`, live target batch `6.831s`, rollback flash `65.917s`, and total
> candidate-start to rollback-ready `303.855s`. The timing aggregator now parses `29/77` canonical
> timelines and projects resident-session `13.898s/target`, `21.35x` vs per-unit flash and `2.13x`
> vs per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_FIND_VPID_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL resident-session scalar pid lookup proof — `find_get_pid`

> ### ✅ STATUS (2026-07-02 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `find_get_pid(1)` as a target-specific scalar PID lookup -> owned `struct pid *`
> ref proof. This is not a `/proc` or `/sys` getter replacement: it proves a scalar lookup ABI plus
> mandatory `put_pid()` cleanup, while keeping the global call gate closed.
>
> Static identity is pinned by export recovery and exact body checks: `find_get_pid`
> link `0xffffff80080d82ec`, one export candidate, map/export agreement, JOPP entry,
> direct BL xrefs `19`, in-body callees `__rcu_read_lock` and `__rcu_read_unlock`,
> no pre-call pointer deref, next symbol `pid_nr_ns` at `+0xe8`, source declaration
> `extern struct pid * find_get_pid(int nr)` at `include/linux/pid.h:124`, and exact pinned words.
> Cleanup `put_pid` is separately verified at `0xffffff80080d753c`, next symbol `free_pid`
> at `+0x70`, declaration `extern void put_pid(struct pid *pid)` at `include/linux/pid.h:90`.
>
> The generic gate stays closed: `find_get_pid` is an explicit DENY seed with
> `auto_call_allowed=false`, and target-specific advisory remains `CONTEXT-SENSITIVE`
> due to the RCU call pair. `put_pid` remains generic `DENY`; it is only used as cleanup for
> returned pid refs.
>
> Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-find-get-pid-pid1-20260701T170346Z/`.
> Result: `a90-repl-live-call-proof-find_get_pid-pass`; `find_get_pid(1)` returned the same pid
> pointer twice, embedded pid number was `0x1`, refcount moved `6 -> 7 -> 6 -> 5`, and two
> `put_pid` cleanups were attempted and OK. Raw runtime pointers and KASLR slide stayed
> private-only.
>
> The first attempt
> `workspace/private/runs/kernel/repl-resident-session-find-get-pid-20260701T165432Z/`
> failed the host contract because `find_get_pid(0)` returned `0x0`. That is now classified as a
> host/operator contract error: `init_task->thread_pid` has PID number 0, but PID 0 is not a useful
> hash lookup proof target. The harness rolled back cleanly before the corrected PID 1 run.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Harness summary was `a90-repl-resident-session-pass`, flash count `2`,
> completed targets `1/1`, timeline errors `[]`. Final rollback health confirmed
> `v2321-usb-clean-identity-rodata` and `selftest pass=11 warn=1 fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required phase events. This run measured candidate flash `64.312s`, candidate boot/health
> `54.987s`, warm reboot `32.671s`, live target batch `7.952s`, rollback flash `63.906s`, and total
> candidate-start to rollback-ready `258.466s`. The timing aggregator now parses `28/76` canonical
> timelines and projects resident-session `13.970s/target`, `21.22x` vs per-unit flash and `2.12x`
> vs per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_FIND_GET_PID_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL resident-session balanced pid ref proof — `get_task_pid`

> ### ✅ STATUS (2026-07-02 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `get_task_pid(init_task, PIDTYPE_PID)` as a target-specific balanced refcount
> primitive. This is not a `/proc` or `/sys` getter replacement: it proves the borrowed
> `task_struct*` + scalar enum -> owned `struct pid*` ref shape, with mandatory `put_pid()` cleanup.
>
> Static identity is pinned by export recovery and exact body checks: `get_task_pid`
> link `0xffffff80080d8204`, one export candidate, map/export agreement, JOPP entry,
> direct BL xrefs `5`, in-body callees `__rcu_read_lock` and `__rcu_read_unlock`,
> no pre-call pointer deref, next symbol `get_pid_task` at `+0x68`, source declaration
> `extern struct pid * get_task_pid(struct task_struct *task, enum pid_type type)` at
> `include/linux/pid.h:94`, and exact pinned words. Cleanup `put_pid` is separately
> verified at `0xffffff80080d753c`, next symbol `free_pid` at `+0x70`, declaration
> `extern void put_pid(struct pid *pid)` at `include/linux/pid.h:90`.
>
> The generic gate stays closed: `get_task_pid` is an explicit DENY seed with
> `auto_call_allowed=false`, and target-specific advisory remains `CONTEXT-SENSITIVE`
> due to the RCU call pair. `put_pid` also remains generic `DENY`; it is only used as
> cleanup for the exact returned pid ref.
>
> Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-get-task-pid-retry-20260701T163708Z/`.
> Result: `a90-repl-live-call-proof-get_task_pid-pass`; direct PID number observation was `0x0`;
> return matched the direct `init_task->thread_pid`; refcount moved `1 -> 2 -> 1`; cleanup was
> attempted and OK. Raw runtime pointers and KASLR slide stayed private-only.
>
> The first attempt
> `workspace/private/runs/kernel/repl-resident-session-get-task-pid-20260701T163156Z/`
> failed before the target call because the host contract incorrectly required the static init PID
> object to be lowmem. The harness rolled back cleanly; the corrected retry requires only a sane
> nonzero kernel pointer while keeping return equality and refcount restoration mandatory.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Harness summary was `a90-repl-resident-session-pass`, flash count `2`,
> completed targets `1/1`, timeline errors `[]`. Final rollback health confirmed
> `v2321-usb-clean-identity-rodata` and `selftest pass=11 warn=1 fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required phase events. This run measured candidate flash `64.133s`, candidate boot/health
> `54.279s`, warm reboot `32.664s`, live target batch `7.361s`, rollback flash `64.782s`, and total
> candidate-start to rollback-ready `257.608s`. The timing aggregator now parses `26/74` canonical
> timelines and projects resident-session `14.203s/target`, `21.07x` vs per-unit flash and `2.11x`
> vs per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_GET_TASK_PID_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL resident-session one-target proof — `get_state_synchronize_sched`

> ### ✅ STATUS (2026-07-02 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `get_state_synchronize_sched()` as a no-argument RCU-sched state reader. This target
> has no `/proc` or `/sys` file-node equivalent and is not the behavior-changing
> `cond_synchronize_sched()` path.
>
> Static identity is pinned by a target-specific `exact-leaf-export+word-boundary` gate:
> link `0xffffff8008150bfc`, one export candidate, map/export agreement, JOPP entry, direct BL xrefs
> `0`, no in-body BL, no pre-call pointer deref, next symbol `cond_synchronize_sched` at `+0x20`,
> source declaration `unsigned long get_state_synchronize_sched(void)` at `include/linux/rcutree.h:79`,
> and exact words
> `f0015788 d5033bbf 91040108 910c2108 c8dffd00 d65f03c0 d503201f 00be7bad`.
>
> Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-get-state-synchronize-sched-20260701T161101Z/`.
> Result: `a90-repl-live-call-proof-get_state_synchronize_sched-pass`; three no-argument calls
> returned nondecreasing RCU-sched state values with max delta `0xe`, inside the proof bound.
> Raw runtime pointers and KASLR slide stayed private-only.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Harness summary was `a90-repl-resident-session-pass`, flash count `2`,
> completed targets `1/1`, timeline errors `[]`. Final independent health confirmed
> `v2321-usb-clean-identity-rodata` and standalone `selftest pass=11 warn=1 fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required phase events. This run measured candidate flash `63.240s`, candidate boot/health
> `43.831s`, warm reboot `33.233s`, live target batch `3.632s`, rollback flash `64.805s`, and total
> candidate-start to rollback-ready `243.131s`. The timing aggregator now parses `24/72` canonical
> timelines and projects resident-session `14.5s/target`, `20.9x` vs per-unit flash and `2.1x` vs
> per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_GET_STATE_SYNCHRONIZE_SCHED_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL VFS-read boot-config observation bundle promoted

> ### ✅ STATUS (2026-07-02 live-proven, resident-session mode, rolled back to v2321)
>
> Codex promoted `a90_repl.py vfs-bundle boot-config`, a named VFS-read observation bundle for
> boot command-line and kernel config provenance exposed through procfs. The bundle reads
> `/proc/cmdline` and `/proc/config.gz` with the existing live-proven
> `filp_open + kernel_read + filp_close` primitive, owned pathname/read/`loff_t` buffers, and
> per-path `kfree` cleanup.
>
> Raw `/proc/cmdline` contents, kernel-config bytes, runtime pointers, and KASLR slide stay
> private-only. Public evidence records only path names, observed byte counts, broad text/binary
> classification, cleanup checks, and pass/fail state.
>
> Host validation passed: `py_compile`, focused VFS bundle tests including
> `test_vfs_read_boot_config_bundle_uses_named_contract`, `tests.test_a90_repl_resident_session`,
> and resident-session dry-run with `--batch vfs-bundle:boot-config`.
>
> Live run:
> `workspace/private/runs/kernel/repl-resident-session-boot-config-20260701T154854Z/`.
> Result: `a90-repl-vfs-read-boot-config-bundle-pass`; 2/2 procfs paths opened, read, closed,
> and cleaned up successfully. `/proc/cmdline` returned 512 bytes classified as proc-style text;
> `/proc/config.gz` returned 512 bytes classified as binary with gzip prefix.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Final resident is `v2321-usb-clean-identity-rodata`; standalone
> `version/status/selftest` passed after rollback with `selftest pass=11 warn=1 fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required phase events. This run measured candidate flash `64.221s`, candidate boot/health
> `43.061s`, mandatory warm reboot `33.222s`, batch REPL selftest `32.226s`, live boot-config
> bundle `175.970s`, rollback flash `64.290s`, rollback boot/health `48.023s`, and total
> candidate-start to rollback-ready `462.352s`. The live bundle is slower than scalar call-proofs
> because `/proc/config.gz` is a compressed procfs stream; keep it an on-demand named observation
> bundle rather than routine light health.
>
> Timing aggregate now uses `23/71` canonical timelines and projects resident-session
> `14.710s/target`, `20.83x` vs per-unit flash, and `2.08x` vs per-unit in-boot batching for
> `batch_size=10`, `resident_batches=10`, `warm_reboot=15s`.
>
> Map outcome: `boot-config` is now the preferred observation surface for boot-parameter and
> kernel-config provenance. Do not add individual getter proofs for equivalent state reachable
> through `/proc/cmdline` or `/proc/config.gz`; reserve individual call-proofs for functions with
> no file-node equivalent or a genuinely new ABI shape.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_VFS_READ_BOOT_CONFIG_BUNDLE_2026-07-02.md`.

## ✅ DONE — REPL VFS-read SoC-fingerprint observation bundle promoted

> ### ✅ STATUS (2026-07-02 live-proven, resident-session mode, rolled back to v2321)
>
> Codex promoted `a90_repl.py vfs-bundle soc-fingerprint`, a named VFS-read observation bundle
> for Qualcomm SoC identity and board fingerprint state exposed under `/sys/devices/soc0/*`.
> This implements KEYSTONE-FIRST / RETIRE-SUBSUMED for the `socinfo_get_*` getter family: use
> file nodes for equivalent state instead of adding more individual state-getter call-proofs.
>
> Public bundle paths are `/sys/devices/soc0/soc_id`, `family`, `machine`, `revision`,
> `vendor`, `raw_id`, `raw_version`, `build_id`, `hw_platform`, `platform_subtype`,
> `platform_subtype_id`, and `serial_number`. Raw file bytes, runtime pointers, KASLR slide,
> and serial/fingerprint values stay private-only; public evidence records path names,
> observed lengths, broad text/decimal classification, and pass/fail checks.
>
> The resident-session harness now accepts `vfs-bundle:<name>` batch items in addition to plain
> call-proof targets, preserving the same flash-once, mandatory warm-reboot-per-batch,
> per-target flush, and rollback-once model. Host validation passed: `py_compile`, focused
> VFS bundle tests, `tests.test_a90_repl_resident_session`, and resident-session dry-run with
> `--batch vfs-bundle:soc-fingerprint`.
>
> Live run:
> `workspace/private/runs/kernel/repl-resident-session-soc-fingerprint-20260701T152851Z/`.
> Result: `a90-repl-vfs-read-soc-fingerprint-bundle-pass`; 12/12 sysfs paths opened, read,
> closed, and cleaned up successfully, all returning printable text. The run used v1-repl
> flash once, mandatory warm reboot before the batch, per-target result flush, and v2321
> rollback. Rollback closed via recovery-direct fallback after a `from-native` rollback
> failure; final standalone `version/status/selftest` confirmed resident
> `v2321-usb-clean-identity-rodata` with `selftest pass=11 warn=1 fail=0`.
>
> Timing aggregate now uses `22/70` canonical timelines and projects resident-session
> `14.107s/target`, `21.21x` vs per-unit flash, and `2.12x` vs per-unit in-boot batching
> for `batch_size=10`, `resident_batches=10`, `warm_reboot=15s`. This run is intentionally
> heavier than scalar call-proofs because it reads 12 sysfs files and the rollback closure
> included a manual/fallback window.
>
> Note: while investigating the long VFS live window, the harness process received SIGINT
> after the bundle had completed. The parent process then had to be killed after
> recovery-direct rollback finished because it held the serial transaction lock during
> rollback-finally health. This was recorded as a host closure artifact; the bundle proof
> passed and the final device state is clean v2321.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_VFS_READ_SOC_FINGERPRINT_BUNDLE_2026-07-02.md`.

## ✅ DONE — REPL resident-session borrowed task leaf boolean proof — `task_curr`

> ### ✅ STATUS (2026-07-02 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `task_curr(const struct task_struct *p)` under a target-specific borrowed
> `init_task` leaf-reader contract, not as a global auto-call seed. Static identity is pinned by
> map address `0xffffff80080eb9fc`, next symbol `check_preempt_curr` at `+0x30`, direct BL xrefs
> `5`, fixed current-image body words, source signature
> `extern int task_curr(const struct task_struct *p)` at `include/linux/sched.h:1734`, pointer arg
> indices `[0]`, leaf body, no BL instructions, no context-sensitive calls, and one pinned pre-call
> borrowed field read `x0+132` (`task->cpu`).
>
> The global classifier remains fail-closed for this non-seeded target: `DENY`,
> `auto_call_allowed=false`, not seed-whitelisted. Generic resolution remains `unverified` because
> the default gate correctly rejects the pinned pre-call `x0` field read
> `map-target-precall-x0-deref:+0x0/imm=0x84/word=0xb9408408` and the leaf has no helper call
> before return. The proof records a separate target-specific `SAFE-WITH-VALID-PTR` contract only
> because the harness supplies borrowed `init_task`, accepts exactly the pinned field read, and
> validates the return as boolean `0`/`1`.
>
> Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-task-curr-20260701T151106Z/`.
> Result: `a90-repl-live-call-proof-task_curr-pass`; three repeated calls returned `0x1`, `0x1`,
> `0x1`. Raw runtime pointer, slide, and borrowed-pointer evidence stayed private; public summaries
> contain only redacted state and boolean return values.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Final resident is `v2321-usb-clean-identity-rodata`; standalone
> `version/status/selftest` passed after rollback with `selftest pass=11 warn=1 fail=0`.
> Live validation obeyed the timing rule: candidate flash `64.317s`, candidate boot/health
> `35.941s`, warm reboot `33.273s`, batch target call window `3.626s`, rollback flash `63.792s`,
> rollback boot-ready marker `1.023s`, total candidate-start to rollback-ready `243.512s`.
>
> Host validation passed: `py_compile`; focused classifier/source/fake proof tests plus
> `tests.test_a90_repl_resident_session` (`Ran 13 tests`, `OK`); host-only `call-safety-sweep`
> for `task_curr`; resident-session dry-run; run-timing aggregator; and `git diff --check`.
> Timing aggregate after this run: `21/69` canonical timelines, resident-session projection
> `20 -> 2` flashes, `12.852s/target`, `21.49x` vs per-unit flash, and `2.15x` vs per-unit
> in-boot batching.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_TASK_CURR_RESIDENT_SESSION_2026-07-02.md`.

## ✅ DONE — REPL resident-session borrowed task + pre-call field-read + owned dual-slot proof — `task_cputime_adjusted`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `task_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st)` under a
> target-specific borrowed `init_task` plus owned dual-result-slot contract, not as a global auto-call
> seed. Static identity is pinned by map/export address `0xffffff80080f7f2c`, target-specific
> `export-recovery` C1 verification with `allow_pre_arg_deref=true`, direct BL xrefs `4`, next symbol
> `cputime_adjust` at `+0x70`, source signature
> `extern void task_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st)` at
> `include/linux/sched/cputime.h:55`, pointer arg indices `[0, 1, 2]`, no context-sensitive calls,
> and fixed callees `cputime_adjust` and `__stack_chk_fail`.
>
> The global classifier remains fail-closed for this non-seeded target: `DENY`,
> `auto_call_allowed=false`, not seed-whitelisted. Generic resolution remains `unverified` because
> the default gate correctly rejects the pinned pre-call `x0` field read
> `map-target-precall-x0-deref:+0x28/imm=0x148/word=0xf940a408`. The proof records a separate
> target-specific `SAFE-WITH-VALID-PTR` contract only because the harness supplies borrowed
> `init_task`, accepts exactly the pinned `x0+328`, `x0+1936`, `x0+1944` field reads, supplies owned
> `utime`/`stime` slots, and validates canary preservation plus `kfree` cleanup.
>
> Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-task-cputime-adjusted-20260701T145629Z/`.
> Result: `a90-repl-live-call-proof-task_cputime_adjusted-pass`; two repeated calls wrote
> `utime=0x0`, `stime=0x0`, preserved the trailing canary, and freed the owned buffer via `kfree`.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Final resident is `v2321-usb-clean-identity-rodata`; standalone
> `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required eight phase events. This run measured `candidate_flash=64.240308s`,
> `warm_reboot=33.011283s`, one-target live batch `13.616407s`, `rollback_flash=64.834542s`,
> total `311.223365s`. The timing aggregator now uses `20` canonical timelines out of `68` and
> projects resident session `20->2` flashes, `12.945s/target`, `21.46x` versus unbatched per-unit
> flash, and `2.15x` versus per-unit in-boot batching for `batch_size=10`,
> `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_TASK_CPUTIME_ADJUSTED_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session borrowed task + owned dual-slot proof — `thread_group_cputime_adjusted`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `thread_group_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st)` under a
> target-specific borrowed `init_task` plus owned dual-result-slot contract, not as a global auto-call
> seed. Static identity is pinned by map address `0xffffff80080f80b4`, generic
> `disasm-signature+xref+map` C1 verification, direct BL xrefs `5`, next symbol `dequeue_task_idle`
> at `+0x88`, source signature
> `extern void thread_group_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st)` at
> `include/linux/sched/cputime.h:56`, pointer arg indices `[0, 1, 2]`, no context-sensitive calls,
> no pre-call x0 deref, and fixed callees `thread_group_cputime`, `cputime_adjust`, and
> `__stack_chk_fail`.
>
> The global classifier remains fail-closed for this non-seeded target: `DENY`,
> `auto_call_allowed=false`, not seed-whitelisted. The generic advisory sees a
> `SAFE-WITH-VALID-PTR` shape but stays `candidate_safe=false` because the unseeded pointer-flow
> contract is not globally vetted. The proof records a separate target-specific
> `SAFE-WITH-VALID-PTR` contract only because the harness supplies borrowed `init_task`, owned
> `utime`/`stime` slots, canary validation, and `kfree` cleanup.
>
> Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-thread-group-cputime-adjusted-20260701T143959Z/`.
> Result: `a90-repl-live-call-proof-thread_group_cputime_adjusted-pass`; two repeated calls wrote
> `utime=0x0`, `stime=0x0`, preserved the trailing canary, and freed the owned buffer via `kfree`.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Final resident is `v2321-usb-clean-identity-rodata`; standalone
> `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required eight phase events. This run measured `candidate_flash=64.117564s`,
> `warm_reboot=33.235699s`, one-target live batch `13.468596s`, `rollback_flash=64.823739s`,
> total `283.070021s`. The timing aggregator now uses `19` canonical timelines and projects resident
> session `20->2` flashes, `13.004s/target`, `21.22x` versus unbatched per-unit flash, and `2.12x`
> versus per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_THREAD_GROUP_CPUTIME_ADJUSTED_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session owned dual-slot proof — `get_iowait_load`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `get_iowait_load(unsigned long *nr_waiters, unsigned long *load)` under a
> target-specific owned dual-result-slot contract, not as a global auto-call seed. Static identity is
> pinned by map address `0xffffff80080ee0ec`, direct BL xref `1`, next symbol `sched_exec` at `+0x28`,
> source signature `extern void get_iowait_load(unsigned long *nr_waiters, unsigned long *load)` at
> `include/linux/sched/stat.h:23`, pointer arg indices `[0, 1]`, BL-free leaf body, and two
> caller-provided memory-base stores only: `str x9, [x0]` and `str x8, [x1]`. Body words:
> `b0013149 d538d088 91240129 8b090108 b9893909 f9000009 f9402508 f9000028 d65f03c0 00be7bad`.
>
> The global classifier remains fail-closed for this non-seeded target: `DENY`,
> `auto_call_allowed=false`, generic resolution `unverified` with
> `map-target-no-helper-call-before-return-or-scan-limit`. The proof records a separate
> target-specific advisory `SAFE-WITH-VALID-PTR` only because the harness supplies owned output slots
> and validates canary preservation plus cleanup.
>
> Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-get-iowait-load-20260701T141901Z/`.
> Result: `a90-repl-live-call-proof-get_iowait_load-pass`; two repeated calls wrote
> `nr_waiters=0x0`, `load=0x100000`, preserved the trailing canary, and freed the owned buffer via
> `kfree`.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Final resident is `v2321-usb-clean-identity-rodata`; standalone
> `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required eight phase events. This run measured `candidate_flash=64.163958s`,
> `warm_reboot=32.635658s`, one-target live batch `13.821801s`, `rollback_flash=65.799174s`,
> total `309.495289s`. The timing aggregator now uses `18` canonical timelines and projects resident
> session `20->2` flashes, `13.085s/target`, `21.06x` versus unbatched per-unit flash, and `2.11x`
> versus per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_GET_IOWAIT_LOAD_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session one-target proof — `sched_clock_cpu`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `sched_clock_cpu(int cpu)` under a target-specific scalar CPU0 read contract,
> not as a global auto-call seed. Static identity is pinned by `disasm-signature+xref+map`:
> link `0xffffff80080f72d4`, direct BL xrefs `16`, next symbol `running_clock` at `+0x40`,
> one internal BL to `sched_clock`, source signature `extern u64 sched_clock_cpu(int cpu)` at
> `include/linux/sched/clock.h:21`, and body words
> `ca1103d0 a9bf43fd 910003fd d0015908 b94fc908 340000a8 9401de62 a8c143fd ca11021e d65f03c0 aa1f03e0 a8c143fd ca11021e d65f03c0 d503201f 00be7bad`.
>
> The global classifier remains fail-closed for this non-seeded target: `DENY`,
> `auto_call_allowed=false`. The proof records a separate target-specific advisory
> `SAFE-SCALAR` and calls only `cpu=0`. Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-sched-clock-cpu-20260701T135937Z/`.
> Result: `a90-repl-live-call-proof-sched_clock_cpu-pass`; three repeated calls returned
> nonzero, nondecreasing values starting at `0xa115db8ff`, max short-run delta `0x24ee361f`,
> below the `10,000,000,000ns` proof bound.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result
> flush, and v2321 rollback once. Final resident is `v2321-usb-clean-identity-rodata`; standalone
> `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required eight phase events. This run measured `candidate_flash=65.090659s`,
> `warm_reboot=32.650446s`, one-target live batch `3.575183s`,
> `rollback_flash=64.381883s`, total `250.367856s`. The timing aggregator now uses `17`
> canonical timelines and projects resident session `20->2` flashes, `13.160s/target`,
> `20.79x` versus unbatched per-unit flash, and `2.08x` versus per-unit in-boot batching for
> `batch_size=10`, `resident_batches=10`.
>
> `find_vpid(int nr)` was rejected before implementation because the source header requires
> `tasklist_lock` or `rcu_read_lock` around PID hash lookup, which the current v1-repl call
> primitive cannot bracket. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_SCHED_CLOCK_CPU_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session one-target proof — `sec_bat_convert_adc_to_temp`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `sec_bat_convert_adc_to_temp(unsigned int adc_ch, int temp_adc)` under a
> target-specific invalid-channel scalar contract, not as a global auto-call seed. Static identity is
> pinned by relocated export recovery plus map agreement: link `0xffffff8009573654`, direct BL xrefs
> `2`, next symbol `sec_bat_get_thr_voltage` at `+0x148`, source signature
> `int sec_bat_convert_adc_to_temp(unsigned int adc_ch, int temp_adc)` at
> `drivers/battery_v2/sec_adc.c:376`, and prefix words
> `ca1103d0 a9bf43fd 910003fd d0011448 f9434108 b4000128 7101481f 540001a0 7101341f 540007a1 f9400509 910ae128`.
>
> The global classifier remains fail-closed for this non-seeded target: `DENY`,
> `auto_call_allowed=false`. The proof route records a separate target-specific advisory
> `SAFE-SCALAR` and calls only the source-defined unsupported-channel path:
> `adc_ch=0`, `temp_adc=12345`. That path never selects the `local_battery` ADC tables and returns the
> sentinel default `25000` (`0x61a8`) regardless of table state. Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-sec-bat-convert-adc-to-temp-20260701T133219Z/`.
> Result: `a90-repl-live-call-proof-sec_bat_convert_adc_to_temp-pass`; observed return `0x61a8`,
> repeated twice, stable, and matching the fixed return contract.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target result flush,
> and v2321 rollback once. Final resident is `v2321-usb-clean-identity-rodata`; standalone
> `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required eight phase events. This run measured `candidate_flash=64.205967s`,
> `warm_reboot=33.253096s`, one-target live batch `2.952422s`, `rollback_flash=64.992606s`, total
> `279.388792s`. The timing aggregator now uses `16` canonical timelines and projects resident
> session `20->2` flashes, `13.4s/target`, `20.6x` versus unbatched per-unit flash, and `2.1x`
> versus per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> `sec_abc_wait_enabled()` was rejected before implementation because disassembly showed non-leaf
> `printk` and `wait_for_completion_timeout` paths, so it is not a read-only getter proof target.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_SEC_BAT_CONVERT_ADC_TO_TEMP_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session one-target proof — `is_boot_recovery`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted `is_boot_recovery()` as the next no-argument Samsung state
> getter. Static identity is pinned by `exact-leaf-map+xref+word-boundary`:
> link `0xffffff80086ec6bc`, JOPP entry, direct BL xrefs `3`, body words
> `90014e08 b949d900 d65f03c0 00be7bad`, next symbol
> `sec_bootstat_add_initcall` at `+0x10`, and source declaration
> `extern unsigned int is_boot_recovery(void)` at
> `drivers/battery_v2/include/sec_battery.h:763`.
>
> The global classifier now treats this exact pinned leaf as `SAFE-SCALAR`
> with no required pointer args. The generic 64-byte scan still sees the
> following function's `__pi_strcmp` call and reports raw `signals.leaf=false`;
> the accepted identity gate is the exact `0x10` next-symbol boundary and
> `exact_leaf_map_ground_truth`. Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-is-boot-recovery-20260701T131159Z/`.
> Result: `a90-repl-live-call-proof-is_boot_recovery-pass`; observed return
> `0x0`, repeated twice, stable, bool-like, and in the `0..0xffffffff`
> contract range. Session used v1-repl flash once, mandatory warm reboot
> before the batch, per-target result flush, and v2321 rollback once.
> Final resident after serial bridge restart is `v2321-usb-clean-identity-rodata`;
> standalone `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level
> `events` schema and all required eight phase events. This run measured
> `candidate_flash=64.310290s`, `warm_reboot=33.243462s`, one-target live
> batch `3.066112s`, `rollback_flash=63.840645s`, total `243.139239s`.
> The timing aggregator now uses `15` canonical timelines and projects
> resident session `20->2` flashes, `13.550s/target`, `20.28x` versus
> unbatched per-unit flash, and `2.03x` versus per-unit in-boot batching for
> `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_IS_BOOT_RECOVERY_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session one-target proof — `sec_abc_get_enabled`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex proved `sec_abc_get_enabled()` as a target-specific Samsung ABC state getter without adding it
> to the global `CALL_SAFETY_SEEDS` auto-call whitelist. Static identity is pinned by
> `exact-leaf-export+word-boundary`: export candidate count `1`, map agrees with export,
> link `0xffffff800935c62c`, body words `d0011708 b9478900 d65f03c0 00be7bad`, next symbol
> `sec_abc_send_event` at `+0x10`, source declaration `extern int sec_abc_get_enabled(void)` in
> `include/linux/sti/abc_common.h:118`, and ABC enum return contract `0..2`
> (`ABC_DISABLED` / `ABC_TYPE1_ENABLED` / `ABC_TYPE2_ENABLED`).
>
> The global classifier remains fail-closed for this non-seeded target: `DENY`,
> `auto_call_allowed=false`. The proof route records a separate target-specific advisory
> `SAFE-SCALAR`, `candidate_safe=true`, and only then calls the leaf under the explicit no-arg
> read-only contract. Live resident-session run:
> `workspace/private/runs/kernel/repl-resident-session-sec-abc-get-enabled-20260701T120126Z/`.
> Result: `a90-repl-live-call-proof-sec_abc_get_enabled-pass`; observed return `0x0`, repeated
> twice, stable and in range. Session used v1-repl flash once, one mandatory warm reboot before
> the batch, per-target result flush, and v2321 rollback once. Final resident is
> `v2321-usb-clean-identity-rodata`; `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events` schema and all
> required eight phase events. This run measured `candidate_flash=64.100786s`,
> `warm_reboot=32.662513s`, one-target live batch `3.050100s`, `rollback_flash=63.650129s`, total
> `248.751145s`. The timing aggregator now uses `11` canonical timelines and projects resident
> session `20->2` flashes, `14.821s/target`, `19.15x` versus unbatched per-unit flash, and `1.91x`
> versus per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_SEC_ABC_GET_ENABLED_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session one-target proof — `sec_debug_get_reset_reason`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex selected `sec_debug_get_reset_reason()` as the next single target after
> rejecting `sec_debug_get_upload_cause()` for logging helper calls and parking
> adjacent `sec_debug_get_reset_write_cnt()` for a future same-shape batch. Static
> identity is pinned by `exact-leaf-map+xref+word-boundary`: link
> `0xffffff80086ed484`, JOPP entry, direct BL xrefs `7`, body words
> `f0012ec8 b944c900 d65f03c0 00be7bad`, next symbol
> `sec_debug_get_reset_write_cnt` at `+0x10`, and source declaration
> `extern unsigned int sec_debug_get_reset_reason(void)` at
> `include/linux/samsung/debug/sec_debug_user_reset.h:22`.
>
> The global classifier now treats this exact pinned leaf as `SAFE-SCALAR` with no
> required pointer args. The proof called it twice with no arguments in resident-session
> mode. Live run:
> `workspace/private/runs/kernel/repl-resident-session-sec-debug-get-reset-reason-20260701T122038Z/`.
> Result: `a90-repl-live-call-proof-sec_debug_get_reset_reason-pass`; observed return
> `0xffeeffee`, repeated twice, stable and in the `0..0xffffffff` contract range.
> Session used v1-repl flash once, mandatory warm reboot before the batch, per-target
> result flush, and v2321 rollback once. Final resident is `v2321-usb-clean-identity-rodata`;
> standalone `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events`
> schema and all required eight phase events. This run measured
> `candidate_flash=65.215950s`, `warm_reboot=20.879940s`, one-target live batch
> `3.274416s`, `rollback_flash=64.848177s`, total `291.053173s`. The timing
> aggregator now uses `12` canonical timelines and projects resident session `20->2`
> flashes, `14.390s/target`, `19.77x` versus unbatched per-unit flash, and `1.98x`
> versus per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_SEC_DEBUG_GET_RESET_REASON_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session one-target proof — `sec_debug_get_reset_write_cnt`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted the adjacent same-shape Samsung reset header getter
> `sec_debug_get_reset_write_cnt()` as the next single target. Static identity is
> pinned by `exact-leaf-map+xref+word-boundary`: link `0xffffff80086ed494`,
> JOPP entry, direct BL xrefs `7`, body words
> `f0012ec8 b944cd00 d65f03c0 00be7bad`, next symbol
> `sec_debug_get_reset_reason_str` at `+0x10`, and source declaration
> `extern int sec_debug_get_reset_write_cnt(void)` at
> `include/linux/samsung/debug/sec_debug_user_reset.h:25`.
>
> The global classifier now treats this exact pinned leaf as `SAFE-SCALAR` with no
> required pointer args. The proof called it twice with no arguments in resident-session
> mode. Live run:
> `workspace/private/runs/kernel/repl-resident-session-sec-debug-get-reset-write-cnt-20260701T123235Z/`.
> Result: `a90-repl-live-call-proof-sec_debug_get_reset_write_cnt-pass`; observed raw
> return `0xffffffff`, repeated twice, stable and in the raw `0..0xffffffff` contract
> range. Interpreted as signed 32-bit `int`, that is `-1`; the proof records the raw
> ABI value without assigning stronger semantics. Session used v1-repl flash once,
> mandatory warm reboot before the batch, per-target result flush, and v2321 rollback
> once. Final resident is `v2321-usb-clean-identity-rodata`; standalone `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level `events`
> schema and all required eight phase events. This run measured
> `candidate_flash=64.126462s`, `warm_reboot=33.232281s`, one-target live batch
> `3.097960s`, `rollback_flash=64.073198s`, total `230.899706s`. The timing
> aggregator now uses `13` canonical timelines and projects resident session `20->2`
> flashes, `14.031s/target`, `19.98x` versus unbatched per-unit flash, and `2.00x`
> versus per-unit in-boot batching for `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_SEC_DEBUG_GET_RESET_WRITE_CNT_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL resident-session one-target proof — `sec_debug_get_reset_reason_str`

> ### ✅ STATUS (2026-07-01 live-proven, resident-session mode, rolled back cleanly)
>
> Codex promoted the adjacent Samsung reset-reason string lookup
> `sec_debug_get_reset_reason_str(unsigned int reason)`. Static identity is
> pinned by `exact-leaf-map+xref+word-boundary`: link `0xffffff80086ed4a4`,
> JOPP entry, direct BL xrefs `6`, body words
> `51000409 52800188 7100313f f0012ec9 1a883008 91134129 8b284508 8b080120 d65f03c0 00be7bad`,
> next symbol `sec_debug_store_extc_idx` at `+0x28`, and source declaration
> `extern char * sec_debug_get_reset_reason_str(unsigned int reason)` at
> `include/linux/samsung/debug/sec_debug_user_reset.h:28`.
>
> The global classifier now treats this exact pinned leaf as `SAFE-SCALAR`
> with no required pointer args and return kind `borrowed-kernel-string-pointer`.
> The proof called bounded scalar reasons `1`, `12`, and out-of-range `13`,
> repeated twice each, bounded-read the borrowed NUL-terminated string, and
> never freed the returned pointer. Live run:
> `workspace/private/runs/kernel/repl-resident-session-sec-debug-get-reset-reason-str-retry-20260701T125452Z/`.
> Result: `a90-repl-live-call-proof-sec_debug_get_reset_reason_str-pass`;
> reason `1 -> "SP"`, reason `12 -> "NP"`, and reason `13 -> "NP"`.
> Reason `13` returned the same borrowed pointer/string as reason `12`,
> confirming the out-of-range clamp. Runtime pointers and slide stayed private.
>
> Attempt 1
> (`workspace/private/runs/kernel/repl-resident-session-sec-debug-get-reset-reason-str-20260701T124848Z/`)
> stopped before target completion on transient REPL marker capture loss
> (`A90R` missing for a non-replay-safe `OP_CALL`); it rolled back to v2321
> cleanly. The proof was tightened to mark this read-only target call
> `replay_safe=True`, and the resident-session harness now writes
> `live_session_end` on exception paths after `live_session_start`.
>
> Session used v1-repl flash once, mandatory warm reboot before the batch,
> per-target result flush, and v2321 rollback once. Final resident is
> `v2321-usb-clean-identity-rodata`; post-bridge-restart standalone
> `selftest fail=0`.
>
> Canonical timing is present in `timeline.json` with the single top-level
> `events` schema and all required eight phase events. This run measured
> `candidate_flash=64.248881s`, `warm_reboot=32.987989s`, one-target live
> batch `11.870893s`, `rollback_flash=63.767765s`, total `234.747757s`.
> The timing aggregator now uses `14` canonical timelines and projects
> resident session `20->2` flashes, `13.785s/target`, `20.10x` versus
> unbatched per-unit flash, and `2.01x` versus per-unit in-boot batching for
> `batch_size=10`, `resident_batches=10`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_SEC_DEBUG_GET_RESET_REASON_STR_RESIDENT_SESSION_2026-07-01.md`.

## ✅ DONE — REPL VFS-read observation bundle — `/proc`/`/sys` file-node keystone promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — `filp_open` + `kernel_read` assembled into bounded file observation
>
> Codex implemented the 2026-07-01 KEYSTONE-FIRST + RETIRE-SUBSUMED steer as
> an actual REPL primitive rather than another lone getter. The previously
> live-proven `filp_open` and `kernel_read` targets are now composed by
> `a90_repl.py vfs-read`: allocate owned pathname/read/`loff_t` buffers,
> write an absolute kernel-visible path, call `filp_open(path, O_RDONLY, 0)`,
> call `kernel_read(file, owned_buffer, read_len, owned_pos)`, close the file
> with `filp_close(file, NULL)`, and `kfree` every owned buffer. Raw file
> bytes, runtime pointers, and KASLR slide stay private-only.
>
> Static gate re-runs C1/source/call-safety before live use:
> `filp_open=0xffffff800828a664` (`export-recovery`, direct BL xrefs `48`,
> source `extern struct file * filp_open(const char *, int, umode_t)`,
> `SAFE-WITH-VALID-PTR` x0 pathname),
> `kernel_read=0xffffff800828bae4` (`export-recovery`, direct BL xrefs `17`,
> source `extern ssize_t kernel_read(struct file *, void *, size_t, loff_t *)`,
> `SAFE-WITH-VALID-PTR` x0/x1/x3 verified pointers), and
> `filp_close=0xffffff800828ac14` (`export-recovery`, direct BL xrefs `67`,
> cleanup-only `SAFE-WITH-VALID-PTR`). `__kmalloc`/`kfree` stay under the
> existing owned-buffer allocator contract, including the no-pre-call-x0-deref
> guard for `__kmalloc`.
>
> Attempt 1
> (`workspace/private/runs/kernel/vfs-read-observation-bundle-20260701T100931Z/`)
> flashed the v1-repl candidate successfully but aborted before any target call
> when serial input fragmented after a successful candidate `version` response.
> It immediately rolled back to v2321; rollback flash matched readback SHA, and
> a bridge restart confirmed final v2321 `version/status/selftest`. This was a
> transport abort, not a promoted proof.
>
> Attempt 2
> (`workspace/private/runs/kernel/vfs-read-observation-bundle-20260701T101310Z/`)
> passed. Baseline v2321 health passed, candidate flash matched the exact
> v1-repl SHA
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`,
> candidate health retry passed after known serial fragmentation, REPL selftest
> passed, the VFS-read bundle passed, post-proof candidate health passed, and
> rollback to v2321 matched SHA
> `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
> Final rollback health retry passed with `selftest pass=11 warn=1 fail=0`,
> and final bridge status was `connected-no-immediate-error`.
>
> The live bundle read five paths in one REPL session:
> `/proc/cmdline` (`128` bytes, text/proc-style, raw content redacted),
> `/proc/sys/fs/file-max` (`7` bytes, text decimal),
> `/proc/sys/kernel/tainted` (`4` bytes, text decimal),
> `/sys/kernel/uevent_seqnum` (`5` bytes, text decimal), and
> `/proc/config.gz` (`128` bytes, binary gzip-style stream). For every path,
> owned allocation, path poke/peek, `filp_open`, `kernel_read` return/pos,
> `filp_close`, and `kfree` checks passed.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/vfs-read-observation-bundle-20260701T101310Z/timeline.json`
> at `2026-07-01T10:13:10Z`: baseline bridge status `0.327s`, baseline health
> `1.449s`, candidate flash `66.065s`, candidate bridge restart `1.097s`,
> candidate health first attempt marker/input fragmentation `10.168s`,
> candidate bridge restart `1.639s`, candidate health retry `8.073s`, REPL
> selftest `5.938s`, live VFS-read bundle `129.323s`, post-proof candidate
> health `1.445s`, rollback flash `64.357s`, rollback bridge restart `0.902s`,
> rollback health first attempt marker/input fragmentation `10.164s`, rollback
> bridge restart `1.671s`, rollback health retry `8.142s`, and final bridge
> status `0.336s`.
>
> Function-map outcome: do not enumerate state getters whose values are
> reachable through `/proc` or `/sys` file nodes. Use the live-proven VFS-read
> observation bundle for those surfaces, and reserve individual call-proofs for
> no-file-node functions or genuinely new ABI shapes. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_VFS_READ_OBSERVATION_BUNDLE_2026-07-01.md`.

## ✅ DONE — REPL VFS-read hardening-posture observation bundle promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — named `/proc/sys/kernel` hardening bundle
>
> Codex added the first named observation bundle on top of the live-proven
> VFS-read primitive: `a90_repl.py vfs-bundle hardening-posture`. The bundle
> reads fixed `/proc/sys/kernel` file-node equivalents through
> `filp_open + kernel_read + filp_close`, with owned pathname/read/`loff_t`
> buffers and per-path `kfree` cleanup. This directly implements the
> RETIRE-SUBSUMED policy: use file nodes for equivalent state instead of adding
> more lone getter call-proofs.
>
> Baseline path preflight found these nodes readable and fixed them as the
> bundle contract: `/proc/sys/kernel/kptr_restrict`,
> `/proc/sys/kernel/dmesg_restrict`,
> `/proc/sys/kernel/perf_event_paranoid`,
> `/proc/sys/kernel/modules_disabled`,
> `/proc/sys/kernel/randomize_va_space`, and
> `/proc/sys/kernel/unprivileged_bpf_disabled`. The bundle deliberately
> excludes `panic_on_oops` because the REPL proof temporarily changes that
> sysctl as a runtime guard; including it would self-contaminate the
> observation. `kexec_load_disabled` and `yama/ptrace_scope` are absent on this
> image.
>
> Static gate remains the VFS-read gate: `filp_open`, `kernel_read`,
> `filp_close`, `__kmalloc`, and `kfree` all resolve through the promoted C2B
> map/export-recovery path and retain their existing C1/source/call-safety
> contracts. No DENY tier was relaxed. `filp_close` is cleanup-only for the
> `struct file *` returned by the same path's `filp_open`.
>
> Live validation passed in
> `workspace/private/runs/kernel/vfs-read-hardening-posture-bundle-20260701T102654Z/`.
> Candidate flash matched the v1-repl SHA
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
> Candidate health first attempt hit known serial input/END-marker
> fragmentation; bridge restart + retry passed. REPL selftest passed. The
> `hardening-posture` bundle then read all six paths successfully in one REPL
> session. Each result was a short text decimal value; exact raw values,
> runtime pointers, and KASLR slide are private-only. Post-proof candidate
> health passed. Rollback to v2321 matched SHA
> `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`;
> final health retry passed with `selftest pass=11 warn=1 fail=0`, and final
> bridge status was `connected-no-immediate-error`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/vfs-read-hardening-posture-bundle-20260701T102654Z/timeline.json`
> at `2026-07-01T10:26:54Z`: rollback/fallback/recovery precondition `0.642s`,
> baseline bridge status `0.320s`, baseline health `2.099s`, candidate flash
> `64.571s`, candidate bridge restart `1.657s`, candidate health first attempt
> marker/input fragmentation `10.151s`, candidate bridge restart `1.645s`,
> candidate health retry `7.105s`, REPL selftest `5.893s`, live hardening
> bundle `117.420s`, post-proof candidate health `1.455s`, rollback flash
> `65.706s`, rollback bridge restart `0.885s`, rollback health first attempt
> marker/input fragmentation `10.139s`, rollback bridge restart `1.637s`,
> rollback health retry `8.089s`, and final bridge status `0.322s`.
>
> Bundle-map outcome: `hardening-posture` is now the preferred observation
> surface for these `/proc/sys/kernel` state nodes. Do not add individual
> call-proofs for the same state unless a future target has no file-node
> equivalent or requires a genuinely new ABI shape. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_VFS_READ_HARDENING_POSTURE_BUNDLE_2026-07-01.md`.

## ✅ DONE — REPL VFS-read kernel-vitals observation bundle promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — named `/proc` kernel vital signs bundle
>
> Codex added `a90_repl.py vfs-bundle kernel-vitals` on top of the live-proven
> VFS-read primitive. The bundle reads `/proc/uptime`, `/proc/loadavg`,
> `/proc/meminfo`, `/proc/stat`, `/proc/vmstat`, and `/proc/version` through
> `filp_open + kernel_read + filp_close`, with owned pathname/read/`loff_t`
> buffers and per-path `kfree` cleanup. Raw file bytes, runtime pointers, and
> KASLR slide stay private-only.
>
> Static gate remains the existing VFS-read gate: `filp_open`, `kernel_read`,
> `filp_close`, `__kmalloc`, and `kfree` retain their promoted C2B
> map/export-recovery resolution and source/call-safety contracts. No DENY tier
> was relaxed. The bundle is the preferred observation surface for standard
> `/proc` kernel vital signs; do not add lone getter proofs for equivalent
> counters.
>
> Live validation passed in
> `workspace/private/runs/kernel/vfs-read-kernel-vitals-bundle-20260701T105200Z/`.
> Candidate flash matched the v1-repl SHA
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
> Candidate health first attempt hit known serial marker/input fragmentation;
> bridge restart + retry passed. REPL selftest passed. The `kernel-vitals`
> bundle then read all six paths successfully in one REPL session with
> `read_data_redacted=true`. Post-proof candidate health passed. Rollback to
> v2321 matched SHA
> `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`;
> final v2321 health passed with `selftest pass=11 warn=1 fail=0`, and final
> bridge status was `connected-no-immediate-error`.
>
> Timing is recorded in the canonical events-only schema at
> `workspace/private/runs/kernel/vfs-read-kernel-vitals-bundle-20260701T105200Z/timeline.json`.
> The file has a single top-level `events` array and the required eight events:
> `candidate_flash_start`, `candidate_flash_done`, `candidate_boot_ready`,
> `live_session_start`, `live_session_end`, `rollback_flash_start`,
> `rollback_flash_done`, and `rollback_boot_ready`. Phase timings:
> candidate flash `63.623s`, candidate boot/health `21.015s`, live session
> `449.778s`, rollback flash `64.713s`, rollback boot/health `20.895s`, total
> candidate-flash-start to rollback-boot-ready `628.457s`.
>
> The proof passed, but the live session is too slow for routine use. Next
> optimization should split heavy `/proc` reads into smaller named bundles or
> add per-path timeout/continue behavior so one slow path cannot dominate the
> whole session. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_VFS_READ_KERNEL_VITALS_BUNDLE_2026-07-01.md`.

## ✅ DONE — REPL kernel taint-state live-call proof batch — `get_taint()` + `test_taint()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — same-shape kernel taint health/state getters
>
> Codex added a new function-map target batch rather than repeating existing
> inventory: `get_taint()` reads the kernel tainted-mask state and
> `test_taint(flag)` validates bounded taint-bit queries against that same
> mask. This extends REPL measurement toward kernel health/status observation.
>
> Static selection pinned `get_taint=0xffffff80080b271c` via
> `exact-leaf-map+xref+word-boundary`: export candidate count `0`, direct BL
> xrefs `1`, JOPP entry, source declaration
> `extern unsigned long get_taint(void)` at `include/linux/kernel.h:519`,
> `SAFE-SCALAR` call-safety, and next-symbol boundary `add_taint` at `+0x10`.
> The proof pinned the complete body plus guard:
> `0x90017308 0xf9470d00 0xd65f03c0 0x00be7bad`.
>
> Static selection pinned `test_taint=0xffffff80080b261c` via
> `exact-leaf-export+word-boundary`: export candidate count `1`, direct BL
> xrefs `0`, JOPP entry, source declaration
> `extern int test_taint(unsigned flag)` at `include/linux/kernel.h:518`,
> `SAFE-SCALAR` call-safety, and next-symbol boundary `no_blink` at `+0x30`.
> This low-xref helper is accepted only under the stricter export row + map
> agreement + exact words + source declaration + boundary contract. The proof
> pinned the complete body plus guard:
> `0x1100fc08 0x7100001f 0x90017309 0x1a80b108 0x91386129 0x13067d08 0xf868d928 0x9ac02508 0x12000100 0xd65f03c0 0xd503201f 0x00be7bad`.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate
> (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, candidate helper `version/status` verification passed,
> explicit candidate `selftest` passed after bridge restart from serial marker
> loss, and REPL selftest returned `a90-repl-v2a1-selftest-pass`.
>
> The proof called both targets in one `call-proof-batch` session.
> `get_taint()` returned stable mask `0x204`, `0x204`. `test_taint()` tested
> flags `0`, `1`, `15`, `31`, and `63` twice each, and every result matched
> `(0x204 >> flag) & 1`; all tested flags returned `0x0`. A final
> `get_taint()` anchor after the bit tests still returned `0x204`. No runtime
> pointer was dereferenced by the host, no cleanup was required, and raw
> runtime values plus the KASLR slide stayed private/redacted.
>
> Post-proof candidate `version/status/selftest` passed with
> `pass=11 warn=1 fail=0`. Rollback to v2321 completed with matching readback
> SHA, rollback helper `version/status` passed, final v2321 standalone
> `selftest` passed after bridge restart from serial marker loss, and final
> bridge status was `connected-no-immediate-error`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-taint-state-batch-20260701T095007Z/timeline.json`
> at `2026-07-01T09:50:07Z`: baseline bridge/version/status/selftest preflight
> `1.950s`, candidate flash helper `65.707s`, candidate selftest first attempt
> marker loss `10.220s`, candidate bridge restart `2.130s`, candidate
> selftest retry `0.440s`, REPL selftest `5.810s`, live proof batch `14.890s`,
> post-proof candidate version/status/selftest `1.390s`, rollback flash helper
> `64.675s`, final selftest first attempt marker loss `10.110s`, final bridge
> status after marker loss `0.320s`, final bridge restart `2.130s`, final
> selftest retry `0.440s`, and final bridge status retry `0.320s`. The helper
> total rows are not additive; all serial bridge operations in the accepted
> live path were sequential.
>
> Function-map outcome: `get_taint` is promoted as live-proven only under the
> no-argument read-only kernel taint-mask contract, and `test_taint` is
> promoted as live-proven only under the bounded scalar taint-flag contract
> anchored to same-session `get_taint()`. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_TAINT_STATE_BATCH_2026-07-01.md`.

## ✅ DONE — REPL Samsung sec_debug state live-call proof batch — `sec_debug_is_enabled()` + `sec_debug_level()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — same-shape no-arg Samsung sec_debug state getters
>
> Codex followed the corrected batch cadence: same-shape read-only state
> getters were grouped into one `v1-repl` boot session and one rollback.
> `sec_debug_is_enabled()` and `sec_debug_level()` were selected from the
> Samsung `sec_debug` header as adjacent no-argument state-observation
> queries. `sec_debug_is_enabled_for_ssr()` stayed parked because its source
> type is `int`, it has only one direct xref, and it was not needed to prove
> this bounded same-shape state batch.
>
> Static selection pinned `sec_debug_is_enabled=0xffffff80086e37cc` via
> `exact-leaf-map+xref+word-boundary`: export candidate count `0`, direct BL
> xrefs `26`, JOPP entry, source declaration
> `extern bool sec_debug_is_enabled(void)` at
> `include/linux/samsung/debug/sec_debug.h:305`, `SAFE-SCALAR` call-safety,
> and next-symbol boundary `sec_modem_loading_fail_to_bootloader` at `+0x38`.
> The proof pinned the complete body plus guard:
> `0xb0014e48 0xb0014e49 0x90012f2a 0x5289e98b 0x91075129 0x9116414a 0xb941d108 0x6b0b011f 0x9a8a0128 0xb9400108 0x7100011f 0x1a9f07e0 0xd65f03c0 0x00be7bad`.
>
> Static selection pinned `sec_debug_level=0xffffff80086e3bb4` via
> `exact-leaf-map+xref+word-boundary`: export candidate count `0`, direct BL
> xrefs `1`, JOPP entry, source declaration
> `extern unsigned int sec_debug_level(void)` at
> `include/linux/samsung/debug/sec_debug.h:306`, `SAFE-SCALAR` call-safety,
> and next-symbol boundary `sec_debug_is_enabled_for_ssr` at `+0x10`. The
> proof pinned the complete body plus guard:
> `0xb0014e48 0xb941d100 0xd65f03c0 0x00be7bad`.
> For both targets, the generic 64-byte classifier scan can include following
> `sec_debug` code after the exact next-symbol boundary, so this proof treats
> the explicit body/guard as the function-body authority.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate
> (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, candidate helper `version/status` verification passed,
> explicit candidate `selftest` passed after bridge restart from serial marker
> loss, and REPL selftest returned `a90-repl-v2a1-selftest-pass`.
>
> The proof called both targets twice with no arguments in one
> `call-proof-batch` session. `sec_debug_is_enabled()` returned bool and
> stable values: `0x0`, `0x0`. `sec_debug_level()` returned stable `uint32_t`
> values: `0x4f4c`, `0x4f4c`. No runtime pointer was dereferenced by the host,
> no cleanup was required, and raw runtime values plus the KASLR slide stayed
> private/redacted.
>
> Post-proof candidate `version/status/selftest` passed with
> `pass=11 warn=1 fail=0`. Rollback to v2321 completed with matching readback
> SHA, rollback helper `version/status` passed, final v2321 standalone
> `selftest` passed after bridge restart from serial marker loss, and final
> bridge status was `connected-no-immediate-error`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-sec-debug-state-batch-20260701T093249Z/timeline.json`
> at `2026-07-01T09:32:49Z`: baseline bridge/version/status/selftest preflight
> `2.144s`, candidate flash helper `65.703s`, candidate selftest first attempt
> marker loss `10.129s`, candidate bridge restart + selftest retry + REPL
> selftest `8.038s`, live proof batch `8.128s`, post-proof candidate
> version/status/selftest `1.233s`, rollback flash helper `64.381s`, final
> selftest first attempt marker loss `10.200s`, final bridge status after
> marker loss `0.330s`, final bridge restart `2.130s`, final selftest retry
> `0.440s`, and final bridge status retry `0.330s`. The helper total rows are
> not additive; all serial bridge operations in the accepted live path were
> sequential.
>
> Function-map outcome: `sec_debug_is_enabled` is promoted as live-proven only
> under the no-argument read-only Samsung sec_debug enabled-state contract, and
> `sec_debug_level` is promoted as live-proven only under the no-argument
> read-only Samsung sec_debug level contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SEC_DEBUG_STATE_BATCH_2026-07-01.md`.

## ✅ DONE — REPL slab allocator availability live-call proof — `slab_is_available()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg slab allocator availability bool getter
>
> Codex followed the corrected batch cadence first: a slab-family sweep checked
> adjacent `slab_*`, `kmem_cache_*`, `kfree_*`, `ksize`, and `kzfree` candidates.
> The only read-only no-argument allocator-state candidate was
> `slab_is_available()`; the nearby candidates were allocation/free/init/RCU or
> pointer-mutating helpers and stayed out of the proof. The live command used
> `call-proof-batch slab_is_available` to preserve the batch entrypoint, but did
> not force an unsafe slab partner into the same boot session.
>
> Static selection pinned `slab_is_available=0xffffff800823839c` via
> `exact-leaf-map+xref+word-boundary`: export candidate count `0`, direct BL
> xrefs `16`, JOPP entry, source declaration `bool slab_is_available(void)` at
> `include/linux/slab.h:122`, and `SAFE-SCALAR` call-safety. The next-symbol
> boundary is `kmalloc_slab` at `+0x18`. The proof pinned the complete body plus
> guard:
> `0xb0016968 0xb94ca908 0x7100091f 0x1a9f97e0 0xd65f03c0 0x00be7bad`.
> The generic 64-byte classifier scan includes `kmalloc_slab` after the boundary,
> so this proof treats the explicit 0x18 body/guard as the function-body
> authority.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact v1-repl
> candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and readback
> SHA, candidate helper `version/status` verification passed, explicit candidate
> `selftest` passed after bridge restart from serial marker loss, and REPL
> selftest returned `a90-repl-v2a1-selftest-pass`.
>
> The proof called `slab_is_available()` twice with no arguments in one
> `call-proof-batch` session. Returns were bool and stable: `0x1`, `0x1`. No
> runtime pointer was dereferenced by the host, no cleanup was required, and raw
> runtime values plus the KASLR slide stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
> Rollback to v2321 completed with matching readback SHA, rollback helper
> `version/status` passed, final v2321 standalone `selftest` passed after bridge
> restart from serial marker loss, and final bridge status was
> `connected-no-immediate-error`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-slab-is-available-20260701T091812Z/timeline.json`
> at `2026-07-01T09:18:12Z`: candidate flash helper `64.726s`,
> candidate selftest first attempt marker loss `10.062s`, bridge restart
> `2.315s`, candidate selftest retry `0.294s`, REPL selftest `5.852s`,
> live proof batch `5.082s`, post-proof candidate selftest `0.296s`,
> rollback flash helper `65.318s`, final selftest first attempt marker loss
> `10.085s`, and final bridge restart + selftest + bridge status `2.756s`.
> The helper total rows are not additive; all serial bridge operations in the
> accepted live path were sequential.
>
> Function-map outcome: `slab_is_available` is promoted as live-proven only under
> the no-argument read-only slab allocator availability contract: the pinned body
> performs a global-load/compare state read and returns a stable bool. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SLAB_IS_AVAILABLE_2026-07-01.md`.

## ✅ DONE — REPL USB/OTG notify live-call proof — `get_otg_notify()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg USB/OTG borrowed-pointer getter
>
> Codex selected `get_otg_notify` as a USB/OTG kernel-state observation target
> outside the saturated `CALL_PROOF_TARGETS` inventory. It extends the function
> map with a read-only getter for the native kernel USB notify core:
> `extern struct otg_notify * get_otg_notify(void)` from
> `include/linux/usb_notify.h:175`.
>
> Static selection pinned `get_otg_notify=0xffffff800901d8d4` via
> `export-recovery` with map agreement, a single export candidate, direct BL
> xrefs `41`, JOPP entry, and a leaf body. The C1 gate classifies it as
> `SAFE-SCALAR`; source/ABI contract is no pointer args. The implementation in
> `drivers/usb/notify/usb_notify.c` was matched as the expected read-only
> pattern: return NULL if `u_notify_core` is absent, return NULL if
> `u_notify_core->o_notify` is absent, otherwise return the borrowed
> `o_notify` pointer. The next-symbol boundary is `inc_hw_param` at `+0x20`;
> the static words pinned the global core load, NULL branch, borrowed
> `o_notify` load, return path, NULL return path, and final `0x00be7bad`
> boundary guard.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health plus explicit candidate `selftest`
> passed.
>
> The first proof attempt called the target but stopped because the host-side
> return predicate was too narrow: it accepted only lowmem borrowed pointers,
> while the live target returned a stable canonical kernel data pointer.
> Candidate health stayed clean after that host-contract failure. The predicate
> was corrected to accept NULL or a stable canonical kernel pointer under this
> borrowed-pointer contract.
>
> The retry called `get_otg_notify()` twice with no arguments. Both calls
> returned the same non-NULL borrowed kernel pointer; the pointer was not
> dereferenced and was not freed. Raw runtime pointer values and the KASLR slide
> stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `selftest pass=11 warn=1
> fail=0`. Rollback to v2321 completed with matching readback SHA. Final
> standalone selftest initially had partial serial capture, then `hide` hit
> known marker-loss noise and `double` input mode proved unsuitable for the
> current bridge state; a host-side bridge restart restored clean framing, and
> the final `selftest` retry passed with `pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-get-otg-notify-20260701T062153Z/timeline.json`
> at `2026-07-01T06:25:00Z`: candidate flash helper `63.720s`,
> candidate explicit selftest `0.299s`, initial live proof host-contract
> failure `4.820s`, post-failure candidate selftest `0.297s`, live proof retry
> pass `5.216s`, post-proof candidate selftest `0.299s`, rollback flash helper
> `63.816s`, final selftest partial capture `0.309s`, final hide marker-loss
> attempt `20.108s`, double input mode failed command encoding `29.921s`,
> bridge restart `1.996s`, and final selftest retry `0.309s`. The helper total
> rows are not additive; all serial bridge commands in this unit were
> sequential.
>
> Function-map outcome: `get_otg_notify` is promoted as live-proven only under
> the no-argument USB/OTG notify borrowed-pointer contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_OTG_NOTIFY_2026-07-01.md`.

## ✅ DONE — REPL USB/OTG notify-data live-call proof — `get_notify_data()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — borrowed `struct otg_notify *` input getter
>
> Codex selected `get_notify_data` as the next USB/OTG read-only state target
> because it moves beyond another no-argument getter: the proof first uses
> `get_otg_notify()` as an input anchor, then passes that live borrowed
> `struct otg_notify *` to `get_notify_data(struct otg_notify *n)`.
>
> Static selection pinned `get_notify_data=0xffffff800901def4` via the new
> target-limited `exact-leaf-export+word-boundary` gate: one export candidate,
> map/export agreement, JOPP entry, leaf body, direct BL xrefs `0` by design,
> no in-body BL, exact words `cbz x0`, `ldr x0,[x0,#160]`, `ret`, final
> `0x00be7bad`, and next-symbol boundary `set_notify_data` at `+0x10`. The C1
> gate classifies it as `SAFE-WITH-VALID-PTR`; required input is
> `x0=borrowed-otg-notify-pointer-from-get_otg_notify`. Source declaration was
> `extern void * get_notify_data(struct otg_notify *n)` from
> `include/linux/usb_notify.h:173`; implementation in
> `drivers/usb/notify/usb_notify.c` matched the read-only pattern: return NULL
> if `n` is NULL, otherwise return borrowed `n->o_data`.
>
> The input anchor remained `get_otg_notify=0xffffff800901d8d4`,
> `export-recovery`, direct BL xrefs `41`, no-argument `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health plus explicit candidate `selftest`
> passed.
>
> The first proof attempt stopped before target calls because serial framing
> missed the END marker for the `panic_on_oops` shell command. Candidate health
> stayed clean. Codex restarted the bridge, restored `panic_on_oops=1`, and
> candidate `selftest` passed. One retry then hit a host CLI option-position
> error before any device action.
>
> The successful retry called `get_otg_notify()` once; it returned a non-NULL
> borrowed kernel pointer. The proof then called
> `get_notify_data(otg_notify_ptr)` twice. Both calls returned the same
> non-NULL borrowed kernel pointer. Neither the input anchor pointer nor the
> returned notify-data pointer was dereferenced or freed. Raw runtime pointer
> values and the KASLR slide stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `selftest pass=11 warn=1
> fail=0`. Rollback to v2321 completed with matching readback SHA. Final
> `hide` hit known marker-loss noise after rollback helper verification; a
> host-side bridge restart restored clean framing, and the final standalone
> `selftest` retry passed with `pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-get-notify-data-20260701T064344Z/timeline.json`
> at `2026-07-01T06:45:51Z`: candidate flash helper `63.554s`,
> candidate explicit selftest `0.298s`, initial live proof marker loss before
> target call `27.427s`, post-failure candidate selftest `0.295s`, bridge
> restart after marker loss `1.984s`, `panic_on_oops` restore and candidate
> selftest `1.317s`, host CLI option-position error `0.139s`, live proof retry
> pass `5.948s`, post-proof candidate selftest `0.291s`, rollback flash helper
> `64.709s`, final hide marker-loss attempt `9.959s`, and final bridge restart
> plus selftest retry `2.452s`. The helper total rows are not additive; all
> serial bridge commands in this unit were sequential.
>
> Function-map outcome: `get_notify_data` is promoted as live-proven only under
> the borrowed `struct otg_notify *` input contract sourced from
> `get_otg_notify()` in the same proof. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_NOTIFY_DATA_2026-07-01.md`.

## ✅ DONE — REPL USB/OTG host-capability live-call proof — `is_usb_host()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — borrowed `struct otg_notify *` bool-state getter
>
> Codex selected `is_usb_host` from the adjacent USB notify state-observation
> neighborhood after considering `get_booster`, `get_usb_mode`,
> `get_cable_type`, `is_blocked`, and `get_hw_param` as a batch. The selected
> target extends the USB notify function map beyond pointer getters: the proof
> first uses `get_otg_notify()` as an input anchor, then passes that live
> borrowed `struct otg_notify *` to `is_usb_host(struct otg_notify *n)` and
> expects a bounded bool-int result.
>
> Static selection pinned `is_usb_host=0xffffff800901e344` via
> `export-recovery` with one export candidate, map/export agreement, JOPP
> entry, direct BL xrefs `1`, target-limited pre-call `x0` deref allowed only
> under the borrowed-pointer contract, and next-symbol boundary
> `set_otg_notify` at `+0xd0`. Prefix/tail word pins covered the JOPP entry,
> early `n->u_notify` load from `[x0,#168]`, bool return path, epilogue, `ret`,
> and final `0x00be7bad` guard. Source declaration was
> `extern int is_usb_host(struct otg_notify *n)` from
> `include/linux/usb_notify.h:169`; implementation in
> `drivers/usb/notify/usb_notify.c` matched the non-owning host-capability
> pattern.
>
> The input anchor remained `get_otg_notify=0xffffff800901d8d4`,
> `export-recovery`, direct BL xrefs `41`, no-argument `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate. A first helper attempt used the wrong
> local marker `v1-repl` and failed before reboot/flash; the v1-repl image
> intentionally preserves the `v2321-usb-clean-identity-rodata` native-init
> identity string, so the corrected retry flashed the exact candidate
> (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> through `native_init_flash.py` with matching pushed-image and readback SHA.
> Candidate helper health plus explicit candidate `selftest` passed.
>
> The successful proof called `get_otg_notify()` once; it returned a non-NULL
> borrowed kernel pointer. The proof then called `is_usb_host(otg_notify_ptr)`
> twice. Both calls returned stable bool-int `0x1`. The borrowed input pointer
> was not dereferenced by the host, freed, or retained. Raw runtime pointer
> values and the KASLR slide stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `selftest pass=11 warn=1
> fail=0`. Rollback to v2321 completed with matching readback SHA. The first
> final health bundle hit known serial marker-loss / AT echo noise after
> rollback helper verification; a host-side bridge restart restored clean
> framing, and final v2321 `version/status/selftest` retry passed with
> `selftest fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-is-usb-host-20260701T065518Z/timeline.json`
> at `2026-07-01T06:59:40Z`: local marker preflight failure before flash
> `0.084s`, candidate flash retry helper `63.770s`, candidate explicit
> selftest `0.201s`, live proof `13.572s`, post-proof candidate selftest
> `0.457s`, rollback flash helper `64.191s`, final health marker-loss attempt
> `10.302s`, final bridge restart `2.153s`, and final v2321 health retry
> `1.388s`. The helper total rows are not additive; all serial bridge commands
> in this unit were sequential.
>
> Function-map outcome: `is_usb_host` is promoted as live-proven only under the
> borrowed `struct otg_notify *` input contract sourced from `get_otg_notify()`
> in the same proof, with return constrained to stable bool-int `0` or `1`.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_IS_USB_HOST_2026-07-01.md`.

## ✅ DONE — REPL USB/OTG HW-param live-call proof — `get_hw_param()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — borrowed `struct otg_notify *` + enum-index slot getter
>
> Codex selected `get_hw_param` as the next adjacent USB notify
> state-observation target after `get_otg_notify`, `get_notify_data`, and
> `is_usb_host`. It extends the function map to a two-argument read-only
> getter: the proof first uses `get_otg_notify()` as an input anchor, then
> passes that live borrowed `struct otg_notify *` plus fixed enum index `0`
> (`USB_CCIC_WATER_INT_COUNT`) to
> `get_hw_param(struct otg_notify *n, enum usb_hw_param index)`.
>
> Static selection pinned `get_hw_param=0xffffff800901f1e4` via
> `export-recovery` with one export candidate, map/export agreement, JOPP
> entry, direct BL xrefs `26`, target-limited pre-call `x0` deref allowed only
> under the borrowed-pointer contract, and next-symbol boundary
> `inc_hw_param_host` at `+0xd0`. Source declaration was
> `extern unsigned long long * get_hw_param(struct otg_notify *n, enum usb_hw_param index)`
> from `include/linux/usb_notify.h:182`; enum parsing in
> `include/linux/usb_hw_param.h` confirmed `USB_CCIC_WATER_INT_COUNT=0` and
> `USB_CCIC_HW_PARAM_MAX=49`. Prefix/tail word pins covered the enum bounds
> check, `n->u_notify` load from `[x0,#168]`, `u_notify->hw_param[index]`
> address calculation, NULL return path, epilogue, `ret`, and final
> `0x00be7bad` guard. The implementation in
> `drivers/usb/notify/usb_notify.c` matched the non-owning slot-getter
> pattern.
>
> The input anchor remained `get_otg_notify=0xffffff800901d8d4`,
> `export-recovery`, direct BL xrefs `41`, no-argument `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate: rollback/fallback images were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health plus explicit candidate
> `selftest` passed.
>
> The successful proof called `get_otg_notify()` once; it returned a non-NULL
> borrowed kernel pointer. The proof then called
> `get_hw_param(otg_notify_ptr, 0)` twice. Both calls returned the same
> non-NULL borrowed kernel pointer. The borrowed input pointer and returned
> slot pointer were not dereferenced by the host, freed, or retained. Raw
> runtime pointer values and the KASLR slide stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `selftest pass=11 warn=1
> fail=0`. Rollback to v2321 completed with matching readback SHA. Final v2321
> `selftest` passed with `pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-get-hw-param-20260701T071300Z/timeline.json`
> at `2026-07-01T07:14:45Z`: candidate flash helper `64.846s`,
> candidate explicit selftest `0.447s`, live proof `13.733s`,
> post-proof candidate selftest `0.452s`, rollback flash helper `65.250s`,
> and final v2321 selftest `0.448s`. The helper total rows are not additive;
> all serial bridge commands in this unit were sequential.
>
> Function-map outcome: `get_hw_param` is promoted as live-proven only under
> the borrowed `struct otg_notify *` input contract sourced from
> `get_otg_notify()` in the same proof, plus enum index `0`
> (`USB_CCIC_WATER_INT_COUNT`), with return constrained to stable
> NULL-or-borrowed `unsigned long long *`. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_HW_PARAM_2026-07-01.md`.

## ✅ DONE — REPL USB/OTG block-state live-call proof — `is_blocked()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — borrowed `struct otg_notify *` + block-type bool getter
>
> Codex selected `is_blocked` as the next adjacent USB notify
> state-observation target after `get_otg_notify`, `get_notify_data`,
> `is_usb_host`, and `get_hw_param`. It extends the function map to a
> borrowed-pointer bool-state query: the proof first uses `get_otg_notify()`
> as an input anchor, then passes that live borrowed `struct otg_notify *`
> plus fixed block type `NOTIFY_BLOCK_TYPE_HOST=1` to
> `is_blocked(struct otg_notify *n, int type)`.
>
> Static selection pinned `is_blocked=0xffffff800901ef44` via
> `export-recovery` with one export candidate, map/export agreement, JOPP
> entry, direct BL xrefs `5`, target-limited pre-call `x0` deref allowed only
> under the borrowed-pointer contract, and next-symbol boundary
> `send_usb_audio_uevent` at `+0x118`. Source declaration was
> `extern bool is_blocked(struct otg_notify *n, int type)` from
> `include/linux/usb_notify.h:178`; enum parsing in the same header confirmed
> `NOTIFY_BLOCK_TYPE_HOST=1` and `NOTIFY_BLOCK_TYPE_ALL=3`. Prefix/tail word
> pins covered the NULL guards, `n->u_notify` load from `[x0,#168]`,
> `u_notify->udev.disable_state` access, type comparisons, host/client/all
> bit-test return tail, epilogue, `ret`, and final `0x00be7bad` guard. The
> implementation in `drivers/usb/notify/usb_notify.c` matched the non-owning
> block-state getter pattern.
>
> The input anchor remained `get_otg_notify=0xffffff800901d8d4`,
> `export-recovery`, direct BL xrefs `41`, no-argument `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate: rollback/fallback images were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health passed. The first explicit
> candidate `selftest` capture hit serial `AT` echo and lacked the END marker;
> after bridge restart, explicit candidate `selftest` passed with
> `pass=11 warn=1 fail=0`.
>
> The successful proof called `get_otg_notify()` once; it returned a non-NULL
> borrowed kernel pointer. The proof then called
> `is_blocked(otg_notify_ptr, 1)` twice. Both calls returned stable bool
> `0x0`. The borrowed input pointer was not dereferenced by the host, freed,
> or retained. Raw runtime pointer values and the KASLR slide stayed
> private/redacted.
>
> Post-proof candidate `selftest` passed with `selftest pass=11 warn=1
> fail=0`. Rollback to v2321 completed with matching readback SHA. The first
> final v2321 `selftest` capture contained `pass=11 warn=1 fail=0` text but
> missed the END marker after serial `AT` echo; after bridge restart, final
> v2321 `selftest` passed with `pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-is-blocked-20260701T072405Z/timeline.json`
> at `2026-07-01T07:28:30Z`: candidate flash helper `63.730s`,
> candidate explicit selftest first capture `10.187s`, candidate explicit
> selftest retry `0.452s`, live proof `5.922s`, post-proof candidate
> selftest `0.448s`, rollback flash helper `64.746s`, final v2321 selftest
> first capture `10.301s`, and final v2321 selftest retry `0.450s`. The
> helper total rows are not additive; all serial bridge commands in this unit
> were sequential.
>
> Function-map outcome: `is_blocked` is promoted as live-proven only under the
> borrowed `struct otg_notify *` input contract sourced from
> `get_otg_notify()` in the same proof, plus enum block type
> `NOTIFY_BLOCK_TYPE_HOST=1`, with return constrained to stable bool `0` or
> `1`. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_IS_BLOCKED_2026-07-01.md`.

## ✅ DONE — REPL vmalloc address-classifier live-call proof — `is_vmalloc_addr()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — scalar address-value classifier
>
> Codex selected `is_vmalloc_addr` as a scalar address-classifier target
> after nearby state candidates were parked: USB leftover helpers such as
> `get_usb_mode`, `get_cable_type`, and `get_booster` stayed denied by the
> current C1 gate; `get_debug_reset_header` was parked because it allocates
> and reads the debug partition; and `is_subsystem_online` was parked because
> its `find_subsys_device()` / `bus_find_device()` path did not yet have a
> proven put/refcount contract.
>
> Static selection pinned `is_vmalloc_addr=0xffffff800825699c` via
> `export-recovery` with map agreement, one export candidate, direct BL xrefs
> `42`, JOPP entry, leaf body, no in-body BL, and no argument dereference
> before return. Source declaration was
> `extern int is_vmalloc_addr(const void *x)` at `include/linux/mm.h:535`.
> The next-symbol boundary is `vmalloc_to_page` at `+0x30`. The proof pinned
> the full leaf classifier body and guard:
> `0xb259cfe8 0xeb08001f 0xd2b7ffe8 0xf2dff7c8 0x1a9f97e9 0xf2ffffe8 0xeb08001f 0x1a9f27e8 0x0a080120 0xd65f03c0 0xd503201f 0x00be7bad`.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health passed. The first explicit
> candidate `selftest` command missed the END marker after serial `AT` echo
> but its body showed `pass=11 warn=1 fail=0`; after bridge restart, the
> explicit candidate selftest passed cleanly.
>
> The proof called `is_vmalloc_addr()` on six fixed scalar address values:
> `0x0 -> 0`, lower boundary `0xffffff8007ffffff -> 0`,
> vmalloc start `0xffffff8008000000 -> 1`,
> mid-range `0xffffff9000000000 -> 1`,
> upper-minus-one `0xffffffbebffeffff -> 1`, and upper boundary
> `0xffffffbebfff0000 -> 0`. All observed returns matched the expected
> boundary table. No runtime pointer was dereferenced by the host, no cleanup
> was required, and raw runtime values plus the KASLR slide stayed
> private/redacted.
>
> Post-proof candidate `selftest` passed with `selftest pass=11 warn=1
> fail=0`. Rollback to v2321 completed with matching readback SHA, rollback
> helper `version/status` passed, final v2321 `version` reported
> `v2321-usb-clean-identity-rodata`, and final standalone `selftest` passed
> with `pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-is-vmalloc-addr-20260701T074339Z/timeline.json`
> at `2026-07-01T07:49:02Z`: candidate flash helper `64.810s`,
> candidate explicit selftest first capture `10.127s` with missing END
> marker but `fail=0` body, candidate selftest retry after bridge restart
> `0.453s`, live proof `7.613s`, post-proof candidate selftest `0.451s`,
> rollback flash helper `63.736s`, final v2321 version `0.312s`, and final
> v2321 selftest `0.200s`. The helper total rows are not additive; all
> serial bridge commands in this unit were sequential.
>
> Function-map outcome: `is_vmalloc_addr` is promoted as live-proven only
> under the scalar-address classifier contract: `x0` is an address value, the
> pinned leaf body must not dereference it, and the return is a bool-int
> matching the fixed vmalloc boundary table. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_IS_VMALLOC_ADDR_2026-07-01.md`.

## ✅ DONE — REPL debugfs registration-state live-call proof — `debugfs_initialized()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg debugfs registration bool getter
>
> Codex first considered nearby no-argument state candidates
> `cpu_mitigations_auto_nosmt()` and `slab_is_available()`, but parked both
> because the current fail-closed C1 identity gate did not verify them in this
> tooling run. `debugfs_initialized()` was selected instead as a no-argument
> read-only kernel-state observation getter with recovered export identity and
> source implementation evidence.
>
> Static selection pinned `debugfs_initialized=0xffffff800841904c` via
> `export-recovery` with map agreement, one export candidate, direct BL xrefs
> `2`, and JOPP entry. The source implementation is
> `bool debugfs_initialized(void)` at `fs/debugfs/inode.c:849`, returning the
> global `debugfs_registered` byte. The C1 gate classifies it as
> `SAFE-SCALAR`; required pointer args are none. The next-symbol boundary is
> `debug_mount` at `+0x10`. The proof pinned the complete 0x10-byte body plus
> guard: `0xb0015ec8 0x397e7100 0xd65f03c0 0x00be7bad`. The generic 64-byte
> classifier scan includes the next local function after the boundary, so this
> proof treats the explicit 0x10 body/guard as the function-body authority.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper `version/status` verification passed.
> The first explicit candidate `selftest` and REPL selftest were accidentally
> run in parallel by the host, causing serial contention / missing END marker;
> the device stayed healthy, and sequential retries passed with candidate
> `selftest pass=11 warn=1 fail=0` plus `a90-repl-v2a1-selftest-pass`.
>
> The proof called `debugfs_initialized()` twice with no arguments. Returns
> were bool and stable: `0x1`, `0x1`. No runtime pointer was dereferenced by
> the host, no cleanup was required, and raw runtime values plus the KASLR
> slide stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
> Rollback to v2321 completed with matching readback SHA, rollback helper
> `version/status` passed, final v2321 `version` reported
> `v2321-usb-clean-identity-rodata`, and final standalone `selftest` passed
> with `pass=11 warn=1 fail=0`. The first combined final health capture had
> host-side serial contention during `selftest`; the independent sequential
> retry is the authoritative final health gate.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-debugfs-initialized-20260701T083812Z/timeline.json`
> at `2026-07-01T08:42:46Z`: candidate flash helper `63.771s`,
> candidate selftest first capture hit host serial contention, REPL selftest
> first attempt `10.679s` with host serial contention, REPL selftest retry
> `5.790s`, live proof `5.399s`, rollback flash helper `63.972s`, and final
> v2321 selftest retry passed. The helper total rows are not additive; accepted
> proof and health commands were rerun sequentially after the host-side
> contention mistake.
>
> Function-map outcome: `debugfs_initialized` is promoted as live-proven only
> under the no-argument read-only debugfs registration contract: the pinned
> body performs a global-byte registration-state read and returns a stable
> bool. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_DEBUGFS_INITIALIZED_2026-07-01.md`.

## ✅ DONE — REPL tracefs registration-state live-call proof — `tracefs_initialized()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg tracefs registration bool getter
>
> Codex selected `tracefs_initialized()` as the next kernel-state observation
> target after `debugfs_initialized()`: it reads the sibling tracefs
> registration flag, but is not exported in this image. That made it a bounded
> test of target-limited non-export identity recovery without relaxing the
> global resolver.
>
> Static selection pinned `tracefs_initialized=0xffffff800841b9bc` via
> `exact-leaf-map+xref+word-boundary`: export candidate count `0`, direct BL
> xrefs `2`, JOPP entry, source implementation
> `bool tracefs_initialized(void)` at `fs/tracefs/inode.c:619`, and
> `SAFE-SCALAR` call-safety. The next-symbol boundary is `trace_mount` at
> `+0x10`. The proof pinned the complete body plus guard:
> `0xf0015ea8 0x397eb100 0xd65f03c0 0x00be7bad`. The generic 64-byte
> classifier scan includes `trace_mount` after the boundary, so this proof
> treats the explicit 0x10 body/guard as the function-body authority.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, candidate helper `version/status` verification passed,
> explicit candidate `selftest` passed with `pass=11 warn=1 fail=0`, and REPL
> selftest returned `a90-repl-v2a1-selftest-pass`.
>
> The proof called `tracefs_initialized()` twice with no arguments. Returns
> were bool and stable: `0x1`, `0x1`. No runtime pointer was dereferenced by
> the host, no cleanup was required, and raw runtime values plus the KASLR
> slide stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `pass=11 warn=1 fail=0`.
> Rollback to v2321 completed with matching readback SHA, rollback helper
> `version/status` passed, final v2321 `version` reported
> `v2321-usb-clean-identity-rodata`, final standalone `selftest` passed with
> `pass=11 warn=1 fail=0`, and final bridge status was
> `connected-no-immediate-error`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-tracefs-initialized-20260701T085755Z/timeline.json`
> at `2026-07-01T09:02:04Z`: candidate flash helper `63.700s`,
> candidate selftest passed, REPL selftest `30.001s` host-observed, live proof
> `5.102s` host-observed, post-proof candidate selftest passed, rollback flash
> helper `64.460s`, and final v2321 selftest passed. The helper total rows are
> not additive; all serial bridge operations in the accepted live path were
> sequential.
>
> Function-map outcome: `tracefs_initialized` is promoted as live-proven only
> under the no-argument read-only tracefs registration contract: the pinned
> body performs a global-byte registration-state read and returns a stable
> bool. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_TRACEFS_INITIALIZED_2026-07-01.md`.

## ✅ DONE — REPL CPU mitigation policy live-call proof — `cpu_mitigations_off()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg CPU mitigation policy bool getter
>
> Codex selected `cpu_mitigations_off` from the remaining no-argument `cpu_*`
> advisory candidates after excluding hotplug, teardown, startup, and
> behavior-changing helpers. The selected target is a policy getter, not a CPU
> state transition helper.
>
> Static selection pinned `cpu_mitigations_off=0xffffff80080b5cbc` via
> `export-recovery` with map agreement, one export candidate, direct BL xrefs
> `4`, JOPP entry, leaf body, no in-body BL, and no argument dereference.
> Source declaration was `extern bool cpu_mitigations_off(void)` at
> `include/linux/cpu.h:216`; the Samsung source drop exposes the declaration,
> while static words pin the live leaf implementation:
> `0xb0012468 0xb9453108 0x7100011f 0x1a9f17e0 0xd65f03c0 0x00be7bad`.
> The next-symbol boundary is `cpu_mitigations_auto_nosmt` at `+0x18`.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, candidate helper health passed, candidate standalone
> `selftest` passed with `pass=11 warn=1 fail=0`, and REPL selftest returned
> `a90-repl-v2a1-selftest-pass`.
>
> The proof called `cpu_mitigations_off()` twice with no arguments. Returns
> were bool and stable: `0x0`, `0x0`. No runtime pointer was dereferenced by
> the host, no cleanup was required, and raw runtime values plus the KASLR
> slide stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `selftest pass=11 warn=1
> fail=0`. Rollback to v2321 completed with matching readback SHA, rollback
> helper `version/status` passed, final v2321 `version` reported
> `v2321-usb-clean-identity-rodata`, and final standalone `selftest` passed
> cleanly with `pass=11 warn=1 fail=0`. One combined final health capture had
> serial echo noise during the selftest command; the independent retry is the
> authoritative final health gate.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-cpu-mitigations-off-20260701T082237Z/timeline.json`
> at `2026-07-01T08:27:10Z`: candidate flash helper `64.756s`, REPL selftest
> `5.992s`, live proof `5.642s`, and rollback flash helper `63.699s`. The
> helper total rows are not additive; serial bridge commands in the proof path
> were sequential.
>
> Function-map outcome: `cpu_mitigations_off` is promoted as live-proven only
> under the no-argument read-only CPU mitigation policy contract: the pinned
> leaf body performs a global policy enum check and returns a stable bool.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CPU_MITIGATIONS_OFF_2026-07-01.md`.

## ✅ DONE — REPL RCU state live-call proof — `get_state_synchronize_rcu()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg RCU grace-period state getter
>
> Codex selected `get_state_synchronize_rcu` from the state-observation sweep
> as a new no-argument RCU state getter. The adjacent advisory-safe
> `get_net_ns_by_fd(int fd)` candidate stayed parked because it reaches
> fd-backed namespace lookup and `fput`, so it needs a stronger fd/refcount
> contract before being a clean one-target proof.
>
> Static selection pinned `get_state_synchronize_rcu=0xffffff8008150a74` via
> `export-recovery` with map agreement, one export candidate, direct BL xrefs
> `1`, JOPP entry, leaf body, no in-body BL, and no argument dereference.
> Source declaration was `unsigned long get_state_synchronize_rcu(void)` at
> `include/linux/rcutree.h:77`. The Samsung source drop also contains the
> `rcutiny.h` inline fallback but not the RCU implementation source file, so
> this proof pins the live rcutree implementation with static words:
> `0xf0015788 0xd5033bbf 0x91300108 0x910c2108 0xc8dffd00 0xd65f03c0 0xd503201f 0x00be7bad`.
> The next-symbol boundary is `cond_synchronize_rcu` at `+0x20`.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health passed. The first explicit
> candidate `selftest` capture timed out after serial `AT` marker loss and no
> complete body; after bridge restart, explicit candidate selftest passed
> cleanly with `pass=11 warn=1 fail=0`.
>
> The proof called `get_state_synchronize_rcu()` three times with no
> arguments. Returns were nondecreasing and stayed inside the bounded
> short-run delta contract: `0xe4a`, `0xe67`, `0xe7f`, max delta `0x35`.
> No runtime pointer was dereferenced by the host, no cleanup was required,
> and raw runtime values plus the KASLR slide stayed private/redacted.
>
> Post-proof candidate `selftest` passed with `selftest pass=11 warn=1
> fail=0`. Rollback to v2321 completed with matching readback SHA, rollback
> helper `version/status` passed, and final v2321 `version` reported
> `v2321-usb-clean-identity-rodata`. The first final v2321 `selftest` capture
> included `pass=11 warn=1 fail=0` but missed the END marker after serial
> `AT` echo; after bridge restart, final standalone `selftest` passed cleanly.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-get-state-synchronize-rcu-20260701T080141Z/timeline.json`
> at `2026-07-01T08:09:48Z`: baseline version `0.449s`, baseline status
> `1.051s`, baseline selftest `0.453s`, candidate flash helper `63.767s`,
> candidate explicit selftest first capture `120.194s` with marker-loss
> timeout, candidate selftest retry after bridge restart `0.455s`, live proof
> `5.893s`, post-proof candidate selftest `0.448s`, rollback flash helper
> `63.795s`, final v2321 version `0.451s`, final v2321 selftest first capture
> `120.143s` with missing END marker, and final v2321 selftest retry
> `0.459s`. The helper total rows are not additive; all serial bridge
> commands in this unit were sequential.
>
> Function-map outcome: `get_state_synchronize_rcu` is promoted as
> live-proven only under the no-argument read-only RCU state contract: the
> pinned leaf body performs the barrier/acquire-load path, returns an unsigned
> long state value, and the short repeated proof must be nondecreasing within
> the bounded delta. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_STATE_SYNCHRONIZE_RCU_2026-07-01.md`.

## ✅ DONE — REPL current fs-state live-call proof — `current_umask()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg current-task umask getter
>
> Codex selected `current_umask` as a current-task fs-state observation target,
> distinct from the global VFS counters proven in previous units. It extends
> the function map with a read-only getter for the calling task's `fs->umask`:
> `extern int current_umask(void)` from `include/linux/fs.h:2257`.
>
> Static selection pinned `current_umask=0xffffff80082d3a24` via
> `export-recovery` with map agreement, a single export candidate, direct BL
> xrefs `14`, JOPP entry, and a leaf body. The C1 gate classifies it as
> `SAFE-SCALAR`; source/ABI contract is no pointer args. The next-symbol
> boundary is `vfs_statfs` at `+0x18`; the static words pinned `mrs current`,
> `load fs`, `load umask`, `ret`, padding, and the final `0x00be7bad`
> boundary guard.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health passed. The first explicit
> candidate health attempt hit serial capture noise after valid `hide/version`
> content; the sequential retry passed `hide/version/status/selftest`.
>
> Two no-argument live calls returned `0x12` and `0x12`, within permission-bit
> range `0..0777` and stable across the short repeat. Raw runtime pointers and
> the slide stayed private/redacted.
>
> Post-proof `hide/status/selftest` passed with `selftest pass=11 warn=1
> fail=0` and `pstore entries=0`. Rollback to v2321 completed with matching
> readback SHA. Final explicit health first hit serial capture noise after the
> rollback helper verification; a later sequential `hide/version/status/selftest`
> retry passed and confirmed resident `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-current-umask-20260701T055733Z/timeline.json`:
> candidate flash helper `64.553s`, candidate flash start to boot ready `65s`,
> candidate explicit health initial `12.990s`, candidate explicit health retry
> `6.720s`, live proof `5.658s`, post-proof health `1.220s`, rollback flash
> helper `64.686s`, rollback flash start to boot ready `65s`, final health
> initial `16.308s`, final health retry `6.678s`, and candidate start to final
> health done approximately `218s`. The helper/start-to-boot rows are not
> additive; all serial bridge commands in this unit were sequential.
>
> Function-map outcome: `current_umask` is promoted as live-proven only under
> the no-argument current-fs read-only umask contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CURRENT_UMASK_2026-07-01.md`.

## ✅ DONE — REPL VFS dirty-inode live-call proof — `get_nr_dirty_inodes()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg VFS inode-state getter
>
> Codex selected `get_nr_dirty_inodes` as a VFS kernel-state observation target
> paired with, but distinct from, the already-proven `get_max_files`. It
> extends the function map with a read-only approximation of dirty inode count:
> `extern long get_nr_dirty_inodes(void)` from `fs/internal.h:146`.
>
> Static selection pinned `get_nr_dirty_inodes=0xffffff80082b1234` via
> `disasm-signature+xref+map` with direct BL xrefs `4` and JOPP entry. The C1
> gate classifies it as `SAFE-SCALAR`; source/ABI contract is no pointer args.
> The static implementation check verified `fs/inode.c` computes
> `get_nr_inodes() - get_nr_inodes_unused()` and clamps negative values to
> zero. The next-symbol boundary is `proc_nr_inodes` at `+0xf8`; the 62-word
> body, `cpumask_next` loop call sites, and final `0x00be7bad` boundary guard
> were pinned.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health passed. The first explicit
> candidate health attempt hit serial framing noise after `hide`; the
> sequential retry passed `hide/version/status/selftest`.
>
> Two no-argument live calls returned `0x69d9` and `0x69d9`, nonnegative and
> below the conservative sane bound. The contract allows short-repeat drift;
> this run happened to be stable. Raw runtime pointers and the slide stayed
> private/redacted.
>
> Post-proof `hide/status/selftest` passed with `selftest pass=11 warn=1
> fail=0` and `pstore entries=0`. Rollback to v2321 completed with matching
> readback SHA. Final explicit `hide/version/status/selftest` passed on the
> first attempt and confirmed resident `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-get-nr-dirty-inodes-20260701T054957Z/timeline.json`:
> candidate flash helper `64.623s`, candidate flash start to boot ready `65s`,
> candidate explicit health initial `12.529s`, candidate explicit health retry
> `6.734s`, live proof `4.824s`, post-proof health `1.236s`, rollback flash
> helper `63.669s`, rollback flash start to boot ready `64s`, final health
> `3.671s`, and candidate start to final health done approximately `187s`.
> The helper/start-to-boot rows are not additive; all serial bridge commands in
> this unit were sequential.
>
> Function-map outcome: `get_nr_dirty_inodes` is promoted as live-proven only
> under the no-argument read-only VFS dirty-inode approximation contract.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_NR_DIRTY_INODES_2026-07-01.md`.

## ✅ DONE — REPL VFS open-file-limit live-call proof — `get_max_files()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg VFS state getter
>
> Codex selected `get_max_files` as a VFS kernel-state observation target
> rather than another generic helper. It extends the function map with a
> read-only query for the kernel open-file table limit:
> `extern unsigned long get_max_files(void)` from `include/linux/fs.h:71`.
>
> Static selection pinned `get_max_files=0xffffff800829005c` via
> `export-recovery` with map agreement, a single export candidate, direct BL
> xrefs `1`, and JOPP entry. The C1 gate classifies it as `SAFE-SCALAR`;
> source/ABI contract is no pointer args. The static implementation check
> verified `fs/file_table.c` contains `get_max_files(void)` returning
> `files_stat.max_files`. The next-symbol boundary is `proc_nr_files` at
> `+0x18`; the 6-word body and final `0x00be7bad` boundary guard were pinned.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, and candidate helper health passed. The first explicit
> candidate health attempt hit serial `cmdv1AT` framing noise after `hide`;
> the sequential retry passed `hide/version/status/selftest`.
>
> The first proof attempt failed before any target call because `--source-root`
> pointed at the parent `workspace/private/inputs/kernel_source`, so the
> implementation check could not read `fs/file_table.c`. The successful retry
> used the concrete
> `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel`
> root. Two no-argument live calls then both returned `0x71c6a`, positive,
> below the conservative sane bound, and stable across the short repeat. Raw
> runtime pointers and the slide stayed private/redacted.
>
> Post-proof `hide/status/selftest` passed with `selftest pass=11 warn=1
> fail=0` and `pstore entries=0`. Rollback to v2321 completed with matching
> readback SHA. Final explicit health first showed the `version` body but lost
> the END marker to serial framing noise; a later sequential
> `hide/version/status/selftest` retry passed and confirmed resident
> `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-get-max-files-20260701T054248Z/timeline.json`:
> candidate flash helper `65.663s`, candidate flash start to boot ready `66s`,
> candidate explicit health initial `12.567s`, candidate explicit health retry
> `6.691s`, live proof initial `2.666s`, live proof retry `5.410s`,
> post-proof health `1.231s`, rollback flash helper `64.683s`, rollback flash
> start to boot ready `65s`, final health initial `12.346s`, final health
> retry `6.684s`, and candidate start to final health done approximately
> `274s`. The helper/start-to-boot rows are not additive; all serial bridge
> commands in this unit were sequential.
>
> Function-map outcome: `get_max_files` is promoted as live-proven only under
> the no-argument read-only VFS open-file-limit contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_MAX_FILES_2026-07-01.md`.

## ✅ DONE — REPL memory-state result-slot live-call proof — `si_meminfo()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — owned `struct sysinfo` result slot
>
> Codex selected `si_meminfo` as a post-saturation kernel-state observation
> target rather than another scalar lib/time helper. It extends the function
> map with an owned result-slot memory-state vector: `extern void
> si_meminfo(struct sysinfo * val)` from `include/linux/mm.h:2208`.
>
> Static selection pinned `si_meminfo=0xffffff800820deb4` via
> `export-recovery` with map agreement, a single export candidate, direct BL
> xrefs `8`, and JOPP entry. The C1 gate classifies it as
> `SAFE-WITH-VALID-PTR` only when x0 is an owned `struct sysinfo` result slot;
> the next-symbol boundary is `show_free_areas` at `+0x78`. The body was
> pinned with 30 static words, including the entry guard and final
> `0x00be7bad` boundary guard.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, candidate helper health passed, and the target proof passed.
> The proof allocated an owned result slot with `__kmalloc`, prefilled it and
> a trailing canary, called `si_meminfo(result_slot)`, peeked the slot, then
> freed it with `kfree`.
>
> Public observed fields were `totalram_pages=0x14ffeb`,
> `freeram_pages=0x126e83`, `sharedram_pages=0x1528`,
> `bufferram_pages=0x352`, `totalhigh_pages=0x0`,
> `freehigh_pages=0x0`, and `mem_unit=0x1000`. The proof verified positive
> total RAM, free/shared/buffer pages not above total RAM, zero highmem fields
> on this arm64 image, `mem_unit=4096`, trailing canary preservation, and
> `kfree` cleanup OK. Raw runtime pointers, the slide, and owned result-slot
> pointer stayed private/redacted.
>
> Candidate explicit health first hit serial `ATATAT` framing noise on
> `version`, then a sequential `hide/version/status/selftest` retry passed.
> Post-proof `hide/status/selftest` passed with `selftest pass=11 warn=1
> fail=0` and `pstore entries=0`. Rollback to v2321 completed with matching
> readback SHA. Final explicit health first passed `version` and then hit
> serial `ATAT` framing noise on `status`; a later sequential
> `hide/version/status/selftest` retry passed and confirmed resident
> `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-si-meminfo-20260701T053520Z/timeline.json`:
> candidate flash helper `63.651s`, candidate flash start to boot ready `64s`,
> candidate explicit health initial `10.031s`, candidate explicit health retry
> `3.680s`, live proof `24.898s`, post-proof health `1.232s`, rollback flash
> helper `64.509s`, rollback flash start to boot ready `65s`, final health
> initial `10.845s`, final health retry `5.689s`, and candidate start to final
> health done approximately `216s`. The helper/start-to-boot rows are not
> additive; all serial bridge commands in this unit were sequential.
>
> Function-map outcome: `si_meminfo` is promoted as live-proven only under the
> owned kmalloc `struct sysinfo` result-slot contract with trailing canary and
> `kfree` cleanup. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SI_MEMINFO_2026-07-01.md`.

## ✅ DONE — REPL NCM intermediate-timeout live-call proof — `get_intermediate_timeout()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg NCM timeout state
>
> Codex selected `get_intermediate_timeout` as a post-saturation state getter
> rather than another generic lib/time helper. A source-backed advisory sweep
> found `extern unsigned int get_intermediate_timeout(void)` in
> `include/net/ncm.h:140`; nearby apparent candidates stayed parked because
> `get_debug_reset_header` allocates/reads/prints/frees, `get_empty_filp`
> reaches file allocation plus credential/security/RCU paths, and
> `get_dump_page` reaches `__get_user_pages`.
>
> Static selection pinned `get_intermediate_timeout=0xffffff80099a5ff4` via
> `export-recovery` with map agreement, direct BL xrefs `4`, no pointer args,
> and `SAFE-SCALAR` C1 gate after seeding. The next-symbol boundary is
> `knox_collect_conntrack_data` at `+0x10`; static word checks pinned the full
> leaf body and guard: `0x90010268`, `0xb9495100`, `0xd65f03c0`,
> `0x00be7bad`.
>
> The live proof obeyed the flash gate: rollback/fallback/TWRP artifacts were
> confirmed, baseline v2321 `version/status/selftest` passed, the exact
> v1-repl candidate (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`)
> flashed through `native_init_flash.py` with matching pushed-image and
> readback SHA, candidate helper health passed, and the target proof passed.
> Two no-argument calls both returned `0x0`, stable and inside the
> `unsigned int` timeout range. Raw runtime pointers and the slide stayed
> private/redacted.
>
> A host-side mistake launched the initial candidate explicit `hide/selftest`
> health command in parallel with the live proof; `hide` hit serial `AT`
> framing noise while `selftest` passed. The trusted health gate is the later
> sequential post-proof rerun, which passed `hide/selftest/status` with
> `selftest pass=11 warn=1 fail=0` and `pstore entries=0`. Rollback to v2321
> completed with matching readback SHA. Final explicit health first hit serial
> `ATAT` framing noise on `version`, then `hide` plus a short settle retry
> passed `version/selftest/status`, confirming resident
> `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-get-intermediate-timeout-20260701T052423Z/timeline.json`:
> candidate flash helper `65.532s`, candidate flash start to boot ready `66s`,
> candidate explicit health initial `14s`, live proof `14s`, post-proof health
> `4s`, rollback flash helper `64.278s`, rollback flash start to boot ready
> `64s`, final health initial `11s`, final health retry `4s`, and candidate
> start to final health done `211s`.
>
> Function-map outcome: `get_intermediate_timeout` is promoted as live-proven
> only under the no-argument read-only NCM intermediate-timeout contract: the
> current image body is the pinned `adrp; ldr w0; ret` leaf global-load, and
> return values must be stable `unsigned int` values in `0..0xffffffff`. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_INTERMEDIATE_TIMEOUT_2026-07-01.md`.

## ✅ DONE — REPL scheduler IO-wait live-call proof — `nr_iowait()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg scheduler IO-wait state
>
> Codex selected `nr_iowait` as the next one-target recovery from the earlier
> scheduler-counter batch attempts, which had recorded `nr_iowait` as
> `not called`. Later one-target recovery runs promoted only
> `nr_context_switches`, `nr_processes`, and `nr_running`; this run used the
> checked `call-proof` CLI directly and called only `nr_iowait()`.
>
> Static selection pinned `nr_iowait=0xffffff80080ee024` via
> `disasm-signature+xref+map`, source declaration
> `extern unsigned long nr_iowait(void)` at `include/linux/sched/stat.h:21`,
> no pointer args, direct BL xrefs `2`, next-symbol boundary `nr_iowait_cpu`
> at `+0xa0`, and `SAFE-SCALAR` C1 gate. The static word checks pinned the
> 40-word body, including the `cpumask_next` loop over possible CPUs and
> per-CPU IO-wait count load/add sequence. Same-shape neighbor `nr_running` is
> already promoted; `nr_iowait_cpu`, `single_task_running`, and `si_swapinfo`
> stayed `DENY`.
>
> The live proof obeyed the flash gate: candidate/rollback/fallback SHA values
> and TWRP were confirmed; baseline v2321 `version/status/selftest` passed; the
> v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA; candidate
> helper health passed; and `nr_iowait()` passed. Explicit candidate
> `hide/selftest` passed on the first attempt; a stray serial `A` appeared after
> the protocol END marker but did not affect rc. Two target reads both returned
> `0x0` (`delta=0x0`), inside the sane count range, valid for an idle IO-wait
> count, and stable across the short repeat. Raw runtime pointers and the slide
> stayed private/redacted.
>
> Post-proof `status/selftest` stayed `fail=0`, with `pstore entries=0` in the
> status inventory. Rollback to v2321 completed with matching readback SHA. Final
> resident `version/selftest/status` passed after one settled `hide` serial
> resync retry, with `selftest pass=11 warn=1 fail=0` and `version` confirming
> `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-nr-iowait-20260701T050434Z/timeline.json`:
> candidate flash helper `64.754s`, candidate flash start to boot ready `65s`,
> candidate explicit health `1s`, live proof `6s`, post-proof health `1s`,
> rollback flash helper `66.103s`, rollback flash start to boot ready `67s`,
> final health initial `11s`, final health retry `2s`, and candidate start to
> final health done `216s`.
>
> Function-map outcome: `nr_iowait` is promoted as live-proven only under the
> no-argument read-only scheduler IO-wait count contract: return value must be a
> sane nonnegative `unsigned long` in this native-init proof environment and
> stable or bounded-drift across a short repeated call. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_NR_IOWAIT_2026-07-01.md`.

## ✅ DONE — REPL scheduler runnable-count live-call proof — `nr_running()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg scheduler runnable-count state
>
> Codex selected `nr_running` as the next one-target recovery from the earlier
> scheduler-counter batch attempts, which had recorded `nr_running` as
> `not called`. Later one-target recovery runs promoted only
> `nr_context_switches` and `nr_processes`; this run used the checked
> `call-proof` CLI directly and called only `nr_running()`.
>
> Static selection pinned `nr_running=0xffffff80080edebc` via
> `disasm-signature+xref+map`, source declaration
> `extern unsigned long nr_running(void)` at `include/linux/sched/stat.h:19`,
> no pointer args, direct BL xrefs `4`, next-symbol boundary
> `single_task_running` at `+0xa0`, and `SAFE-SCALAR` C1 gate. The static word
> checks pinned the 40-word body, including the `cpumask_next` loop over
> possible CPUs and per-CPU runnable-count load/add sequence. Same-shape
> neighbor `nr_iowait` stayed safe but uncalled/unpromoted in this unit;
> `nr_iowait_cpu`, `single_task_running`, and `si_swapinfo` stayed `DENY`.
>
> The live proof obeyed the flash gate: candidate/rollback/fallback SHA values
> and TWRP were confirmed; baseline v2321 `version/status/selftest` passed; the
> v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA; candidate
> helper health passed; and `nr_running()` passed. The first explicit
> post-flash `hide/selftest` hit `ATAT` serial framing noise, then a `12s` settle
> plus bridge status check and explicit `selftest` passed. Two target reads both
> returned `0x1` (`delta=0x0`), positive, inside the sane count range, and
> stable across the short repeat. Raw runtime pointers and the slide stayed
> private/redacted.
>
> Post-proof `status/selftest` stayed `fail=0`, with `pstore entries=0` in the
> status inventory. Rollback to v2321 completed with matching readback SHA. Final
> resident `version/selftest/status` passed after one settled `hide` serial
> resync retry, with `selftest pass=11 warn=1 fail=0` and `version` confirming
> `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-nr-running-20260701T045709Z/timeline.json`:
> candidate flash helper `64.761s`, candidate flash start to boot ready `65s`,
> candidate explicit health initial `11s`, candidate explicit health retry `1s`,
> live proof `6s`, post-proof health `1s`, rollback flash helper `64.784s`,
> rollback flash start to boot ready `64s`, final health initial `11s`, final
> health retry `2s`, and candidate start to final health done `252s`.
>
> Function-map outcome: `nr_running` is promoted as live-proven only under the
> no-argument read-only scheduler runnable-count contract: return value must be a
> sane positive `unsigned long` in this native-init proof environment and stable
> or bounded-drift across a short repeated call. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_NR_RUNNING_2026-07-01.md`.

## ✅ DONE — REPL scheduler process-count live-call proof — `nr_processes()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg scheduler process-count state
>
> Codex selected `nr_processes` as the next one-target recovery from the earlier
> scheduler-counter batch attempts, which had stopped before any target call.
> This run used the checked `call-proof` CLI directly and called only
> `nr_processes()`.
>
> Static selection pinned `nr_processes=0xffffff80080ae02c` via
> `disasm-signature+xref+map`, source declaration `extern int nr_processes(void)`
> at `include/linux/sched/stat.h:18`, no pointer args, direct BL xrefs `1`,
> next-symbol boundary `arch_release_task_struct` at `+0xa0`, and `SAFE-SCALAR`
> C1 gate. The static word checks pinned the 40-word body, including the
> `cpumask_next` loop over possible CPUs and per-CPU process-count load/add
> sequence. Neighboring `nr_iowait_cpu`, `single_task_running`, and
> `si_swapinfo` stayed `DENY`.
>
> The live proof obeyed the flash gate: candidate/rollback/fallback SHA values
> and TWRP were confirmed; baseline v2321 `version/status/selftest` passed; the
> v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA; candidate
> helper health passed; and `nr_processes()` passed. The first explicit
> post-flash `hide/selftest` hit `ATAT` serial framing noise, then a `12s` settle
> plus bridge status check and explicit `selftest` passed. Two target reads both
> returned `0x1c1` (`delta=0x0`), positive, inside the sane count range, and
> stable across the short repeat. Raw runtime pointers and the slide stayed
> private/redacted.
>
> Post-proof `status/selftest` stayed `fail=0`, with `pstore entries=0` in the
> status inventory. Rollback to v2321 completed with matching readback SHA. Final
> resident `version/selftest/status` passed after one settled `hide` serial
> resync retry, with `selftest pass=11 warn=1 fail=0` and `version` confirming
> `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-nr-processes-20260701T044817Z/timeline.json`:
> candidate flash helper `72s`, candidate flash start to boot ready `72s`, live
> proof `6s`, post-proof health `2s`, rollback flash helper `73s`, rollback flash
> start to boot ready `73s`, final health total `66s`, final health retry `1`,
> and candidate start to final health done `300s`.
>
> Function-map outcome: `nr_processes` is promoted as live-proven only under the
> no-argument read-only scheduler process-count contract: return value must be a
> sane positive `int` in this native-init proof environment and stable or
> bounded-drift across a short repeated call. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_NR_PROCESSES_2026-07-01.md`.

## ✅ DONE — REPL scheduler context-switch counter live-call proof — `nr_context_switches()` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg scheduler counter state
>
> Codex selected `nr_context_switches` as a fresh one-target recovery from the
> earlier scheduler-counter batch attempts, which had both stopped before any
> target call due host-side wrapper/bridge issues. This run used the checked
> `call-proof` CLI directly and called only `nr_context_switches()`.
>
> Static selection pinned `nr_context_switches=0xffffff80080edf84` via
> `disasm-signature+xref+map`, source declaration
> `extern unsigned long long nr_context_switches(void)` at
> `include/linux/kernel_stat.h:52`, no pointer args, direct BL xrefs `4`,
> next-symbol boundary `nr_iowait` at `+0xa0`, and `SAFE-SCALAR` C1 gate. The
> static word checks pinned the 40-word body, including the `cpumask_next` loop
> over possible CPUs and per-CPU counter load/add sequence. Neighboring
> `nr_iowait_cpu`, `single_task_running`, and `si_swapinfo` stayed `DENY`.
>
> The live proof obeyed the flash gate: candidate/rollback/fallback SHA values
> and TWRP were confirmed; baseline v2321 `version/status/selftest` passed; the
> v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA; candidate
> helper health passed; and `nr_context_switches()` passed. The first explicit
> post-flash `hide` hit serial framing noise, then a `12s` settle plus bridge
> status check and explicit `selftest` passed. Two target reads returned
> `0x1ff6a` then `0x201b9` (`delta=0x24f`), both inside the sane counter range
> and nondecreasing. Raw runtime pointers and the slide stayed private/redacted.
>
> Post-proof `status/selftest` stayed `fail=0`, with `pstore entries=0` in the
> status inventory. Rollback to v2321 completed with matching readback SHA. Final
> resident `version/selftest/status` passed after one `hide` serial resync retry,
> with `selftest pass=11 warn=1 fail=0` and `version` confirming
> `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-nr-context-switches-20260701T043820Z/timeline.json`:
> candidate flash helper `65s`, candidate flash start to boot ready `72s`, live
> proof `6s`, post-proof health `1s`, rollback flash helper `64s`, rollback
> flash start to boot ready `64s`, final health total `19s`, final health retry
> `1`, and candidate start to final health done `446s`.
>
> Function-map outcome: `nr_context_switches` is promoted as live-proven only
> under the no-argument read-only scheduler context-switch counter contract:
> return value must be a sane `unsigned long long` and nondecreasing across a
> short repeated call. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_NR_CONTEXT_SWITCHES_2026-07-01.md`.

## ✅ DONE — REPL boot-time result-slot live-call proof — `getboottime64(struct timespec64 *ts)` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — owned boot-time `timespec64` result slot
>
> Codex selected `getboottime64` as the next timekeeping result-slot proof after
> `getnstimeofday64`: instead of realtime wall-clock time, this target writes boot
> wall-clock state. The trusted contract is narrow: x0 must be an owned `kmalloc`
> result slot for `struct timespec64` plus trailing canary, each call is bracketed
> by same-session `ktime_get_real_seconds()` and `ktime_get_seconds()` anchors, and
> the slot is freed with `kfree`.
>
> Static selection pinned `getboottime64=0xffffff800816181c` via `export-recovery`
> with map agreement, source declaration `extern void getboottime64(struct timespec64 *ts)`
> at `include/linux/timekeeping.h:49`, direct BL xrefs `3`, no pre-call x0 deref rows,
> result-slot access accepted only under `SAFE-WITH-VALID-PTR`, and next-symbol
> boundary `get_seconds` at `+0x40`. The static word checks pinned the full 16-word
> body through the guard, including `ns_to_timespec` and final `stp x0, x1, [x19]`.
> Anchors `ktime_get_real_seconds=0xffffff800815f694` and
> `ktime_get_seconds=0xffffff800815f66c` stayed previously proven `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate: candidate/rollback/fallback SHA values and
> TWRP were confirmed; baseline v2321 `version/status/selftest` passed; the v1-repl
> candidate (`b846ae9f...`) flashed with matching readback SHA; candidate health
> passed; and `getboottime64()` passed. Read 1 used realtime anchors
> `0x5a524417..0x5a52441b` and monotonic anchors `0x6c..0x70`, wrote
> `tv_sec=0x5a5243ab`, `tv_nsec=0x0ec384f8`, and matched boot anchor range
> `0x5a5243a4..0x5a5243b2`. Read 2 used realtime anchors
> `0x5a52441e..0x5a524423` and monotonic anchors `0x74..0x77`, wrote the same
> `tv_sec/tv_nsec`, and matched the same boot anchor range. Both reads had valid
> nsec range, stable repeated total nsec, changed result-slot bytes, preserved
> canary, and successful `kfree` cleanup. Raw runtime pointers and the slide stayed
> private/redacted.
>
> Post-proof `status/selftest` stayed `fail=0`. Rollback to v2321 completed with
> matching readback SHA. Final resident `version/selftest` passed after one `hide`
> serial resync retry, with `selftest pass=11 warn=1 fail=0` and `version`
> confirming `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-getboottime64-20260701T042618Z/timeline.json`:
> candidate flash helper `63s`, candidate flash start to boot ready `70s`, live
> proof `21s`, post-proof health `1s`, rollback flash helper `64s`, rollback flash
> start to boot ready `64s`, final health total `23s`, final health retry `1`, and
> candidate start to final health done `285s`.
>
> Function-map outcome: `getboottime64` is promoted as live-proven only under the
> owned-boot-time-`timespec64` result-slot contract, with
> `ktime_get_real_seconds() - ktime_get_seconds()` used as same-session anchor and
> `kfree` cleanup required. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GETBOOTTIME64_2026-07-01.md`.

## ✅ DONE — REPL realtime result-slot live-call proof — `getnstimeofday64(struct timespec64 *tv)` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — owned realtime `timespec64` result slot
>
> Codex selected `getnstimeofday64` as a one-target post-saturation proof that expands the
> timekeeping map from scalar seconds and monotonic result-slot reads into realtime wall-clock
> `struct timespec64` writes. The trusted contract is narrow: x0 must be an owned `kmalloc`
> result slot for `struct timespec64` plus trailing canary, each target call is bracketed by
> same-session `ktime_get_real_seconds()` anchors, and the slot is freed with `kfree`.
>
> Static selection pinned `getnstimeofday64=0xffffff800815f174` via `export-recovery`
> with map agreement, source declaration `extern void getnstimeofday64(struct timespec64 *tv)`
> at `include/linux/timekeeping.h:48`, direct BL xrefs `88`, JOPP entry, early x0-derived
> result-slot access accepted only under `SAFE-WITH-VALID-PTR`, and next-symbol boundary
> `ktime_get` at `+0x128`. The static word checks pinned the prologue, clocksource read
> springboard, result-slot stores including final `stp x9, x8, [x19]`, return, stack-check
> path, and guard. Anchor `ktime_get_real_seconds=0xffffff800815f694` stayed the previously
> proven `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate: candidate/rollback/fallback SHA values and TWRP were
> confirmed; baseline v2321 `version/status/selftest` passed; the v1-repl candidate
> (`b846ae9f...`) flashed with matching readback SHA; candidate health passed after one
> serial resync; and `getnstimeofday64()` passed. Read 1 was bracketed by anchors
> `0x5a524059..0x5a52405d` and wrote `tv_sec=0x5a524059`, `tv_nsec=0x232e4641`.
> Read 2 was bracketed by anchors `0x5a524060..0x5a524064` and wrote
> `tv_sec=0x5a524061`, `tv_nsec=0x0e3e62b1`. Both reads had valid nsec range,
> anchor-range seconds, nondecreasing total ns, changed result-slot bytes, preserved canary,
> and successful `kfree` cleanup. Raw runtime pointers and the slide stayed private/redacted.
>
> Post-proof `status/selftest` stayed `fail=0`. A post-proof `busybox dmesg` log probe exposed
> an `a90_android_exe` `subsystem_put()` WARN on the `esoc0` close path during log collection;
> follow-up selftest still passed and the trace was outside the REPL target path, so this is
> recorded as a residual native-exec/log-probe warning rather than a `getnstimeofday64`
> contract failure. Rollback to v2321 completed with matching readback SHA. Final resident
> `selftest/version` passed after `hide` serial resync, with `selftest pass=11 warn=1 fail=0`
> and `version` confirming `v2321-usb-clean-identity-rodata`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-getnstimeofday64-20260701T040907Z/timeline.json`:
> candidate flash helper `64s`, candidate flash start to boot ready `71s`, live proof `21s`,
> post-proof health/log probe `7s`, rollback flash helper `64s`, rollback flash start to boot
> ready `75s`, final health total `75s`, final health retry `2s`, and candidate start to
> final health done `433s`.
>
> Function-map outcome: `getnstimeofday64` is promoted as live-proven only under the
> owned-realtime-`timespec64` result-slot contract, with `ktime_get_real_seconds()` used as
> same-session anchor and `kfree` cleanup required. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GETNSTIMEOFDAY64_2026-07-01.md`.

## ✅ DONE — REPL timekeeping aggregate-return live-call proof — `current_kernel_time64()` x0 tv_sec promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — no-arg `timespec64` seconds field
>
> Codex selected `current_kernel_time64` from the timekeeping neighborhood as a post-saturation
> pivot: unlike the already-proven scalar seconds getters, this function returns a
> `struct timespec64` aggregate. The current v1-repl call ABI captures x0 only, so the promoted
> contract is intentionally narrow: `current_kernel_time64()` is trusted only for the x0
> `tv_sec` field, not for x1 `tv_nsec`.
>
> Static selection pinned `current_kernel_time64=0xffffff8008161894` via `export-recovery`
> with map agreement, source declaration `struct timespec64 current_kernel_time64(void)` at
> `include/linux/timekeeping.h:27`, direct BL xrefs `26`, JOPP entry, leaf shape, no arg
> deref, full 20-word body match, and next-symbol boundary `get_monotonic_coarse64` at
> `+0x50`. The anchor `ktime_get_real_seconds=0xffffff800815f694` remained the previously
> proven `SAFE-SCALAR` realtime-seconds getter.
>
> The live proof obeyed the flash gate: preflight confirmed candidate/rollback/fallback SHA
> values, TWRP, bridge, and baseline v2321 health; the v1-repl candidate (`b846ae9f...`)
> flashed with matching readback SHA; candidate explicit health passed after one serial
> END-marker retry; and `current_kernel_time64()` passed. Anchor values were
> `ktime_get_real_seconds() before=0x5a523ab0` and `after=0x5a523ab2`; two target x0
> returns were `0x5a523ab1` and `0x5a523ab2`, nonnegative, nondecreasing, and inside the
> anchor range. Raw runtime pointers and the slide stayed private/redacted. Post-proof
> selftest stayed `fail=0`; rollback to v2321 completed with matching readback SHA; final
> `version/status/selftest` passed after `hide` serial resync with
> `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-current-kernel-time64-20260701T034714Z/timeline.json`:
> candidate flash helper `63.640s`, candidate health retry total `30s`, live proof `7s`,
> post-proof candidate health `1s`, rollback flash helper `63.555s`, final health retry
> total `51s`, and candidate start to final health done `244s`.
>
> Function-map outcome: `current_kernel_time64` is promoted as live-proven only under the
> no-argument `timespec64.tv_sec` x0 contract, with `ktime_get_real_seconds()` used as a
> same-session anchor. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CURRENT_KERNEL_TIME64_2026-07-01.md`.

## ✅ DONE — REPL aggregate-return pair live-call proof — `current_kernel_time64()` x0/x1 promoted

> ### ✅ STATUS (2026-07-03 live-proven, rolled back cleanly) — same-call `timespec64` return pair
>
> Codex closed the REPL ABI-shape gap by adding a deliberately narrow call-pair
> v1-repl companion image. The normal v1-repl image remains the resident default;
> this image keeps the same magic/op layout but prints `R%llx:%llx` after `op3`
> so a small arm64 aggregate return can be captured as post-call x0:x1.
>
> Static gate pinned `current_kernel_time64=0xffffff8008161894` via
> `export-recovery` with map agreement, source declaration
> `struct timespec64 current_kernel_time64(void)`, no pointer args, `SAFE-SCALAR`
> callability, 20-word body match, and next-symbol boundary
> `get_monotonic_coarse64` at `+0x50`. The anchor
> `ktime_get_real_seconds=0xffffff800815f694` remained the same-session realtime
> seconds bound.
>
> The candidate call-pair image
> (`boot_linux_tier2_repl_v1_call_pair.img`,
> SHA256 `2c9c3a1638a98fc134158f49de80d1501f0d1eab50e59e828dc8d4b853e3c495`)
> flashed through `native_init_flash.py` with matching readback SHA. Live proof
> returned two valid pairs: x0 values `0x5a545b2f` and `0x5a545b30`, x1 values
> `0x389fd96d` and `0x1c03a16d`, with `tv_nsec <= 999999999`, nondecreasing
> total time, and x0 bounded by `ktime_get_real_seconds()` anchors
> `0x5a545b2f..0x5a545b30`. Post-proof health stayed `fail=0`; rollback to
> v2321 completed through the checked helper with matching readback SHA; final
> v2321 `version/status/selftest` passed after one serial-noise selftest retry
> (`selftest pass=11 warn=1 fail=0`).
>
> Function-map outcome: `current_kernel_time64` is now promoted under the full
> no-argument `timespec64` return contract: x0=`tv_sec`, x1=`tv_nsec`, captured
> from the same call by the call-pair REPL variant. This closes the struct-return
> ABI representative required by the 2026-07-03 REPL finish-line steer. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_CURRENT_KERNEL_TIME64_RETURN_PAIR_2026-07-03.md`.

## ✅ DONE — REPL pid current-namespace live-call proof — `pid_vnr(init_task->thread_pid)` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — borrowed `struct pid *` to current-namespace `pid_t`
>
> Codex selected `pid_vnr` from the same pid namespace neighborhood after
> `task_active_pid_ns(init_task)` and `pid_nr_ns(init_task->thread_pid, active_ns)` proved the
> direct `init_task->thread_pid` and active namespace observation path. The proof calls only
> `pid_vnr(init_task->thread_pid)`, where the pointer is read directly from the verified
> global `init_task` state immediately before the call. The pointer is borrowed, not owned,
> not freed, and not generalized to arbitrary pid objects.
>
> Static selection pinned `pid_vnr=0xffffff80080d8414` via `export-recovery` with map agreement,
> source declaration `pid_t pid_vnr(struct pid *pid)` at `include/linux/pid.h:181`, direct BL
> xrefs `27`, JOPP entry, leaf shape, and next-symbol boundary `__task_pid_nr_ns` at `+0x58`.
> The pinned body reads the current task namespace internally through `sp_el0`, then validates
> the passed pid's level and namespace before returning `pid->numbers[level].nr`. The
> call-safety gate classifies it as `SAFE-WITH-VALID-PTR` only when x0 is
> `init-task-thread_pid-struct-pid`.
>
> The live proof obeyed the flash gate: preflight confirmed candidate/rollback/fallback SHA
> values and baseline v2321 health, the v1-repl candidate (`b846ae9f...`) flashed with matching
> readback SHA, candidate health retry passed after serial framing noise, and
> `pid_vnr(init_task->thread_pid)` passed. Direct observation found `pid_level=0`,
> `namespace_level=0`, and expected pid nr `0x0`; two calls returned `0x0`. Because
> `pid_vnr` obtains current internally, the current namespace match is recorded as
> `inferred-by-return-equality-not-directly-peeked`. Raw pointer values and the slide stayed
> private/redacted. Post-proof selftest stayed `fail=0`; rollback to v2321 completed with
> matching readback SHA; final `status` passed with `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-pid-vnr-20260701T032646Z/timeline.json`:
> candidate flash helper `65.747s`, candidate boot-ready after helper done `16.0s`,
> candidate health retry `0.0s`, live proof `8.0s`, post-proof candidate health `1.0s`,
> rollback flash helper `63.694s`, rollback boot-ready after helper done `9.0s`, final
> status health `1.0s`, and candidate start to final status done `216.0s`.
>
> Function-map outcome: `pid_vnr` is promoted as live-proven only under the
> `pid_vnr(init_task->thread_pid)` borrowed-pid/current-namespace contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_PID_VNR_2026-07-01.md`.

## ✅ DONE — REPL pid/namespace two-pointer live-call proof — `pid_nr_ns(init_task->thread_pid, active_ns)` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — borrowed `struct pid *` + borrowed `pid_namespace *`
>
> Codex selected `pid_nr_ns` from the same task/pid namespace neighborhood after
> `task_active_pid_ns(init_task)` proved the active namespace derivation path. The proof calls only
> `pid_nr_ns(init_task->thread_pid, active_ns)`, where both pointers are read directly from the
> verified global `init_task` state immediately before the call. Neither pointer is owned, freed, or
> generalized to arbitrary pid/task objects.
>
> Static selection pinned `pid_nr_ns=0xffffff80080d83d4` via `export-recovery` with map agreement,
> source declaration `pid_t pid_nr_ns(struct pid *pid, struct pid_namespace *ns)` at
> `include/linux/pid.h:180`, direct BL xrefs `16`, JOPP entry, leaf shape, and next-symbol boundary
> `pid_vnr` at `+0x40`. The pinned body reads `ns->level` (`ldr w8,[x1,#2096]`), `pid->level`
> (`ldr w9,[x0,#4]`), verifies the level and namespace match, then returns
> `pid->numbers[level].nr` (`ldr w0,[x8,#72]`). The call-safety gate classifies it as
> `SAFE-WITH-VALID-PTR` only when x0 is `init-task-thread_pid-struct-pid` and x1 is
> `init-task-active-pid-namespace`.
>
> The live proof obeyed the flash gate: preflight confirmed candidate/rollback/fallback SHA values
> and baseline v2321 health, the v1-repl candidate (`b846ae9f...`) flashed with matching readback
> SHA, candidate health retry passed after serial framing noise, and
> `pid_nr_ns(init_task->thread_pid, active_ns)` passed. Direct observation found `pid_level=0`,
> `namespace_level=0`, and expected pid nr `0x0`; two calls returned `0x0`. Raw pointer values and
> the slide stayed private/redacted. Post-proof selftest stayed `fail=0`; rollback to v2321
> completed with matching readback SHA; final `version/status/selftest` retry passed with
> `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-pid-nr-ns-20260701T031018Z/timeline.json`:
> candidate flash helper `64.749s`, candidate explicit health initial attempt `31.0s`,
> candidate health retry `2.0s`, live proof `9.0s`, post-proof candidate health `1.0s`,
> rollback flash helper `63.839s`, final health initial attempt `31.0s`, final health retry
> `2.0s`, and candidate start to final health retry done `270.0s`.
>
> Function-map outcome: `pid_nr_ns` is promoted as live-proven only under the
> `pid_nr_ns(init_task->thread_pid, active_ns)` borrowed-pid / borrowed-namespace contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_PID_NR_NS_2026-07-01.md`.

## ✅ DONE — REPL borrowed namespace-pointer live-call proof — `task_active_pid_ns(init_task)` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — borrowed global `task_struct *` to borrowed `pid_namespace *`
>
> Codex selected `task_active_pid_ns` to extend the REPL proof map beyond scalar field getters:
> the proof calls only `task_active_pid_ns(init_task)`, where `init_task` is the verified global
> data symbol, borrowed/read-only, never freed, and not a general arbitrary task pointer. The
> returned `struct pid_namespace *` is also borrowed: it is compared for identity only, not
> dereferenced or freed in the public proof.
>
> Static selection pinned `task_active_pid_ns=0xffffff80080d7e84` via `export-recovery` with map
> agreement, source declaration
> `extern struct pid_namespace * task_active_pid_ns(struct task_struct *tsk)` at
> `include/linux/pid_namespace.h:107`, direct BL xrefs `31`, JOPP entry, leaf shape, and
> next-symbol boundary `attach_pid` at `+0x28`. The pinned instruction path is
> `ldr x8,[x0,#1824]`, `cbz x8`, `ldr w9,[x8,#4]`, `add x8,x8,x9,lsl #5`,
> `ldr x0,[x8,#80]`, `ret`. The call-safety gate classifies it as `SAFE-WITH-VALID-PTR`
> only when x0 is `global-init_task-task_struct`.
>
> The live proof obeyed the flash gate: preflight confirmed candidate/rollback/fallback SHA values
> and baseline v2321 health, the v1-repl candidate (`b846ae9f...`) flashed with matching readback
> SHA, candidate health passed, and `task_active_pid_ns(init_task)` passed. The proof first read
> `init_task->thread_pid` at offset `0x720`, read `pid->level` at `0x4` (`pid_level=0`), then
> read the expected namespace pointer through `thread_pid + 0x50 + (level << 5)`, matching the
> verified disassembly. Two calls returned the same borrowed pointer as the direct observation;
> raw pointer values and the slide stayed private/redacted. Post-proof selftest stayed `fail=0`;
> rollback to v2321 completed with matching readback SHA; final `version/status/selftest` passed
> with `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-task-active-pid-ns-20260701T025649Z/timeline.json`:
> candidate flash helper `63.727s`, candidate explicit health `1.0s`, live proof `7.0s`,
> post-proof candidate health `1.0s`, rollback flash helper `65.324s`, final explicit health
> `1.0s`, and candidate start to final health done `178.0s`.
>
> Function-map outcome: `task_active_pid_ns` is promoted as live-proven only under the
> `task_active_pid_ns(init_task)` borrowed-global-task / borrowed-pid-namespace contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_TASK_ACTIVE_PID_NS_2026-07-01.md`.

## ✅ DONE — REPL struct-pointer live-call proof — `task_prio(init_task)` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — borrowed global `task_struct *` getter
>
> Codex selected `task_prio` to extend the REPL proof map beyond saturated no-argument scalar
> helpers. The proof is intentionally narrow: it calls only `task_prio(init_task)`, where
> `init_task` is the verified global data symbol, borrowed/read-only, never freed, and not a
> general arbitrary task pointer.
>
> Static selection pinned `task_prio=0xffffff80080ef394` via `leaf-map-disasm+xref`, source
> declaration `extern int task_prio(const struct task_struct *p)` at `include/linux/sched.h:1720`,
> one direct BL xref, JOPP entry, leaf shape, next-symbol boundary `idle_task` at `+0x10`, and
> exact identity words `ldr w8,[x0,#168]`, `sub w0,w8,#100`, `ret`, next sentinel. The generic C1
> resolver originally kept this shape unverified because it is a leaf with an early x0 dereference
> and no helper call; the fix did not loosen C1 globally. It added only a target-specific
> leaf-map ground-truth row plus proof-pinned exact words. The call-safety gate classifies it as
> `SAFE-WITH-VALID-PTR` only when x0 is `global-init_task-task_struct`.
>
> The live proof obeyed the flash gate: preflight confirmed candidate/rollback/fallback SHA values
> and baseline v2321 health, the v1-repl candidate (`b846ae9f...`) flashed with matching readback
> SHA, candidate health passed after a bridge restart/retry for serial framing noise, and
> `task_prio(init_task)` passed. The proof first read `init_task->prio` at offset `0xa8` as `0x78`,
> fixed the expected return as `0x78 - 100 = 0x14` (`20` signed), then called `task_prio(init_task)`
> twice; both calls returned `0x14`. Post-proof selftest stayed `fail=0`; rollback to v2321
> completed with matching readback SHA; final `version/status/selftest` passed with
> `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-task-prio-20260701T023649Z/timeline.json`:
> candidate flash helper `64.715s`, candidate boot ready after retry `64.0s`, live proof `6.0s`,
> post-proof candidate health `7.0s`, rollback flash helper `63.634s`, rollback boot ready final
> health `21.0s`, and candidate start to final health done `252.0s`.
>
> Function-map outcome: `task_prio` is promoted as live-proven only under the
> `task_prio(init_task)` borrowed-global-task direct-field contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_TASK_PRIO_2026-07-01.md`.

## ✅ DONE — REPL swapcache memory-state live-call proof — `total_swapcache_pages` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — swapcache page-count getter
>
> Codex selected `total_swapcache_pages` as a read-only memory-state observation target instead of
> another saturated time/lib helper. Host triage kept sysfs `show`-style callbacks parked because
> the current C1 oracle still cannot prove table-bound show callbacks with direct-call confidence.
> The selected target is source-backed at `include/linux/swap.h:413`
> (`extern unsigned long total_swapcache_pages(void)`), takes no arguments, returns a scalar page
> count, and uses only its internal RCU read-side lock/unlock path.
>
> Static selection pinned `total_swapcache_pages=0xffffff8008260bd4` via
> `disasm-signature+xref+map`, with direct BL xrefs `9`, no pre-call argument pointer
> dereferences, next-symbol boundary `show_swap_cache_info` at `+0x88`, and all 35 identity words
> pinned through the next-entry first word. The C1 call gate classifies it as `SAFE-SCALAR`;
> the classifier still surfaces the expected context-sensitive warning because the body contains
> `__rcu_read_lock`/`__rcu_read_unlock`.
>
> The live proof obeyed the flash gate: preflight confirmed rollback/fallback/TWRP SHA values and
> baseline v2321 health, the v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA,
> candidate health passed after bridge restart/retry for serial framing noise, and
> `total_swapcache_pages()` returned `0x0 -> 0x0` under the bounded nonnegative page-count
> contract. Post-proof candidate health stayed `selftest fail=0`; rollback to v2321 completed with
> matching readback SHA; final health passed after bridge restart/retry with
> `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-total-swapcache-pages-20260701T020827Z/timeline.json`:
> candidate flash helper `55.520s`, candidate explicit health initial attempt `11.0s`,
> candidate bridge restart `4.0s`, candidate health retry `1.0s`, live proof `6.0s`,
> post-proof health `0.0s`, rollback flash helper `64.706s`, final explicit health initial
> attempt `11.0s`, final bridge restart `4.0s`, final health retry `2.0s`, and candidate start
> to final health retry done `261.0s`.
>
> Function-map outcome: `total_swapcache_pages` is promoted as live-proven only under the
> no-argument swapcache page-count read-only contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_TOTAL_SWAPCACHE_PAGES_2026-07-01.md`.

## ✅ DONE — REPL timekeeping seconds batch live-call proof — `ktime_get_seconds` + `ktime_get_real_seconds` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — same-session time64 seconds getters
>
> Codex followed the 2026-07-01 batch cadence rule and proved two adjacent no-argument
> timekeeping seconds getters in one v1-repl boot session. Host triage compared the adjacent
> timekeeping scalar candidates: `ktime_get_seconds` and `ktime_get_real_seconds` were selected,
> `ktime_get_resolution_ns` stayed parked because the resolver could not verify it through the
> export/direct-xref gate (`direct_bl_xref_count=0`), and `ktime_get_raw` stayed rejected because
> static analysis saw a precall x0 dereference.
>
> Static selection pinned `ktime_get_seconds=0xffffff800815f66c` and
> `ktime_get_real_seconds=0xffffff800815f694`, both via `export-recovery` with map agreement,
> source declarations `extern time64_t ktime_get_seconds(void)` and
> `extern time64_t ktime_get_real_seconds(void)` (`include/linux/timekeeping.h:44-45`), no
> pointer args, and leaf bodies. The proof pins the full identity bodies:
> `ktime_get_seconds` through `ktime_get_real_seconds` at `+0x28` and
> `ktime_get_real_seconds` through `__ktime_get_real_seconds` at `+0x18`. The C1 call gate
> classifies both as `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate: preflight confirmed rollback/fallback SHA values and
> baseline v2321 health, the v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA,
> candidate health passed after bridge restart/retry for serial AT noise, and the same-session
> batch proof passed. `ktime_get_seconds()` returned `0x59 -> 0x5a` with max delta `0x1`;
> `ktime_get_real_seconds()` returned stable `0x5a521ebc` with max delta `0x0`. Post-proof
> candidate health stayed `selftest fail=0`; rollback to v2321 completed with matching readback
> SHA; final health passed after bridge restart/retry with `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-timekeeping-seconds-batch-20260701T014723Z/timeline.json`:
> candidate flash helper `63.708s`, candidate explicit health initial attempt `30.0s`,
> candidate bridge restart `2.0s`, candidate health retry `2.0s`, live batch proof `9.0s`,
> post-proof health `1.0s`, rollback flash helper `64.628s`, final explicit health initial
> attempt `31.0s`, final bridge restart `2.0s`, final health retry `1.0s`, and candidate start
> to final health retry done `296.0s`.
>
> Function-map outcome: `ktime_get_seconds` and `ktime_get_real_seconds` are promoted as
> live-proven only under the no-argument read-only nonnegative/nondecreasing time64 seconds
> contracts. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_TIMEKEEPING_SECONDS_BATCH_2026-07-01.md`.

## ✅ DONE — REPL current process-group state live-call proof — `is_current_pgrp_orphaned` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — current pgrp orphan-status bool getter
>
> Codex expanded the current-state observation surface with `is_current_pgrp_orphaned` under a
> no-argument bool-int contract. Host triage used an adjacent-candidate batch rather than a single
> isolated pick: `current_kernel_time64` was parked because the current v1-repl op3 captures only
> x0 while the struct-return proof needs x0/x1 lanes, `get_debug_reset_header` stayed excluded for
> alloc/read/free/printk behavior, and `is_current_pgrp_orphaned` was selected as a no-arg
> read-only current task/process-group state query despite its heavier tasklist read-lock traversal.
>
> Static selection pinned `is_current_pgrp_orphaned=0xffffff80080b72bc` via
> `disasm-signature+xref+map`, source declaration `extern int is_current_pgrp_orphaned(void)`
> (`include/linux/tty.h:506`), direct BL xrefs `2`, no pointer args, and next-symbol boundary
> `mm_update_next_owner` at `+0xd8`. The proof pins all 54 identity words, including the JOPP
> entry, `_raw_read_lock`, `_raw_read_unlock`, final `ret`, and next-entry sentinel. The C1 call
> gate classifies it as `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate: preflight confirmed rollback/fallback SHA values and
> baseline v2321 health, the v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA,
> candidate health passed after a safe observation retry for serial capture noise, and
> `is_current_pgrp_orphaned()` returned stable bool-int `0x1` twice. Post-proof candidate health
> stayed `selftest fail=0`; rollback to v2321 completed with matching readback SHA; final health
> passed with `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-is-current-pgrp-orphaned-20260701T012647Z/timeline.json`:
> candidate flash helper `64.628s`, candidate explicit health initial attempt `34.0s`, candidate
> health retry `1.0s`, live proof `5.0s`, post-proof health `0.0s`, rollback flash helper
> `63.568s`, final explicit health `1.0s`, and candidate start to final health done `302.0s`.
>
> Function-map outcome: `is_current_pgrp_orphaned` is promoted as live-proven only under the
> no-argument current task/process-group orphan-status bool contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_IS_CURRENT_PGRP_ORPHANED_2026-07-01.md`.

## ✅ DONE — REPL current-task state live-call proof — `can_do_mlock` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — current-task mlock allowance bool getter
>
> Codex expanded the already covered `CALL_PROOF_TARGETS` inventory with one new current-task
> state observation target and proved `can_do_mlock` under a no-argument bool contract. Host
> triage compared `can_do_mlock`, `is_current_pgrp_orphaned`, and `get_debug_reset_header`;
> `get_debug_reset_header` was excluded because it allocates/reads/frees and prints, and
> `is_current_pgrp_orphaned` was parked as a heavier tasklist read-lock traversal.
>
> Static selection pinned `can_do_mlock=0xffffff800824bb0c` via `export-recovery`, source
> declaration `extern bool can_do_mlock(void)` (`include/linux/mm.h:1303`), direct BL xrefs
> `1`, no pointer args, and next-symbol boundary `clear_page_mlock` at `+0x40`. The proof pins
> all 16 identity words, including the current-task state reads, the `capable(CAP_IPC_LOCK)`
> call path, the final `ret`, and the next-entry sentinel. The C1 call gate classifies it as
> `SAFE-SCALAR`.
>
> The live proof obeyed the flash gate: preflight retry confirmed rollback/fallback SHA values
> and baseline v2321 health, the v1-repl candidate (`b846ae9f...`) flashed with matching readback
> SHA, candidate health passed after a safe observation retry for one serial END-marker
> truncation, and `can_do_mlock()` returned stable bool `0x1` twice. Post-proof candidate health
> stayed `selftest fail=0`; rollback to v2321 completed with matching readback SHA; final health
> passed after bridge restart/retry with `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-can-do-mlock-20260701T010937Z/timeline.json`:
> candidate flash helper `64.629s`, candidate explicit health initial attempt `1.0s`, candidate
> health retry `1.0s`, live proof `6.0s`, post-proof health `0.0s`, rollback flash helper
> `63.562s`, final explicit health initial attempt `30.0s`, final bridge restart `3.0s`,
> final health retry `1.0s`, and candidate start to final health retry done `268.0s`.
>
> Function-map outcome: `can_do_mlock` is promoted as live-proven only under the no-argument
> current-task mlock allowance bool contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CAN_DO_MLOCK_2026-07-01.md`.

## ✅ DONE — REPL read-only memory-state live-call proof — `vm_commit_limit` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — memory commit-limit scalar getter
>
> Codex proved `vm_commit_limit` as a no-argument read-only memory overcommit accounting getter.
> Static selection pinned `vm_commit_limit=0xffffff800822b0e4` via `leaf-map-disasm+xref`,
> source declaration `unsigned long vm_commit_limit(void)` (`include/linux/mman.h:94`),
> direct BL xrefs `1`, leaf shape, and next-symbol boundary `vm_memory_committed` at `+0x50`.
> The proof pins all 20 identity words, including the final `ret` and the next-entry sentinel.
> The C1 call gate classifies it as `SAFE-SCALAR` with no required pointer arguments.
>
> The live proof obeyed the flash gate: preflight v2321 health passed, rollback images were present
> with expected SHA values, the v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA,
> candidate health passed after a safe observation retry for one serial END-marker truncation, and
> the proof called `vm_commit_limit()` twice with no arguments. Both calls returned the same sane
> nonzero page count, `0x9dff5`, and no returned value was dereferenced or freed.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-vm-commit-limit-20260701T004333Z/timeline.json`:
> candidate flash helper `63.775s`, candidate explicit health initial attempt `61.0s`, candidate
> health retry `1.0s`, live proof `5.0s`, rollback flash helper `63.675s`, final explicit health
> `1.0s`, and candidate start to final health done `302.0s`. The candidate initial `version`
> observation hit serial END-marker truncation; `selftest fail=0` and `status=ok` were visible,
> and a safe retry passed cleanly.
>
> Function-map outcome: `vm_commit_limit` is promoted as live-proven only under the no-argument
> read-only memory commit-limit scalar contract. The scheduler-counter batch remains stopped under
> the fails-twice rule unless explicitly reopened. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_VM_COMMIT_LIMIT_2026-07-01.md`.

## ✅ DONE — REPL result-slot state-writer live-call proof — `get_avenrun` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — scheduler load-average result-slot writer
>
> Codex proved `get_avenrun` as another result-slot state-writer, but this time against kernel
> scheduler load-average state rather than timekeeping. Static selection pinned
> `get_avenrun=0xffffff80080f6da4` via `leaf-map-disasm+xref`, source declaration
> `extern void get_avenrun(unsigned long *loads, unsigned long offset, int shift)`
> (`include/linux/sched/loadavg.h:16`), direct BL xrefs `3`, JOPP leaf shape, and next-symbol
> boundary `calc_load_fold_active` at `+0x40`. The proof pins all 16 identity words, including
> the three stores into `[x0]`, `[x0,#8]`, and `[x0,#16]`, the final `ret`, and the next-entry
> sentinel. The C1 call gate classifies it as `SAFE-WITH-VALID-PTR` only with x0 bound to an
> owned `unsigned long[3]` load-average result slot and x1/x2 fixed to zero.
>
> The live proof obeyed the flash gate: preflight v2321 health passed, rollback images were present
> with expected SHA values, the v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA,
> candidate health passed after a safe observation retry for one serial END-marker truncation, and
> the proof allocated an owned result slot, called `get_avenrun(ptr, 0, 0)`, read back three sane
> fixed-point load-average values, verified the canary, and freed the slot with `kfree`. Observed
> values were `load[0]=0x1499`, `load[1]=0x6cc`, and `load[2]=0x26b`; `cleanup_ok=true`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-get-avenrun-20260701T002458Z/timeline.json`:
> candidate flash helper `63.660s`, candidate explicit health initial attempt `30.0s`, candidate
> health retry `1.0s`, live proof `11.0s`, rollback flash helper `64.726s`, final explicit health
> initial attempt `61.0s`, final health retry `2.0s`, and candidate start to final health retry
> done `291.0s`. The candidate and final initial `status` observations both hit serial END-marker
> truncation; `version` and `selftest fail=0` were visible, and safe retries passed cleanly.
>
> Function-map outcome: `get_avenrun` is promoted as live-proven only under the owned load-average
> result-slot contract (`offset=0`, `shift=0`). Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_AVENRUN_2026-07-01.md`.
> Next selection should keep the operator's policy intact: adjacent/similar candidates may be
> batched when they share one shape, but do not loosen DENY/behavior-changing gates just to reach a
> target.

## ✅ DONE — REPL result-slot state-writer live-call proof — `ktime_get_ts64` promoted

> ### ✅ STATUS (2026-07-01 live-proven, rolled back cleanly) — timekeeping result-slot writer
>
> Codex proved `ktime_get_ts64` as a result-slot state-writer target rather than another saturated
> scalar/string helper. Static selection pinned `ktime_get_ts64=0xffffff800815f534` via
> `export-recovery`, source declaration `extern void ktime_get_ts64(struct timespec64 *ts)`
> (`include/linux/timekeeping.h:43`), direct BL xrefs `39`, and next-symbol boundary
> `ktime_get_seconds` at `+0x138`. The C1 call gate classifies it as `SAFE-WITH-VALID-PTR` only
> with x0 bound to an owned kmalloc `struct timespec64` result slot plus trailing canary.
>
> The live proof obeyed the flash gate: preflight v2321 health passed, rollback images were present
> with expected SHA values, the v1-repl candidate (`b846ae9f...`) flashed with matching readback SHA,
> candidate health passed, and the proof allocated an owned result slot, called `ktime_get_ts64`, read
> back two sane/nondecreasing `tv_sec/tv_nsec` values, verified the canary, and freed the slot with
> `kfree`. Final observed pass cases were `tv_sec=0x8e tv_nsec=0x28eb0361` and
> `tv_sec=0x94 tv_nsec=0x0a5c1823`; `cleanup_ok=true`.
>
> One useful correction landed during the unit: the first instrumented proof failed only the old
> `5s` `bounded_short_delta` contract (`delta=0x14d8b7572`, about `5.596s`) while every semantic
> field was good. The proof now uses a `30s` serial-REPL proof budget and, more importantly, returns
> structured fail evidence (`case_results` + `failure_reason`) instead of throwing before JSON is
> written.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-ktime-get-ts64-retry-20260701T000637Z/timeline.json`:
> candidate flash `65.0s`, candidate flash to explicit health `102.0s`, first instrumented proof
> `16.0s`, relaxed proof `16.0s`, live session total `92.0s`, rollback flash `65.0s`, rollback to
> final explicit health `103.0s`, rollback to final version retry `112.0s`, and candidate start to
> final version retry `325.0s`.
>
> Function-map outcome: `ktime_get_ts64` is promoted as live-proven under the owned-timespec64
> result-slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KTIME_GET_TS64_2026-07-01.md`.
> Next selection should continue the operator's batch/saturation policy: group adjacent same-shape
> candidates when useful, but pivot toward unproven ABI/state-observation shapes rather than
> enumerating another low-information scalar variant.

## ⚠️ STOPPED — REPL state-observation live-call proof attempt — `of_flat_dt_is_compatible` live faulted, fenced known-unsafe

> ### ⚠️ STATUS (2026-07-01 attempted, rolled back cleanly) — flat-DT compatibility helper not promoted
>
> Codex attempted the next post-saturation pivot candidate, `of_flat_dt_is_compatible`, as a
> read-only kernel-state observation helper rather than another same-shape scalar/string proof.
> Static selection pinned `of_flat_dt_is_compatible=0xffffff800a66cc34`, source declaration
> `extern int of_flat_dt_is_compatible(unsigned long node, const char *name)`, root node offset
> `0`, and owned compatible-string buffers for a positive `qcom,sm8150` case plus an impossible
> negative case.
>
> The device attempt obeyed the flash gate: baseline v2321 health passed, the v1-repl candidate
> (`b846ae9f...`) flashed with matching readback SHA, candidate helper health passed, explicit
> candidate `version/selftest/status` passed after a serial-framing retry, and REPL selftest passed.
> The target live call then faulted before returning: stdout tail showed `[signal 11]`,
> `run rc=139 (101ms)`, and no `A90R` output. The unit stopped immediately and rolled back to v2321.
> Final explicit `version/selftest/status` passed with `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-of-flat-dt-is-compatible-20260630T233514Z/timeline.json`:
> candidate flash `65.0s`, candidate helper done to explicit REPL-ready marker `13.0s`, live session
> total `95.0s`, live call-proof attempt `11.0s`, rollback flash `65.0s`, rollback helper done to
> final explicit health `33.0s`, and candidate start to final health done `310.0s`.
>
> **No function-map entry is promoted.** The code now fences `of_flat_dt_is_compatible` as
> `known-unsafe-live-call`; `resolve_verified(..., purpose="call")` returns `blocked-known-unsafe`,
> and classifier CLI reports `DENY`. Host validation after the fence passed: `py_compile`, focused
> tests (`Ran 3 tests`, `OK`), full `tests.test_a90_repl` (`Ran 172 tests`, `OK`), classifier CLI,
> and `git diff --check`. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_OF_FLAT_DT_IS_COMPATIBLE_ABORTED_2026-07-01.md`.

> **(history)** Audio CORE is device-proven + promoted (`0.10.0`); its Tier-C polish is optional background.
>
> **⚠️ KEY RE-SCOPE (operator, 2026-06-19): the DISPLAY IS ALREADY PROVEN — do NOT treat "can native init draw to the screen" as an
> open question.** `workspace/public/src/native-init/a90_kms.c` (682 lines) already does real **DRM/KMS**: opens `/dev/dri/card0`,
> `DRM_IOCTL_MODE_GETRESOURCES` → picks crtc/connector/mode, mmaps the active framebuffer (`kms_active_map`), and the HUD / menu /
> about screens render text+rects to the panel via `a90_kms_framebuffer()` + `a90_draw_text`/`a90_draw_rect`. So the framebuffer /
> cont-splash / "panel-init brick-caution" framing is MOOT — native init drives the panel today. **The video epic is therefore a
> PLAYBACK-PIPELINE problem on a proven display, not a display-feasibility problem.** Venus HW decode is NOT needed (demos use
> pre-rendered frames).
>
> **The real open questions (performance / pipeline, much lower risk than feasibility):**
> 1. **Full-frame blit throughput** — HUD draws occasional static text/rects; video needs full-screen bitmap blit at ~30 fps
>    (Bad Apple ≈ 6500 frames). Add a "blit a full framebuffer-sized bitmap into the mapped KMS fb" primitive (memcpy into the
>    existing map) and measure sustainable fps (downscale / lower color depth if needed). Page-flip vs direct-map is a tearing-polish detail.
> 2. **Frame streaming** — stream ~thousands of pre-rendered raw frames from storage (same pattern as audio PCM streaming).
> 3. **A/V sync** — time frame blits to the audio PCM position (audio engine already proven; needs the file/stream-PCM input path too).
>
> **VID-0 (host-only):** confirm the existing `a90_kms` fb is usable for full-frame blit (resolution/format/stride from `a90_kms.c`),
> design the host pre-processing (decode audio → 48k/stereo/16-bit PCM; render frames → raw bitmaps at fb format) + the on-device
> frame/PCM streaming + blit/sync loop. Deliverable: pipeline plan. **VID-1+ device steps:** add the blit primitive, measure fps with a
> test pattern, then wire pre-rendered Bad Apple frames + audio. Recoverable boot-partition flashes only; rollback `v2321`.
> **Bright lines still apply:** no backlight/PMIC/PWM/regulator/GDSC writes; forbidden partitions absolute. (Panel-init brick-caution is
> moot since `a90_kms` already drives the existing mode — do not regress into a from-scratch panel re-init either.)
>
> **⚡ IMPLEMENTATION RECIPE (web-validated, operator 2026-06-19) — build the playback path the DOCUMENTED standard way; do NOT re-derive or per-pixel-draw frames.**
> Our `a90_kms.c` already does the hard 80% (KMS modeset + a single DRM **dumb buffer** via `MODE_CREATE_DUMB`/`MAP_DUMB` + `mmap(MAP_SHARED)` + `SETCRTC`, format **XBGR8888**, stride-honored). The video upgrade is the textbook DRM-dumb-buffer playback pattern:
> 1. **Double-buffer + page-flip (kills tearing, gives vsync + the A/V-sync clock):** allocate a **2nd dumb buffer**, draw the next frame into the *back* buffer, then `drmModePageFlip()` (`DRM_IOCTL_MODE_PAGE_FLIP`) scheduled for the next **vblank**. The flip is async — a flip-complete **event arrives on the drm fd**; read it in the loop and use its vblank timestamp as the **frame cadence + audio-sync anchor**. (We currently have 1 buffer + one `SETCRTC`; add buffer #2 + the flip loop.)
> 2. **Frame update = bulk WC memcpy, NEVER per-pixel:** pre-render frames on the HOST to **linear XBGR8888 matching the fb stride**, then **`memcpy` the whole frame** into the mmap'd back buffer. Dumb-buffer maps are **write-combine** → *sequential* memcpy is fast (kernel docs: "fast WC memcpy"), but the existing per-pixel `a90_draw_rect`/font primitives are **slow on WC** and must NOT be used for full-frame video. Add a `a90_kms_blit_frame(fb, src, len)` bulk primitive.
> 3. **Constraints:** dumb buffers are **LINEAR-only** → frames must be linear + stride-aligned (downscale Bad Apple if full-res 30 fps is bandwidth-bound; measure real fps with a test pattern first).
> **Reference implementations to consult (fetch these — do not reinvent the ioctl sequence):** `serviceberry3/android_drm_dumb` (Android DRM dumb-buffer-to-screen, our exact platform); the dvdhrm drm-howto "modeset-double-buffered"/"modeset-vsync" + "Advanced DRM Mode-Setting API" (page-flip/vblank-event loop); FFmpeg's `kmsdrm` output device (same decode→memcpy-dumb→flip pattern; we do NOT run ffmpeg on-device — host pre-decodes to raw frames/PCM, device just streams+blits). We are software-only (no Mesa/GPU/Adreno) — this dumb-buffer+memcpy+page-flip path needs no GPU.
>
> **🎞️ SMOOTH-PLAYBACK STANDARDS (web-validated, operator REFERENCE 2026-06-20) — for the "frames feel choppy/judder" class.** The current stream play loop (`v319/30_status_hud.inc.c`) does **SD read → mono1 unpack → per-pixel upscale → blit → flip ALL serially per frame, with no prefetch** — so any per-frame variance (SD latency, the nested-loop scaler) makes frames late → judder, and with sync-drop on, dropped → stutter. The blit/double-buffer/page-flip skeleton is correct; what's missing maps to two industry standards:
> 1. **Frame pacing (AOSP/Android "Swappy" Frame Pacing library is the canonical impl).** Core rule: *"a consistent 30 Hz is smoother than a hybrid where some frames show for 16.6 ms and others 33.3 ms."* 30 fps content on the ~60 Hz panel must present **every source frame for a FIXED integer # of vblanks (here 2)**, scheduled to the display clock. We **already read page-flip completion events** (V2877) → use them as the vblank counter to hold each frame exactly 2 flips. Uneven hold = judder even at **zero** drops. Corollary: **a steady cadence beats chasing exact sync by dropping** — keep the V2927 direction of a *less* aggressive drop policy.
> 2. **Decode-ahead / render-ahead queue (producer-consumer ring buffer).** Standard streaming-player structure = a **compressed-frame queue + a decoded-frame queue**, with decode running *ahead* to keep the decoded queue full; presentation only does memcpy+flip off the decoded ring. This **decouples SD I/O + mono1 decode from the vblank deadline** (a 1–2 frame decode-ahead is enough to absorb our variance). Native init is largely single-threaded, so even a simple "decode the next 1–2 frames during slack" lookahead (not necessarily a full producer thread) gets most of the benefit.
> 3. **Push work to the host (extreme of "separate decode from the consumer").** Pre-render frames on the host at the **final on-screen resolution** so the device skips the per-frame upscale (the heaviest critical-path step), and/or pre-expanded format so it skips unpack — trading asset size (keep `mono1` at final res to stay compact). Device then ≈ read+memcpy only.
> **Refs:** Android Frame Pacing / Swappy (`developer.android.com/games/sdk/frame-pacing`, `source.android.com/docs/core/graphics/frame-pacing`), Raph Levien "Swapchains and frame pacing", render-ahead/decode-ahead queue (producer-consumer ring buffer). **This is REFERENCE/direction for the choppiness class — not a committed step; fold into the Bad Apple DoD #1 (presented ≥ 95 %) work.**

> **📍 STATUS (2026-06-20) — Bad Apple Player HUD demo DONE; pipeline proven end-to-end.** (Display proven; Venus not needed — the recon framing below is historical only.) Loop progress V2864→V2964:
> - DRM/KMS inventory (V2864), `video` command surface (V2865–V2867), animation scaffold (V2868–V2869).
> - **Q1 full-frame blit throughput** — blitbench live (V2871–V2872) ✅.
> - **Q2 frame streaming** — A90VSTR stream reader live (V2874–V2875) ✅.
> - **Q3 page-flip / vblank clock** — flipprobe 12/12 @ ~59.9 fps (V2876–V2877), stream page-flip mode (V2878–V2879) ✅ — the recipe's double-buffer + `drmModePageFlip` path is live.
> - **Audio file-PCM input** (V2880–V2881) ✅ — engine now plays arbitrary PCM, not only the 440 Hz tone.
> - **A/V co-run + sync** — AV PCM video co-run (V2882), AV sync telemetry + stream (V2884–V2886) ✅.
> - **Video cache** command + trusted cache + AV-sync + preset (V2904–V2912) ✅ — frames cached on SD for playback.
> - **Bad Apple asset** prepared host-side (V2903 wrapper) → seeded to SD cache → wired as `DEMO > Bad Apple` Player HUD.
> - **🎬 Bad Apple demo DONE ✅ (V2947 full-song / V2964 smooth)** — full 232 s / 6962 frames, **0 dropped**, even ~30 fps cadence, audio audible + A/V synced (operator-confirmed), BEAT FLASH + read-only dashboard live, `selftest fail=0`, init `0.10.49`. **All five Definition-of-Done criteria met** (see demo-targets). The journey validated the smooth-playback standards: uneven 16/50 ms pageflip cadence + full-HUD-repaint cost = visible stutter even at 0 drops → fixed via setcrtc default (V2960) + **incremental HUD repaint** (V2963/V2964).
> **🎬 Nyan Cat demo DONE ✅ (V2975/V2976, `A90VSTR2 pal8-rle` ~35× compression, 30 fps).** DOOM is now in progress
> (input solved via **serial doompad** over the command bridge — V3014/V3015 — no OTG keyboard / no touch needed; built-in
> touch is a concluded dead-end, see Touch block). **DOOM render scaffold (`doomgeneric`) is the active work.**
>
> **📌 Versioning / checkpoint plan (operator, 2026-06-21):**
> - **PATCH-level kept "demo checkpoint" DONE (V3021/V3022)** — built ONE image bundling the validated video pipeline +
>   **Bad Apple + Nyan** demos, then live-validated BOTH in that single image: Bad Apple full-song Player HUD and Nyan
>   Player HUD preview both passed, `selftest fail=0`, and rollback to v2321 passed. Kept milestone:
>   `A90 Linux init 0.10.72 (v3021-demo-checkpoint-badapple-nyan)`, boot SHA256
>   `c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7`.
>   This is NOT a MINOR roll and does NOT replace the v2321 rollback net — it locks in the known-good demo state before
>   further DOOM work can regress it.
> - **DOOM CORE DONE ✅ (V3032 visible frame / V3033–V3034 visible playable loop / V3035–V3041 dashboard, init `0.10.79`):**
>   doomgeneric runs the real shareware WAD, frames blit to the panel via KMS, serial-doompad input drives gameplay
>   (move/fire), DOOM dashboard/HUD added; device was left on the DOOM image for operator demo.
> - **0.11.0 (MINOR) RESERVED for video-epic close — GATED on a DOOM demo FINISHING/OPTIMIZATION pass first
>   (operator, 2026-06-22). Do NOT roll 0.11.0 on a rough DOOM.** Before promotion, do the polish round (same spirit as
>   Bad Apple's cadence/HUD-cost fixes): **frame pacing + sustained fps** (real-time → steadier matters more than for
>   Bad Apple), **640×400→1080×2400 upscale quality** (integer/aspect/letterbox), **dashboard incremental repaint**
>   (no full-HUD repaint per frame — reuse the V2963 lesson), **input responsiveness** (doompad→`DG_GetKey` latency,
>   simultaneous move+fire, key repeat), **DOOM audio** (music/SFX → PCM path, or explicitly defer per the "SFX optional"
>   ladder note), and **longer-session stability** (no hang over sustained play). THEN build the 0.11.0 promotion image
>   bundling Bad Apple + Nyan + the polished DOOM, live-validate all three, pin version+SHA+promotion report = video-epic
>   close. DOOM stays on the 0.10.x line through the finishing pass; v2321 remains the rollback net.
> - **0.11.0 VIDEO EPIC PROMOTION CLOSED ✅ (V3157, 2026-06-25):** `A90 Linux init 0.11.0
>   (v3157-video-epic-promotion)`, boot SHA256
>   `cc458455e64af62720eebe2f80d7f8b49ea8c8bd3a96368b8a5311b685c4ad33`. Same image live-validated
>   Bad Apple Player HUD 300 frames at `30065` fps_milli / 0 drops, Nyan Player HUD 300 frames at
>   `30053` fps_milli / 0 drops, DOOM WAD SHA match + 120-frame foreground loop (`rc=0`, 120 presented,
>   0 missed shared frames) + bounded background/SFX start (`audio_rc=0`, worker stopped cleanly). Reports:
>   `docs/reports/NATIVE_INIT_V3157_VIDEO_EPIC_PROMOTION_SOURCE_BUILD_2026-06-25.md` and
>   `docs/reports/NATIVE_INIT_V3157_VIDEO_EPIC_PROMOTION_LIVE_2026-06-25.md`. This closes the Video epic
>   and unlocks the reserved GPU G0 only under its bounded/bright-line rules.
> - **🎯 FRAME-PACING DIAGNOSIS CLOSED — next pass = SCALE optimization (operator, 2026-06-23).** The choppiness hunt
>   (V3061→V3101) is **done; stop telemetering.** By live measurement every infra stutter source was found and removed:
>   dashboard thermal-sysfs read (V3069/74), SETCRTC path → KMS pageflip (V3077), file handoff → `shared-mmap-seq` + pace
>   socket (V3079–88), and the **large 3:2 per-frame CPU scaler = confirmed stutter source (V3095, decision
>   `large-scaler-is-stutter-source`)**. At 1:1 the pageflip is flawless (`flip_delta ≈ 16.6 ms`, V3095/V3101); the only
>   residual is **DOOM-inherent 35 Hz logic on a 60 Hz panel with no interpolation** (V3101: half the visible frames repeat
>   the same `gametic`, `max_same_run=2`). That stepped motion is **DOOM being DOOM, NOT a bug and NOT a 0.11.0 blocker** —
>   frame interpolation is a separate quality backlog item, not part of this pass. **Do not add more tick/phase telemetry
>   units — the cause is proven.**
> - **SCALE optimization RESOLVED ✅ (V3124/V3128, 2026-06-23).** "Enlarge ⇒ slow" was an artifact of the presenter's
>   *per-frame CPU pixel scaling*, not of size. Fixed via **pre-scaled producer (1×) + `shared-mmap-direct-blit`**: the
>   engine pre-scales once into the large buffer it owns and the presenter does a direct shared-mmap blit (no second scale
>   copy, no full clear). V3128 audit confirmed **large per-frame scaling is off the critical path — the large DOOM frame
>   stays within the 16.6 ms vblank budget**. HW display-plane scaling was therefore not needed. Residual stepped motion is
>   the DOOM-inherent 35 Hz/60 Hz cadence (interpolation backlog, not a blocker). This fed directly into the V3157 promotion.
> - **DOOM host-only policy gate DONE (V3023)** — the WAD-backed `doomgeneric` frontier resumed after the V3020 host
>   probe; source provenance, WAD/runtime-private policy, boot-size caps, bounded command surface, and rollback-gated
>   live-validation requirements are now pinned without flashing or staging WAD data.
> - **DOOM private-source full-engine link DONE (V3024)** — the pinned private `doomgeneric` source now compiles 80
>   engine C files plus the A90 serial-doompad/runtime-WAD bridge into an AArch64 static private artifact; no WAD data,
>   ramdisk, boot image, or device action was produced.
> - **DOOM native-init command/boot bridge DONE (V3025)** — the V3024 private engine probe helper is now bundled into
>   the private V3025 boot candidate ramdisk as `/bin/a90_doomgeneric_private_engine_v3024`, and native-init exposes
>   `video demo doom engine-probe` plus `video.status.doomgeneric.*` / `video.demo.engine.active` status markers.
>   Input remains `serial-doompad-to-DG_GetKey`, sound remains `-nosound -nomusic`, WAD files in ramdisk are `0`, and
>   the generated private boot image SHA256 is `d028ece642793a7a6242295c86cd6caedbd533f733282120c0575116f012e95f`.
> - **DOOM command bridge live validation DONE (V3026)** — rollback-gated live validation flashed the exact V3025 image,
>   confirmed `version`/`status`/`selftest`, validated `video demo doom status` and `video demo doom engine-probe`
>   (`engine_probe.rc=0`, `timed_out=0`), then rolled back to V2321 with `selftest fail=0`. This proves the internal
>   serial-doompad-to-`DG_GetKey` bridge on-device; OTG keyboard is not required for this proof path.
> - **DOOM runtime-private WAD staging preflight DONE / CONTRACT READY (V3027)** — host-only preflight pinned the
>   runtime staging contract (`/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD`, max `67108864` bytes, SHA verify before
>   future command, cleanup after smoke, no public/ramdisk/boot WAD bytes) and confirmed public WAD count `0`.
>   Exactly one private IWAD/WAD candidate is now present and valid: `4196020` bytes, magic `IWAD`, SHA256
>   `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`.
> - **DOOM SD runtime WAD stage DONE (V3028)** — the selected V3027 WAD is now staged on the device SD runtime
>   path `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD` with device-side SHA256
>   `1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`, size `4196020`, mode `0600`,
>   and post-stage `selftest fail=0`. No flash, boot image, ramdisk, public WAD, or forbidden partition path was touched.
> - **DOOM SD-WAD command implementation DONE (V3029)** — host-only source build produced the
>   `0.10.74` / `v3029-doomgeneric-sd-wad-command` private boot candidate
>   `boot_linux_v3029_doomgeneric_sd_wad_command.img` with SHA256
>   `9b45abb847ac64c9032f0e873038a3abf577e27f2dabc2ceccad8cd8e95cf804`. Native-init now has
>   `video demo doom verify --wad runtime-private --sha256 EXPECTED` and bounded
>   `video demo doom play [frames] --wad runtime-private --sha256 EXPECTED` handling around the SD-staged
>   WAD path `/mnt/sdext/a90/runtime/doom/v3028/DOOM1.WAD`; the V3029 helper SHA256 is
>   `435dc0bda50dff6c27410ed727d4d513c02bfba89e876ff654a045cf00d26b44`. WAD files in ramdisk are
>   `0`, public WAD count remains `0`, and WAD bytes are not embedded in the boot image.
> - **DOOM SD-WAD command live validation DONE (V3030)** — rollback-gated live validation flashed the exact
>   V3029 candidate (`9b45abb847ac64c9032f0e873038a3abf577e27f2dabc2ceccad8cd8e95cf804`) through
>   `native_init_flash.py`, confirmed candidate `version`/`status`/`selftest fail=0`, validated
>   `video demo doom verify --wad runtime-private --sha256 EXPECTED` (`sha256_match=1`, `magic=IWAD`,
>   `ok=1`) and bounded `video demo doom play 4 --wad runtime-private --sha256 EXPECTED` (`rc=0`,
>   `timed_out=0`), then rolled back to V2321 with final `selftest fail=0`.
> - **DOOM WAD-backed visible frame/menu integration source build DONE (V3031)** — host-only source build
>   produced the `0.10.75` / `v3031-doomgeneric-visible-frame` private boot candidate
>   `boot_linux_v3031_doomgeneric_visible_frame.img` with SHA256
>   `1fefa60b9530cf4cfeb21f2419b77e7d9ca4258078899e3826a0c99918912fb4`. The private helper now supports
>   `--wad-frame-dump ... --output /tmp/a90-doomgeneric-v3031-frame.xbgr8888`, and native-init exposes
>   `video demo doom frame [frames] --wad runtime-private --sha256 EXPECTED` to verify the SD WAD, request
>   one bounded raw `640x400` `xbgr8888` frame, blit it through the existing KMS dumb-buffer path, and restore
>   the DEMO > DOOM menu preview. WAD files in ramdisk are `0`, public WAD count remains `0`, and WAD bytes
>   are not embedded in the boot image.
> - **DOOM WAD-backed visible frame live validation DONE (V3032)** — rollback-gated live validation flashed
>   the exact V3031 candidate (`1fefa60b9530cf4cfeb21f2419b77e7d9ca4258078899e3826a0c99918912fb4`)
>   through `native_init_flash.py`, confirmed candidate `version`/`status`/`selftest fail=0`, then ran
>   `video demo doom frame 8 --wad runtime-private --sha256 EXPECTED`: WAD SHA matched, `magic=IWAD`,
>   `render.ok=1`, `display.presented=1`, `display.rc=0`, and `doomframe` presented a 1080x2400 KMS
>   framebuffer. A bounded `video demo doom play 4 --wad runtime-private --sha256 EXPECTED` smoke also
>   passed (`rc=0`, `timed_out=0`). Rollback to V2321 passed with final `selftest fail=0`.
> - **DOOM WAD-backed visible playable loop source build DONE (V3033)** — host-only source build produced
>   the `0.10.76` / `v3033-doomgeneric-visible-loop` private boot candidate
>   `boot_linux_v3033_doomgeneric_visible_loop.img` with SHA256
>   `8fa375702a5023d9cc1f0811c310993a86f58154d658047b8edbe44eece30a97`. The private helper now supports
>   `--wad-frame-loop ... --input-state /tmp/a90-doomgeneric-v3033-input.state --frame-ms 50`; native-init
>   exposes foreground `video demo doom loop [frames] --wad runtime-private --sha256 EXPECTED`,
>   background `loop-start`/`loop-status`/`loop-stop`, and mirrors `doompad key` state into the helper input
>   file. Host keyboard control is via `host_doompad_keyboard_v3033.py` over the existing serial command bridge;
>   WAD files in ramdisk are `0`, public WAD count remains `0`, and WAD bytes are not embedded in boot.
> - **NEXT CHECKPOINT: V3034 rollback-gated visible playable DOOM loop live validation** — flash only the exact
>   V3033 boot image via `native_init_flash.py`, health-check, run foreground `video demo doom loop 8 --wad
>   runtime-private --sha256 EXPECTED`, then run `loop-start` with bounded host keyboard `doompad` transitions,
>   stop the loop, confirm presentation/input markers, and rollback to V2321.
> - Parallel optional polish: dashboard formatting, fonts/ASCII charset, beat-flash tuning.

**Historical recon framing (Venus HW-decode / cont-splash feasibility, VID-0/1/2):** SUPERSEDED — the display is
proven (see the re-scope + STATUS above) and Venus is **not** needed (demos use pre-rendered frames). The
original recon notes live in git history / `docs/reports/`. Do not regress into Venus PIL bring-up or a
from-scratch DSI panel init; bright lines (no backlight/PMIC/PWM/regulator/GDSC) still hold.

### Downstream demo targets (REFERENCE / direction only — NOT an active directive)

The payoff demos the audio + video tracks aim at. This is **direction, not a committed step list**
(refine the exact approach from recon results), and it is **gated**: do NOT start any item until its
prerequisites are actually proven. Until then this block is **orientation only** — e.g. it tells the
video recon to **optimize for a drawable display framebuffer (the demos need it), not Venus** (the
demos need no hardware video decode). Do not let it pull the loop off the one active frontier.

**Demo target ladder (operator direction, 2026-06-19): ① Bad Apple → ② Nyan Cat → ③ DOOM** —
increasing difficulty. Each builds on the same enablers (display framebuffer, audio, then input).

**Surface them under a `DEMO >` submenu in the native-init menu (operator direction, 2026-06-19).** Use the existing menu/app
pattern (`a90_menu.c` — same as `ABOUT >` / `CHANGELOG >` / the audio screens, rendered on the KMS framebuffer). Each demo = a
menu item whose handler launches the demo, and **each must be bounded + interruptible (key / duration / serial interrupt) and must
restore the menu+HUD on exit** (full-screen demos take over the framebuffer; redraw the menu when they end). Audio amplitude cap
(≤0.2) and best-effort/non-boot-blocking rules still apply. The `DEMO >` **scaffold can be built early** — wire `Audio` now (it just
delegates to the existing `audio play` / chime), and leave `Bad Apple` / `Nyan Cat` / `DOOM` as "coming soon" stubs that fill in as
each lands, so each demo becomes a simple "plug into the menu" task. **`Audio` and `Bad Apple` are DONE ✅** (Bad Apple = full-song
Player HUD, V2947/V2964 — see the Player HUD spec below); **`Nyan Cat` is the next rung**, with `DOOM` still a downstream stub. This `DEMO` corner lives in the **feature/test image**
(`0.10.x` audio-cmd / video line), not the `v2321` rollback baseline; promoting it is a separate later decision.

Enablers + demos, dependency-ordered (prereq in parens):
- **Boot chime = sound check** (prereq: audio — DONE) — PID-1 init plays a bundled bounded-amplitude
  chime at boot, **best-effort / non-fatal — never block boot on audio**. Minimal "audio integrated
  into the system" proof; a natural first use of the Tier-B `audio` command.
- **Display framebuffer** (prereq: none — this *is* the video recon's display sub-target) — a
  drawable inherited **cont-splash** surface (`/dev/dri/card0` or `/dev/fb0`) + region blit; **no
  from-scratch DSI panel init, no backlight/PMIC/regulator writes (brick-caution); if the splash
  surface is already torn down, STOP and report rather than re-lighting the panel**. This is the
  make-or-break probe for the whole demo ladder.
- **① Bad Apple** (prereq: audio [DONE] + display framebuffer) — B&W silhouette anim: pre-decoded raw
  frames + raw PCM + a sync loop (no codec, no Venus). The first AV-integration demo; audio half is
  already proven, so this is the strongest first target once the framebuffer lands.
  - **Presentation = "Player HUD" (operator direction, 2026-06-20).** Not a bare fullscreen playback — a
    composited player: **top region = the Bad Apple video** (source is 4:3; integer-upscale into the top of
    the 1080×2400 portrait fb), **bottom region = a live dashboard**. Each frame = render into the page-flip
    back buffer `[blit video region + draw dashboard]` → flip; the dashboard redraws at frame cadence.
  - **Dashboard telemetry — read-only `/proc`+`/sys` ONLY** (no writes; no PMIC/regulator/thermal-write —
    safety lines hold): CPU load (`/proc/stat` jiffies delta, `/proc/loadavg`), CPU temp
    (`/sys/class/thermal/thermal_zone*/temp`), GPU load (`/sys/class/kgsl/kgsl-3d0/gpubusy` —
    **expected ~idle: the blit is CPU memcpy, not GPU-accelerated; display the real value anyway, it is
    honest**), GPU temp (thermal zone), current frame `N/total`, and a **progress bar + `mm:ss`** position.
    Exact node paths to be confirmed by a read-only on-device probe on the feature image.
  - **A/V sync must be made *visible*, two layers:**
    - **(rigorous) drift readout + lamp** — show audio clock `A = PCM-consumed/48000` and video clock
      `V = frames-presented/fps` side by side with **`Δ = A−V` in ms** and a **sync lamp** (green `|Δ|<33ms`
      / yellow `<66ms` / red beyond). This is just surfacing the **already-built V2884/V2886 AV-sync
      telemetry** — no new infra. **Clock caveat:** PCM-bytes-written ≠ what is audibly playing (DSP
      buffering), so use the **DSP-consumed position** or subtract a **measured fixed latency**, else Δ shows
      a false constant drift.
    - **(intuitive) BEAT FLASH** (operator pick, 2026-06-20) — offline-extract onset/beat timestamps from the
      audio (ffmpeg, host-side, one-time) and **pulse a border/marker on those timestamps driven by the
      AUDIO clock**; when the flash visually coincides with Bad Apple's beat-synced motion accents, sync is
      self-evident on screen.
  - **Asset scope (current operator direction):** full song, downscaled. Bad Apple is **4:3 landscape**, so the
    video asset is **480×360** (≈21.6 KB/frame `mono1` × ~6960 frames ≈ **150 MB**; device-side integer-upscale
    ×2 → 960×720 into the top region). Full-res full-song ≈ 2.2 GB is too big for the SD cache — RLE format
    would fix that but is a later format-extension unit. Audio pre-rendered at **0.15 volume** (within
    the ≤0.2 cap). Host prep is **V2903** (`prepare_badapple_assets_v2903.py`) — source media stays private
    under `workspace/private/`, never committed.
  - **Generated asset (READY, 2026-06-20):** `workspace/private/demo-assets/video/v2903-badapple-480x360-full/`
    (private, uncommitted) — `video-stream/frames.a90vstr` (6962 frames, 480×360 `mono1`, 150,490,668 B,
    sha256 `9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0`) + `audio/audio.s16le`
    (48 kHz stereo S16LE, 0.15 vol, full 232 s, 44,561,952 B,
    sha256 `b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75`) + `video-stream/manifest.json`.
    **Next:** seed via the **V2900 chunked SD-cache uploader** (confirm the SD-cache size cap is ≥150 MB
    first), then wire the Player HUD handler. (`yt-dlp`+static `ffmpeg` live under `workspace/private/tools/bin/`
    for re-extraction / other demos.)
  - **🎯 DEFINITION OF DONE — Bad Apple demo (operator, 2026-06-20). Marker `pass=1` is NOT done; the run must
    also meet these. A run that passes its markers while dropping the picture is a FAIL, not a pass.**
    1. **Frames actually presented, not dropped to catch up** — over a *full-length* (not 300-frame slice) synced
       play, **`presented/total ≥ 0.95`** (drop rate < 5 %). **Explicit FAIL example: V2920 `presented=1
       dropped=299` (`first_presented_frame=299`, `initial_drop_late≈782 ms`)** — the audio anchor carried a
       fixed offset and the drop-policy threw away the whole picture. That is the bug to fix, not a pass.
    2. **Anchor-offset corrected** — the constant `initial_drop_late` (DSP/audio-start latency; the GOAL clock
       caveat above) must be **measured and subtracted** (or the anchor re-based / the initial catch-up capped)
       so video does not start "already late." Sync Δ within **±33 ms** after correction.
    3. **Audio audible + in sync** — the PCM track plays through the speaker (≤0.2 amp) time-aligned to the video,
       not merely "pcm_write_attempted".
    4. **Player HUD actually rendered** — bottom dashboard (CPU load/temp, GPU load/temp [honest ~idle], frame
       `N/total`, progress bar) **and the BEAT FLASH** are on screen, not just the layout split.
    5. **Full length** — the whole 232 s asset plays start→end (or an explicit operator-chosen clip), bounded +
       interruptible, restores menu+HUD on exit, rollback/health unaffected (`selftest fail=0`).
    Until all five hold, the Bad Apple demo is **in-progress**, not done. (This pins the *demo's* acceptance bar;
    it does **not** narrow the epic — Nyan Cat / DOOM remain the downstream ladder on the same pipeline.)
- **② Nyan Cat — 🎯 NEXT CHARTERED RUNG (operator, 2026-06-20)** (prereq: same as Bad Apple — all met). Color +
  looping animation + looping music; reuses the proven Player-HUD / page-flip / A-V-sync pipeline (still
  framebuffer-blit, still no Venus). **The format-efficiency Tier-1 work is folded in here as Nyan's *enabler*,
  NOT a standalone epic:** color frames raw blow up fast (mono1's 1-bit trick is gone → even a palette/RGB565 is
  several× bigger), so Nyan is the **concrete forcing function** that pulls in a **compact on-device-decodable
  format**. Design the format *from Nyan's actual needs* (palette-indexed and/or RLE / delta-frames for a short
  looping clip), with Bad Apple's `A90VSTR mono1` as the existing reference and the device staying light (cheap
  decode → bulk blit; no GPU/Venus). Deliverable = Nyan playing the Player-HUD demo *and* a small compact-format
  win proven on real content. (Do NOT build an abstract "format epic" with no consumer — bind every format unit
  to making Nyan playable/efficient.) Looping + short = also a good first test of seamless loop playback.
- **Touch bring-up** (prereq: none; parallel-able) — read the touch panel via evdev `/dev/input/event*`. The input
  track for DOOM. **Progress (2026-06-20): device FOUND, event-read NOT yet proven.** `inputscan` (V2977/78) enumerated
  9 input nodes incl. **`event6 sec_touchscreen`** + `event8 sec_touchpad`; `readinput event6` (V2979) timed out with
  **0 events** (`readinput-touch-sample-not-proven`).
  - **🔎 TWRP-validated recipe (operator host-side RE, 2026-06-20 — `workspace/private/inputs/firmware/twrp/recovery.img`):**
    TWRP's ramdisk has **NO touch enable / firmware-load / sysfs / chmod on input nodes** — it just **opens
    `/dev/input/event*` and reads**. So the panel is brought up by the **kernel built-in driver at boot; no userspace
    power/enable is needed** (bright lines safe — do NOT add PMIC/regulator/backlight writes for touch). Cross-check:
    native init **already reads input today** — `a90_input.c` opens `event0`/`event3` and reads **EV_KEY** (the menu
    nav buttons work), proving the input subsystem is live under native init. **Touch = the same subsystem, just
    `event6` with `EV_ABS`/`ABS_MT` instead of `EV_KEY`.**
  - **Recipe:** open `/dev/input/event6` `O_RDONLY|O_NONBLOCK` + poll (reuse the existing `a90_input.c` poll loop),
    and **add the multitouch-protocol-B parse**: `ABS_MT_SLOT` / `ABS_MT_TRACKING_ID` / `ABS_MT_POSITION_X` /
    `ABS_MT_POSITION_Y` / `BTN_TOUCH` / `SYN_REPORT`. The only gap vs today is the `EV_ABS/ABS_MT` parse path (current
    code parses `EV_KEY` only). **Live validation REQUIRES an operator finger-touch during the read window.** If a
    *real* touch still yields 0 events, only THEN suspect driver runtime-PM/suspend → else pivot DOOM input to the
    USB-keyboard fallback. So `0 events` so far ≈ "nobody touched in the window," not a hardware/power wall.
  - **🛑 CONCLUDED (2026-06-20, V2982–V2993): built-in touch is a DEAD END under native init.** With the operator
    physically touching during bounded windows, BOTH `event6 sec_touchscreen` and `event8 sec_touchpad` emitted
    **0 events** (V2982; reconfirmed V2989–V2991 dual-touch). The panel registers as a touch device but does not
    *deliver* events under native init (runtime-PM/suspend or panel-power coupling never resumed — not crackable
    within bright lines). **Decision `v2993-doom-input-frontier-pivot-keyboard-fallback`: DOOM input → USB keyboard
    over OTG** (the GOAL-anticipated fallback). The loop built an input MUX (touch/keyboard/button proxy, V2994–V2998)
    + DOOM keyboard gate (V3004–V3013).
  - **✅ SUPERSEDED (V3014–V3017): no OTG hardware wait for the next DOOM step.** The OTG keyboard path remains a
    fallback diagnostic, but V3014 added a serial `doompad` controller, V3015 validated its state live, V3016 wired
    that state into a bounded foreground KMS `doomplay` loop, and V3017 live-validated `video demo doom play 8`
    consuming `forward+fire` (`player.y 1200→1128`) with rollback to V2321 and `selftest fail=0`. The current input
    surface for DOOM iteration is therefore `serial-doompad-consumed`, not `external-hardware-stimulus-required`.
- **③ DOOM = capstone** (prereq: display + input [touch *or* USB-keyboard fallback]; audio SFX
  optional) — `doomgeneric`: `DG_DrawFrame` → framebuffer region, `DG_GetKey` → the proven input surface
  (`doompad` now; touch/USB keyboard remain fallback diagnostics). Combines display + input + audio; biggest jump
  (real-time render loop + interactive input). **Next safe unit after V3017:** host-only `doomgeneric`/WAD feasibility
  and asset-policy work. Do not flash a WAD-backed engine until source provenance, boot-size impact, IWAD/shareware
  asset policy, bounded runtime controls, and rollback validation are pinned in a source-build report.

**Venus (HW video decode) is NOT on this demo path** — it stays an optional, separate track for
real-video / headless-media, only if explicitly chartered later.

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

## Audio frontier history — CLOSED

The detailed V2428 → V2815 ACDB / App-Type / Magisk investigation log lived here; it is closed (audio DONE — see
the Audio section above). Full detail: `CLAUDE.md` + `docs/reports/`. No active audio directive remains.

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

## Timing instrumentation (every device-touching V-iteration, all tracks)

**Step 6 (DEVICE) must record phase-level timestamps, not just pass/fail**, whenever a sub-goal
flashes/reboots the device — this applies to every track (REPL, GPU, audio, SoftAP,
server-distro, etc.), not just one epic. Capture at minimum: `candidate_flash_start`,
`candidate_flash_done`, `candidate_boot_ready` (device/helper first responds),
`live_session_start`, `live_session_end` (the actual work — calls/commands/validation),
`rollback_flash_start`, `rollback_flash_done`, `rollback_boot_ready` (final selftest pass).
Store `timeline.json` with a single canonical top-level schema only:
`{"events":[{"name":"candidate_flash_start","timestamp_utc":"..."}, ...]}`. The top-level
object must contain only `events`; ad-hoc `phases_elapsed_sec`, `steps`, `commands`,
`phases`, or nested `timeline` subobjects are forbidden. Each event item must contain only
`name` and UTC ISO8601 `timestamp_utc`. Surface a short "## Timing" section (per-phase
elapsed + total) in the `docs/reports/...` writeup (step 7). This is cheap (a few timestamp
calls around existing phase boundaries) and lets future analysis separate **flash/reboot
overhead from actual work time** — e.g. to size a batching win (see the 2026-07-01 OPERATOR
STEER above) instead of guessing from commit cadence alone.

## 🟢 GPU epic — first-light G0→G5 ✅, triangle H0→H5 ✅, compute C0→C3 ✅, accel-2D D0→D3 ✅, monitor M0→M3 ✅, zero-copy scanout Z0→Z3 ✅ (all eye-confirmed; GPU epic CLOSED), next = SoftAP server-endgame pivot

**Persistent HARD FRAMING (inherited by every GPU rung, do not deviate):**
- **freedreno / Mesa / KGSL-direct ONLY.** The proprietary Adreno blob path (libGLESv2/EGL/OpenCL via Bionic/Android
  userspace) is structurally impossible in static native-init and is **FORBIDDEN** — never write blob/EGL bring-up
  units (same HAL/blob wall that made audio a multi-hundred-cycle slog; chasing it = overnight churn, no device payoff).
- **Legitimate GPU driver bring-up, NOT exploitation.** Does NOT reopen the CLOSED kernel-security recon: no
  CVE-2023-33047 / UAF / memory-corruption / heap-spray / exploit-dev. KGSL is used only for normal command submission.
- **Bright lines absolute:** no GDSC / regulator / PMIC / GPIO / power-rail writes; bounded/timeout-guarded probes only
  (never an unbounded blocking `open()` as a loop unit). Recoverable boot-partition flashes only, rollback `v2321`.

**DONE — G0→G5 ladder complete + device-proven (V3174→V3206, init `0.11.30`, audit `v3206-gpu-epic-completion-audit-pass`).**
What was actually proven (first-light skeleton, *not* acceleration): G0 the `/dev/kgsl-3d0` open-hang root-cause = GPU
**firmware visibility / GMU cold-start blocking, NOT a power wall** → cleanly resolved by `firmware_class.path` prep
(pure sysfs, no power write), bounded open returns; G1 KGSL context create/destroy; G2 GPU buffer alloc + mmap; G3 noop
command stream submitted → fenced → retired (GPU executes submitted packets); G4 **A6xx A2D 2D solid-fill** rendered,
CPU-readback verified (`0xa5c3f00d`); G5 GPU-filled buffer CPU-copied into the KMS dumb framebuffer and presented
(`1080x2400`, `kms-blit-presented`). All with `proprietary_blob_attempted=0`, `power_write_attempted=0`, selftest
`fail=0`. **Honest boundaries (NOT done): no triangle/3D rasterization, no shader (no ir3 compiler ran), no compute, no
zero-copy/plane scanout (G5 is CPU-copy), and no demo is GPU-accelerated yet.** This is the control-path first-light,
the foundation — not graphics.

**FIRST TRIANGLE H0→H5 = DONE + EYE-CONFIRMED (2026-06-26, init `0.11.73`).** Operator visually confirmed a GREEN
RIGHT-TRIANGLE on the panel. The long no-pixel wall's root cause was the **blend/output register group**
(`RB_BLEND_CNTL=0xffff0100`, `RB_MRT0.BLEND_CONTROL=0x08040804`, `SP_BLEND_CNTL=0x100`) — found via a built
**cffdump-diff tool** (`native_gpu_h3_cffdump_diff_v3286.py`) against a local A640 cffdump reference: V3286 diff →
V3290 first pixels (`readback_changed_count=672`) → V3292 KMS present → V3295/V3296 strict linear-triangle proof
(`strict_linear_triangle_sample_proof=1`) → V3298 visual hold. Operator nudges that landed: FS-output `0xfc` invalid
regids, A640 device-DB magic regs (`freedreno_devices.py`, necessary-not-sufficient); ruled out HLSQ-rename and the
CCU-flush hypothesis. The H0→H5 detail below is retained as the done record. **The first triangle proves "GPU draws the
screen."**

**VISIBLE COMPUTE demo C0→C3 = DONE + EYE-CONFIRMED (2026-06-26, init `0.11.77`).** Proves "GPU does
real WORK" (the multipurpose-server motivation), not just display. The ladder mirrored H0→H5, reused the proven
G0-G3 KGSL submit/fence/buffer core + the H5 KMS present path, and swapped the 3D draw for a hand-assembled ir3
COMPUTE dispatch. Same HARD FRAMING and bright lines were preserved (freedreno/KGSL-direct, NO blob/EGL/OpenCL/BLAS,
NO power writes, NO panel re-init, recoverable, rollback `v2321`).
**Operator PRE-STAGED the compute reference (2026-06-26) so C0 starts warm and does NOT repeat the triangle's 40-probe
stall** — staged at `/tmp/a90-mesa-gpu-src/a6xx_compute_dispatch_reference.txt` (+ `comp_a6xx.cc` = Mesa computerator
hand-built a6xx compute cmdstream, `comp_fd6_compute.cc`, and `kern_*.asm` = known-good ir3 compute kernels). It pins
the ordered CS dispatch envelope, CS register offsets (from local a6xx.xml), the UAV output-buffer binding, and the
ir3 `stib`/`ldib` buffer ops.
- **C0** (host-only recon): confirm/encode the CS dispatch envelope from the staged reference — `cs_restore`→`SP_CS_*`
  program (CONFIG.enabled+nuav, CNTL_0/1, WGE_CNTL, BASE, INSTR_SIZE) + `CP_LOAD_STATE6 ST6_SHADER`; UAV bind
  (`SP_CS_UAV_BASE`/`USIZE` + `CP_LOAD_STATE6 ST6_UAV`); `CP_SET_MARKER RM6_COMPUTE`; `SP_CS_NDRANGE_0..6` + KERNEL_GROUP;
  `CP_EXEC_CS(ngroups)`; WFI. **Hand-assemble the kernel from `kern_invocationid.asm`** (do NOT port the Mesa compiler);
  reuse the V3246 ir3-disasm to verify bytes.
- **C1** dispatch the trivial kernel = `kern_invocationid.asm` (writes per-invocation id to the UAV buffer). **PASS
  criterion: readback `buf[i] == i` for grid 32 (or `changed_count>0` with the per-invocation pattern).** If unchanged,
  do NOT churn "what's missing" — immediately run the execution-proof bisect (CP_MEM_WRITE sentinel to `buf[0]` before
  `CP_EXEC_CS`; drop `KGSL_CONTEXT_NO_SNAPSHOT` and read GPU fault state), then register-diff against `comp_a6xx.cc`.
- **C2** Mandelbrot-or-pattern kernel: each invocation = one pixel → `z=z²+c` bounded escape loop (float `mul.f`/`add.f`/`cmps.f`
  + predicate/branch from `kern_branch.asm`) → color buffer. **Crux.** If ir3 float+loop too fiddly, FALL BACK to a
  simpler per-pixel kernel (gradient/xy-pattern) — still proves "GPU computes per pixel and shows it" — and record it.
  **V3302 used the fallback: a 128x128 workgroup-id UAV pattern, live readback-proven.**
- **C3** blit the compute output to `/dev/dri/card0` via the proven H5 present path (reuse tile→linear if needed);
  operator visually confirmed the rainbow gradient / square-grid fractal-like pattern on the panel = compute-demo close.
  **Matrix/GPGPU math is ABSORBED here** (no standalone matmul, no blob/BLAS). Modularization stays an extraction
  (rule-of-three) after the chain's consumers exist.

**② GPU-ACCELERATED 2D = texturing + frame blit/scale (D0→D3) = DONE + EYE-CONFIRMED.** The real acceleration payoff: the demo
player (Bad Apple/DOOM) blits frames via CPU `memcpy` today; make the GPU sample + scale + composite them. Brings up
the A6xx texture pipe (TPL1 sampler + texture/IBO descriptor) and a textured fullscreen quad — reuses the proven H
triangle pipeline (VS/raster/RB) + H5 present; the new pieces are the sampler state and an ir3 FS that does `sam`
(texture sample). Same HARD FRAMING / bright lines. **Apply the proven method: PRE-STAGE the reference first** (fetch
`fd6_texture.cc` + the fd6 tex-const/IBO emit + a6xx TPL1 regs, the same way compute used computerator) so D0 starts
warm and does not repeat a stall; carry the execution-proof bisect + register-diff-against-fd6 discipline.
- **D0** (host-only recon): A6xx texture/sampler state — TPL1 sampler descriptor + texture (IBO) descriptor + how the
  FS binds them (`CP_LOAD_STATE6 ST6_TEX`/`ST6_SHADER`), and the ir3 `sam` op. Hand-assemble a textured FS (sample tex
  at interpolated UV → output); reuse the triangle's VS/raster/RB. Verify bytes with the V3246 ir3-disasm.
  **V3304 landed the Mesa fd6 texture/TPL1 reference recon; V3305 landed the D1 textured FS shader-byte gate.**
- **D1** render a fullscreen quad sampling a STATIC test texture (e.g. an uploaded checkerboard) → readback proof that
  the FS sampled it (output matches the texture pattern). PASS = sampled pattern present, not clear. Same bisect if not.
- **D2** feed a REAL frame (a demo/SD-cache frame) as the texture; GPU scales/blits it to the output buffer → readback.
  PASS = scaled frame content in the buffer.
- **D3** wire the GPU textured-quad blit into the demo player's present path (replace the CPU `memcpy` blit); present +
  measure (fps / CPU freed); operator confirms the demo still renders correctly via the GPU blit = ② close. This makes
  the GPU a real CONSUMER of existing work and is the third call site for the ③ rule-of-three extraction.

**③ on-panel GPU-accelerated SYSTEM MONITOR (M0→M3) — DONE + EYE-CONFIRMED; this visible/useful consumer DELIVERED the
rule-of-three extraction.** Rather than a bare refactor, build a glanceable on-panel system dashboard (per-core/cluster
CPU, freq, thermals, GPU, battery) as a 4th real GPU consumer; building it forces a clean reuse of the G0-G3 KGSL core +
H draw + ②D texture/blit, so the ③ extraction falls out organically (GOAL discipline: formalize the API only after the
call sites reveal its shape). Useful for the server/appliance endgame, eye-confirmable, and **bright-line-trivially safe
— ALL reads (`/proc`,`/sys`) + KMS present, NO power writes.** Same HARD FRAMING.
- **M0** (data layer, host+device, read-only): build the sampler + history ring buffers from real sysfs/proc — per-core
  `/proc/stat`; **cluster auto-detect** (`cpufreq/related_cpus` + `cpuinfo_max_freq` + `cpu_capacity` + `/proc/cpuinfo`
  MIDR `0xd0b`=A76 / `0xd05`=A55) to label cores Prime/Gold/Silver (SD855 = 1×A76@2.84 + 3×A76@2.42 + 4×A55@1.78);
  `/sys/class/thermal/*` zones; KGSL `/sys/class/kgsl/kgsl-3d0/{gpu_busy_percentage,devfreq/cur_freq,temp}`; battery
  `power_supply/battery/{current_now,voltage_now,capacity,temp}` (device-total power; per-core power NOT cleanly
  available — model-estimate only, label as such). Enumerate the actual nodes on-device first; do not hardcode.
- **M1** render a static dashboard with the EXISTING draw primitives (text + filled rects from the G4/HUD path): per-core
  usage bars labeled by cluster, freq/temp/GPU/battery readouts. Eye-confirm the layout is correct.
- **M2** GPU-accelerated LIVE graphs: scrolling history line/area graphs via the ②D textured-quad/blit path, smooth
  real-time redraw (the continuous-repaint workload that genuinely exercises the GPU 2D path = the 4th consumer).
- **M3** polish + the **③ EXTRACTION**: with H-draw + compute + ②D-blit + monitor all pulling on the same core, extract
  the shared KGSL submit/fence/buffer/texture/present layer into a clean internal helper (bounded refactor; demos +
  monitor both call it); selftest stays green, all consumers still work. Operator eye-confirm the live monitor = ③ close.
  Then ④ zero-copy, or pivot to the server-endgame (SoftAP).

**STATUS (2026-06-27) — C0 host-only recon landed as V3299; C1 shader-byte gate landed as V3300; C1 native-init source/build + live UAV readback proof landed as V3301; C2 128x128 compute pattern source/build + live readback proof landed as V3302; C3 source/build + device-presented-held proof landed as V3303 and is now operator eye-confirmed; D0 texture reference recon landed as V3304; D1 textured FS shader-byte gate landed as V3305 and closed live as V3310; D2 real SD-cache Bad Apple frame texture readback closed live as V3311; D3 source/build first landed as V3312, live exposed a fork/protocol bug, and fork-fixed V3313 passed telemetry live validation plus a no-flash 60 s eye-confirm replay hold. V3314 added high-contrast `--start-frame 515` plus a stricter final-frame semantic gate; live presentation, hold, KMS, and health were clean, but exact source-pixel validation missed one scaled-edge sample (`semantic_match_count=63`, `semantic_mismatch_count=1`). V3315 fixed that validation-design gap with a bounded 3x3 source-neighborhood tolerance and passed live: `semantic_sample_count=64`, `match_count=64`, `exact_match_count=63`, `edge_tolerant_match_count=1`, `mismatch_count=0`, `output_other_count=0`, post-probe `selftest fail=0`, no GPU fault-filter match. The operator then visually confirmed the held GPU-blit output: "배드애플 보였다 프레임은 정상적으로 나오는거 같았다". Rung ② is DONE + EYE-CONFIRMED. NEXT = ③ modularization/extraction backlog.**

**STATUS (2026-06-27 M0 kickoff) — V3316 completed the required read-only node enumeration for the on-panel system
monitor. The device exposes CPU topology/frequency, `/proc/stat`, memory/load, KGSL GPU busy/frequency/temp, thermal
zones, and battery/power-supply nodes without writes. SD855 clusters are discoverable from `cpufreq/related_cpus` plus
max frequency as Silver `0-3` @ 1.7856 GHz, Gold `4-6` @ 2.4192 GHz, and Prime `7` @ 2.8416 GHz; implementation must derive
those labels dynamically and tolerate absent/empty thermal nodes. No boot artifact was built and no flash was run. NEXT =
M0 sampler + history ring probe telemetry (`gpu.m0.monitor.*`).**

**STATUS (2026-06-27 M0 live) — V3317 implemented `a90_monitor.c/.h` plus `gpu m0-monitor-sampler-probe`, built
`boot_linux_v3317_gpu_m0_monitor_sampler.img` (SHA256
`47dcc28d9a9de86a56258bfd066839d5d3e3c93f9c5b55e6de266d3ffb5ba813`), flashed through `native_init_flash.py`, and passed
live validation. Probe telemetry reported `cpu.count=8`, `cluster.count=3`, `history.count=3`, derived labels Silver
`0-3`, Gold `4-6`, Prime `7`, KGSL model `Adreno640v2`, GPU freq/temp, thermal zone summary, battery readouts, and
`power_write_attempted=0` / `kms_present_attempted=0`; post-probe selftest stayed `pass=12 warn=1 fail=0`. M0 is DONE.
NEXT = M1 static dashboard with existing draw primitives.**

**STATUS (2026-06-27 M1 live) — V3318 implemented `gpu m1-monitor-dashboard-probe` using the M0 sampler plus existing
draw/KMS primitives, built `boot_linux_v3318_gpu_m1_monitor_dashboard.img` (SHA256
`e5a3905e94f65d8a8a071955cea92ddd3e0037c0c3839946f9c5c2357fdd6858`), flashed through `native_init_flash.py`, and passed
live validation. Probe telemetry reported `cpu.count=8`, `cluster.count=3`, `history.count=3`, KGSL model
`Adreno640v2`, framebuffer `1080x2400` stride `4352`, `kgsl_submit_attempted=0`, `kms_present_attempted=1`,
`present_rc=0`, `hold_elapsed_ms=5000`, and `result=dashboard-presented`; post-probe selftest stayed
`pass=12 warn=1 fail=0`. M1 is DONE. NEXT = M2 GPU-accelerated live graphs via the 2D textured-quad/blit path.**

**STATUS (2026-06-27 M2 live) — V3319 implemented `gpu m2-monitor-live-graph-probe`, built
`boot_linux_v3319_gpu_m2_monitor_live_graphs.img` (SHA256
`4b78660fa1721006ec57f1295a02e65f32546638823f2c537a01dddc30b99fee`), flashed through `native_init_flash.py`, and passed
live validation. Probe telemetry reported the live monitor mono1 graph source (`480x360` stride `60`) scaled through the
proven D3 KGSL textured-quad path to a `960x720` target, `kgsl_submit_attempted=1`, `kms_present_attempted=1`,
`presented=12`, `present_rc=0`, `graph_points=13`, `graph_pixels_set=2724`, `cpu.count=8`, `cluster.count=3`, KGSL model
`Adreno640v2`, `pm4_dwords=409`, `semantic.sample_count=64`, `semantic.match_count=64`, `semantic.mismatch_count=0`,
`semantic.output_other_count=0`, and `result=monitor-live-graph-pass`; post-probe selftest stayed
`pass=12 warn=1 fail=0`. M2 is DONE. NEXT = M3 polish + shared KGSL submit/fence/buffer/texture/present extraction.**

**STATUS (2026-06-27 M3 live telemetry) — V3320 extracted the D3-named 2D present path into the shared
`gpu_2d_present_*` layer and routed both D3 video texture present plus M2 live monitor graphs through
`gpu_2d_present_create_session` / `gpu_2d_present_render_frame_to_kms`. Built
`boot_linux_v3320_gpu_m3_monitor_extraction.img` (SHA256
`dd2f4fa31b81340ad35477cb0d23655b9b837887272a4224926311e04ef43ea2`), flashed through
`native_init_flash.py`, and passed telemetry live validation. `gpu m3-monitor-extraction-probe --frames 12
--interval-ms 200 --timeout-ms 60000 --hold-ms 5000 --materialize-devnode` reported
`gpu.m3.extract.layer=gpu_2d_present_v1`, shared core `bo-map,sync-to-gpu,submit-wait,linear-readback,kms-copy`,
M2 delegate `result=monitor-live-graph-pass`, `presented=12`, `present_rc=0`, `semantic.match_count=64`,
`semantic.mismatch_count=0`, `semantic.output_other_count=0`, and
`result=shared-2d-present-monitor-pass`. Focused D3 regression with Bad Apple frame 515 for 3 frames also passed:
`extraction_layer=gpu_2d_present_v1`, `result=video-texture-present-pass`, `presented=3`, `present_rc=0`,
`semantic.match_count=64`, `semantic.output_other_count=0`; the operator confirmed the Bad Apple path was visible
and frames looked normal. Post-probe selftest stayed `pass=12 warn=1 fail=0`. M3 telemetry is DONE; explicit operator
eye-confirmation of the held live monitor panel remains if the ③ rung is to be marked eye-confirmed/closed.**

**STATUS (2026-06-27 M3 held replay) — No-flash V3320 live monitor replay was run for eye-confirmation. A 60 s hold
attempt intentionally hit the same `--timeout-ms 60000` budget and killed the child at timeout; follow-up selftest
remained `pass=12 warn=1 fail=0`. A second replay with `--hold-ms 45000` completed cleanly in `47454ms`:
`gpu.m3.extract.layer=gpu_2d_present_v1`, M2 delegate `result=monitor-live-graph-pass`, `presented=12`,
`graph_pixels_set=2732`, `cpu.count=8`, `cluster.count=3`, `semantic.match_count=64`, `semantic.mismatch_count=0`,
`semantic.output_other_count=0`, and `result=shared-2d-present-monitor-pass`; post-replay selftest again stayed
`pass=12 warn=1 fail=0`. A third replay with `--hold-ms 50000` also completed cleanly in `53661ms` with
`presented=12`, `graph_pixels_set=2722`, `semantic.match_count=64`, `semantic.output_other_count=0`, and post-replay
selftest `pass=12 warn=1 fail=0`. Operator eye-confirmation of the held live monitor panel is still pending before
marking the ③ monitor rung eye-confirmed/closed.**

**STATUS (2026-06-27 M3 60s hold budget fix) — V3321 fixed the V3320 visual-hold rough edge by splitting the monitor
parent watchdog into render timeout + visual hold budget + 5 s margin. Built
`boot_linux_v3321_gpu_m3_hold_timeout_budget.img` (SHA256
`48050046e743694d6e74ed6123b49f87d5d2dd0f87a44bd14e3d548431ca9a49`), flashed through `native_init_flash.py`, and
passed live validation. After hiding the auto menu, `gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200
--timeout-ms 60000 --hold-ms 60000 --materialize-devnode` reported `parent_timeout_ms=125000`,
`timeout_split=render-plus-visual-hold`, `timed_out=0`, `child_killed=0`, M2 delegate
`result=monitor-live-graph-pass`, `presented=12`, `present_rc=0`, `graph_pixels_set=2733`, `cpu.count=8`,
`cluster.count=3`, `semantic.match_count=64`, `semantic.mismatch_count=0`, `semantic.output_other_count=0`, and
`result=shared-2d-present-monitor-pass`; duration was `62502ms`. Focused D3 Bad Apple regression also stayed green
(`result=video-texture-present-pass`, `presented=3`, `present_rc=0`, `semantic.match_count=64`,
`semantic.output_other_count=0`) and post-probe selftest stayed `pass=12 warn=1 fail=0`. A no-flash operator replay then
confirmed the human-facing close: the first `hide` run showed the monitor graph but had possible auto-HUD interference;
the second run stopped auto-HUD with `stophud` first and again passed (`presented=12`, `timed_out=0`, `child_killed=0`,
`graph_pixels_set=2720`, `semantic.match_count=64`, `semantic.mismatch_count=0`, `semantic.output_other_count=0`,
duration `63588ms`, follow-up selftest `pass=12 warn=1 fail=0`). The operator confirmed: "보인다 유지되는거 같다".
The ③ monitor rung is DONE + EYE-CONFIRMED.**

**CLOSED RUNG HISTORY = ④ zero-copy KMS/dmabuf scanout (Z0→Z3).** This rung made the GPU-rendered
buffer the scanout buffer directly, with no CPU copy on the present path. The final solution is V3335:
full-panel KMS dumb scanout buffer imported into KGSL, rendered by the GPU, presented through primary
`SETCRTC`, then restored to the previous base framebuffer. Bright lines stayed unchanged: KMS present +
GPU only, NO backlight/PMIC/PWM/regulator/GDSC writes, NO panel re-init, recoverable boot-partition
flash, rollback `v2321`.
- **Z0 (host-only recon).** From the staged Mesa/freedreno sources in `/tmp/a90-mesa-gpu-src/` (fd6_gmem/resolve, the
  `fdl6_*` layout helpers, `a6xx.xml` RB/scanout regs) + the existing `a90_kms.c` modeset path, pin: what tiling/UBWC
  modifier the GPU writes for the demo/monitor color buffer, what DRM format-modifier the A90 display plane accepts on
  `/dev/dri/card0` (enumerate `drmModeGetPlane`/IN_FORMATS read-only), and whether a shared linear buffer or a tiled
  buffer with a matching modifier is the feasible zero-copy path. Enumerate the actual on-device plane formats — do not
  hardcode. Output: a written zero-copy feasibility decision + the exact buffer allocation/modifier recipe.
- **Z1 (allocator bridge proof).** Prove one shared scanout-linear allocation path before any present: a buffer that KMS
  can accept as an `XBGR8888` framebuffer and that can plausibly become the GPU render target. Keep the CPU-copy present
  path as the live fallback.
- **Z2 (shared GPU target + live present).** Make that shared buffer the actual GPU output target, then page-flip the
  GPU-rendered buffer directly to scan-out for one of the existing consumers
  (monitor graph or Bad Apple blit) with the CPU copy removed; measure CPU/fps/latency delta vs the copy path; confirm
  no GPU fault, `selftest fail=0`, rollback to `v2321` clean.
- **Z3 (eye-confirm + close).** Operator visually confirms the zero-copy consumer renders correctly on-panel and holds;
  record the measured efficiency win. Eye-confirm = ④ closed = **GPU epic closed**. Then re-charter to SoftAP.**

**STATUS (2026-06-27 Z0 modifier recon) — V3322 completed the no-flash display-side zero-copy feasibility pass.**
Read-only helper `a90_drm_modifier_probe_z0` was built as a static AArch64 binary
(`sha256=4e79afa9d7bdb470f8038876e4973dbcf60ae6f47a6f980036709549e6bb937a`), installed temporarily via
NCM/bridge-nc, and queried `/dev/dri/card0` only. Live result on resident `0.11.92`:
`plane_count=16`, `compatible_active_crtc=16`, `rect_props=16`, `DRM_CAP_ADDFB2_MODIFIERS=1`,
`DRM_CAP_PRIME=0x3 import=1 export=1`, all 16 planes expose `XBGR8888`, but no plane exposes an
`IN_FORMATS` modifier blob (`rc=-61`, modifier counts all zero). Therefore the explicit
`QCOM_TILED3`/UBWC modifier route is NOT evidenced on this display stack. The only safe Z1 route is
**implicit/legacy linear scanout**: keep `DRM_FORMAT_XBGR8888`, 960x720, stride 3840, and first prove
one shared scanout-linear allocation path (`msm` DRM GEM `MSM_BO_SCANOUT | MSM_BO_WC` and GEM/iova or
dmabuf bridge) before removing the current KGSL-linear → KMS CPU copy. If the existing KGSL path cannot
target/import that shared GEM/dma-buf, pivot the submit path to DRM `msm` for this rung or close
zero-copy as infeasible on KGSL-only. Report:
`docs/reports/NATIVE_INIT_V3322_GPU_Z0_ZERO_COPY_MODIFIER_RECON_2026-06-27.md`.**

**STATUS (2026-06-27 Z1 shared-linear allocator preflight) — V3323 completed the no-flash DRM msm
shared-linear preflight.** Helper `a90_drm_msm_shared_linear_probe_z1` was built static
(`sha256=d5e86d6b2ab180374977c14817867894d42538bf26ffe8817f41ba422950a4d2`), installed temporarily via
NCM/bridge-nc, and ran on resident `0.11.92` with pre/post `selftest fail=0`. Live result:
`DRM_CAP_DUMB_BUFFER=1`, `DRM_CAP_ADDFB2_MODIFIERS=1`, `DRM_CAP_PRIME=0x3 import=1 export=1`;
`DRM_IOCTL_MSM_GEM_NEW` with `MSM_BO_SCANOUT | MSM_BO_WC` succeeded for `960x720`, stride `3840`,
bytes `2764800`; `MSM_INFO_GET_OFFSET` succeeded; mmap/writeback samples succeeded; PRIME
export/import succeeded; `DRM_IOCTL_MODE_ADDFB2` accepted the GEM as `XBGR8888`; cleanup `RMFB` and
GEM close succeeded. `MSM_INFO_GET_IOVA` and `MSM_INFO_GET_FLAGS` returned `-22`, so Z1 proves the
display-side shared-linear scanout allocation path but **does not yet prove current KGSL submit can
directly target that memory**. Active next: find/prove a KGSL dma-buf/import-or-target route for this
GEM, or pivot the zero-copy source unit to DRM `msm` submit; do not remove the current KGSL→KMS CPU
copy fallback until a shared GPU target is proven. Report:
`docs/reports/NATIVE_INIT_V3323_GPU_Z1_SHARED_LINEAR_PREFLIGHT_2026-06-27.md`.**

**STATUS (2026-06-27 Z2 KGSL dma-buf import preflight) — V3324 proved the shared buffer reaches
both KMS and KGSL.** Helper `a90_kgsl_dmabuf_import_probe_z2` was built static
(`sha256=02ab83482f3f86231e65015a8cfe963b4fc7deebd5e12d888d7ab209da719d15`), installed temporarily
via NCM/bridge-nc, and ran no-flash/no-present/no-submit on resident `0.11.92` with pre/post
`selftest fail=0`. Live result: DRM msm `MSM_BO_SCANOUT | MSM_BO_WC` GEM for `960x720`, stride
`3840`, bytes `2764800` created and mmap-sampled; PRIME export succeeded; `ADDFB2` accepted it as an
`XBGR8888` KMS framebuffer; KGSL opened `/dev/kgsl-3d0`; `IOCTL_KGSL_GPUOBJ_IMPORT` with
`KGSL_USER_MEM_TYPE_DMABUF` imported the same PRIME fd (`id=1`, flags `0x140080`); `GPUOBJ_INFO`
returned `gpuaddr=0x500000000`, `size=2764800`, `va_len=2764800`; KGSL free, `RMFB`, and DRM handle
close all succeeded. This proves the allocator/import bridge needed for zero-copy. Next source unit:
replace the current `session->linear` KGSL allocation with the imported scanout GEM for the guarded
render target, then page-flip it only after readback/telemetry proves the imported BO was written
correctly; keep CPU-copy fallback. Report:
`docs/reports/NATIVE_INIT_V3324_GPU_Z2_KGSL_DMABUF_IMPORT_PREFLIGHT_2026-06-27.md`.**

**STATUS (2026-06-27 Z2 imported scanout render-target source build) — V3325 built the first guarded
native-init path that renders into a KMS-acceptable scanout GEM imported into KGSL.** Source adds
`gpu z2-imported-scanout-target-probe [--timeout-ms N] [--materialize-devnode]`. The child probe
creates a DRM msm `MSM_BO_SCANOUT | MSM_BO_WC` `960x720`/stride `3840` linear GEM, mmap-clears it,
exports PRIME, attaches it as an `XBGR8888` framebuffer with `ADDFB2`, imports the same fd through
KGSL `GPUOBJ_IMPORT` with `KGSL_USER_MEM_TYPE_DMABUF`, replaces the M3 shared `session->linear`
target with that imported object, submits the existing textured monitor graph PM4 into the imported
target, then validates readback semantics without a KMS copy or present. Static validation passed:
`py_compile`, focused V3325 unittest, V3321 M3 regression unittest, `git diff --check`, AArch64
compile smoke, and full boot build. Boot artifact:
`workspace/private/inputs/boot_images/boot_linux_v3325_gpu_z2_imported_scanout_target.img`
(`sha256=3c0d2180627c6fd35f8997e5a720931bb44c3793e83929a5ad66f8b6dd341112`, size `63778816`
bytes). Live flash/health passed on `0.11.93`; the first run was correctly blocked by a busy menu
(`rc=-16`) until `hide`, then the probe showed the functional proof: `drm.open_rc=0`,
`drm.msm_gem_new_rc=0`, `drm.prime_export_rc=0`, `drm.addfb2_rc=0`, KGSL import/info `0`,
`gpuaddr=0x500300000`, `render_rc=0`, `pm4_dwords=409`, `changed_count=691200`, semantic exact match
`64/64`, output-other `0`, no KMS copy/present, cleanup `0`, and post-probe `selftest fail=0`.
The only failing field was the pass-gate self-reference (`summary.result_rc` checked before the child
assigned final `result_rc`), so V3325 is a live functional PASS with a reportable gate false negative.
Reports: `docs/reports/NATIVE_INIT_V3325_GPU_Z2_IMPORTED_SCANOUT_TARGET_SOURCE_BUILD_2026-06-27.md`
and `docs/reports/NATIVE_INIT_V3325_GPU_Z2_IMPORTED_SCANOUT_TARGET_LIVE_FALSE_NEGATIVE_2026-06-27.md`.**

**STATUS (2026-06-27 Z2 imported scanout render-target pass gate live) — V3326 fixed the
V3325 pass predicate and closed the shared GPU target proof.** Source removes the premature
`summary.result_rc == 0` predicate from `gpu_z2_imported_target_summary_passed()` while leaving the
render path unchanged. Static validation passed (`py_compile`, V3326 focused unittest, V3325 source
contract, V3321 M3 regression, `git diff --check`, full boot build). Boot artifact:
`workspace/private/inputs/boot_images/boot_linux_v3326_gpu_z2_imported_scanout_pass_gate.img`
(`sha256=9a63d1f1c8c2ad8aac6cdf63232d71466b2bcf97b5bec5ad7fb62f45601d39d4`, size `64978944`
bytes). Rollback images were re-confirmed, flash used only `native_init_flash.py`, and live health
passed on `A90 Linux init 0.11.94 (v3326-gpu-z2-imported-scanout-pass-gate)` with `selftest fail=0`.
Live command `gpu z2-imported-scanout-target-probe --timeout-ms 60000 --materialize-devnode` returned
`gpu.z2.import.result=z2-imported-scanout-render-target-pass`, `result_rc=0`, DRM msm scanout GEM
create/export/`ADDFB2` all `0`, KGSL dma-buf import/info `0`, `gpuaddr=0x500300000`,
`render_rc=0`, `pm4_dwords=409`, `graph_pixels_set=2178`, `changed_count=691200`, semantic exact
match `64/64`, output-other `0`, `kms_copy_attempted=0`, `kms_present_attempted=0`, elapsed
`39525781ns`, and post-probe `selftest fail=0`. **Z2 shared scanout-linear GPU target is proven.**
Active next: Z3 page-flip/present the same imported FB directly, hold it for operator eye-confirm,
and record the CPU-copy removal/latency delta before closing the GPU epic. Reports:
`docs/reports/NATIVE_INIT_V3326_GPU_Z2_IMPORTED_SCANOUT_PASS_GATE_SOURCE_BUILD_2026-06-27.md` and
`docs/reports/NATIVE_INIT_V3326_GPU_Z2_IMPORTED_SCANOUT_PASS_GATE_LIVE_2026-06-27.md`.**

**OPERATOR REDIRECT (2026-06-27, Z3 present wall) — STOP iterating overlay-plane present variants;
present the imported scanout FB on the PRIMARY crtc via the already-proven SETCRTC path.** V3327–V3332
all failed the same step: presenting the imported MSM_BO_SCANOUT FB on a DPU **overlay** plane returned
`EACCES` then `SETPLANE/atomic EINVAL` (`-13` → `-22`). GPU render/import/semantic were all clean
(`64/64`); the failure is the DPU SSPP overlay-plane format/zpos/rect constraint, **not** a zero-copy
problem. Do NOT keep cycling legacy-setplane / master-fd / atomic / overlay-filter / overlay-state
variants — that is the overlay rabbit hole. Instead reuse the working full-screen present:
`a90_kms.c` `kms_present()` already does `DRM_IOCTL_MODE_SETCRTC` on the **primary** crtc with the
full panel mode (`mode.hdisplay × mode.vdisplay`) and gives `base_present_rc=0`. For Z3, allocate the
imported scanout GEM at **full panel size** (not 960×720 at an overlay offset), GPU-render the monitor
graph into it, `ADDFB2` (already `rc=0`), then present via that same base path with
`setcrtc.fb_id = imported_fb_id` — i.e. swap the dumb `fb_id` for the imported scanout `fb_id` in the
existing primary SETCRTC. That IS zero-copy (GPU output BO == scanout BO, no `memcpy`) and avoids the
overlay SSPP entirely. Keep the CPU-copy dumb base as live fallback. Then hold for operator eye-confirm
and record the CPU-copy-removal/latency delta = ④ close = GPU epic closed. If primary SETCRTC with an
imported PRIME/dmabuf FB itself fails, THAT is the real new datum to report — not another overlay variant.**

**STATUS (2026-06-27 Z3 primary SETCRTC pass + eye-confirmed) — V3335 implemented, live-validated,
and operator-confirmed the primary-CRTC zero-copy route after the overlay wall.** Source adds
`gpu z3-imported-scanout-primary-probe`, an `a90_kms_present_external_fb()` helper, dynamic full-panel
target overrides for the shared GPU 2D presenter, and stride-aware semantic/readback sampling for KMS
dumb pitch padding. Built `boot_linux_v3335_gpu_z3_primary_setcrtc.img`
(`sha256=e7e0240e7894e9bd54a0a4fd5a3bf267b126097a5177ccd17686076528ea736b`), flashed only through
`native_init_flash.py`, and booted `A90 Linux init 0.11.103 (v3335-gpu-z3-primary-setcrtc)` with
post-flash selftest `pass=12 warn=1 fail=0`. After `stophud`, live command
`gpu z3-imported-scanout-primary-probe --timeout-ms 60000 --hold-ms 12000 --materialize-devnode`
completed device-side in `12243ms` with `result=z3-imported-scanout-primary-setcrtc-pass`: full-panel
KMS dumb scanout target `1080x2400`, stride `4352`, bytes `10444800`; PRIME export `0`; KGSL dma-buf
import/info `0`; `render_rc=0`; semantic `64/64` exact; `kms_copy_attempted=0`; primary
`SETCRTC present_rc=0`; base FB `restore_rc=0`; cleanup `RMFB/dumb_destroy/close_prime/close_drm_fd`
all `0`; follow-up selftest stayed `pass=12 warn=1 fail=0`. The first host `a90ctl` read timed out
before the 12 s hold finished, but the bridge capture and `last` confirmed command rc `0`. The
operator then confirmed the held primary SETCRTC graph was visible and remained on-panel:
"보인다 유지되는거 같다". **Z3 is PASS + EYE-CONFIRMED; ④ zero-copy scanout is CLOSED, and the GPU
epic is DONE.** Reports:
`docs/reports/NATIVE_INIT_V3335_GPU_Z3_PRIMARY_SETCRTC_SOURCE_BUILD_2026-06-27.md` and
`docs/reports/NATIVE_INIT_V3335_GPU_Z3_PRIMARY_SETCRTC_LIVE_2026-06-27.md`.**

## ✅ DONE — REPL post-epic guarded live-call proof — `is_scm_armv8` cached SCM convention bool

> ### ✅ STATUS (2026-07-01 live pass) — `is_scm_armv8` promoted only under cached-path guard
>
> Codex revisited the previously rejected Qualcomm SCM convention query without loosening the safety
> gate. The old rejection remains correct for the cold path: if `scm_version == SCM_UNKNOWN`,
> `is_scm_armv8()` executes SMC probing and writes SCM convention state. The new proof makes that
> hazard load-bearing: it pre-peeks the cached `scm_version` word and refuses to call unless the value
> is already a known nonzero enum, so the function can only take the cached read-only bool path.
>
> Static validation pinned `is_scm_armv8=0xffffff800869493c` by `export-recovery`, direct BL xrefs
> `29`, source declaration `extern bool is_scm_armv8(void)` from `include/soc/qcom/scm.h:112`,
> implementation `drivers/soc/qcom/scm.c:566`, and next boundary `scm_call2 +0xe8`. Body gates cover
> the cached `scm_version` load/branch/compare/cset/ret and SMC-path sentinel words so the runtime
> guard protects the exact branch it is avoiding.
>
> Host validation passed: `py_compile`; focused classifier/source/fake-proof tests (`Ran 4 tests`,
> `OK`); full fake `SelftestIntegrationTests` (`Ran 124 tests`, `OK`); classifier CLI over
> `is_scm_armv8` (`SAFE-SCALAR=1`, seed count `131`). Live validation obeyed the flash gate:
> rollback/fallback/TWRP artifacts were confirmed, baseline v2321 `version/status/selftest` passed,
> the exact v1-repl candidate (`b846ae9f...`) flashed through `native_init_flash.py` with matching
> readback SHA, candidate `version/selftest/status` passed, REPL selftest passed, guarded call-proof
> passed, and rollback to v2321 completed with final `version/selftest/status` passing
> (`selftest pass=11 warn=1 fail=0`).
>
> Live result: runtime preflight observed cached `scm_version=0x3` (`SCM_ARMV8`), expected return
> `0x1`, and `is_scm_armv8()` returned stable bool `0x1` twice. Post-call peek confirmed
> `scm_version` stayed `0x3`. The proof would abort before call if the cache were `SCM_UNKNOWN`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-is-scm-armv8-20260630T230729Z/timeline.json`:
> candidate preflash marker-fail attempt `0.097s`, candidate flash helper `63.752s`, candidate flash
> start to explicit boot ready `73.642s`, candidate explicit health `1.38s`, REPL selftest `5.68s`,
> live proof `6.54s`, live session total `28.268s`, rollback flash helper `63.684s`, rollback flash
> start to helper boot ready `71.936s`, final explicit health `20.68s`, final standalone version retry
> `0.46s`, and candidate start to final health done `249.686s`.
>
> Function-map entry is promoted only under
> `auto_call_policy=cached-path-proof-only-not-mass-call`, no arguments, cached SCM convention read,
> cleanup `n/a-scalar-cached-read-only`. Raw slide/runtime values stayed private. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_IS_SCM_ARMV8_2026-07-01.md`.

## ✅ DONE — REPL post-epic batch live-call proof — Samsung SMEM DDR revision getters

> ### ✅ STATUS (2026-07-01 live pass) — `get_ddr_revision_id_1/2` promoted under corrected raw/low8 contract
>
> Codex revisited the previously parked `get_ddr_revision_id_1` after the operator corrected the
> selection rule: adjacent/similar candidates should be batched when they share the same shape. The
> bounded unit selected the adjacent Samsung SMEM DDR revision getters `get_ddr_revision_id_1` and
> `get_ddr_revision_id_2`, both no-argument read-only scalar getters. The old one-target failure was
> not a call-routing or safety failure; it was a public contract mismatch because the REPL captures
> raw x0 while the source-level `uint8_t` value is the stable low byte of the current-image raw word.
>
> Static validation pinned `get_ddr_revision_id_1=0xffffff80086ef82c` and
> `get_ddr_revision_id_2=0xffffff80086ef8ec`, both by `disasm-signature+xref+map`, both with direct
> BL xrefs `1`, source declarations `extern uint8_t get_ddr_revision_id_1(void)` and
> `extern uint8_t get_ddr_revision_id_2(void)` from `include/linux/samsung/sec_smem.h:196-197`, no
> pointer args, and no early arg-pointer derefs. Body gates cover the `qcom_smem_get` call, field
> load, null-return path, ret, next-symbol guard, and the `get_ddr_revision_id_1` shift/extract return
> transform that explains raw `0x60106`.
>
> Host validation passed: `py_compile`; focused classifier/source/seed/fake-batch tests
> (`Ran 4 tests`, `OK`); full `tests/test_a90_repl.py` (`Ran 170 tests`, `OK`); classifier CLI over
> the two selected targets (`SAFE-SCALAR=2`); and `git diff --check`. Live validation obeyed the flash
> gate: rollback/fallback/TWRP artifacts were confirmed, baseline v2321
> `version/status/selftest` passed, the exact v1-repl candidate
> (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`) flashed through
> `native_init_flash.py` with matching readback SHA, candidate `version/selftest/status` passed, REPL
> selftest passed, both targets were proved in one `call-proof-batch` session, and rollback to v2321
> completed with final `version/selftest/status` passing (`selftest pass=11 warn=1 fail=0`).
>
> Live result: `get_ddr_revision_id_1()` returned stable raw `0x60106` twice, source-level low8
> `0x6`. `get_ddr_revision_id_2()` returned stable raw `0x601` twice, source-level low8 `0x1`.
>
> Timing was recorded per the 2026-07-01 timing rule in
> `workspace/private/runs/kernel/live-call-proof-ddr-revision-batch-20260630T224417Z/timeline.json`:
> candidate flash helper `64.216s`, candidate flash start to explicit boot ready `64.669s`, candidate
> explicit health total `1.156s`, REPL selftest `185.924s`, live batch proof `9.265s`, live session
> total `195.194s`, rollback flash helper `64.845s`, rollback flash start to explicit boot ready
> `65.257s`, final explicit health total `1.089s`, and candidate start to rollback ready `325.836s`.
>
> Function-map entries are promoted only under the same-session batch contract:
> `auto_call_policy=same-session-batch-proof-only-not-mass-call`, no arguments, read-only Samsung SMEM
> DDR revision fields, cleanup `n/a-scalar-smem-read-only`. Raw slide/runtime values stayed private.
> This supersedes the earlier 2026-06-30 `get_ddr_revision_id_1` PARKED block; that block remains as
> historical evidence of the contract mismatch. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_DDR_REVISION_BATCH_2026-07-01.md`.

## ✅ DONE — REPL post-epic batch live-call proof — FS/VFS scalar state getters

> ### ✅ STATUS (2026-07-01 live pass) — same-session FS state batch after BATCH correction
>
> Codex followed the corrected "adjacent/similar candidates in one batch" rule and selected two
> no-argument FS/VFS state getters with the same read-only scalar shape: `get_max_files` and
> `get_nr_dirty_inodes`. `get_ddr_revision_id_1` stayed parked because its prior raw return violated
> the proposed `uint8_t` contract; raw-spinlock/blockdev neighbors stayed out of this batch.
>
> Static validation pinned `get_max_files=0xffffff800829005c` by `export-recovery`, direct BL xrefs
> `1`, next symbol `proc_nr_files` at `+0x18`, source declaration
> `extern unsigned long get_max_files(void)`, and exact 6-word body match. `get_nr_dirty_inodes` is
> pinned at `0xffffff80082b1234` by `disasm-signature+xref+map`, direct BL xrefs `4`, next symbol
> `proc_nr_inodes` at `+0xf8`, source declaration `extern long get_nr_dirty_inodes(void)`, and exact
> 62-word body match. Both targets are `SAFE-SCALAR`, no pointer args, no early arg-pointer derefs,
> and no context calls.
>
> Host validation passed: `py_compile`; focused classifier/fake-batch/batch-CLI/seed-inventory tests;
> full `tests/test_a90_repl.py` (`Ran 169 tests`, `OK`); and classifier CLI over the two targets
> (`SAFE-SCALAR=2`). Live validation obeyed the flash gate. Attempt 1 flashed the exact v1-repl
> candidate and rolled back cleanly but stopped before target calls after a redundant candidate
> `a90ctl selftest` hit serial `AT` echo and missed the `A90P1 END` marker. Attempt 2 flashed the same
> candidate, passed helper selftest, passed REPL selftest, proved both targets in one
> `call-proof-batch` session, and rolled back to v2321 with final sequential
> `version/status/selftest` passing (`selftest pass=11 warn=1 fail=0`) after host-side bridge resync.
>
> Live result: `get_max_files()` returned stable `0x71c6a` twice. `get_nr_dirty_inodes()` returned
> sane nonnegative dirty-inode approximations `0x6c2a` then `0x6c29`; short-repeat drift is allowed by
> the contract.
>
> Timing was recorded per the 2026-07-01 timing rule. Attempt 1: candidate flash helper `64.297s`,
> explicit health before serial parse failure `11.002s`, live proof not reached, rollback flash helper
> `80.313s`, rollback explicit health `1.125s`. Attempt 2: candidate flash helper `67.083s`,
> candidate status `0.336s`, REPL selftest `171.114s`, live batch proof `8.819s`, rollback flash
> helper `63.646s`, final bridge resync plus explicit health `2.918s`. Attempt 2 timeline is
> reconstructed from helper timestamps plus command wall time because it was continued manually rather
> than through a single wrapper-owned monotonic timeline.
>
> Function-map entries are promoted only under the same-session batch contract:
> `auto_call_policy=same-session-batch-proof-only-not-mass-call`, no arguments, read-only FS/VFS scalar
> state, cleanup `n/a-fs-vfs-read-only`. Raw slide/runtime values stayed private. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_FS_STATE_BATCH_2026-07-01.md`.

## ✅ DONE — REPL one-target live-call proof — kernel wall-clock seconds getter

> ### ✅ STATUS (2026-07-01 live pass) — `get_seconds` one-target proof
>
> Codex selected a new read-only timekeeping state getter after the `get_diplayport_status`
> proof: `get_seconds`. Host static gates passed before live call: `py_compile`; focused
> classifier/source/fake-proof tests (`Ran 3 tests`, `OK`); full `tests/test_a90_repl.py`
> (`Ran 168 tests`, `OK`); and classifier CLI over the selected/parked set showed
> `get_seconds` as `SAFE-SCALAR` while `get_host_os_type` and `get_pkey_press` remained
> `DENY`/parked.
>
> Static identity is pinned to `get_seconds=0xffffff800816185c` by `export-recovery`,
> direct BL xrefs `51`, next symbol `__current_kernel_time` at `+0x18`, exact 6-word
> current-image body match (`b0016fe8 912c0108 f9403500 d65f03c0 d503201f 00be7bad`),
> no pointer args, no pre-call argument pointer derefs, and source declaration
> `unsigned long get_seconds(void)` from `include/linux/timekeeping.h:26`.
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs were confirmed, bridge
> healthy, baseline v2321 `version/status/selftest` passed, the exact v1-repl candidate
> (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`) flashed through
> `native_init_flash.py` with matching readback SHA, candidate `version/selftest/status`
> passed after bridge restart + settle, and `a90_repl.py call-proof get_seconds` returned
> nondecreasing wall-clock seconds `0x5a51e676` then `0x5a51e677` under the fixed no-argument
> read-only contract (`delta <= 2s`). Candidate post-proof selftest stayed `fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule: candidate flash helper `63.673s`,
> candidate flash start to boot ready `84.795s`, live proof session `5.820s`, rollback flash
> helper `65.264s`, rollback flash start to boot ready `87.284s`, total candidate-start to
> rollback-ready `178.345s`.
>
> Rollback to clean v2321 completed through `native_init_flash.py` with matching readback SHA.
> Final explicit `version/selftest/status` passed (`selftest pass=11 warn=1 fail=0`). Function-map
> entry is promoted only under the one-target contract:
> `auto_call_policy=one-target-proof-only-not-mass-call`, no arguments, return nondecreasing
> kernel wall-clock seconds with short-run delta `<=2s`, cleanup `n/a-scalar-read-only`.
> Raw slide/runtime values stayed private. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_SECONDS_2026-07-01.md`.

## ⚠️ STOPPED — REPL scheduler counter batch second live-call proof attempt aborted before live proof

## ✅ DONE — REPL one-target live-call proof — CCIC DisplayPort status getter

> ### ✅ STATUS (2026-07-01 live pass) — `get_diplayport_status` one-target proof
>
> Codex selected one new read-only state getter outside the stopped scheduler-counter sub-goal:
> `get_diplayport_status` (symbol/source spelling is `diplayport`). Host static gates passed before
> live call: `py_compile`; focused `tests.test_a90_repl` classifier/source/fake-proof tests
> (`Ran 14 tests`, `OK`); and classifier CLI over the selected/parked set showed
> `get_diplayport_status` as the only `SAFE-SCALAR` target while `get_ddr_revision_id_2`,
> `get_debug_reset_header`, `get_empty_filp`, and `get_dump_page` stayed `DENY`/parked.
>
> Static identity is pinned to `get_diplayport_status=0xffffff80095a5f14` by
> `disasm-signature+xref+map`, direct BL xrefs `1`, next symbol `process_check_accessory` at
> `+0x58`, exact 22-word current-image body match, no pointer args, no pre-call argument pointer
> derefs, and source declaration `extern int get_diplayport_status(void)` from
> `include/linux/ccic/s2mm005_ext.h:98`. The body reads the global CCIC status pointer, returns
> `0` if absent, or reads the status field and may emit its built-in `printk` line before returning
> the same bounded status field.
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs were confirmed, bridge
> healthy, baseline v2321 `version/status/selftest` passed, the exact v1-repl candidate
> (`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`) flashed through
> `native_init_flash.py` with matching readback SHA, candidate `version/selftest/status` passed
> after bridge restart + settle, and `a90_repl.py call-proof get_diplayport_status` returned
> stable `0x0` twice under the fixed no-argument read-only status contract (`0..0xff`). Candidate
> post-proof selftest stayed `fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule: candidate flash helper `64.665s`,
> candidate flash start to boot ready `85.473s`, live proof session `5.280s`, rollback flash
> helper `64.272s`, rollback flash start to boot ready `84.964s`, total candidate-start to
> rollback-ready `176.173s`.
>
> Rollback to clean v2321 completed through `native_init_flash.py` with matching readback SHA.
> Final explicit `version/selftest/status` passed (`selftest pass=11 warn=1 fail=0`). Function-map
> entry is promoted only under the one-target contract:
> `auto_call_policy=one-target-proof-only-not-mass-call`, no arguments, return stable status
> `0x0` in `0..0xff`, cleanup `n/a-scalar-read-only`. Raw slide/runtime values stayed private.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_DIPLAYPORT_STATUS_2026-07-01.md`.

> ### ⚠️ STATUS (2026-07-01 attempted, rolled back cleanly) — corrected bridge cadence passed, ad-hoc import wrapper failed before target calls
>
> Codex retried the scheduler-counter batch only after host-validating the
> corrected bridge cadence on resident v2321 (`a90_bridge.py restart`, `12s`
> settle, `a90ctl --timeout 30 version/selftest/status`). Static gates still
> passed for `nr_processes`, `nr_running`, `nr_iowait`, and
> `nr_context_switches`; parked neighbors (`nr_iowait_cpu`,
> `single_task_running`, `get_avenrun`, `si_swapinfo`) stayed denied.
>
> The live attempt flashed the same v1-repl candidate through
> `native_init_flash.py`; candidate SHA/readback matched, the helper's built-in
> native-init verify passed, and explicit candidate `version/selftest/status`
> passed after bridge restart + `12s` settle. The run then stopped before any
> REPL proof call because the ad-hoc Python wrapper loaded `a90_repl.py` via
> `importlib` without the script directory on `sys.path`, so
> `_workspace_bootstrap` was not importable. No scheduler counter was called.
> Rollback to v2321 completed with matching readback SHA, and explicit final
> `version/selftest/status` passed after bridge restart + `12s` settle
> (`selftest pass=11 warn=1 fail=0`).
>
> Timing was recorded per the 2026-07-01 timing rule: candidate flash helper
> `63.794s`, candidate flash start to boot ready `85.885s`, live proof session
> not reached, rollback flash helper `68.237s`, rollback flash start to boot
> ready `89.049s`, candidate-start to rollback-ready `174.946s`.
>
> Host-only fix now added: `a90_repl.py call-proof-batch target...` runs
> multiple proof targets in one `ReplSession` through the normal script entrypoint
> and writes combined private evidence via `--evidence-dir`. Validation passed:
> `py_compile`, `call-proof-batch --help`, focused fake batch CLI test, and
> `git diff --check`.
>
> **No scheduler counter function-map entry is promoted from this attempt.**
> Because this is the second aborted scheduler-counter device attempt, stop
> flashing this sub-goal under the active `fails-twice -> stop` rule. Any new
> flash needs explicit operator approval and should use the new batch CLI rather
> than an ad-hoc import wrapper. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SCHEDULER_COUNTER_BATCH_ATTEMPT2_ABORTED_2026-07-01.md`.

## ⚠️ STOPPED — REPL scheduler counter batch live-call proof attempt aborted before live proof

> ### ⚠️ STATUS (2026-07-01 attempted, rolled back cleanly) — host wrapper post-flash settle/timeout issue, no target promoted
>
> Codex prepared the next BATCH unit for adjacent read-only scheduler counters:
> `nr_processes`, `nr_running`, `nr_iowait`, and `nr_context_switches`. Static
> host gates passed (`py_compile`, focused tests, full `tests.test_a90_repl`
> `Ran 165 tests`, `OK`, `git diff --check`, and classifier CLI showing the four
> selected targets as `SAFE-SCALAR` while `nr_iowait_cpu`, `single_task_running`,
> `get_avenrun`, and `si_swapinfo` stayed `DENY`/parked).
>
> The live attempt flashed the exact v1-repl candidate through
> `native_init_flash.py`; recovery/TWRP was reached before the boot write, the
> candidate SHA/readback matched, and the helper's built-in native-init
> `version/status` verification passed. The wrapper then restarted the host
> bridge, waited only a short settle, and its explicit `a90ctl version` check
> failed with an END-marker timeout before any REPL proof call ran. The wrapper
> rolled back to v2321; rollback SHA/readback matched and the rollback helper's
> built-in native-init verification passed. A later manual bridge restart,
> longer settle, and `a90ctl --timeout 30 version/selftest/status` confirmed
> final resident v2321 with `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule: candidate flash helper
> `63.706s`, candidate explicit bridge restart to health failure `15.056s`,
> live proof session `0.000s` (not reached), rollback flash helper `75.140s`,
> rollback explicit bridge restart to first health failure `15.059s`, manual
> final bridge settle/health pass `13.370s`, total candidate-start to rollback
> ready `196.183s`.
>
> **No scheduler counter function-map entry is promoted from this attempt.**
> Next safe action is host-only: fix the wrapper cadence to wait longer after
> bridge restart and use `a90ctl --timeout 30 version -> selftest -> status`
> before live REPL proof. Any new flash should be an explicit new attempt, not
> an automatic retry loop. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SCHEDULER_COUNTER_BATCH_ABORTED_2026-07-01.md`.

## ✅ DONE — REPL post-epic batch live-call proof — memory state observation getters

> ### ✅ STATUS (2026-07-01 live pass) — same-session memory-state observation batch
>
> Codex continued the corrected BATCH cadence with a read-only memory-state
> observation unit. One `v1-repl` boot session proved `si_mem_available()` and
> `si_meminfo(struct sysinfo *val)` under separate per-target contracts:
> `si_mem_available` is trusted only as a no-argument scalar available-page
> getter, and `si_meminfo` is trusted only with a kmalloc-owned `struct sysinfo`
> result slot plus trailing canary and paired `kfree` cleanup.
>
> Static gates passed: both targets use C1 `export-recovery`; exact current-image
> word checks and next-symbol boundaries matched (`si_mem_available -> si_meminfo`
> `0xd8`, `si_meminfo -> show_free_areas` `0x78`); source signatures came from
> `include/linux/mm.h:2207-2208`; and the call-safety classifier reported
> `SAFE-SCALAR=1`, `SAFE-WITH-VALID-PTR=1`, `DENY=8` over the memory/scheduler
> neighbor set. Parked neighbors include `get_avenrun`, `si_swapinfo`,
> `total_swapcache_pages`, `nr_processes`, `nr_running`, `nr_iowait`,
> `vm_commit_limit`, and `vm_memory_committed`.
>
> Host validation passed: `py_compile`; focused classifier/source/fake-batch
> tests; full `tests/test_a90_repl.py` (`Ran 164 tests`, `OK`); and
> `git diff --check`. Live validation obeyed the timing rule:
> candidate flash helper `63.695s`, candidate boot/health `19.923s`, live proof
> session `29.024s`, rollback flash helper `64.159s`, rollback boot/health
> `22.415s`, total candidate-start to rollback-ready `200.735s`.
>
> Live results: `si_mem_available()` returned `0x129e22` then `0x129d8c`
> (bounded drift `0x96`). `si_meminfo()` wrote sane fields into the owned result
> slot: totalram `0x14ffea`, freeram `0x126ee3`, sharedram `0x1528`,
> bufferram `0x34d`, highmem `0`, mem_unit `0x1000`; canary and `kfree`
> cleanup both passed. Candidate post-live `selftest fail=0`; rollback to
> v2321 completed with final `selftest pass=11 warn=1 fail=0`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_MEMORY_STATE_BATCH_2026-07-01.md`.

## ✅ DONE — REPL post-epic batch live-call proof — SDE RSC scalar state getters

> ### ✅ STATUS (2026-07-01 live pass) — same-session SDE RSC state-observation batch
>
> Codex continued the corrected BATCH cadence with a new read-only state-observation shape:
> one `v1-repl` boot session proved three adjacent SDE RSC scalar getters with fixed
> `SDE_RSC_INDEX=0`: `get_sde_rsc_current_state`, `get_sde_rsc_primary_crtc`, and
> `get_sde_rsc_version`. Static validation pinned `get_sde_rsc_current_state=0xffffff8008861bec`
> (xrefs `4`), `get_sde_rsc_primary_crtc=0xffffff8008861b7c` (xrefs `1`), and
> `get_sde_rsc_version=0xffffff8008861c64` (xrefs `1`), all `export-recovery`. Source
> declarations came from `include/linux/sde_rsc.h:291`, `:299`, and `:319`; all three
> signatures are scalar-only, exact current-image word gates passed, and returns are bounded
> by the predeclared contracts.
>
> Adjacent client-pointer helpers stayed parked: `sde_rsc_client_get_vsync_refcount`,
> `sde_rsc_client_reset_vsync_refcount`, `sde_rsc_client_is_state_update_complete`, and
> `sde_rsc_client_trigger_vote` remain `DENY` because they need a separate valid
> `struct sde_rsc_client *` and side-effect contract.
>
> Host validation passed: `py_compile`; focused classifier/source/fake-batch tests; full
> `tests.test_a90_repl` (`Ran 163 tests`, `OK`); and CLI `call-safety-classify` over the
> SDE RSC scalar/client cluster (`SAFE-SCALAR=4`, `DENY=4`). Live validation obeyed the
> flash gate: baseline v2321 `version/selftest/status` passed, v1-repl candidate
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` flashed through
> `native_init_flash.py` with matching readback SHA, explicit candidate health passed after
> bridge restart + settle, all three proof calls passed in one `ReplSession`, and rollback to
> v2321 completed with matching readback SHA plus final `selftest pass=11 warn=1 fail=0`.
>
> Live result: `get_sde_rsc_current_state(0)` returned stable `0x1`;
> `get_sde_rsc_primary_crtc(0)` returned stable `0x85`; `get_sde_rsc_version(0)` returned
> stable `0x2`.
>
> Timing was recorded per the 2026-07-01 timing rule: candidate flash helper `68.319s`,
> candidate bridge/health-to-ready `24.486s`, live proof session `10.887s`, rollback flash
> helper `64.204s`, rollback bridge/health-to-ready `24.482s`, total candidate-start to
> rollback-ready `194.786s`. Operational note: one pre-proof wrapper attempt used a wrong
> private source-root path and stopped before any live call; it rolled back cleanly before the
> corrected pass.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SDE_RSC_STATE_BATCH_2026-07-01.md`.

## ✅ DONE — REPL post-epic batch live-call proof — bitmap allocation wrappers + paired cleanup

> ### ✅ STATUS (2026-07-01 live pass) — adjacent bitmap allocation batch after saturation pivot
>
> Codex continued the corrected BATCH cadence with a new capability shape: scalar allocation
> wrappers that return owned kernel pointers. One `v1-repl` boot session proved adjacent
> `bitmap_alloc(nbits, gfp)` and `bitmap_zalloc(nbits, gfp)`, both with fixed bounded
> `nbits=130`, `GFP_KERNEL`, 24 expected bytes, and paired `bitmap_free` cleanup. Static
> validation pinned `bitmap_alloc=0xffffff800855e0dc`, `bitmap_zalloc=0xffffff800855e10c`,
> and `bitmap_free=0xffffff800855e134`, all `export-recovery`; source declarations came from
> `include/linux/bitmap.h:93-95`. `bitmap_zalloc` additionally proved zero initialization
> before the write pattern.
>
> Adjacent region helpers stayed parked: `bitmap_allocate_region`, `bitmap_find_free_region`,
> and `bitmap_release_region` remain `DENY` because they mutate caller-provided bitmap
> pointers and need a separate owned-buffer mutation contract.
>
> Host validation passed: `py_compile`; focused classifier/source/fake-batch tests; full
> `tests.test_a90_repl` (`Ran 162 tests`, `OK`); and host call-safety sweep over the bitmap
> allocation/region cluster (`bitmap_alloc`, `bitmap_zalloc`, `bitmap_free` candidate-safe;
> the three region helpers denied). Live validation obeyed the flash gate: baseline v2321
> `version/selftest/status` passed, v1-repl candidate
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` flashed through
> `native_init_flash.py` with matching readback SHA, explicit candidate health passed after
> bridge restart + settle, the two proof calls passed in one `ReplSession`, and rollback to
> v2321 completed with matching readback SHA plus final `selftest pass=11 warn=1 fail=0`.
>
> Timing was recorded per the 2026-07-01 timing rule: candidate flash helper `68.329s`,
> candidate bridge/health-to-ready `25.418s`, live proof session `16.703s`, rollback flash
> helper `65.220s`, rollback bridge/health-to-ready `26.478s`, total candidate-start to
> rollback-ready `202.149s`. Operational note: three pre-proof attempts exposed a host-side
> serial/cmdv1 cadence issue after flash/restart; each rolled back cleanly. The passing
> wrapper restarts the serial bridge, waits for settle, then runs `version -> selftest ->
> status`.
>
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BITMAP_ALLOCATION_BATCH_2026-07-01.md`.

## ✅ DONE — REPL post-epic batch live-call proof — current task state / credential read-only contracts

> ### ✅ STATUS (2026-07-01 live pass) — same-session current-state batch after batch correction
>
> Codex continued the corrected BATCH cadence: one `v1-repl` boot session proved three adjacent
> `SAFE-SCALAR` read-only current-state targets instead of one candidate per flash. Batch targets:
> `current_umask()`, `in_group_p(kgid_t)`, and `in_egroup_p(kgid_t)`. Static C1/source/call-safety
> validation passed for all three: `current_umask=0xffffff80082d3a24`, `export-recovery`, direct-BL
> xrefs `14`, source declaration `extern int current_umask(void)` from `include/linux/fs.h:2257`;
> `in_group_p=0xffffff80080e211c`, `export-recovery`, xrefs `30`, source declaration
> `extern int in_group_p(kgid_t)` from `include/linux/cred.h:67`; and
> `in_egroup_p=0xffffff80080e218c`, `export-recovery`, xrefs `8`, source declaration
> `extern int in_egroup_p(kgid_t)` from `include/linux/cred.h:68`. All three bodies are leaf,
> no early arg-pointer deref, and exact current-image word gates were pinned.
>
> Adjacent candidates were intentionally parked: `current_chrooted` stayed `DENY` due weak C1 and
> path/spinlock helper calls; `capable`/`ns_capable` stayed out because disassembly shows a current
> task flag store after `security_capable` (not read-only); `has_capability*` stayed context-sensitive;
> `task_active_pid_ns`/`pid_nr_ns`/`pid_vnr` need a new valid-pointer contract.
>
> Host validation passed: `py_compile`; focused classifier/source/fake-batch tests; full
> `tests/test_a90_repl.py` (`Ran 161 tests`, `OK`); and CLI `call-safety-classify` over the batch
> plus parked neighbors (`SAFE-SCALAR=3`, `DENY=8`). Live validation obeyed the flash gate:
> baseline v2321 `version/status/selftest` passed, v1-repl candidate
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, candidate
> `selftest` passed after one serial `AT` desync resync, the three proof calls passed in one
> `ReplSession`, and rollback to v2321 completed with matching readback SHA and final
> `selftest pass=11 warn=1 fail=0` after one final serial resync.
>
> Live result: `current_umask()` returned stable `0x12`; `in_group_p(0)` and `in_egroup_p(0)`
> returned `1` twice; `in_group_p(0x7fff)` and `in_egroup_p(0x7fff)` returned `0` twice.
> Candidate flash total `63.377s`; rollback total `64.311s`. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CURRENT_STATE_BATCH_2026-07-01.md`.

## ✅ DONE — REPL post-epic batch live-call proof — `task_struct *` read-only kernel-state contracts

> ### ✅ STATUS (2026-07-01 live pass) — first same-session batch proof after operator BATCH correction
>
> Codex corrected the previous single-candidate framing and promoted a same-shape batch in one
> `v1-repl` boot session. The batch targeted read-only `task_struct *` state queries using the global
> `init_task` pointer only: `__task_pid_nr_ns(init_task, PIDTYPE_PID, NULL)` and
> `sched_get_group_id(init_task)`. Static C1/source/call-safety validation passed for both targets:
> `__task_pid_nr_ns=0xffffff80080d846c`, `export-recovery`, direct-BL xrefs `114`, source declaration
> `pid_t __task_pid_nr_ns(struct task_struct *task, enum pid_type type, struct pid_namespace *ns)` from
> `include/linux/sched.h:1426`; and `sched_get_group_id=0xffffff8008122e64`,
> `disasm-signature+xref+map`, direct-BL xrefs `1`, source declaration
> `extern unsigned int sched_get_group_id(struct task_struct *p)` from `include/linux/sched.h:552`.
> Both entries are `SAFE-WITH-VALID-PTR`, not scalar-safe, and retain the expected RCU
> `context-sensitive-locking-or-sleep-call-in-scan` warning. Neighbor candidates `task_prio`,
> `task_curr`, and `sched_get_init_task_load` stayed `DENY` due current C1 rejection.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused
> classifier/source/fake-batch tests; full `tests/test_a90_repl.py` (`Ran 160 tests`, `OK`);
> and CLI `call-safety-classify` over the batch plus parked neighbors (`SAFE-WITH-VALID-PTR=2`,
> `DENY=3`). The fake integration test runs both targets through one `ReplSession`, matching the live
> batch cadence.
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP artifacts were confirmed, bridge
> healthy, baseline v2321 `version/status/selftest` passed, v1-repl candidate
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, and candidate
> selftest stayed `pass=11 warn=1 fail=0`. A first candidate flash invocation with
> `--expect-version v1-repl` stopped before flash because that marker is absent from the local image;
> the retried SHA/readback-gated flash did the actual device write.
>
> Result: both same-session proofs passed. `__task_pid_nr_ns` returned pid `0x0` twice for
> `init_task/PIDTYPE_PID/NULL`; `sched_get_group_id` first directly observed
> `init_task->sched_task_group == NULL` and then returned group id `0x0` twice. Raw runtime address,
> slide, and borrowed-pointer evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-task-struct-batch-20260701/`. Codex rolled back to
> clean v2321 through `native_init_flash.py`; v2321 readback SHA matched. The rollback helper's
> post-verify wait was interrupted only after v2321 `version` output was visible; manual final
> `status` and `selftest` then confirmed `pass=11 warn=1 fail=0`. Final resident is v2321. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_TASK_STRUCT_BATCH_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `get_ddr_vendor_name` borrowed DDR vendor string contract

> ### ✅ STATUS (2026-07-01 live pass) — `get_ddr_vendor_name` promoted under no-arg SMEM borrowed-string contract
>
> Ninety-seventh one-target live-call proof after the REPL epic close, and the first follow-on proof
> after the operator's saturation-stop/pivot steer to prefer read-only kernel-state observation over
> more saturated scalar/lib variants. Codex selected `get_ddr_vendor_name`, a Samsung SMEM DDR
> identity query, because it extends the function map as a measurement instrument: no arguments,
> read-only SMEM access, and a borrowed `char *` result that can be bounded-read without ownership
> transfer. Static C1 verified `get_ddr_vendor_name=0xffffff80086ef6ac`,
> `disasm-signature+xref+map`, direct-BL xrefs `2`, source declaration
> `extern char* get_ddr_vendor_name(void)` from `include/linux/samsung/sec_smem.h:194`, and next
> boundary `get_ddr_DSF_version` at `+0xc8`. The proof gates the current-image body: stack setup,
> SMEM vendor-info ID, `qcom_smem_get` call, SMEM vendor-word load, vendor-table address
> materialization, 4-bit vendor-index mask, vendor string table load, NULL error return, RET, and
> next-entry guard.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 159 tests`, `OK`);
> CLI `call-safety-classify get_ddr_vendor_name` (`SAFE-SCALAR`, no required pointer args,
> `disasm-signature+xref+map`, first words matching the SMEM getter body); and focused
> `call-safety-sweep` (`SAFE-SCALAR`, scalar-only source declaration, gate seeded).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, candidate
> selftest stayed `pass=11 warn=1 fail=0`, and REPL selftest retry returned
> `a90-repl-v2a1-selftest-pass`. The first REPL selftest attempt hit known host-side serial framing
> loss on a `cmdv1x` shell command before any REPL op completed; short resync plus a minimal
> `cmdv1x` run check passed, then the retry completed cleanly.
>
> Result: `a90-repl-live-call-proof-get_ddr_vendor_name-pass`; checks covered C1 identity, next
> symbol boundary, no-arg source contract, `SAFE-SCALAR` call-safety, static SMEM getter words, and
> two bounded runtime calls. Both calls returned a stable non-NULL borrowed pointer, and the bounded
> 32-byte string read decoded to the same printable NUL-terminated vendor string `SEC`. Raw runtime
> address/slide/borrowed-pointer evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-get-ddr-vendor-name-20260701/proof/`; the public
> summary redacts the pointer and exposes only the stable vendor string. Post-proof candidate
> selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final standalone
> selftest confirmed `pass=11 warn=1 fail=0`. Function map records `get_ddr_vendor_name` only under
> the no-argument SMEM borrowed-string contract: call, bounded-read printable C string, never free.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_DDR_VENDOR_NAME_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__usecs_to_jiffies` HZ=100 round-up contract

> ### ✅ STATUS (2026-07-01 live pass) — `__usecs_to_jiffies` promoted under current-image HZ=100 round-up/saturation contract
>
> Ninety-sixth one-target live-call proof after the REPL epic close. The implemented
> `CALL_PROOF_TARGETS` inventory was fully covered by prior reports, so Codex expanded the function
> map with the adjacent scalar conversion helper `__usecs_to_jiffies`; `nsec_to_clock_t` remained
> excluded because C1 identity verification is unavailable in the current map/image pair. Static C1
> verified `__usecs_to_jiffies=0xffffff8008158414`, `export-recovery`, direct-BL xrefs `17`,
> scalar-only source declaration `extern unsigned long __usecs_to_jiffies(const unsigned int u)`
> from `include/linux/jiffies.h:374`, and next boundary `timespec64_to_jiffies` at `+0x38`. The
> current image body compares against saturation threshold `0xffffb1e0`, returns
> `MAX_JIFFY_OFFSET` for too-large inputs, otherwise adds rounding constant `9999`, multiplies by
> divide-by-10000 magic `0xd1b71759`, shifts by `45`, returns, then hits the next-entry guard. The
> proof contract is current-image scalar `unsigned int` microseconds input: inputs above
> `0xffffb1e0` return `MAX_JIFFY_OFFSET`; all other fixed cases return `ceil(u / 10000)` for
> HZ=100.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 158 tests`, `OK`);
> CLI `call-safety-classify __usecs_to_jiffies` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words matching the HZ=100 round-up/saturation body); and focused
> `call-safety-sweep` (`SAFE-SCALAR`, scalar-only source declaration, gate seeded).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, slow-mode
> candidate health stayed `selftest fail=0`, and REPL selftest returned
> `a90-repl-v2a1-selftest-pass`. One normal-mode health command hit serial input noise before the
> END marker; slow mode retried cleanly.
>
> Result: `a90-repl-live-call-proof-__usecs_to_jiffies-pass`; checks covered C1 identity, next
> symbol boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, threshold compare,
> saturation return, divide-by-10000 magic, rounding add, multiply, shift, RET, alignment NOP, next
> guard, and seven fixed cases: `0x0 -> 0x0`, `0x1 -> 0x1`, `0x270f -> 0x1`,
> `0x2710 -> 0x1`, `0x2711 -> 0x2`, `0x7fffffff -> 0x346dd`, and
> `0xffffb1e1 -> 0x3ffffffffffffffe`. No owned resource was created and no returned pointer exists;
> raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-usecs-to-jiffies-20260701/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final slow-mode
> standalone selftest confirmed `pass=11 warn=1 fail=0`. Function map records
> `__usecs_to_jiffies` only under the current-image HZ=100 round-up/saturation contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_USECS_TO_JIFFIES_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__msecs_to_jiffies` HZ=100 round-up contract

> ### ✅ STATUS (2026-07-01 live pass) — `__msecs_to_jiffies` promoted under current-image HZ=100 round-up/saturation contract
>
> Ninety-fifth one-target live-call proof after the REPL epic close. The implemented
> `CALL_PROOF_TARGETS` inventory was fully covered by prior reports, so Codex expanded the function
> map with a new scalar candidate. Host-only triage compared `__msecs_to_jiffies`,
> `__usecs_to_jiffies`, and the still-parked `nsec_to_clock_t`; `nsec_to_clock_t` remained excluded
> because C1 identity verification is unavailable in the current map/image pair. Static C1 verified
> `__msecs_to_jiffies=0xffffff80081583ec`, `export-recovery`, direct-BL xrefs `398`, scalar-only
> source declaration `extern unsigned long __msecs_to_jiffies(const unsigned int m)` from
> `include/linux/jiffies.h:301`, and next boundary `__usecs_to_jiffies` at `+0x28`. The current
> image body loads magic `0xcccccccd`, adds rounding constant `9`, tests bit 31 for the kernel
> negative-timeout convention, multiplies/shifts by `35`, conditionally selects `MAX_JIFFY_OFFSET`,
> returns, then hits the next-entry guard. The proof contract is current-image scalar
> `unsigned int` milliseconds input: bit31-set inputs return `MAX_JIFFY_OFFSET`; all other fixed
> cases return `ceil(m / 10)` for HZ=100.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 157 tests`, `OK`);
> CLI `call-safety-classify __msecs_to_jiffies` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words matching the HZ=100 round-up/saturation body); and focused
> `call-safety-sweep` (`SAFE-SCALAR`, scalar-only source declaration, gate seeded).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed. The first REPL
> selftest attempt hit serial input noise while writing the `panic_on_oops` guard; slow-mode retry
> returned `a90-repl-v2a1-selftest-pass`.
>
> Result: `a90-repl-live-call-proof-__msecs_to_jiffies-pass`; checks covered C1 identity, next
> symbol boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, divide-by-10 magic,
> rounding add, bit31 test, multiply, saturation constant, shift, conditional select, RET, next
> guard, and six fixed cases: `0x0 -> 0x0`, `0x1 -> 0x1`, `0xa -> 0x1`,
> `0xb -> 0x2`, `0x7fffffff -> 0xccccccd`, and
> `0x80000000 -> 0x3ffffffffffffffe`. No owned resource was created and no returned pointer exists;
> raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-msecs-to-jiffies-20260701/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final slow-mode
> standalone selftest confirmed `pass=11 warn=1 fail=0`. Function map records
> `__msecs_to_jiffies` only under the current-image HZ=100 round-up/saturation contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_MSECS_TO_JIFFIES_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `jiffies64_to_nsecs` bounded multiply contract

> ### ✅ STATUS (2026-07-01 live pass) — `jiffies64_to_nsecs` promoted under current-image bounded multiply-by-10000000 contract
>
> Ninety-fourth one-target live-call proof after the REPL epic close. Codex selected
> `jiffies64_to_nsecs` after the adjacent jiffies/time scalar helpers were live-proven.
> `nsec_to_clock_t` stayed parked because C1 identity remains unresolved for that symbol in the
> current map/image pair. Static C1 verified `jiffies64_to_nsecs=0xffffff80081585b4`,
> `export-recovery`, direct-BL xrefs `1`, scalar-only source declaration
> `extern u64 jiffies64_to_nsecs(u64 j)` from `include/linux/jiffies.h:299`, and next boundary
> `nsecs_to_jiffies64` at `+0x18`. The current image body loads multiplier `0x989680`, performs a
> 64-bit multiply, returns, then hits the next-entry guard. The proof contract is current-image
> scalar `u64` jiffies input bounded so `j * 10000000` fits in `u64`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 156 tests`, `OK`);
> CLI `call-safety-classify jiffies64_to_nsecs` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words matching the multiply-by-10000000 body); and focused
> `call-safety-sweep` (`SAFE-SCALAR`, scalar-only source declaration, gate seeded).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, and slow-mode
> REPL selftest returned `a90-repl-v2a1-selftest-pass`.
>
> Result: `a90-repl-live-call-proof-jiffies64_to_nsecs-pass`; checks covered C1 identity, next
> symbol boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, multiplier construction,
> multiply, RET, alignment NOP, next-entry guard, and four fixed cases: `0x0 -> 0x0`,
> `0x1 -> 0x989680`, `0x64 -> 0x3b9aca00`, and
> `0x1ad7f29abca -> 0xffffffffff6e4100`. No owned resource was created and no returned pointer
> exists; raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-jiffies64-to-nsecs-20260701/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final standalone
> selftest confirmed `pass=11 warn=1 fail=0`. Function map records `jiffies64_to_nsecs` only under
> the current-image bounded multiply-by-10000000 contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_JIFFIES64_TO_NSECS_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `jiffies_to_msecs` bounded multiply contract

> ### ✅ STATUS (2026-07-01 live pass) — `jiffies_to_msecs` promoted under current-image bounded multiply-by-10 contract
>
> Ninety-third one-target live-call proof after the REPL epic close. Codex selected
> `jiffies_to_msecs` after the adjacent jiffies/time scalar helpers were live-proven. `nsec_to_clock_t`
> stayed parked because C1 identity remains unresolved for that symbol in the current map/image pair.
> The earlier host-only blocker for `jiffies_to_msecs` was the source oracle attaching a
> preprocessor continuation macro to the declaration; this unit fixed that by skipping
> `#define ... \` continuation lines during signature extraction. Static C1 then verified
> `jiffies_to_msecs=0xffffff8008158154`, `export-recovery`, direct-BL xrefs `279`, scalar-only
> source declaration `extern unsigned int jiffies_to_msecs(const unsigned long j)` from
> `include/linux/jiffies.h:291`, and next boundary `jiffies_to_usecs` at `+0x10`. The current image
> body computes `j * 5`, shifts left once to `j * 10`, returns, then hits the next-entry guard. The
> proof contract is current-image scalar `unsigned long` jiffies input bounded so `j * 10` fits in
> `unsigned int`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 155 tests`, `OK`);
> CLI `call-safety-classify jiffies_to_msecs` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words matching the multiply-by-10 body); and focused
> `call-safety-sweep` (`SAFE-SCALAR`, scalar-only source declaration, gate seeded).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, and helper `version/status` passed. The first
> REPL selftest attempt hit serial input noise before the END marker while setting the `panic_on_oops`
> guard; slow-mode retry returned `a90-repl-v2a1-selftest-pass`.
>
> Result: `a90-repl-live-call-proof-jiffies_to_msecs-pass`; checks covered C1 identity, next symbol
> boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, multiply-by-10 instruction
> sequence, RET, next-entry guard, and four fixed cases: `0x0 -> 0x0`, `0x1 -> 0xa`,
> `0x7b -> 0x4ce`, and `0x19999999 -> 0xfffffffa`. No owned resource was created and no returned
> pointer exists; raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-jiffies-to-msecs-20260701/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final standalone
> selftest confirmed `pass=11 warn=1 fail=0`. Function map records `jiffies_to_msecs` only under the
> current-image bounded multiply-by-10 contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_JIFFIES_TO_MSECS_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `nsecs_to_jiffies` fixed-point nanosecond conversion contract

> ### ✅ STATUS (2026-07-01 live pass) — `nsecs_to_jiffies` promoted under current-image divide-by-10000000 contract
>
> Ninety-second one-target live-call proof after the REPL epic close. Codex selected
> `nsecs_to_jiffies` after the adjacent `nsecs_to_jiffies64` contract was proven. `nsec_to_clock_t`
> stayed parked because C1 identity verification remains unresolved for that symbol in the current
> map/image pair. Static C1 verified `nsecs_to_jiffies=0xffffff80081585ec`, `export-recovery`,
> direct-BL xrefs `7`, scalar-only source declaration
> `extern unsigned long nsecs_to_jiffies(u64 n)` from `include/linux/jiffies.h:454`, and next
> boundary `timespec_add_safe` at `+0x20`. The current image body builds magic
> `0xd6bf94d5e57a42bd`, executes `umulh`, shifts right by `23` for total fixed-point shift `87`,
> returns, then hits the next-entry guard. The proof contract is current-image scalar `u64`
> nanosecond inputs returning `(n * 0xd6bf94d5e57a42bd) >> 87` as an `unsigned long`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 154 tests`, `OK`);
> CLI `call-safety-classify nsecs_to_jiffies` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words matching the fixed-point conversion body); and focused
> `call-safety-sweep` (`SAFE-SCALAR`, scalar-only source declaration, gate seeded).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, candidate
> standalone selftest retry passed after one serial-noise read, and `a90-repl-v2a1-selftest-pass`
> confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-nsecs_to_jiffies-pass`; checks covered C1 identity, next symbol
> boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, magic construction, `umulh`,
> `lsr #23`, RET, next-entry guard, and six fixed cases: `0x0 -> 0x0`, `0x98967f -> 0x0`,
> `0x989680 -> 0x1`, `0x75bcd15 -> 0xc`, `0x3b9aca00 -> 0x64`, and
> `0xffffffffffffffff -> 0x1ad7f29abca`. No owned resource was created and no returned pointer
> exists; raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-nsecs-to-jiffies-20260701/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final standalone
> selftest retry captured the END marker with `pass=11 warn=1 fail=0` after one serial-noise read.
> Function map records `nsecs_to_jiffies` only under the current-image fixed-point conversion
> contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_NSECS_TO_JIFFIES_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `nsecs_to_jiffies64` fixed-point nanosecond conversion contract

> ### ✅ STATUS (2026-07-01 live pass) — `nsecs_to_jiffies64` promoted under current-image divide-by-10000000 contract
>
> Ninety-first one-target live-call proof after the REPL epic close. Codex selected
> `nsecs_to_jiffies64` from the remaining time/jiffies scalar helpers. `nsec_to_clock_t` stayed
> parked because C1 identity verification failed for that symbol in the current map/image pair.
> Static C1 verified `nsecs_to_jiffies64=0xffffff80081585cc`, `export-recovery`, direct-BL xrefs
> `1`, scalar-only source declaration `extern u64 nsecs_to_jiffies64(u64 n)` from
> `include/linux/jiffies.h:453`, and next boundary `nsecs_to_jiffies` at `+0x20`. The current image
> body builds magic `0xd6bf94d5e57a42bd`, executes `umulh`, shifts right by `23` for total
> fixed-point shift `87`, returns, then hits the next-entry guard. The proof contract is current-
> image scalar `u64` nanosecond inputs returning `(n * 0xd6bf94d5e57a42bd) >> 87`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 153 tests`, `OK`);
> CLI `call-safety-classify nsecs_to_jiffies64` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words matching the fixed-point conversion body); and focused
> `call-safety-sweep` (`SAFE-SCALAR`, scalar-only source declaration, gate seeded).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call. One prompt echo
> appeared as an unknown command in the helper transcript, but the bounded helper verification and
> subsequent REPL selftest passed.
>
> Result: `a90-repl-live-call-proof-nsecs_to_jiffies64-pass`; checks covered C1 identity, next
> symbol boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, magic construction,
> `umulh`, `lsr #23`, RET, next-entry guard, and six fixed cases:
> `0x0 -> 0x0`, `0x98967f -> 0x0`, `0x989680 -> 0x1`, `0x75bcd15 -> 0xc`,
> `0x3b9aca00 -> 0x64`, and `0xffffffffffffffff -> 0x1ad7f29abca`. No owned resource was
> created and no returned pointer exists; raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-nsecs-to-jiffies64-20260701/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final standalone
> selftest retry captured the END marker with `pass=11 warn=1 fail=0` after one serial-noise read.
> Function map records `nsecs_to_jiffies64` only under the current-image fixed-point conversion
> contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_NSECS_TO_JIFFIES64_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `clock_t_to_jiffies` fixed positive identity contract

> ### ✅ STATUS (2026-07-01 live pass) — `clock_t_to_jiffies` promoted under current-image positive identity contract
>
> Ninetieth one-target live-call proof after the REPL epic close. Codex selected
> `clock_t_to_jiffies` from the adjacent time/jiffies scalar helpers after `jiffies_64_to_clock_t`,
> `jiffies_to_clock_t`, and `jiffies_to_usecs` were already live-proven. `nsec_to_clock_t` stayed
> parked because C1 identity verification failed for that symbol in the current map/image pair.
> Static C1 verified `clock_t_to_jiffies=0xffffff8008158584`, `export-recovery`, direct-BL xrefs
> `24`, scalar-only source declaration `extern unsigned long clock_t_to_jiffies(unsigned long x)`
> from `include/linux/jiffies.h:450`, and next boundary `jiffies_64_to_clock_t` at `+0x8`. The
> current image body is the identity leaf `0xd65f03c0` followed by `0x00be7bad`, so the proof
> contract is fixed positive unsigned long clock values returning unchanged as unsigned long jiffies
> values.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 152 tests`, `OK`); `git diff --check`;
> CLI `call-safety-classify clock_t_to_jiffies` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words `0xd65f03c0` and `0x00be7bad`); and focused
> `call-safety-sweep` (`SAFE-SCALAR`, scalar-only source declaration, gate seeded).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-clock_t_to_jiffies-pass`; checks covered C1 identity, next
> symbol boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, identity RET, next-entry
> guard, and fixed positive cases `0x0`, `0x1`, `0x12345678`, and `0x7fffffff` returning unchanged.
> No owned resource was created and no returned pointer exists; raw runtime address/slide evidence
> stayed private under
> `workspace/private/runs/kernel/live-call-proof-clock-t-to-jiffies-20260701/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final standalone
> selftest confirmed `pass=11 warn=1 fail=0`. Function map records `clock_t_to_jiffies` only under
> the current-image fixed-positive identity contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CLOCK_T_TO_JIFFIES_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `jiffies_to_usecs` bounded multiply contract

> ### ✅ STATUS (2026-07-01 live pass) — `jiffies_to_usecs` promoted under current-image bounded multiply-by-10000 contract
>
> Eighty-ninth one-target live-call proof after the REPL epic close. Codex selected
> `jiffies_to_usecs` from the host-only time/jiffies scalar sweep. The adjacent `jiffies_to_msecs`
> helper was parked because the current source-signature oracle selected it with nearby macro text
> attached, while `jiffies_to_usecs` had a clean scalar-only declaration
> `extern unsigned int jiffies_to_usecs(const unsigned long j)` from `include/linux/jiffies.h:292`.
> Static C1 verified `jiffies_to_usecs=0xffffff8008158164`, `export-recovery`, direct-BL xrefs `25`,
> and next boundary `timespec_trunc` at `+0x10`. The current image body loads multiplier `10000`,
> multiplies into `w0`, returns, then hits the next-entry guard, so the proof contract is bounded
> unsigned long inputs whose product `j * 10000` fits in unsigned int.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 151 tests`, `OK`); `git diff --check`; and
> CLI `call-safety-classify jiffies_to_usecs` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words `0x5284e208`, `0x1b087c00`, `0xd65f03c0`, and `0x00be7bad`).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, and helper `version/status` passed. First REPL
> selftest attempt hit serial noise while setting `panic_on_oops`; the bounded retry passed with
> `a90-repl-v2a1-selftest-pass` before the target call.
>
> Result: `a90-repl-live-call-proof-jiffies_to_usecs-pass`; checks covered C1 identity, next symbol
> boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, multiplier load, multiply, RET,
> next-entry guard, and fixed bounded cases `0x0 -> 0x0`, `0x1 -> 0x2710`, `0x7b -> 0x12c4b0`,
> and `0x68db8 -> 0xffffe380`. No owned resource was created and no returned pointer exists; raw
> runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-jiffies-to-usecs-20260701/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final standalone
> selftest retry captured the END marker with `pass=11 warn=1 fail=0` after one serial-noise read.
> Function map records `jiffies_to_usecs` only under the current-image bounded multiply contract.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_JIFFIES_TO_USECS_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `jiffies_to_clock_t` fixed positive identity contract

> ### ✅ STATUS (2026-07-01 live pass) — `jiffies_to_clock_t` promoted under current-image positive identity contract
>
> Eighty-eighth one-target live-call proof after the REPL epic close. Codex selected
> `jiffies_to_clock_t` from the host-only time/jiffies scalar sweep after `jiffies_64_to_clock_t`
> was already live-proven. Adjacent helpers such as `jiffies_to_msecs`, `jiffies_to_usecs`,
> `nsecs_to_jiffies64`, and `nsecs_to_jiffies` remain separate targets because their arithmetic
> bodies and return-width contracts differ. Static C1 verified
> `jiffies_to_clock_t=0xffffff800815857c`, `export-recovery`, direct-BL xrefs `72`, scalar-only
> source declaration `extern clock_t jiffies_to_clock_t(unsigned long x)` from
> `include/linux/jiffies.h:444`, and next boundary `clock_t_to_jiffies` at `+0x8`. The current image
> body is the identity leaf `0xd65f03c0` followed by `0x00be7bad`, so the proof contract is fixed
> positive unsigned long inputs returning unchanged.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 150 tests`, `OK`); `git diff --check`; and
> CLI `call-safety-classify jiffies_to_clock_t` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words `0xd65f03c0` and `0x00be7bad`).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call. One parallel health
> probe hit serial transaction-lock contention during REPL selftest; the sequential rerun passed.
>
> Result: `a90-repl-live-call-proof-jiffies_to_clock_t-pass`; checks covered C1 identity, next
> symbol boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, identity RET, next-entry
> guard, and fixed positive cases `0x0`, `0x1`, `0x12345678`, and `0x7fffffff` returning unchanged.
> No owned resource was created and no returned pointer exists; raw runtime address/slide evidence
> stayed private under `workspace/private/runs/kernel/live-call-proof-jiffies-to-clock-20260701/proof/`.
> Post-proof candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321
> through `native_init_flash.py`, readback SHA matched, helper `version/status` passed, and final
> standalone selftest confirmed `pass=11 warn=1 fail=0`. Function map records `jiffies_to_clock_t`
> only under the current-image fixed-positive identity contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_JIFFIES_TO_CLOCK_T_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `jiffies_64_to_clock_t` fixed u64 identity contract

> ### ✅ STATUS (2026-07-01 live pass) — `jiffies_64_to_clock_t` promoted under current-image identity contract
>
> Eighty-seventh one-target live-call proof after the REPL epic close. Codex selected
> `jiffies_64_to_clock_t` from the host-only time/jiffies scalar sweep. The sweep also produced
> adjacent conversion/time candidates, but this target had the narrowest contract: C1 verified
> `jiffies_64_to_clock_t=0xffffff800815858c`, `export-recovery`, direct-BL xrefs `3`, scalar-only
> source declaration `extern u64 jiffies_64_to_clock_t(u64 x)` from `include/linux/jiffies.h:451`,
> and next boundary `nsec_to_clock_t` at `+0x8`. The current image body is the identity leaf
> `0xd65f03c0` followed by `0x00be7bad`, so the proof contract is fixed u64 inputs returning
> unchanged. Adjacent conversion helpers and any non-identity build configuration remain unpromoted.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 149 tests`, `OK`); `git diff --check`; and
> CLI `call-safety-classify jiffies_64_to_clock_t` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`, first words `0xd65f03c0` and `0x00be7bad`).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, and helper `version/status` passed. A transient
> serial parse fragment was cleared by restarting the serial bridge; candidate selftest then returned
> `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target
> call.
>
> Result: `a90-repl-live-call-proof-jiffies_64_to_clock_t-pass`; checks covered C1 identity, next
> symbol boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, identity RET, next-entry
> guard, and fixed u64 cases `0x0`, `0x1`, and `0x123456789abcdef0` returning unchanged. No owned
> resource was created and no returned pointer exists; raw runtime address/slide evidence stayed
> private under `workspace/private/runs/kernel/live-call-proof-jiffies64-to-clock-20260701/proof/`.
> Post-proof candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321
> through `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient
> final serial parse fragment was cleared by restarting the serial bridge, and final standalone
> selftest confirmed `pass=11 warn=1 fail=0`. Function map records `jiffies_64_to_clock_t` only under
> the current-image fixed-u64 identity contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_JIFFIES_64_TO_CLOCK_T_2026-07-01.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `is_sde_rsc_available` SDE_RSC_INDEX bool contract

> ### ✅ STATUS (2026-06-30 live pass) — `is_sde_rsc_available` promoted under SDE_RSC_INDEX-only bool contract
>
> Eighty-sixth one-target live-call proof after the REPL epic close. Codex selected
> `is_sde_rsc_available` from a scalar candidate pass after the already-proven `CALL_PROOF_TARGETS`
> set was saturated. The contract was narrowed before live execution: call only
> `is_sde_rsc_available(SDE_RSC_INDEX)` with `SDE_RSC_INDEX=0`, treat the display-RSC table as
> read-only, and do not dereference or free any returned pointer because the function returns a bool.
> `is_scm_armv8` was rejected for an SMC/cache-miss/static-write path, `is_current_pgrp_orphaned` was
> rejected for lock/traversal surface, and `find_vpid` was left parked for a separate RCU/lifetime
> contract.
>
> C1 verified `is_sde_rsc_available=0xffffff8008861b04`, `export-recovery`, direct-BL xrefs `1`,
> source declaration `bool is_sde_rsc_available(int rsc_index)` from `include/linux/sde_rsc.h:282`,
> and next boundary `get_sde_rsc_primary_crtc` at `+0x78`. The proof gates static words
> `0xca1103d0`, `0xa9bf43fd`, `0x2a0003e3`, `0x7100141f`, `0x540000ab`, `0x90014348`,
> `0x91014108`, `0xf863d908`, `0xb40000a8`, `0x52800020`, `0x97e364a7`, `0x2a1f03e0`,
> `0xd65f03c0`, `0xd503201f`, and `0x00be7bad`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 148 tests`, `OK`); `git diff --check`; and
> CLI `call-safety-classify is_sde_rsc_available` (`SAFE-SCALAR`, no required pointer args,
> `export-recovery`).
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, and helper `version/status` passed. A transient
> serial parse fragment was cleared by restarting the serial bridge; candidate selftest then returned
> `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target
> call.
>
> Result: `a90-repl-live-call-proof-is_sde_rsc_available-pass`; checks covered C1 identity, next
> symbol boundary, scalar-only source contract, `SAFE-SCALAR` call-safety, index bound check,
> display-RSC table address/load, NULL branch, true/false returns, false-path `printk`, and two
> repeated calls with input index `0` returning stable bool `0x1`. No owned resource was created and
> no returned pointer exists; raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-is-sde-rsc-available-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient final
> serial parse fragment was cleared by restarting the serial bridge, and final standalone
> `version/status/selftest` confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records
> `is_sde_rsc_available` only under the `SDE_RSC_INDEX=0` read-only bool contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_IS_SDE_RSC_AVAILABLE_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `get_boot_stat_time` boot-stat MMIO counter contract

> ### ✅ STATUS (2026-06-30 live pass) — `get_boot_stat_time` promoted under no-arg read-only counter contract
>
> Eighty-fifth one-target live-call proof after the REPL epic close. Codex selected
> `get_boot_stat_time` from the host-only `get_` prefix sweep because it was the only new advisory
> `SAFE-SCALAR` candidate, then narrowed the contract before live execution. C1 verified
> `get_boot_stat_time=0xffffff80086979e4`, `disasm-signature+xref+map`, direct-BL xrefs `4`, JOPP
> entry true, source declaration `extern unsigned int get_boot_stat_time(void)` from
> `include/soc/qcom/boot_stats.h:39`, and implementation body
> `return readl_relaxed(mpm_counter_base);` from `drivers/soc/qcom/boot_stats.c`. The actual function
> body is bounded by `get_boot_stat_freq` at `+0x60`; the proof gates static words `0xa9be43fd`,
> `0xf9000bf3`, `0xd0015088`, `0x52800020`, `0xf9401d13`, `0xaa1303e1`, `0x97ecd440`,
> `0x34000120`, `0xb9400260`, `0xd5033f9f`, `0xd5033fdf`, `0xf9400bf3`, `0xd65f03c0`, and
> `0x00be7bad`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 147 tests`, `OK`); `git diff --check`; and
> CLI `call-safety-classify get_boot_stat_time` (`SAFE-SCALAR`, no required pointer args, first BL
> resolved to `uncached_logk`). The adjacent `get_boot_stat_freq` remains unpromoted because C1 still
> marks its tiny leaf body unverified.
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, and helper `version/status` passed. A transient
> serial parse fragment was cleared by restarting the serial bridge; candidate selftest then returned
> `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target
> call.
>
> Result: `a90-repl-live-call-proof-get_boot_stat_time-pass`; checks covered C1 identity, next symbol
> boundary, no-arg source contract, source implementation, `SAFE-SCALAR` call-safety, counter-base
> setup, `uncached_logk`, both MMIO counter load paths, barriers, and three repeated calls returning
> nonzero uint32 counter values `0x29eb84`, `0x2a2dac`, and `0x2a7000` with max short-run delta
> `0x4254`. No owned resource was created and no returned pointer exists; raw runtime address/slide
> evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-get-boot-stat-time-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient final
> serial parse fragment was cleared by restarting the serial bridge, and final standalone
> `version/status/selftest` confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records
> `get_boot_stat_time` only under the no-arg read-only boot-stat timer contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_BOOT_STAT_TIME_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `get_ddr_DSF_version` SMEM uint32 DSF-version contract

> ### ✅ STATUS (2026-06-30 live pass) — `get_ddr_DSF_version` promoted under no-arg SMEM read-only contract
>
> Eighty-fourth one-target live-call proof after the REPL epic close. Codex continued the Samsung
> SMEM DDR getter sweep after `get_ddr_total_density` passed and `get_ddr_revision_id_1` was parked.
> The new target was `get_ddr_DSF_version` because C1 verified
> `get_ddr_DSF_version=0xffffff80086ef774`, `disasm-signature+xref+map`, direct-BL xrefs `4`, JOPP
> entry true, source contract `extern uint32_t get_ddr_DSF_version(void)` from
> `include/linux/samsung/sec_smem.h:195`, and no arguments. The actual function body is bounded by
> `get_ddr_revision_id_1` at `+0xb8`; the proof gates static words `0xd100c3ff`, `0x528010e1`,
> `0x910003e2`, `0x97fe8952`, `0xf94003e8`, `0xaa0003f3`, `0xb9406a60`, `0x2a1f03e0`,
> `0xd65f03c0`, and `0x00be7bad`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused tests
> (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 146 tests`, `OK`); `git diff --check`; and
> CLI `call-safety-classify get_ddr_DSF_version` (`SAFE-SCALAR`, no required pointer args, first BL
> resolved to `qcom_smem_get`). The selection explicitly avoided re-promoting `get_ddr_revision_id_1`
> because its previous live result proved the raw return was a shifted SMEM word, not the
> source-level byte-sized contract.
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, helper `version/status` passed, candidate
> selftest returned `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path
> before the target call.
>
> Result: `a90-repl-live-call-proof-get_ddr_DSF_version-pass`; checks covered C1 identity, next
> symbol boundary, no-arg source contract, `SAFE-SCALAR` call-safety, SMEM ID/buffer setup,
> `qcom_smem_get`, DSF-version field load, NULL/error return, and two repeated calls returning the
> stable nonzero uint32 value `0x650000`. No owned resource was created and no returned pointer
> exists; raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-get-ddr-dsf-version-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient final
> serial parse fragment was cleared by restarting the serial bridge, and final standalone
> `version/status/selftest` confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records
> `get_ddr_DSF_version` only under the no-arg SMEM read-only uint32 contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_DDR_DSF_VERSION_2026-06-30.md`.

## ✅ SUPERSEDED — REPL post-epic one-target live-call proof attempt — `get_ddr_revision_id_1` raw return mismatch

> ### ✅ SUPERSEDED (2026-07-01 by DDR revision batch) / historical status (2026-06-30 live fail, rolled back cleanly)
>
> Eighty-third one-target live-call proof attempt after the REPL epic close. Codex selected
> `get_ddr_revision_id_1` as the next Samsung SMEM DDR getter after `get_ddr_total_density` because
> C1 verified `get_ddr_revision_id_1=0xffffff80086ef82c`, `disasm-signature+xref+map`, direct-BL
> xrefs `1`, JOPP entry true, source contract `extern uint8_t get_ddr_revision_id_1(void)` from
> `include/linux/samsung/sec_smem.h:196`, and no arguments. Static gating covered `qcom_smem_get`,
> next boundary `get_ddr_revision_id_2` at `+0xc0`, revision source word load `0xb9401268`, return
> transform `0x53087d00`, return, padding NOP, and next guard.
>
> The temporary uncommitted harness passed `py_compile`, focused tests, full `tests.test_a90_repl`
> (`Ran 146 tests`, `OK`), and temporary CLI classify as `SAFE-SCALAR`. Live validation obeyed the
> flash gate: rollback/fallback/TWRP SHAs confirmed, baseline v2321 health passed, v1-repl candidate
> flashed through `native_init_flash.py` with matching readback SHA, candidate selftest returned
> `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path.
>
> Result: live call reached the target and returned, but failed the predeclared raw `uint8_t` contract:
> raw REPL return was `0x60106`. Disassembly explains the mismatch: the return path is `ldr w8,
> [x19,#16]` followed by `lsr w0, w8, #8`, not a byte mask. This means the raw x0 value is a shifted
> SMEM word, not the intended byte-sized source-level value. At the time, the target was **not
> promoted**, no function map row was added, and the temporary seed/proof target was removed. This is
> superseded by the 2026-07-01 adjacent DDR revision batch, which promotes `get_ddr_revision_id_1` and
> `get_ddr_revision_id_2` under the corrected raw/low8 contract only. Candidate post-fail selftest
> stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, serial bridge was
> restarted, and final standalone `version/selftest` confirmed v2321 with `pass=11 warn=1 fail=0`.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_DDR_REVISION_ID_1_FAILED_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `get_ddr_total_density` SMEM uint8 density contract

> ### ✅ STATUS (2026-06-30 live pass) — `get_ddr_total_density` promoted under no-arg SMEM read-only contract
>
> Eighty-second one-target live-call proof after the REPL epic close. Codex continued the scalar/no-pointer
> `get_*` sweep after `get_current_napi_context` and selected `get_ddr_total_density` because C1 verified
> `get_ddr_total_density=0xffffff80086ef9a4`, `disasm-signature+xref+map`, direct-BL xrefs `1`, JOPP
> entry true, source contract `extern uint8_t get_ddr_total_density(void)` from
> `include/linux/samsung/sec_smem.h:198`, and no arguments. The actual function body is bounded by
> `get_ddr_rcw_tDQSCK` at `+0xb8`; the proof gates static words `0xd100c3ff`, `0x528010c1`,
> `0x910003e2`, `0x97fe88c6`, `0xf94003e8`, `0xaa0003f3`, `0x39404e60`, `0x2a1f03e0`,
> `0xd65f03c0`, and `0x00be7bad`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; full
> `tests.test_a90_repl` (`Ran 145 tests`, `OK`); `git diff --check`; and CLI
> `call-safety-classify get_ddr_total_density` (`SAFE-SCALAR`, no required pointer args, first BL
> resolved to `qcom_smem_get`). Candidate selection deliberately skipped `get_boot_stat_freq` because
> current C1 policy leaves the tiny leaf body unverified, skipped `get_boot_stat_time` because it reads
> a changing counter and calls logging machinery, and skipped `get_debug_reset_header` because it
> allocates, reads a debug partition, logs, and frees.
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, and helper `version/status` passed. A transient
> serial parse fragment was cleared by restarting the serial bridge; candidate selftest then returned
> `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target
> call.
>
> Result: `a90-repl-live-call-proof-get_ddr_total_density-pass`; checks covered C1 identity, next
> symbol boundary, no-arg source contract, `SAFE-SCALAR` call-safety, SMEM ID/buffer setup,
> `qcom_smem_get`, total-density field load, NULL/error return, and two repeated calls returning the
> stable nonzero uint8 value `0x6`. No owned resource was created and no returned pointer exists; raw
> runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-get-ddr-total-density-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient final
> serial parse fragment was cleared by restarting the serial bridge, and final standalone
> `version/status/selftest` confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records
> `get_ddr_total_density` only under the no-arg SMEM read-only uint8 contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_DDR_TOTAL_DENSITY_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `get_current_napi_context` process-context NULL contract

> ### ✅ STATUS (2026-06-30 live pass) — `get_current_napi_context` promoted under no-arg REPL process-context only
>
> Eighty-first one-target live-call proof after the REPL epic close. Codex continued the scalar/no-pointer
> `get_*` sweep after `get_cpu_device` and selected `get_current_napi_context` because C1 verified
> `get_current_napi_context=0xffffff800971f284`, `export-recovery`, direct-BL xrefs `10`, JOPP entry
> true, source contract `extern struct napi_struct * get_current_napi_context(void)` from
> `include/linux/netdevice.h:3327`, and no arguments. The actual function body is bounded by
> `netdev_has_upper_dev` at `+0x20`; the proof gates static words `0xd0007fc9`, `0xd538d088`,
> `0x910c0129`, `0x8b090108`, `0xf9400900`, `0xd65f03c0`, `0xd503201f`, and `0x00be7bad`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify get_current_napi_context` (`SAFE-SCALAR`, no required pointer args); focused
> unittest coverage for static classification, source signature, and the fake-transport no-arg proof;
> and full `tests.test_a90_repl` (`Ran 144 tests`, `OK`). Candidate selection deliberately skipped
> `get_debug_reset_header` because it allocates, reads a debug partition, logs, and frees, and skipped
> DDR/boot-stat getters because their SMEM/logging paths and device-specific return contracts are weaker.
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/status/selftest` passed, v1-repl candidate flashed through
> `native_init_flash.py` with matching readback SHA, and helper `version/status` passed. A transient
> candidate standalone selftest parse miss was cleared by restarting the serial bridge; candidate
> selftest then returned `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL
> path before the target call.
>
> Result: `a90-repl-live-call-proof-get_current_napi_context-pass`; checks covered C1 identity, next
> symbol boundary, no-arg source contract, `SAFE-SCALAR` call-safety, the per-CPU current-NAPI pointer
> load sequence, and two repeated REPL process-context calls returning NULL. No owned resource was
> created and no pointer was returned; raw runtime address/slide evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-get-current-napi-context-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient final
> standalone `version` parse miss was cleared by restarting the serial bridge, and final standalone
> `version` plus selftest confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records
> `get_current_napi_context` only under the no-arg REPL process-context NULL contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_CURRENT_NAPI_CONTEXT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `get_cpu_device` scalar CPU lookup contract

> ### ✅ STATUS (2026-06-30 live pass) — `get_cpu_device` promoted under scalar CPU index only
>
> Eightieth one-target live-call proof after the REPL epic close. Codex pivoted from the completed
> bitmap mutation-helper sweep to the scalar `get_*` family and selected `get_cpu_device` because C1
> verified `get_cpu_device=0xffffff8008992a5c`, `export-recovery`, direct-BL xrefs `38`, JOPP entry
> true, leaf/no-BL shape, no arg-derived memory bases, source contract
> `extern struct device * get_cpu_device(unsigned cpu)` from `include/linux/cpu.h:38`, and no pointer
> arguments. The proof gates static words `0x90011448`, `0xb940f908`, `0x6b00011f`, `0x54000229`,
> `0xf868d928`, `0x36000108`, `0xf8605908`, `0xf8696900`, and `0xaa1f03e0`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify get_cpu_device` (`SAFE-SCALAR`, no required pointer args); focused unittest
> coverage for static classification, source signature, and the new fake-transport scalar proof; and
> full `tests.test_a90_repl` (`Ran 143 tests`, `OK`). Candidate selection deliberately skipped
> `__bitmap_equal`/`__bitmap_intersects` because current C1 policy leaves them unverified at zero
> direct-BL xrefs, and skipped `get_boot_stat_time` because it calls logging machinery and has a
> weaker externally checkable return contract.
>
> Live validation obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy,
> baseline v2321 `version/selftest` passed, v1-repl candidate flashed through `native_init_flash.py`
> with matching readback SHA, and helper `version/status` passed. A transient candidate standalone
> selftest parse miss was cleared by restarting the serial bridge; candidate selftest then returned
> `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the
> target call.
>
> Result: `a90-repl-live-call-proof-get_cpu_device-pass`; checks covered C1 identity, scalar source
> contract, `SAFE-SCALAR` call-safety, static range/possible/per-CPU/null-return words, `cpu=0`
> returning a non-NULL sane kernel lowmem borrowed pointer, and `cpu=0xffffffff` returning NULL. The
> returned CPU0 pointer is borrowed, not owned; it was not dereferenced or freed, and raw runtime
> address/slide/return-pointer evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-get-cpu-device-20260630/proof/`. Post-proof candidate
> selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient final
> standalone `version` parse miss was cleared by restarting the serial bridge, and final standalone
> `version` plus selftest confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records
> `get_cpu_device` only under the scalar CPU index + borrowed return contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_GET_CPU_DEVICE_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__bitmap_clear` owned bitmap range-clear contract

> ### ✅ STATUS (2026-06-30 live pass) — `__bitmap_clear` promoted under owned bitmap + bounded `start/len` only
>
> Seventy-ninth one-target live-call proof after the REPL epic close. Codex continued the bitmap
> mutation-helper sweep after `__bitmap_set` and selected `__bitmap_clear` because C1 verified
> `__bitmap_clear=0xffffff800855cf14`, `export-recovery`, direct-BL xrefs `33`, JOPP entry true,
> leaf/no-BL shape, source contract
> `extern void __bitmap_clear(unsigned long *map, unsigned int start, int len)`
> from `include/linux/bitmap.h:125`, and pointer arg x0 only. The proof gates static words
> `0x53067c2c`, `0xf940012e`, `0x8a2b01ce`, `0xf900012e`, `0xf800859f`, `0xf940012c`,
> `0x8a280188`, and `0xf9000128`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify __bitmap_clear` (`SAFE-WITH-VALID-PTR`, required x0 `bitmap-buffer`);
> focused unittest coverage for static classification, source signature, and the new fake-transport
> bitmap range-clear proof; and full `tests.test_a90_repl` (`Ran 142 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, helper `version/status` passed, native selftest returned
> `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the
> target call. The candidate image keeps the v2321 version string, so artifact identity was pinned by
> local and boot-block readback SHA rather than by version text.
>
> Result: `a90-repl-live-call-proof-__bitmap_clear-pass`; checks covered C1 identity, source pointer
> contract, `SAFE-WITH-VALID-PTR` call-safety, one owned 128-bit bitmap initialized to all ones plus
> canary, six mutation cases (`start/len`: `5/0`, `1/1`, `4/6`, `62/5`, `80/8`, `0/128`), expected
> range-clear bitmap bytes, canary preservation, and `kfree` cleanup. Raw runtime
> address/slide/allocation/observed-byte evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-bitmap-clear-20260630/proof/`. Post-proof candidate
> selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient final
> standalone `version` parse miss was cleared by restarting the serial bridge, and final standalone
> `version` plus selftest confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records
> `__bitmap_clear` only under the owned-bitmap + scalar bounded `start/len` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BITMAP_CLEAR_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__bitmap_set` owned bitmap range-set contract

> ### ✅ STATUS (2026-06-30 live pass) — `__bitmap_set` promoted under owned bitmap + bounded `start/len` only
>
> Seventy-eighth one-target live-call proof after the REPL epic close. Codex continued the bitmap
> mutation-helper sweep after `__bitmap_or` and selected `__bitmap_set` because C1 verified
> `__bitmap_set=0xffffff800855ce7c`, `export-recovery`, direct-BL xrefs `24`, JOPP entry true,
> leaf/no-BL shape, source contract
> `extern void __bitmap_set(unsigned long *map, unsigned int start, int len)`
> from `include/linux/bitmap.h:124`, and pointer arg x0 only. `__bitmap_clear` was verified as a
> nearby future candidate but parked for this unit. The proof gates static words `0x53067c2c`,
> `0xf940012e`, `0xaa0b01ce`, `0xf900012e`, `0xf8008588`, `0xf940012c`, and `0xf9000128`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify __bitmap_set` (`SAFE-WITH-VALID-PTR`, required x0 `bitmap-buffer`);
> focused unittest coverage for static classification, source signature, and the new fake-transport
> bitmap range-set proof; and full `tests.test_a90_repl` (`Ran 141 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, helper `version/status` passed, native selftest returned
> `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the
> target call. The candidate image keeps the v2321 version string, so artifact identity was pinned by
> local and boot-block readback SHA rather than by version text.
>
> Result: `a90-repl-live-call-proof-__bitmap_set-pass`; checks covered C1 identity, source pointer
> contract, `SAFE-WITH-VALID-PTR` call-safety, one owned 128-bit bitmap plus canary, six mutation
> cases (`start/len`: `5/0`, `1/1`, `4/6`, `62/5`, `80/8`, `0/128`), expected range-set bitmap
> bytes, canary preservation, and `kfree` cleanup. Raw runtime address/slide/allocation/observed-byte
> evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-bitmap-set-20260630/proof/`. Post-proof candidate
> selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient final
> selftest parse miss was cleared by restarting the serial bridge, and final standalone `version` plus
> selftest confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records `__bitmap_set` only
> under the owned-bitmap + scalar bounded `start/len` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BITMAP_SET_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__bitmap_or` owned dst/src/src bitmap contract

> ### ✅ STATUS (2026-06-30 live pass) — `__bitmap_or` promoted under owned destination/source/source bitmaps + bounded `nbits` only
>
> Seventy-seventh one-target live-call proof after the REPL epic close. Codex continued the bitmap
> mutation-helper sweep after `__bitmap_andnot` and selected `__bitmap_or` because C1 verified
> `__bitmap_or=0xffffff800855cbb4`, `export-recovery`, direct-BL xrefs `2`, JOPP entry true,
> leaf/no-BL shape, source contract
> `extern void __bitmap_or(unsigned long *dst, const unsigned long *bitmap1, const unsigned long *bitmap2, unsigned int nbits)`
> from `include/linux/bitmap.h:113`, and pointer args x0/x1/x2 only. `__bitmap_xor` and
> `__bitmap_and` were inspected but parked because they still have zero direct-BL xrefs under the
> current C1 gate. The proof gates static words `0x2a0303e8`, `0x9100fd08`, `0xd346fd08`,
> `0xf840842a`, `0xf840844b`, `0xaa0a016a`, and `0xf800840a`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify __bitmap_or` (`SAFE-WITH-VALID-PTR`, required x0 `bitmap-dst-buffer`,
> x1 `bitmap-left-buffer`, x2 `bitmap-right-buffer`); focused unittest coverage for static
> classification, source signature, and the new fake-transport OR mutation proof; and full
> `tests.test_a90_repl` (`Ran 140 tests`, `OK`). Live validation obeyed the flash gate:
> rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321 `version/status/selftest`
> passed, v1-repl candidate flashed through `native_init_flash.py` with matching readback SHA,
> helper `version/status` passed, candidate standalone selftest was retried after one intentional
> bridge cleanup and returned `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass` confirmed
> the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-__bitmap_or-pass`; checks covered C1 identity, source pointer
> contract, `SAFE-WITH-VALID-PTR` call-safety, owned 128-bit destination/left/partial-right/full-right
> buffers plus canaries, six mutation cases (`nbits=0`, `10`, `64`, `80`, `128` partial-right, and
> `128` full-right), destination matching `left | right` for the covered unsigned-long words,
> left/right/canary immutability, destination canary preservation, and `kfree` cleanup for all four
> buffers. Raw runtime address/slide/allocation/observed-byte evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-bitmap-or-20260630/proof/`. Post-proof candidate
> selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, a transient
> post-restart socket reset was cleared by retry, and final standalone `version` plus selftest
> confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records `__bitmap_or` only under
> the owned-destination/source/source bitmap + scalar bounded `nbits` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BITMAP_OR_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__bitmap_andnot` owned dst/src/mask bitmap contract

> ### ✅ STATUS (2026-06-30 live pass) — `__bitmap_andnot` promoted under owned destination/source/mask bitmaps + bounded `nbits` only
>
> Seventy-sixth one-target live-call proof after the REPL epic close. Codex continued the bitmap
> mutation-helper sweep after `__bitmap_complement` and selected `__bitmap_andnot` because C1
> verified `__bitmap_andnot=0xffffff800855cc24`, `export-recovery`, direct-BL xrefs `1`, JOPP
> entry true, leaf/no-BL shape, source contract
> `extern int __bitmap_andnot(unsigned long *dst, const unsigned long *bitmap1, const unsigned long *bitmap2, unsigned int nbits)`
> from `include/linux/bitmap.h:117`, and pointer args x0/x1/x2 only. The proof gates static words
> `0x53067c69`, `0xf840856e`, `0xf840858f`, `0x8a2f01ce`, `0xf80085ae`,
> `0xf869682a`, `0xf869684b`, `0xf829680a`, and `0x1a9f07e0`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify __bitmap_andnot` (`SAFE-WITH-VALID-PTR`, required x0
> `bitmap-dst-buffer`, x1 `bitmap-src-buffer`, x2 `bitmap-mask-buffer`); focused unittest coverage
> for static classification, source signature, and the new fake-transport mutation/return proof; and
> full `tests.test_a90_repl` (`Ran 139 tests`, `OK`). Live validation obeyed the flash gate:
> rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321 `version/status/selftest`
> passed, v1-repl candidate flashed through `native_init_flash.py` with matching readback SHA,
> helper `version/status` passed, a bridge prompt restart cleared a transient standalone selftest
> desync, candidate selftest stayed `pass=11 warn=1 fail=0`, and `a90-repl-v2a1-selftest-pass`
> confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-__bitmap_andnot-pass`; checks covered C1 identity, source pointer
> contract, `SAFE-WITH-VALID-PTR` call-safety, owned 128-bit destination/source/partial-mask/full-mask
> buffers plus canaries, seven mutation/return cases (`nbits=0` partial-mask false,
> `10/64/80/91/128` partial-mask positives, and `128` full-mask false), destination matching
> `source & ~mask`, source/mask/canary immutability, destination canary preservation, and `kfree`
> cleanup for all four buffers. Raw runtime address/slide/allocation/observed-byte evidence stayed
> private under `workspace/private/runs/kernel/live-call-proof-bitmap-andnot-20260630/proof/`.
> Post-proof candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321
> through `native_init_flash.py`, readback SHA matched, helper `version/status` passed, bridge prompt
> was restarted once to clear a residual probe byte, and final standalone `version` plus selftest
> confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records `__bitmap_andnot` only under
> the owned-destination/source/mask bitmap + scalar bounded `nbits` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BITMAP_ANDNOT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__bitmap_complement` owned dst/src bitmap contract

> ### ✅ STATUS (2026-06-30 live pass) — `__bitmap_complement` promoted under owned destination/source bitmaps + bounded `nbits` only
>
> Seventy-fifth one-target live-call proof after the REPL epic close. Codex continued the bitmap
> helper sweep after `__bitmap_subset` and selected the first simple mutation helper rather than
> widening to the still-parked zero-direct-xref bitmap helpers. Static C1 verified
> `__bitmap_complement=0xffffff800855c8e4`, `export-recovery`, direct-BL xrefs `1`, JOPP entry
> true, leaf/no-BL shape, source contract
> `extern void __bitmap_complement(unsigned long *dst, const unsigned long *src, unsigned int nbits)`
> from `include/linux/bitmap.h:105`, and pointer args x0/x1 only. The proof gates static words
> `0x53067c48`, `0xf840854c`, `0xf800856c`, `0xf8686829`, and `0xf8286809`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify __bitmap_complement` (`SAFE-WITH-VALID-PTR`, required x0
> `bitmap-dst-buffer`, x1 `bitmap-src-buffer`); focused unittest coverage for static
> classification, source signature, and the new fake-transport mutation proof; and full
> `tests.test_a90_repl` (`Ran 138 tests`, `OK`). Live validation obeyed the flash gate:
> rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321 `version/status/selftest`
> passed, v1-repl candidate flashed through `native_init_flash.py` with matching readback SHA,
> the first standalone candidate selftest attempt hit a transient bridge `AT` desync but a follow-up
> `version` re-synchronized the bridge and candidate selftest stayed `pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-__bitmap_complement-pass`; checks covered C1 identity, source
> pointer contract, `SAFE-WITH-VALID-PTR` call-safety, owned 128-bit destination and source bitmap
> buffers plus canaries, five mutation cases (`nbits=0` no-op, `10` low-tail destination
> complement, `64` first-word boundary, `80` second-word tail, `128` full-size complement), source
> bitmap/canary immutability, destination canary preservation, and `kfree` cleanup for both buffers.
> Raw runtime address/slide/allocation/observed-byte evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-bitmap-complement-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, helper `version/status` passed, bridge prompt was
> restarted once to clear a transient `AT` desync, and final standalone `version` plus selftest
> confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records `__bitmap_complement` only
> under the owned-destination/source bitmap + scalar bounded `nbits` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BITMAP_COMPLEMENT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__bitmap_subset` two-owned-bitmap contract

> ### ✅ STATUS (2026-06-30 live pass) — `__bitmap_subset` promoted under two owned bitmaps + bounded `nbits` only
>
> Seventy-fourth one-target live-call proof after the REPL epic close. Codex continued the bitmap
> helper sweep after `__bitmap_weight`. Non-underscored `bitmap_empty/full/equal/intersects/subset`
> names were absent from the verified System.map, and `__bitmap_equal`/`__bitmap_intersects` stayed
> parked because their direct BL xref count is `0` under the current C1 rules. `__bitmap_subset` was
> selected because C1 verified `__bitmap_subset=0xffffff800855cd3c`, `export-recovery`, direct-BL
> xrefs `3`, JOPP entry true, leaf/no-BL shape, source contract
> `extern int __bitmap_subset(const unsigned long *bitmap1, const unsigned long *bitmap2, unsigned int nbits)`
> from `include/linux/bitmap.h:121`, and pointer args x0/x1 only. The proof gates static words
> `0x53067c49`, `0xf940014c`, `0xf940016d`, `0xf869680a`, and `0xf8696829`.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify __bitmap_subset` (`SAFE-WITH-VALID-PTR`, required x0/x1
> `bitmap-buffer`); focused unittest coverage for static classification, source signature, and the
> new fake-transport proof; and full `tests.test_a90_repl` (`Ran 137 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, candidate selftest stayed `pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-__bitmap_subset-pass`; checks covered C1 identity, source
> pointer contract, `SAFE-WITH-VALID-PTR` call-safety, four owned 128-bit unsigned-long bitmaps
> (`src`, `full`, `partial`, `empty`) plus canaries, eight-case return table
> (`0-bit nonempty -> 1`, `empty/full-size -> 1`, `nbits=10/64/80 positives -> 1`,
> `missing bit90 at nbits=91 -> 0`, `full-size partial -> 0`, `full-size full -> 1`),
> all bitmap/canary immutability, and `kfree` cleanup for every buffer. Raw runtime
> address/slide/allocation evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-bitmap-subset-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, `version/status` passed, and final standalone
> selftest confirmed `pass=11 warn=1 fail=0`. Function map records `__bitmap_subset` only under the
> two-owned-bitmap + scalar bounded `nbits` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BITMAP_SUBSET_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__bitmap_weight` owned-bitmap popcount contract

> ### ✅ STATUS (2026-06-30 live pass) — `__bitmap_weight` promoted under owned bitmap + bounded `nbits` only
>
> Seventy-third one-target live-call proof after the REPL epic close. Codex first considered
> `bitmap_ord_to_pos`, but left it parked because the current C1 path had no export and no direct BL
> xrefs. `__bitmap_weight` was selected instead to extend the bitmap helper sweep from bit search to
> bitmap popcount. Static C1 verified `__bitmap_weight=0xffffff800855cdd4`, `export-recovery`,
> direct-BL xrefs `19`, JOPP entry true, non-leaf shape, pinned internal BL words `0x940042b6` and
> `0x940042aa` to already proven `__sw_hweight64`, source contract
> `extern int __bitmap_weight(const unsigned long *bitmap, unsigned int nbits)` from
> `include/linux/bitmap.h:123`, and pointer arg x0 only.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify __bitmap_weight` (`SAFE-WITH-VALID-PTR`, required x0 `bitmap-buffer`);
> focused unittest coverage for static classification, source signature, and the new fake-transport
> proof; and full `tests.test_a90_repl` (`Ran 136 tests`, `OK`). Live validation obeyed the flash
> gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, candidate selftest stayed `pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-__bitmap_weight-pass`; checks covered C1 identity, source
> pointer contract, `SAFE-WITH-VALID-PTR` call-safety, one owned 128-bit unsigned-long bitmap plus
> canary, seven-case return table (`nbits=0 -> 0`, `10 -> 3`, `64 -> 5`, `80 -> 7`, `91 -> 8`,
> `127 -> 8`, `128 -> 9`), bitmap/canary immutability, and `kfree` cleanup. Raw runtime
> address/slide/allocation evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-bitmap-weight-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, `version/status` passed, a combined final read hit
> serial noise and was rechecked with separate read-only commands, and final standalone selftest
> confirmed `pass=11 warn=1 fail=0`. Function map records `__bitmap_weight` only under the owned
> bitmap + scalar bounded `nbits` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BITMAP_WEIGHT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `cpumask_next_and` two-owned-cpumask contract

> ### ✅ STATUS (2026-06-30 live pass) — `cpumask_next_and` promoted under two owned cpumasks + runtime `nr_cpu_ids=8` only
>
> Seventy-second one-target live-call proof after the REPL epic close. After `cpumask_next`,
> `cpumask_any_but`, and `cpumask_next_wrap`, Codex selected `cpumask_next_and` to widen the cpumask
> wrapper sweep from one owned cpumask to two owned cpumasks. Static C1 verified
> `cpumask_next_and=0xffffff80099a9e44`, `export-recovery`, direct-BL xrefs `88`, JOPP entry true,
> non-leaf wrapper shape, internal BL to already proven `find_next_bit`, source contract
> `int cpumask_next_and(int n, const struct cpumask *, const struct cpumask *)` from
> `include/linux/cpumask.h:216`, and pointer args x1/x2 only. The proof gates wrapper words
> `0x52800101` (`mov w1,#8`), `0x97aeebee` (BL to `find_next_bit`),
> `0xb940faa8` (runtime `nr_cpu_ids` load), and `0xf868da68` (x2/andp word load).
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify cpumask_next_and` (`SAFE-WITH-VALID-PTR`, required x1/x2
> `cpumask-buffer`); focused unittest coverage for static classification, source signature, and the
> new fake-transport proof; and full `tests.test_a90_repl` (`Ran 135 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, candidate selftest stayed `pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-cpumask_next_and-pass`; checks covered C1 identity, source
> pointer contract, `SAFE-WITH-VALID-PTR` call-safety, compiled `nr_cpumask_bits=8`, runtime
> `nr_cpu_ids=8`, two owned cpumask allocations, seven-case return table
> (`src={1,3,6},and={3,6},n=-1 -> 3`, `n=2 -> 3`, `n=3 -> 6`, `n=6 -> 8`,
> `src={1},and={3,6},n=-1 -> 8`, `src={},and={3,6},n=-1 -> 8`,
> `src={1,3,6},and={},n=-1 -> 8`), src/and cpumask and canary immutability, and `kfree`
> cleanup for both buffers. Raw runtime address/slide/allocation evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-cpumask-next-and-20260630/proof/`.
> Post-proof candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321
> through `native_init_flash.py`, readback SHA matched, `version/status` passed, and final standalone
> selftest confirmed `pass=11 warn=1 fail=0`. Function map records `cpumask_next_and` only under the
> two-owned-cpumask + scalar `n` + runtime 8-CPU contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CPUMASK_NEXT_AND_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `cpumask_next_wrap` owned-cpumask wrap iterator contract

> ### ✅ STATUS (2026-06-30 live pass) — `cpumask_next_wrap` promoted under owned cpumask + scalar wrap-state contract only
>
> Seventy-first one-target live-call proof after the REPL epic close. After `cpumask_next` and
> `cpumask_any_but`, Codex selected `cpumask_next_wrap` before widening to `cpumask_next_and`
> because it still has one cpumask pointer; the extra surface is scalar `n`, `start`, and wrap-state.
> Static C1 verified `cpumask_next_wrap=0xffffff80099a9f1c`, `export-recovery`, direct-BL xrefs `6`,
> JOPP entry true, non-leaf wrapper shape, internal BL to already proven `find_next_bit`, source
> contract `extern int cpumask_next_wrap(int n, const struct cpumask *mask, int start, bool wrap)`
> from `include/linux/cpumask.h`, and pointer arg x1 only. The proof gates both wrapper constants:
> `0x52800101` (`mov w1,#8`) for the `find_next_bit` size and `0x52800117` (`mov w23,#8`) for the
> sentinel.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify cpumask_next_wrap` (`SAFE-WITH-VALID-PTR`, required x1 `cpumask-buffer`);
> focused unittest coverage for static classification, source signature, and the new fake-transport
> proof; and full `tests.test_a90_repl` (`Ran 134 tests`, `OK`). Live validation obeyed the flash
> gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, candidate selftest stayed `pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-cpumask_next_wrap-pass`; checks covered C1 identity, source
> pointer contract, `SAFE-WITH-VALID-PTR` call-safety, compiled `nr_cpumask_bits=8`, sentinel `8`,
> owned cpumask allocation, six-case return table (`{2,6},n=3,start=4,wrap=0 -> 6`,
> `{2},n=3,start=4,wrap=0 -> 2`, `{2,6},n=1,start=4,wrap=1 -> 2`,
> `{2,6},n=6,start=4,wrap=1 -> 2`, `{2,6},n=2,start=4,wrap=1 -> 8`,
> `{},n=3,start=4,wrap=0 -> 8`), cpumask/canary immutability, and `kfree` cleanup.
> Raw runtime address/slide/allocation evidence stayed private
> under `workspace/private/runs/kernel/live-call-proof-cpumask-next-wrap-20260630/proof/`.
> Post-proof candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321
> through `native_init_flash.py`, readback SHA matched, `version/status` passed, and final standalone
> selftest confirmed `pass=11 warn=1 fail=0`. Function map records `cpumask_next_wrap` only under the
> owned cpumask + scalar `n/start/wrap-state` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CPUMASK_NEXT_WRAP_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `cpumask_any_but` owned-cpumask exclusion contract

> ### ✅ STATUS (2026-06-30 live pass) — `cpumask_any_but` promoted under owned cpumask + runtime `nr_cpu_ids=8` contract only
>
> Seventieth one-target live-call proof after the REPL epic close. After `cpumask_next`, Codex selected
> the next smallest cpumask wrapper, `cpumask_any_but`, rather than widening immediately to
> `cpumask_next_and` or `cpumask_next_wrap`. Static C1 verified
> `cpumask_any_but=0xffffff80099a9ebc`, `export-recovery`, direct-BL xrefs `1`, JOPP entry true,
> non-leaf wrapper shape, internal BL to already proven `find_next_bit`, source contract
> `int cpumask_any_but(const struct cpumask *mask, unsigned int cpu)` from `include/linux/cpumask.h`,
> and pointer arg x0 only. The proof gates the wrapper's `0x52800101` (`mov w1,#8`) instruction and
> reads runtime `nr_cpu_ids` as `8` before accepting sentinel returns.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify cpumask_any_but` (`SAFE-WITH-VALID-PTR`, required x0 `cpumask-buffer`);
> focused unittest coverage for static classification, seed inventory, source signature, and the
> new fake-transport proof; and full `tests.test_a90_repl` (`Ran 133 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, candidate selftest stayed `pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-cpumask_any_but-pass`; checks covered C1 identity, source pointer
> contract, `SAFE-WITH-VALID-PTR` call-safety, compiled `nr_cpumask_bits=8`, static and runtime
> `nr_cpu_ids=8`, owned cpumask poke/peek, five-case return table (`{2,6},cpu=1 -> 2`,
> `{2,6},cpu=2 -> 6`, `{2,6},cpu=6 -> 2`, `{2},cpu=2 -> 8`, `{},cpu=2 -> 8`),
> cpumask/canary immutability, and `kfree` cleanup. Raw runtime address/slide/allocation evidence
> stayed private under `workspace/private/runs/kernel/live-call-proof-cpumask-any-but-20260630/proof/`.
> Post-proof candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321
> through `native_init_flash.py`, readback SHA matched, `version/status` passed, and final standalone
> `version` plus selftest confirmed v2321 with `pass=11 warn=1 fail=0`. Function map records
> `cpumask_any_but` only under the owned cpumask + scalar excluded CPU + runtime 8-CPU contract.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CPUMASK_ANY_BUT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `cpumask_next` owned-cpumask contract

> ### ✅ STATUS (2026-06-30 live pass) — `cpumask_next` promoted under owned cpumask + compiled `nr_cpumask_bits=8` contract only
>
> Sixty-ninth one-target live-call proof after the REPL epic close. After the bitmap scanner trio
> landed, Codex selected the smallest wrapper extension, `cpumask_next`, rather than widening trust
> across `cpumask_next_and`, `cpumask_any_but`, `cpumask_next_wrap`, or `bitmap_ord_to_pos`. Static C1
> verified `cpumask_next=0xffffff80099a9e14`, `export-recovery`, direct-BL xrefs `1563`, JOPP entry
> true, non-leaf wrapper shape, internal BL to already proven `find_next_bit`, source contract
> `unsigned int cpumask_next(int n, const struct cpumask *srcp)` from `include/linux/cpumask.h`, and
> pointer arg x1 only. The proof additionally gates the wrapper instruction word `0x52800101`
> (`mov w1,#8`) so the compiled `nr_cpumask_bits=8` contract cannot silently drift.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify cpumask_next` (`SAFE-WITH-VALID-PTR`, required x1 `cpumask-buffer`);
> focused unittest coverage for static classification, seed inventory, source signature, and the
> new fake-transport proof; and full `tests.test_a90_repl` (`Ran 132 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, candidate selftest stayed `pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-cpumask_next-pass`; checks covered C1 identity, source pointer
> contract, `SAFE-WITH-VALID-PTR` call-safety, compiled `nr_cpumask_bits=8`, owned cpumask
> poke/peek with set CPU bits `2` and `6`, five-case return table (`n=-1 -> 2`, `n=1 -> 2`,
> `n=2 -> 6`, `n=6 -> 8`, `n=7 -> 8`), cpumask/canary immutability, and `kfree` cleanup. Raw
> runtime address/slide/allocation evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-cpumask-next-20260630/proof/`. Post-proof candidate
> selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, `version/status` passed, a first standalone final
> `version` read hit serial sync noise (`A90P1 END marker not found`) while bridge stayed connected,
> and retry plus final standalone selftest confirmed v2321 with `pass=11 warn=1 fail=0`. Function map
> records `cpumask_next` only under the owned cpumask + compiled 8-CPU mask contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_CPUMASK_NEXT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `find_last_bit` owned-bitmap contract

> ### ✅ STATUS (2026-06-30 live pass) — `find_last_bit` promoted under owned bitmap + bounded scalar size contract only
>
> Sixty-eighth one-target live-call proof after the REPL epic close. After the
> `find_next_bit`/`find_next_zero_bit` proofs, Codex selected the adjacent reverse bitmap scanner
> rather than widening trust across wrapper helpers such as `bitmap_ord_to_pos` or `cpumask_next`.
> Static C1 verified `find_last_bit=0xffffff8008564f0c`, `export-recovery`, direct-BL xrefs `9`,
> JOPP entry true, leaf/no-BL, no tainted-argument calls, and source contract
> `extern unsigned long find_last_bit(const unsigned long *addr, unsigned long size)` from
> `include/linux/bitops.h` with pointer arg x0 only. The analyzer reports size-derived address flow
> through x1, so the proof contract explicitly bounds scalar size inside the owned bitmap allocation.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify find_last_bit` (`SAFE-WITH-VALID-PTR`, required x0 `bitmap-buffer`);
> focused unittest coverage for static classification, seed inventory, source signature, and the
> new fake-transport proof; and full `tests.test_a90_repl` (`Ran 131 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, one ordinary `a90ctl selftest` read hit serial noise before the REPL path,
> and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-find_last_bit-pass`; checks covered C1 identity, source pointer
> contract, `SAFE-WITH-VALID-PTR` call-safety, owned 128-bit bitmap poke/peek, six-case return table
> (`size=128 -> 90`, `size=88 -> 73`, `size=64 -> 9`, `size=10 -> 9`, `size=9 -> 9`,
> `size=0 -> 0`), bitmap/canary immutability, and `kfree` cleanup. Raw runtime
> address/slide/allocation evidence stayed private under
> `workspace/private/runs/kernel/live-call-proof-find-last-bit-20260630/proof/`. Post-proof
> candidate selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, `version/status` passed, final standalone selftest
> confirmed `pass=11 warn=1 fail=0`, and bridge status returned connected. Function map records
> `find_last_bit` only under the owned bitmap + bounded scalar size contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_FIND_LAST_BIT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `find_next_bit` owned-bitmap contract

> ### ✅ STATUS (2026-06-30 live pass) — `find_next_bit` promoted under owned bitmap + bounded scalar size/offset contract only
>
> Sixty-seventh one-target live-call proof after the REPL epic close. After the
> `find_next_zero_bit` proof, Codex selected the adjacent positive bitmap scanner for a separate
> target-specific proof instead of generalizing trust across the bit-search family. Static C1 verified
> `find_next_bit=0xffffff8008564e2c`, `export-recovery`, direct-BL xrefs `564`, JOPP entry true,
> leaf/no-BL, no tainted-argument calls, and source contract
> `extern unsigned long find_next_bit(const unsigned long *addr, unsigned long size, unsigned long offset)`
> from `include/asm-generic/bitops/find.h` with pointer arg x0 only. The analyzer still reports
> conservative size/offset address-flow through x1/x2, so the proof contract explicitly bounds both
> scalar size and scalar offset inside the owned bitmap allocation.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify find_next_bit` (`SAFE-WITH-VALID-PTR`, required x0 `bitmap-buffer`);
> focused unittest coverage for static classification, seed inventory, source signature, and the
> new fake-transport proof; and full `tests.test_a90_repl` (`Ran 130 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target
> call.
>
> Result: `a90-repl-live-call-proof-find_next_bit-pass`; checks covered C1 identity, source pointer
> contract, `SAFE-WITH-VALID-PTR` call-safety, owned 128-bit bitmap poke/peek, six-case return table
> (`size=128,offset=0 -> 9`, `size=128,offset=10 -> 73`, `size=128,offset=74 -> 90`,
> `size=80,offset=64 -> 73`, `size=88,offset=74 -> 88`, `size=128,offset=91 -> 128`),
> bitmap/canary immutability, and `kfree` cleanup. Raw runtime address/slide/allocation evidence
> stayed private under `workspace/private/runs/kernel/live-call-proof-find-next-bit-20260630/proof/`.
> Post-proof selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, `version/status` passed, and final standalone
> selftest retry confirmed `pass=11 warn=1 fail=0` after one serial-noise read. Function map records
> `find_next_bit` only under the owned bitmap + bounded scalar size/offset contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_FIND_NEXT_BIT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `find_next_zero_bit` owned-bitmap contract

> ### ✅ STATUS (2026-06-30 live pass) — `find_next_zero_bit` promoted under owned bitmap + bounded scalar size/offset contract only
>
> Sixty-sixth one-target live-call proof after the REPL epic close. Candidate selection found that the
> existing 65 proof targets were already live-proven, then swept adjacent bit helpers. `memblock_*`
> candidates were rejected despite advisory hits because they are behavior-changing allocator state,
> and `find_next_bit` stayed parked because the current analyzer still reports conservative
> size/offset address-flow. Codex selected only `find_next_zero_bit`: static C1 verified
> `find_next_zero_bit=0xffffff8008564e94`, `export-recovery`, direct-BL xrefs `120`, JOPP entry
> true, leaf/no-BL, no tainted-argument calls, and source contract
> `extern unsigned long find_next_zero_bit(const unsigned long *addr, unsigned long size, unsigned long offset)`
> from `include/asm-generic/bitops/find.h` with pointer arg x0 only.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; CLI
> `call-safety-classify find_next_zero_bit` (`SAFE-WITH-VALID-PTR`, required x0 `bitmap-buffer`);
> focused unittest coverage for static classification, seed inventory, source signature, and the
> new fake-transport proof; and full `tests.test_a90_repl` (`Ran 129 tests`, `OK`). Live validation
> obeyed the flash gate: rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321
> `version/status/selftest` passed, v1-repl candidate flashed through `native_init_flash.py` with
> matching readback SHA, one transient serial END-marker miss during first REPL selftest was retried,
> and `a90-repl-v2a1-selftest-pass` confirmed the REPL path before the target call.
>
> Result: `a90-repl-live-call-proof-find_next_zero_bit-pass`; checks covered C1 identity, source
> pointer contract, `SAFE-WITH-VALID-PTR` call-safety, owned 128-bit bitmap poke/peek, five-case
> return table (`size=128,offset=0 -> 9`, `size=128,offset=10 -> 73`,
> `size=128,offset=74 -> 128`, `size=80,offset=64 -> 73`, `size=80,offset=74 -> 80`), bitmap/canary
> immutability, and `kfree` cleanup. Raw runtime address/slide/allocation evidence stayed private
> under `workspace/private/runs/kernel/live-call-proof-find-next-zero-bit-20260630/proof/`.
> Post-proof selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, `version/status` passed, and final standalone
> selftest retry confirmed `pass=11 warn=1 fail=0` after one serial-noise read. Function map records
> `find_next_zero_bit` only under the owned bitmap + bounded scalar size/offset contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_FIND_NEXT_ZERO_BIT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__sw_hweight64` scalar popcount contract

> ### ✅ STATUS (2026-06-30 live pass) — `__sw_hweight64` promoted under scalar unsigned-64 contract only
>
> Sixty-fifth one-target live-call proof after the REPL epic close. Candidate selection revisited the
> previously parked adjacent bit helper: static C1 already verified `__sw_hweight64` by
> `export-recovery`, but the source oracle failed closed because the parser did not recognize kernel
> typedef spellings such as `__u64`. Codex fixed the source parser narrowly by adding kernel
> `__u8`, `__u16`, `__u32`, and `__u64` to typed-argument recognition, added the `include/linux/bitops.h` hint, and then
> selected only `__sw_hweight64` for proof. Static gate: `__sw_hweight64=0xffffff800856d8e4`,
> `export-recovery`, direct-BL xrefs `228`, JOPP entry true, leaf/no-BL, no argument memory
> dereference, no tainted-argument call, and scalar arg-taint stayed out of memory-base use. Source
> contract: `extern unsigned long __sw_hweight64(__u64 w)` from `include/linux/bitops.h`, no pointer
> args.
>
> Host validation passed: `py_compile` for `a90_repl.py` and `tests/test_a90_repl.py`; focused
> unittest set covering static classification, seed inventory, source signature lookup, and fake
> call-proof (`Ran 4 tests`, `OK`); full `tests.test_a90_repl` (`Ran 128 tests`, `OK`); and CLI
> `call-safety-classify __sw_hweight64` (`SAFE-SCALAR`). Live validation obeyed the flash gate:
> rollback/fallback/TWRP SHAs confirmed, bridge healthy, baseline v2321 health checked, v1-repl
> candidate flashed through `native_init_flash.py` with matching readback SHA, and
> `a90-repl-v2a1-selftest-pass` confirmed the REPL path was resident. Codex then ran
> `call-proof __sw_hweight64` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-__sw_hweight64-pass`; checks covered C1 identity, source
> scalar-only contract, `SAFE-SCALAR` call-safety, and a five-case table:
> `0x0000000000000000 -> 0`, `0xffffffffffffffff -> 64`, `0xaaaaaaaaaaaaaaaa -> 32`,
> `0x8000000000000000 -> 1`, and `0xa90f00dca90f00dc -> 26`. Raw runtime address/slide evidence
> stayed private under `workspace/private/runs/kernel/live-call-proof-sw-hweight64-20260630/proof/`.
> Post-proof selftest stayed `pass=11 warn=1 fail=0`; Codex rolled back to clean v2321 through
> `native_init_flash.py`, readback SHA matched, `version/status` passed, and final standalone
> selftest stayed `pass=11 warn=1 fail=0`. Function map records `__sw_hweight64` only under the
> scalar unsigned-64 input contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SW_HWEIGHT64_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__sw_hweight8` scalar popcount contract

> ### ✅ STATUS (2026-06-30 live pass) — `__sw_hweight8` promoted under scalar unsigned-8 contract only
>
> Sixty-fourth one-target live-call proof after the REPL epic close. Candidate selection continued
> the scalar bit-helper sweep: `__sw_hweight8` was `SAFE-SCALAR` advisory with source signature found,
> while `__sw_hweight64` stayed parked because source signature lookup was still missing. Codex
> selected only `__sw_hweight8` and extended `a90_repl.py` `call-proof` with a fixed 8-bit case table.
> Static gate: `__sw_hweight8=0xffffff800856d8b4`, `export-recovery`, direct-BL xrefs `23`, JOPP
> entry true, leaf/no-BL, no arg pointer derefs, clean scalar arg-taint proof. Source contract:
> `extern unsigned int __sw_hweight8(unsigned int w)` from `include/linux/bitops.h`, no pointer args.
> Call-safety tier: `SAFE-SCALAR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, retried through one transient serial END-marker
> timeout while setting `panic_on_oops`, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof __sw_hweight8` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-__sw_hweight8-pass`; checks covered C1 identity, source
> signature, call-safety contract, and scalar case table: `0x00 -> 0`, `0xff -> 8`,
> `0xaa -> 4`, `0x80 -> 1`, `0xa9 -> 4`.
>
> Candidate selftest after proof stayed `pass=11 warn=1 fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata`, rollback helper health passed, and final standalone
> `selftest pass=11 warn=1 fail=0` after one transient serial `ATATAT` capture retry. Function map
> records `__sw_hweight8` only under the scalar unsigned-8 input contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SW_HWEIGHT8_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__sw_hweight16` scalar popcount contract

> ### ✅ STATUS (2026-06-30 live pass) — `__sw_hweight16` promoted under scalar unsigned-16 contract only
>
> Sixty-third one-target live-call proof after the REPL epic close. Candidate selection compared the
> adjacent bit helper candidates: `__sw_hweight16` and `__sw_hweight8` were `SAFE-SCALAR` advisory
> candidates, while `__sw_hweight64` stayed parked because source signature lookup was missing. Codex
> selected `__sw_hweight16` as the next single target and extended `a90_repl.py` `call-proof` with a
> fixed 16-bit case table. Static gate: `__sw_hweight16=0xffffff800856d87c`, `export-recovery`,
> direct-BL xrefs `19`, JOPP entry true, leaf/no-BL, no arg pointer derefs, clean scalar arg-taint
> proof. Source contract: `extern unsigned int __sw_hweight16(unsigned int w)` from
> `include/linux/bitops.h`, no pointer args. Call-safety tier: `SAFE-SCALAR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof __sw_hweight16` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-__sw_hweight16-pass`; checks covered C1 identity, source
> signature, call-safety contract, and scalar case table: `0x0000 -> 0`, `0xffff -> 16`,
> `0xaaaa -> 8`, `0x8000 -> 1`, `0xa90d -> 7`.
>
> Candidate selftest after proof stayed `pass=11 warn=1 fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata`, rollback helper health passed, and final standalone
> `selftest pass=11 warn=1 fail=0`. Function map records `__sw_hweight16` only under the scalar
> unsigned-16 input contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SW_HWEIGHT16_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__sw_hweight32` scalar popcount contract

> ### ✅ STATUS (2026-06-30 live pass) — `__sw_hweight32` promoted under scalar unsigned-32 contract only
>
> Sixty-second one-target live-call proof after the REPL epic close. Candidate selection rejected
> `memscan` for this unit because C1 identity remained unverified (`direct_bl_xrefs=0`, x0 memory
> flow, unseeded pointer contract). Codex instead selected scalar-only `__sw_hweight32`, then extended
> `a90_repl.py` `call-proof` with a fixed case table. Static gate:
> `__sw_hweight32=0xffffff800856d844`, `export-recovery`, direct-BL xrefs `36`, JOPP entry true,
> leaf/no-BL, no arg pointer derefs, clean scalar arg-taint proof. Source contract:
> `extern unsigned int __sw_hweight32(unsigned int w)` from `include/linux/bitops.h`, no pointer args.
> Call-safety tier: `SAFE-SCALAR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, then ran REPL selftest. The first REPL selftest
> attempt hit a transient serial END-marker timeout while setting `panic_on_oops`; immediate device
> health stayed `selftest pass=11 warn=1 fail=0`, and a retry returned
> `a90-repl-v2a1-selftest-pass`. Then Codex ran `call-proof __sw_hweight32` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-__sw_hweight32-pass`; checks covered C1 identity, source
> signature, call-safety contract, and scalar case table: `0x00000000 -> 0`, `0xffffffff -> 32`,
> `0xaaaaaaaa -> 16`, `0x80000000 -> 1`, `0xa90f00dc -> 13`.
>
> Candidate selftest after proof stayed `pass=11 warn=1 fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata`, rollback helper health passed, and final standalone
> `selftest pass=11 warn=1 fail=0`. Function map records `__sw_hweight32` only under the scalar
> unsigned-32 input contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SW_HWEIGHT32_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `__sysfs_match_string` owned sysfs array contract

> ### ✅ STATUS (2026-06-30 live pass) — `__sysfs_match_string` promoted under owned array/search contract only
>
> Sixty-first one-target live-call proof after the REPL epic close. Codex extended
> `a90_repl.py` `call-proof` with `__sysfs_match_string`, using one tool-owned layout containing
> an owned `const char *` array, owned NUL-terminated string entries, an owned search string
> `A90SYSFSMATCH-BRAVO\n`, and canaries around all controlled regions. Static gate:
> `__sysfs_match_string=0xffffff80099b9d1c`, `export-recovery`, direct-BL xrefs `11`, JOPP
> entry true, leaf/no-BL. Source contract:
> `int __sysfs_match_string(const char * const *array, size_t n, const char *s)` from
> `include/linux/string.h`; x0 and x2 are pointer args and x1 is scalar bounded count.
> Call-safety tier: `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, then ran REPL selftest. The first REPL
> selftest attempt hit a transient serial END-marker timeout while setting `panic_on_oops`;
> immediate device health stayed `selftest pass=11 warn=1 fail=0`, and a retry returned
> `a90-repl-v2a1-selftest-pass`. Then Codex ran `call-proof __sysfs_match_string` with the
> C2B verified map.
>
> Result: `a90-repl-live-call-proof-__sysfs_match_string-pass`; checks covered C1 identity,
> source signature, call-safety contract, owned layout allocation/poke/peek, newline-tolerant
> hit returning index `1`, missing search returning `0xffffffea`, zero count returning
> `0xffffffea`, unchanged table/items/search regions, and `kfree-owned-sysfs-match-string-layout-ok`.
>
> Candidate selftest after proof stayed `pass=11 warn=1 fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata`, rollback helper health passed, and final standalone
> `selftest pass=11 warn=1 fail=0`. Function map records `__sysfs_match_string` only under
> the owned array plus owned search string and bounded-count contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SYSFS_MATCH_STRING_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `match_token` owned exact table contract

> ### ✅ STATUS (2026-06-30 live pass) — `match_token` promoted under owned exact `match_token` table only
>
> Sixtieth one-target live-call proof after the REPL epic close. Codex extended
> `a90_repl.py` `call-proof` with `match_token`, using one tool-owned layout containing a
> mutable option string `A90MATCH-TOKEN`, a 16-byte-entry `match_token` table with one exact
> no-`%` pattern plus a NULL-pattern terminator, an owned `substring_t args[MAX_OPT_ARGS]`
> canary region, and canaries around all controlled regions. Static gate:
> `match_token=0xffffff800855b404`, `export-recovery`, direct-BL xrefs `23`, JOPP entry
> true, non-leaf helper calling `__pi_strcmp`, `strchr`, `simple_strtoul`, `__pi_strncmp`,
> `__pi_strlen`, and `simple_strtol`. Source contract:
> `int match_token(char *, const match_table_t table, substring_t args[])` from
> `include/linux/parser.h`; the `match_table_t` array typedef is treated as an x1 pointer
> after typedef-decay, so x0/x1/x2 are all required owned pointers. Call-safety tier:
> `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, then ran REPL selftest. The first REPL
> selftest attempt hit a transient serial END-marker timeout while setting `panic_on_oops`;
> immediate device health stayed `selftest pass=11 warn=1 fail=0`, and a wider-timeout retry
> returned `a90-repl-v2a1-selftest-pass`. Then Codex ran `call-proof match_token` with the
> C2B verified map.
>
> Result: `a90-repl-live-call-proof-match_token-pass`; checks covered C1 identity, source
> signature, call-safety contract, owned layout allocation/poke/peek, exact-pattern token
> return `0x4a90`, unchanged table, unchanged args region, unchanged input string, unchanged
> pattern string, and `kfree-owned-match-token-layout`.
>
> Candidate selftest after proof stayed `pass=11 warn=1 fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata`; rollback helper health passed, then the first standalone
> final selftest hit a serial echo-noise END-marker miss and the immediate retry returned
> `selftest pass=11 warn=1 fail=0`. Function map records `match_token` only under the owned
> exact-table contract; `%d/%s/%u/%o/%x` substring extraction paths remain separate future
> targets. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_MATCH_TOKEN_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `match_strdup` owned substring duplicate contract

> ### ✅ STATUS (2026-06-30 live pass) — `match_strdup` promoted under owned `substring_t` only
>
> Fifty-ninth one-target live-call proof after the REPL epic close. Codex extended
> `a90_repl.py` `call-proof` with `match_strdup`, using one tool-owned layout containing a
> `substring_t {from,to}` slot, bounded text `A90MATCH-STRDUP-Q-END`, and canaries around the
> controlled source regions. Static gate: `match_strdup=0xffffff800855b98c`,
> `export-recovery`, direct-BL xrefs `28`, JOPP entry true, non-leaf helper calling
> `__kmalloc` and `__memcpy`, source contract `char * match_strdup(const substring_t *)`
> from `include/linux/parser.h`, x0 as the substring pointer, and call-safety tier
> `SAFE-WITH-VALID-PTR`. The target's x0 memory reads are allowed only because x0 is a
> verified owned `substring_t`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, then ran REPL selftest. The first REPL
> selftest attempt hit a transient serial END-marker timeout while setting `panic_on_oops`;
> immediate device health stayed `selftest pass=11 warn=1 fail=0`, and a wider-timeout retry
> returned `a90-repl-v2a1-selftest-pass`. Then Codex ran `call-proof match_strdup` with the
> C2B verified map.
>
> Result: `a90-repl-live-call-proof-match_strdup-pass`; checks covered C1 identity, source
> signature, call-safety contract, owned layout allocation/poke/peek, sane distinct returned
> duplicate pointer (redacted), duplicate bytes matching the substring plus generated NUL,
> unchanged `substring_t`, unchanged input text, and `kfree-owned-match-strdup-layout-and-duplicate`.
>
> Candidate selftest after proof stayed `pass=11 warn=1 fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. The final
> health read contained minor serial echo noise before the valid END marker. Function map
> records `match_strdup` only under the owned substring plus returned-owned-duplicate cleanup
> contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_MATCH_STRDUP_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `match_octal` owned substring result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `match_octal` promoted under owned `substring_t` + owned `int *result` only
>
> Fifty-eighth one-target live-call proof after the REPL epic close. Codex extended
> `a90_repl.py` `call-proof` with `match_octal`, using one tool-owned layout containing a
> `substring_t {from,to}` slot, bounded octal text `755`, an owned 4-byte result slot, and
> canaries around the controlled regions. Static gate: `match_octal=0xffffff800855b83c`,
> `export-recovery`, direct-BL xrefs `14`, JOPP entry true, non-leaf wrapper calling
> `match_number` after setting `w2=8` for octal parsing, source contract
> `int match_octal(substring_t *, int *result)` from `include/linux/parser.h`, x0 as the
> substring pointer and x1 as the result pointer, and call-safety tier
> `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, then ran REPL selftest. The first REPL
> selftest attempt hit a transient serial END-marker timeout while setting `panic_on_oops`;
> immediate device health stayed `selftest pass=11 warn=1 fail=0`, and a wider-timeout retry
> returned `a90-repl-v2a1-selftest-pass`. Then Codex ran `call-proof match_octal` with the
> C2B verified map.
>
> Result: `a90-repl-live-call-proof-match_octal-pass`; checks covered C1 identity, source
> signature, call-safety contract, owned layout allocation/poke/peek, return `0`, result slot
> value `493` with raw `0x000001ed`, unchanged `substring_t`, unchanged input text, preserved
> result-slot canary, and `kfree-owned-match-octal-layout`.
>
> Candidate selftest after proof stayed `pass=11 warn=1 fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map
> records `match_octal` only under the owned substring plus owned int-result contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_MATCH_OCTAL_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `match_int` owned substring result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `match_int` promoted under owned `substring_t` + owned `int *result` only
>
> Fifty-seventh one-target live-call proof after the REPL epic close. Codex extended
> `a90_repl.py` `call-proof` with `match_int`, using one tool-owned layout containing a
> `substring_t {from,to}` slot, bounded decimal text `12345`, an owned 4-byte result slot, and
> canaries around the controlled regions. Static gate: `match_int=0xffffff800855b65c`,
> `export-recovery`, direct-BL xrefs `54`, JOPP entry true, non-leaf wrapper calling
> `match_number` after setting `w2=0` for auto-base decimal parsing, source contract
> `int match_int(substring_t *, int *result)` from `include/linux/parser.h`, x0 as the
> substring pointer and x1 as the result pointer, and call-safety tier
> `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof match_int` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-match_int-pass`; checks covered C1 identity, source
> signature, call-safety contract, owned layout allocation/poke/peek, return `0`, result slot
> value `12345` with raw `0x00003039`, unchanged `substring_t`, unchanged input text, preserved
> result-slot canary, and `kfree-owned-match-int-layout`.
>
> Candidate selftest after proof stayed `pass=11 warn=1 fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map
> records `match_int` only under the owned substring plus owned int-result contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_MATCH_INT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `memzero_explicit` owned zeroing contract

> ### ✅ STATUS (2026-06-30 live pass) — `memzero_explicit` promoted under owned destination + bounded count only
>
> Fifty-sixth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `memzero_explicit`, using one tool-owned initialized destination buffer, scalar
> zero count `24`, a post-count tail region, and a post-buffer canary. Static gate:
> `memzero_explicit=0xffffff80099b9dd4`, `export-recovery`, direct-BL xrefs `140`, JOPP entry true,
> non-leaf helper calling `__memset`, source contract `void memzero_explicit(void *s, size_t count)`
> from `include/linux/string.h`, x0 as destination pointer and x1 as scalar count, and call-safety
> tier `SAFE-WITH-VALID-PTR`. Disasm confirmed `x1 -> x2`, `w1 = 0`, then
> `__memset(x0, 0, x1)`. The return value is intentionally ignored because the source API is `void`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, confirmed post-flash selftest fail=0, got
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof memzero_explicit` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-memzero_explicit-pass`; checks covered C1 identity, source
> signature, call-safety contract, owned buffer allocation/poke/peek, ignored void return, first
> 24 bytes zeroed, bytes after count preserved, post-count canary preserved, and
> `kfree-owned-memzero-explicit-destination-buffer`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`; the final read had
> minor serial echo noise but a valid END marker and rc=0/status=ok. Function map records
> `memzero_explicit` only under the owned destination plus bounded zero-count contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_MEMZERO_EXPLICIT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `strsep` owned tokenizer mutation contract

> ### ✅ STATUS (2026-06-30 live pass) — `strsep` promoted under owned char** slot + owned mutable string + owned delimiter only
>
> Fifty-fifth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strsep`, using one tool-owned `char **` cursor slot pointing to one tool-owned
> mutable NUL-terminated string and one tool-owned NUL-terminated delimiter string. Static gate:
> `strsep=0xffffff80099b9b94`, `export-recovery`, direct-BL xrefs `230`, JOPP entry true,
> leaf/no-BL tokenizer, source contract `extern char * strsep(char **,const char *)` from
> `include/linux/string.h`, x0/x1 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
> Disasm confirmed the early x0 `char **` dereference, delimiter/string byte reads, delimiter NUL
> write into the owned mutable string, and next-cursor write back through the owned slot. The
> pre-arg-deref allowance is scoped only to the owned cursor-slot layout.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, confirmed post-flash selftest fail=0, got
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strsep` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-strsep-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `strsep(&cursor, ",")` over `A90STRSEP-HEAD,Q-TAIL`, return offset `0`, delimiter offset `14`
> replaced with NUL, cursor slot advanced to offset `15`, delimiter immutability, slot/string/
> delimiter canary preservation, and `kfree-owned-strsep-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final sequential retry `selftest pass=11 warn=1 fail=0` after
> one final serial framing-noise read. Function map records `strsep` only under the owned slot/string/
> delimiter contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_STRSEP_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtoll` signed long long result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtoll` promoted under owned signed numeric string + owned ll result slot only
>
> Fifty-fourth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtoll`, using one tool-owned NUL-terminated signed numeric string, scalar
> base `16`, and one tool-owned `long long *` result slot. Static gate:
> `kstrtoll=0xffffff800856b524`, `export-recovery`, direct-BL xrefs `42`, JOPP entry true,
> non-leaf signed parser calling `kstrtoull`, source contract
> `int __must_check kstrtoll(const char *s, unsigned int base, long long *res)` from
> `include/linux/kernel.h`, x0/x2 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
> Disasm confirmed direct x0 sign/prefix reads before first BL, the bounded unsigned parse call into
> `kstrtoull`, and one 8-byte success write to x2/result slot. The pre-arg-deref allowance is scoped
> only to the owned signed string buffer.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, confirmed post-flash selftest fail=0, got
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof kstrtoll` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrtoll-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `kstrtoll("-1234567890abcdef", 16, &res) == 0`, result slot storing signed
> `-1311768467294899695` with raw two's-complement `0xedcba9876f543211`, input immutability,
> 8-byte result-slot canary preservation, and `kfree-owned-kstrtoll-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final sequential retry `selftest pass=11 warn=1 fail=0` after
> one final serial framing-noise read. Function map records `kstrtoll` only under the owned signed
> numeric string plus scalar base plus owned signed-long-long result slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOLL_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtoull` unsigned long long result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtoull` promoted under owned unsigned numeric string + owned ull result slot only
>
> Fifty-third one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtoull`, using one tool-owned NUL-terminated unsigned numeric string, scalar
> base `16`, and one tool-owned `unsigned long long *` result slot. Static gate:
> `kstrtoull=0xffffff800856b3f4`, `export-recovery`, direct-BL xrefs `196`, JOPP entry true,
> leaf/no-BL parser, source contract
> `int __must_check kstrtoull(const char *s, unsigned int base, unsigned long long *res)` from
> `include/linux/kernel.h`, x0/x2 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
> Disasm confirmed x0-derived bounded string reads and one 8-byte success write `str x9, [x2]` to
> the x2 result slot.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, retried one serial-noisy post-flash selftest,
> got `a90-repl-v2a1-selftest-pass`, then ran `call-proof kstrtoull` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrtoull-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `kstrtoull("1234567890abcdef", 16, &res) == 0`, result slot storing
> `0x1234567890abcdef`, input immutability, 8-byte result-slot canary preservation, and
> `kfree-owned-kstrtoull-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final sequential retry `selftest pass=11 warn=1 fail=0` after
> one final serial framing-noise read. Function map records `kstrtoull` only under the owned unsigned
> numeric string plus scalar base plus owned unsigned-long-long result slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOULL_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtobool` bool result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtobool` promoted under owned bool string + owned bool result slot only
>
> Fifty-second one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtobool`, using one tool-owned NUL-terminated bool string and one tool-owned
> `bool *` result slot. Static gate: `kstrtobool=0xffffff800856baa4`, `export-recovery`,
> direct-BL xrefs `50`, JOPP entry true, leaf/no-BL bool parser, source contract
> `int __must_check kstrtobool(const char *s, bool *res)` from `include/linux/kernel.h`, x0/x1
> pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`. Disasm confirmed direct x0 string reads
> and success writes to the x1 result slot using `strb`; `allow_pre_arg_deref=True` is accepted only
> under the owned NUL string contract.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof kstrtobool` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrtobool-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek, `kstrtobool("Y", &res) == 0`, result slot
> storing bool `true` with raw `0x01`, input immutability, 1-byte result-slot canary preservation, and
> `kfree-owned-kstrtobool-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final sequential retry `selftest pass=11 warn=1 fail=0` after
> one combined health read hit transient serial framing noise. Function map records `kstrtobool` only
> under the owned bool string plus owned bool result slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOBOOL_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtos8` signed 8-bit result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtos8` promoted under owned signed numeric string + owned s8 result slot only
>
> Fifty-first one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtos8`, using one tool-owned NUL-terminated signed numeric string, scalar
> base `10`, and one tool-owned `s8 *` result slot. Static gate:
> `kstrtos8=0xffffff800856ba24`, `export-recovery`, direct-BL xrefs `12`, JOPP entry true,
> non-leaf helper calling `kstrtoll`, source contract
> `int __must_check kstrtos8(const char *s, unsigned int base, s8 *res)` from
> `include/linux/kernel.h`, x0/x2 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
> Disasm confirmed signed 8-bit range validation via `cmp x8, w8, sxtb`/`b.eq` and a 1-byte
> success write `strb w8, [x19]` to the x2 result slot.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof kstrtos8` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrtos8-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `kstrtos8("-85", 10, &res) == 0`, result slot storing signed `-85` with raw `0xab`, input
> immutability, 1-byte result-slot canary preservation, and `kfree-owned-kstrtos8-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kstrtos8` only under the owned signed numeric string plus scalar base plus owned signed-8 result
> slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOS8_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtou8` unsigned 8-bit result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtou8` promoted under owned numeric string + owned u8 result slot only
>
> Fiftieth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtou8`, using one tool-owned NUL-terminated unsigned numeric string, scalar
> base `10`, and one tool-owned `u8 *` result slot. Static gate:
> `kstrtou8=0xffffff800856b9a4`, `export-recovery`, direct-BL xrefs `59`, JOPP entry true,
> non-leaf helper calling `kstrtoull`, source contract
> `int __must_check kstrtou8(const char *s, unsigned int base, u8 *res)` from
> `include/linux/kernel.h`, x0/x2 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
> Disasm confirmed unsigned 8-bit range validation via `cmp x8, #0xff`/`b.ls` and a 1-byte
> success write `strb w8, [x19]` to the x2 result slot.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof kstrtou8` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrtou8-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `kstrtou8("213", 10, &res) == 0`, result slot storing unsigned `213` with raw `0xd5`, input
> immutability, 1-byte result-slot canary preservation, and `kfree-owned-kstrtou8-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kstrtou8` only under the owned unsigned numeric string plus scalar base plus owned unsigned-8
> result slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOU8_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtou16` unsigned 16-bit result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtou16` promoted under owned numeric string + owned u16 result slot only
>
> Forty-ninth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtou16`, using one tool-owned NUL-terminated unsigned numeric string, scalar
> base `10`, and one tool-owned `u16 *` result slot. Static gate:
> `kstrtou16=0xffffff800856b8a4`, `export-recovery`, direct-BL xrefs `17`, JOPP entry true,
> non-leaf helper calling `kstrtoull`, source contract
> `int __must_check kstrtou16(const char *s, unsigned int base, u16 *res)` from
> `include/linux/kernel.h`, x0/x2 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
> Disasm confirmed unsigned 16-bit range validation via high-bit discard check `lsr #16`/`cbz` and a
> 2-byte success write `strh w8, [x19]` to the x2 result slot.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof kstrtou16` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrtou16-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `kstrtou16("54321", 10, &res) == 0`, result slot storing unsigned `54321` with raw `0xd431`,
> input immutability, 2-byte result-slot canary preservation, and
> `kfree-owned-kstrtou16-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kstrtou16` only under the owned unsigned numeric string plus scalar base plus owned unsigned-16
> result slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOU16_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtos16` signed 16-bit result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtos16` promoted under owned signed numeric string + owned s16 result slot only
>
> Forty-eighth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtos16`, using one tool-owned NUL-terminated signed numeric string, scalar
> base `10`, and one tool-owned `s16 *` result slot. Static gate:
> `kstrtos16=0xffffff800856b924`, `export-recovery`, direct-BL xrefs `1`, JOPP entry true,
> non-leaf helper calling `kstrtoll`, source contract
> `int __must_check kstrtos16(const char *s, unsigned int base, s16 *res)` from
> `include/linux/kernel.h`, x0/x2 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
> Disasm confirmed signed 16-bit range validation via `sxth` and a 2-byte success write
> `strh w8, [x19]` to the x2 result slot.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof kstrtos16` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrtos16-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `kstrtos16("-1234", 10, &res) == 0`, result slot storing signed `-1234` with raw `0xfb2e`,
> input immutability, 2-byte result-slot canary preservation, and
> `kfree-owned-kstrtos16-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kstrtos16` only under the owned signed numeric string plus scalar base plus owned signed-16 result
> slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOS16_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtoint` signed result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtoint` promoted under owned signed numeric string + owned int result slot only
>
> Forty-seventh one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtoint`, using one tool-owned NUL-terminated signed numeric string, scalar
> base `10`, and one tool-owned `int *` result slot. Static gate:
> `kstrtoint=0xffffff800856b824`, `export-recovery`, direct-BL xrefs `167`, JOPP entry true,
> non-leaf helper calling `kstrtoll`, source contract
> `int __must_check kstrtoint(const char *s, unsigned int base, int *res)` from
> `include/linux/kernel.h`, x0/x2 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof kstrtoint` with the C2B verified map. The first proof attempt hit transient REPL
> transport noise before a completed result, candidate selftest stayed `fail=0`, and a bounded retry
> completed cleanly.
>
> Result: `a90-repl-live-call-proof-kstrtoint-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `kstrtoint("-12345", 10, &res) == 0`, result slot storing signed `-12345` with raw
> `0xffffcfc7`, input immutability, result-slot canary preservation, and
> `kfree-owned-kstrtoint-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kstrtoint` only under the owned signed numeric string plus scalar base plus owned signed-int result
> slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOINT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrtouint` owned-string/result-slot contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrtouint` promoted under owned numeric string + owned uint result slot only
>
> Forty-sixth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrtouint`, using one tool-owned NUL-terminated numeric string, scalar base
> `10`, and one tool-owned `unsigned int *` result slot. Static gate:
> `kstrtouint=0xffffff800856b7a4`, `export-recovery`, direct-BL xrefs `217`, JOPP entry true,
> non-leaf helper calling `kstrtoull`, source contract
> `int __must_check kstrtouint(const char *s, unsigned int base, unsigned int *res)` from
> `include/linux/kernel.h`, x0/x2 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof kstrtouint` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrtouint-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek,
> `kstrtouint("123456789", 10, &res) == 0`, result slot storing `123456789`, input immutability,
> result-slot canary preservation, and `kfree-owned-kstrtouint-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kstrtouint` only under the owned numeric string plus scalar base plus owned unsigned-int result
> slot contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRTOUINT_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `simple_strtoull` owned-string integer parser contract

> ### ✅ STATUS (2026-06-30 live pass) — `simple_strtoull` promoted under owned numeric string + owned endp slot only
>
> Forty-fifth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `simple_strtoull`, using one tool-owned NUL-terminated numeric string, one
> tool-owned `char **` end-pointer output slot, and scalar base `16`. Static gate:
> `simple_strtoull=0xffffff80099ba314`, `export-recovery`, direct-BL xrefs `9`, JOPP entry true,
> non-leaf helper calling `_parse_integer_fixup_radix` and `_parse_integer`, source contract
> `extern unsigned long long simple_strtoull(const char *,char **,unsigned int)` from
> `include/linux/kernel.h`, x0/x1 pointer args, and call-safety tier `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, got `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof simple_strtoull` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-simple_strtoull-pass`; checks covered C1 identity, source
> signature, call-safety contract, owned buffer allocation/poke/peek,
> `simple_strtoull("1234abcdZ", &endp, 16) == 0x1234abcd`, `endp` pointing to the owned input
> pointer plus offset `8`, input immutability, end-slot canary preservation, and
> `kfree-owned-simple-strtoull-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `simple_strtoull` only under the owned numeric string plus owned endp output slot plus scalar base
> contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SIMPLE_STRTOULL_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `parse_option_str` owned-string option parser contract

> ### ✅ STATUS (2026-06-30 live pass) — `parse_option_str` promoted under owned comma-option/source strings only
>
> Forty-fourth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `parse_option_str`, using one tool-owned NUL-terminated comma-separated option
> string and one tool-owned NUL-terminated option string. Static gate:
> `parse_option_str=0xffffff80099a9c44`, `disasm-signature+xref+map`, direct-BL xrefs `3`, JOPP
> entry true, calls `__pi_strlen`/`__pi_strncmp`, early x0 byte read allowed only under the owned
> string contract, and source contract `extern bool parse_option_str(const char *str, const char *option)`
> from `include/linux/kernel.h` with x0/x1 as the pointer arguments. Call-safety tier is
> `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, retried through one transient serial `AT` capture
> noise event, got `a90-repl-v2a1-selftest-pass`, then ran `call-proof parse_option_str` with the
> C2B verified map.
>
> Result: `a90-repl-live-call-proof-parse_option_str-pass`; checks covered C1 identity, source
> signature, call-safety contract, owned buffer allocation/poke/peek, exact token hit returning `1`,
> prefix-only token miss returning `0`, missing token returning `0`, list/option immutability, and
> `kfree-owned-parse-option-str-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `parse_option_str` only under the owned comma-separated option string plus owned option string
> contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_PARSE_OPTION_STR_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `bin2hex` owned-buffer hex encoder contract

> ### ✅ STATUS (2026-06-30 live pass) — `bin2hex` promoted under owned destination/source buffers + scalar count only
>
> Forty-third one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `bin2hex`, using one tool-owned destination ASCII hex buffer, one tool-owned
> binary source buffer, and scalar byte count `7`. Static gate: `bin2hex=0xffffff800856aaf4`,
> `export-recovery`, direct-BL xrefs `5`, JOPP entry true, leaf/no-BL, no pre-call x0 deref, and
> source contract `extern char * bin2hex(char *dst, const void *src, size_t count)` from
> `include/linux/kernel.h` with x0/x1 as the only pointer arguments. Call-safety tier is
> `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, candidate `selftest pass=11 warn=1 fail=0`,
> and `a90-repl-v2a1-selftest-pass`, then ran `call-proof bin2hex` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-bin2hex-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek, `bin2hex(dst, a90f00dc0ffee1, 7)`
> returning the owned destination pointer plus offset `14` (redacted), destination bytes encoding to
> `a90f00dc0ffee1`, destination canary preservation, source/canary immutability, and
> `kfree-owned-bin2hex-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `bin2hex` only under the owned destination/source buffer plus scalar count contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_BIN2HEX_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `hex2bin` owned-buffer hex decoder contract

> ### ✅ STATUS (2026-06-30 live pass) — `hex2bin` promoted under owned destination/source buffers + scalar count only
>
> Forty-second one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `hex2bin`, using one tool-owned destination byte buffer, one tool-owned ASCII
> hex source buffer, and scalar byte count `7`. Static gate: `hex2bin=0xffffff800856aa3c`,
> `export-recovery`, direct-BL xrefs `15`, JOPP entry true, leaf/no-BL, no pre-call x0 deref, and
> source contract `extern int __must_check hex2bin(u8 *dst, const char *src, size_t count)` from
> `include/linux/kernel.h` with x0/x1 as the only pointer arguments. Call-safety tier is
> `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, candidate `selftest pass=11 warn=1 fail=0`,
> and `a90-repl-v2a1-selftest-pass`, then ran `call-proof hex2bin` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-hex2bin-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned buffer allocation/poke/peek, `hex2bin(dst, "A90f00dC0ffEe1", 7)`
> returning `0`, destination bytes decoding to `a90f00dc0ffee1`, destination canary preservation,
> source/canary immutability, and `kfree-owned-hex2bin-buffers`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. One final
> health read hit transient serial `AT` capture noise and passed on sequential retry. Function map
> records `hex2bin` only under the owned destination/source buffer plus scalar count contract.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_HEX2BIN_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `hex_to_bin` scalar hex decoder contract

> ### ✅ STATUS (2026-06-30 live pass) — `hex_to_bin` promoted under scalar ASCII character only
>
> Forty-first one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `hex_to_bin`, using only scalar ASCII character inputs and no pointer
> arguments. Static gate: `hex_to_bin=0xffffff800856a9dc`, `export-recovery`, direct-BL xrefs
> `80`, JOPP entry true, leaf/no-BL, no argument memory dereference, and source contract
> `extern int hex_to_bin(char ch)` from `include/linux/kernel.h` with no pointer arguments.
> Call-safety tier is `SAFE-SCALAR`.
>
> Live path: baseline v2321 `version/status/selftest` passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, candidate `selftest pass=11 warn=1 fail=0`,
> and `a90-repl-v2a1-selftest-pass`, then ran `call-proof hex_to_bin` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-hex_to_bin-pass`; checks covered C1 identity, source
> signature, call-safety contract, and a fixed scalar case table: `'0' -> 0`, `'9' -> 9`,
> `'a'/'A' -> 10`, `'f'/'F' -> 15`, and invalid `'g' -> 0xffffffff`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. One final
> health read hit transient serial `AT` capture noise and passed on sequential retry. Function map
> records `hex_to_bin` only under the scalar ASCII character contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_HEX_TO_BIN_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kmemdup_nul` owned bounded-buffer duplicate-plus-NUL contract

> ### ✅ STATUS (2026-06-30 live pass) — `kmemdup_nul` promoted under owned source buffer + bounded len + GFP_KERNEL only
>
> Fortieth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kmemdup_nul`, using one tool-owned initialized source buffer, scalar bounded
> copy length `29`, and scalar `GFP_KERNEL`. Static gate:
> `kmemdup_nul=0xffffff800822a85c`, `export-recovery`, direct-BL xrefs `1`, JOPP entry true,
> non-leaf helper calling `__kmalloc_track_caller` and `__memcpy`, then storing a generated NUL at
> duplicate offset `len`. Source contract:
> `extern char * kmemdup_nul(const char *s, size_t len, gfp_t gfp)`, with x0 as the only pointer arg
> and x1/x2 as scalar args. Call-safety tier is `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 selftest passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, candidate `selftest pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof kmemdup_nul` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kmemdup_nul-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned source allocation/poke/peek, `kmemdup_nul(A90KMEMDUPNUL-RAW-Q0123456789,
> 29, GFP_KERNEL)` returning a distinct owned kernel duplicate pointer, duplicate bytes matching the
> bounded source bytes plus generated trailing NUL, source byte after `len` not copied, source/canary
> immutability, and `kfree-owned-kmemdup-nul-source-and-duplicate`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Two host-side
> health reads hit transient serial `AT` capture noise and passed on sequential retry. Function map
> records `kmemdup_nul` only under the owned initialized source buffer + bounded length +
> `GFP_KERNEL` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KMEMDUP_NUL_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kmemdup` owned raw-buffer duplicate contract

> ### ✅ STATUS (2026-06-30 live pass) — `kmemdup` promoted under owned source buffer + bounded len + GFP_KERNEL only
>
> Thirty-ninth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kmemdup`, using one tool-owned initialized source buffer, scalar bounded copy
> length `29`, and scalar `GFP_KERNEL`. Static gate: `kmemdup=0xffffff800822a7fc`,
> `export-recovery`, direct-BL xrefs `912`, JOPP entry true, non-leaf helper calling
> `__kmalloc_track_caller` and `__memcpy`. Source contract:
> `extern void * kmemdup(const void *src, size_t len, gfp_t gfp)`, with x0 as the only pointer arg
> and x1/x2 as scalar args. Call-safety tier is `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 selftest passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, candidate `selftest pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof kmemdup` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kmemdup-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned source allocation/poke/peek, `kmemdup(A90KMEMDUP-RAW, 29,
> GFP_KERNEL)` returning a distinct owned kernel duplicate pointer, duplicate bytes matching the
> bounded source bytes including embedded NUL and non-ASCII byte, source/canary immutability, and
> `kfree-owned-kmemdup-source-and-duplicate`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kmemdup` only under the owned initialized source buffer + bounded length + `GFP_KERNEL` contract.
> Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KMEMDUP_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrndup` owned bounded-string duplicate contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrndup` promoted under owned source string + bounded len + GFP_KERNEL only
>
> Thirty-eighth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrndup`, using one tool-owned NUL-terminated source string buffer, scalar
> bounded length `16`, and scalar `GFP_KERNEL`. Static gate: `kstrndup=0xffffff800822a77c`,
> `export-recovery`, direct-BL xrefs `26`, JOPP entry true, non-leaf helper calling
> `__pi_strnlen`, `__kmalloc_track_caller`, and `__memcpy`. Source contract:
> `extern char * kstrndup(const char *s, size_t len, gfp_t gfp)`, with x0 as the only pointer arg
> and x1/x2 as scalar args. Call-safety tier is `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 selftest passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, candidate `selftest pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof kstrndup` with the C2B verified map.
>
> Result: `a90-repl-live-call-proof-kstrndup-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned source allocation/poke/peek, `kstrndup("A90KSTRNDUP-HEAD-Q-TAIL",
> 16, GFP_KERNEL)` returning a distinct owned kernel duplicate pointer, duplicate bytes matching
> `A90KSTRNDUP-HEAD\0`, source/canary immutability, and
> `kfree-owned-kstrndup-source-and-duplicate`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kstrndup` only under the owned source string + bounded length + `GFP_KERNEL` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRNDUP_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kstrdup` owned-string duplicate contract

> ### ✅ STATUS (2026-06-30 live pass) — `kstrdup` promoted under owned source string + GFP_KERNEL only
>
> Thirty-seventh one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `kstrdup`, using one tool-owned NUL-terminated source string buffer and scalar
> `GFP_KERNEL`. Static gate: `kstrdup=0xffffff800822a664`, `export-recovery`, direct-BL xrefs `160`,
> JOPP entry true, non-leaf helper calling `__pi_strlen`, `__kmalloc_track_caller`, and `__memcpy`.
> Source contract: `extern char * kstrdup(const char *s, gfp_t gfp) __malloc`, with x0 as the only
> pointer arg and x1 as scalar GFP. Call-safety tier is `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 selftest passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, candidate `selftest pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof kstrdup` with the C2B verified map. A first
> health-check attempt hit host-side serial contention because two serial consumers were started in
> parallel; the bridge stayed reachable and the sequential retry passed.
>
> Result: `a90-repl-live-call-proof-kstrdup-pass`; checks covered C1 identity, source signature,
> call-safety contract, owned source allocation/poke/peek, `kstrdup("A90KSTRDUP-SOURCE-Q-END",
> GFP_KERNEL)` returning a distinct owned kernel duplicate pointer, duplicate bytes matching the
> source including NUL, source/canary immutability, and `kfree-owned-kstrdup-source-and-duplicate`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Function map records
> `kstrdup` only under the owned source string + `GFP_KERNEL` contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSTRDUP_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `sysfs_streq` owned-string equality contract

> ### ✅ STATUS (2026-06-30 live pass) — `sysfs_streq` promoted under two owned sysfs strings only
>
> Thirty-sixth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `sysfs_streq`, using two tool-owned NUL-terminated kernel string buffers and no
> host-supplied numeric pointer. Static gate: `sysfs_streq=0xffffff80099b9c14`, `export-recovery`,
> direct-BL xrefs `68`, JOPP entry true, leaf/no-BL. The disasm reads only the two string arguments
> (`ldrb` from x0/x1), so this proof explicitly allows the expected pre-call argument dereference for
> a string helper after the owned-pointer contract is enforced. Source contract:
> `extern bool sysfs_streq(const char *s1, const char *s2)`, with x0/x1 as pointer args. Call-safety
> tier is `SAFE-WITH-VALID-PTR`.
>
> Live path: baseline v2321 selftest passed, flashed the existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` through
> `native_init_flash.py`, confirmed readback SHA, candidate `selftest pass=11 warn=1 fail=0`, and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof sysfs_streq` with the C2B verified map.
> Result: `a90-repl-live-call-proof-sysfs_streq-pass`; checks covered C1 identity, source
> pointer contract, call-safety contract, distinct owned string allocations, newline sysfs equality
> (`"A90SYSFS-VALUE\n"` vs `"A90SYSFS-VALUE"` -> `1`), strict equality (`1`), mismatch
> (`"A90SYSFS-OTHER"` -> `0`), string/canary immutability, and `kfree-owned-sysfs-streq-strings`.
>
> Candidate selftest after proof stayed `fail=0`. Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. One final selftest
> read hit known serial framing noise (`A90P1 END` missing) and passed immediately on retry.
> Function map records `sysfs_streq` only under the two-owned-string contract. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_SYSFS_STREQ_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `match_string` owned string-array contract

> ### ✅ STATUS (2026-06-30 live pass) — `match_string` promoted under owned const-char-pointer array only
>
> Thirty-fifth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `match_string`, using one tool-owned kmalloc layout containing a bounded
> `const char *` array of three owned NUL-terminated strings (`A90MATCH-ALPHA`,
> `A90MATCH-BRAVO`, `A90MATCH-CHARLIE`), a NULL sentinel after the bounded array, and an owned
> search string. Static gate: `match_string=0xffffff80099b9c9c`, `export-recovery`, direct-BL
> xrefs `5`, JOPP entry, calls `__pi_strcmp`, RET in scan at offset `0x78`, and disasm shows
> `w23 = 0xffffffea` as the `-EINVAL` miss/zero-count return. Source contract:
> `int match_string(const char * const *array, size_t n, const char *string)`, with x0 as the
> string-pointer array, x1 as scalar count, and x2 as the search string pointer. The call-safety
> seed is `SAFE-WITH-VALID-PTR`; required valid pointer args are x0 `string-pointer-array` and
> x2 `search-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof match_string` with the C2B verified map.
> Result: `a90-repl-live-call-proof-match_string-pass`; checks covered C1 identity, source
> pointer contract, call-safety contract, owned layout allocation, pointer-array/string
> poke-peek, hit return index `1` for `A90MATCH-BRAVO`, hit layout immutability, missing search
> rewrite to `A90MATCH-MISSING`, missing return `0xffffffea`, zero-count return `0xffffffea`,
> final layout/canary immutability, and `kfree-owned-match-string-layout`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the
> checked helper with readback SHA `ca978551...`; final resident `version`/`selftest` confirmed
> v2321 and `pass=11 warn=1 fail=0`. Function map records `match_string` only under the owned
> pointer-array plus owned-search-string and bounded-count-inside-array contract. This does not
> authorize arbitrary pointer arrays, user pointers, unterminated strings, stale array entries,
> out-of-range counts, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strnstr` owned-substring bounded-length contract

> ### ✅ STATUS (2026-06-30 live pass) — `strnstr` promoted under owned haystack/needle plus bounded length only
>
> Thirty-fourth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strnstr`, using two tool-owned NUL-terminated kernel string buffers:
> haystack `A90STRNSTR-HEAD-NEEDLE-TAIL`, present needle `NEEDLE`, missing needle `ABSENT`,
> hit length `27`, and boundary-miss length `21` to prove the length bound excludes one needle
> byte. Static gate: `strnstr=0xffffff80099b9f44`, `export-recovery`, direct-BL xrefs `268`,
> JOPP entry, calls `__pi_strlen` and `__pi_memcmp`, RET in scan at offset `0x74`.
> Source contract: `extern char * strnstr(const char *, const char *, size_t)`, with x0 as the
> haystack string pointer, x1 as the needle string pointer, and x2 as the scalar bounded length.
> The call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer args are x0
> `haystack-string-buffer` and x1 `needle-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strnstr` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strnstr-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned haystack/needle allocations, buffer poke/peek,
> present-needle return at offset `16`, hit-case string immutability, boundary miss return `0x0`
> at length `21`, boundary-miss string immutability, missing-needle rewrite to `ABSENT`, missing
> return `0x0`, missing-case string immutability, and `kfree-owned-strnstr-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the
> checked helper with readback SHA `ca978551...`; final resident `version`/`selftest` confirmed
> v2321 and `pass=11 warn=1 fail=0`. Function map records `strnstr` only under the owned
> haystack/needle NUL-string plus bounded-length-inside-haystack contract. This does not authorize
> arbitrary pointers, user pointers, unterminated strings, out-of-range lengths, broader substring
> cases, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strncasecmp` owned-string bounded casefold compare contract

> ### ✅ STATUS (2026-06-30 live pass) — `strncasecmp` promoted under two owned NUL strings plus bounded count only
>
> Thirty-third one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strncasecmp`, using two tool-owned NUL-terminated kernel string buffers
> with casefold-equal prefixes `A90STRNCASECMP-PREFIX` and `a90strncasecmp-prefix`, scalar
> count `21`, and post-count bytes `0x5a` vs `0x40` to prove the boundary. Static gate:
> `strncasecmp=0xffffff80099b960c`, `export-recovery`, direct-BL xrefs `88`, JOPP entry,
> leaf/no-BL, RETs in scan, x0/x1 byte-load/casefold compare loop, and x2 count-zero early
> return. Source contract: `extern int strncasecmp(const char *s1, const char *s2, size_t n)`,
> with x0/x1 as string pointer args and x2 as scalar bounded count. The call-safety seed is
> `SAFE-WITH-VALID-PTR`; required valid pointer args are x0 `left-string-buffer` and x1
> `right-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strncasecmp` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strncasecmp-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned left/right string allocations, bounded
> casefold-equal return `0x0`, post-count difference ignored, mismatch offset `15`, folded-left
> byte `0x70`, right mismatch byte `0x40`, positive mismatch return `0x30`, string immutability
> after both calls, and `kfree-owned-strncasecmp-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the
> checked helper with readback SHA `ca978551...`; final resident `version/status` confirmed v2321.
> The first final selftest capture omitted the summary line despite rc `0`, so it was repeated; the
> repeated final slow-mode `selftest` confirmed `pass=11 warn=1 fail=0`. Function map records
> `strncasecmp` only under the two-owned-NUL-terminated-string plus bounded-count-inside-both-buffers
> contract. This does not authorize arbitrary pointers, user pointers, unterminated strings,
> out-of-range counts, locale assumptions beyond the kernel helper behavior observed here, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strcasecmp` owned-string casefold compare contract

> ### ✅ STATUS (2026-06-30 live pass) — `strcasecmp` promoted under two owned NUL strings only
>
> Thirty-second one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strcasecmp`, using two tool-owned NUL-terminated kernel string buffers
> containing `A90STRCASECMP-PROOF-ZZ` and `a90strcasecmp-proof-zz`, then rewriting one
> right-string byte for a first-difference positive-sign case. Static gate:
> `strcasecmp=0xffffff80099b9684`, `export-recovery`, direct-BL xrefs `112`, JOPP entry,
> leaf/no-BL, RET in scan, and byte-load/casefold compare loop. Source contract:
> `extern int strcasecmp(const char *s1, const char *s2)`, with x0/x1 as string pointer
> args. The call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer args are x0
> `left-string-buffer` and x1 `right-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strcasecmp` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strcasecmp-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned left/right string allocations, casefold-equal
> return `0x0`, mismatch offset `20`, folded-left byte `0x7a`, right mismatch byte `0x40`,
> positive mismatch return `0x3a`, string immutability after both calls, and
> `kfree-owned-strcasecmp-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the
> checked helper with readback SHA `ca978551...`; final resident `version/status` confirmed v2321
> and final slow-mode `selftest` confirmed `pass=11 warn=1 fail=0`. Function map records
> `strcasecmp` only under the two-owned-NUL-terminated-string contract. This does not authorize
> arbitrary pointers, user pointers, unterminated strings, locale assumptions beyond the kernel
> helper behavior observed here, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strlcat` owned-buffer size-bounded append contract

> ### ✅ STATUS (2026-06-30 live pass) — `strlcat` promoted under owned dst/src string plus bounded size contract only
>
> Thirty-first one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strlcat`, using one tool-owned mutable destination string buffer first
> containing `A90STRLCAT-DST`, plus one tool-owned NUL-terminated source string buffer containing
> `-SRC-Q-END`, and scalar size `21`. Static gate: `strlcat=0xffffff80099b98f4`,
> `export-recovery`, direct-BL xrefs `522`, JOPP entry, non-leaf helper with three bounded calls
> to `__pi_strlen`, `__pi_strlen`, and `__memcpy`, RET in scan. Disasm also shows a fortified
> `dlen >= size` trap path, so the live input contract pins `size > strlen(dst)` and size inside
> the owned destination allocation. Source contract:
> `extern size_t strlcat(char *, const char *, __kernel_size_t)`, with x0 as the destination
> string buffer pointer, x1 as the source string pointer, and x2 as the bounded size. The
> call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer args are x0
> `destination-buffer` and x1 `source-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strlcat` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strlcat-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned destination/source allocations, destination
> prefix plus source poke/peek, scalar return contract `0x18` (`strlen(dst)+strlen(src)`),
> size-bounded truncated append result `A90STRLCAT-DST-SRC-Q` including NUL, post-NUL tail
> preservation, destination canary preservation, source immutability, and
> `kfree-owned-strlcat-buffers`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final resident `version/status` confirmed v2321 and final
> slow-mode `selftest` confirmed `pass=11 warn=1 fail=0`. One candidate selftest attempt and one
> final selftest attempt hit serial echo noise before END marker; `version` re-synchronized the
> bridge both times, and the repeated selftests passed. Function map records `strlcat` only under
> this owned mutable destination plus owned NUL-terminated source plus bounded size contract. This
> does not authorize arbitrary pointers, user pointers, undersized destinations, `size <= strlen(dst)`,
> unterminated strings, overlapping strings, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strncat` owned-buffer bounded append contract

> ### ✅ STATUS (2026-06-30 live pass) — `strncat` promoted under owned dst/src string plus bounded count contract only
>
> Thirtieth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strncat`, using one tool-owned mutable destination string buffer first
> containing `A90STRNCAT-DST`, plus one tool-owned NUL-terminated source string buffer containing
> `-SRC-Q-END`, and scalar count `6`. Static gate: `strncat=0xffffff80099b98b4`,
> `export-recovery`, direct-BL xrefs `193`, JOPP entry, leaf/no-BL, RETs in scan. Source
> contract: `extern char * strncat(char *, const char *, __kernel_size_t)`, with x0 as the
> destination string buffer pointer, x1 as the source string pointer, and x2 as the bounded count.
> The call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer args are x0
> `destination-buffer` and x1 `source-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strncat` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strncat-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned destination/source allocations, destination
> prefix plus source poke/peek, destination-pointer return contract, bounded append result
> `A90STRNCAT-DST-SRC-Q` including NUL, post-NUL tail preservation, destination canary
> preservation, source immutability, and `kfree-owned-strncat-buffers`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final resident `version/status` confirmed v2321 and final
> `selftest` confirmed `pass=11 warn=1 fail=0`. Function map records `strncat` only under this
> owned mutable destination plus owned NUL-terminated source plus bounded count contract. This does
> not authorize arbitrary pointers, user pointers, undersized destinations, unterminated strings,
> overlapping strings, unbounded counts, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strcat` owned-buffer append contract

> ### ✅ STATUS (2026-06-30 live pass) — `strcat` promoted under owned dst/src string contract only
>
> Twenty-ninth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strcat`, using one tool-owned mutable destination string buffer first
> containing `A90STRCAT-DST`, plus one tool-owned NUL-terminated source string buffer containing
> `-SRC-Q-END`. Static gate: `strcat=0xffffff80099b988c`, `export-recovery`, direct-BL xrefs
> `77`, JOPP entry, leaf/no-BL, RETs in scan. Source contract:
> `extern char * strcat(char *, const char *)`, with x0 as the destination string buffer pointer
> and x1 as the source string pointer. The call-safety seed is `SAFE-WITH-VALID-PTR`; required
> valid pointer args are x0 `destination-buffer` and x1 `source-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strcat` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strcat-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned destination/source allocations, destination
> prefix plus source poke/peek, destination-pointer return contract, append result
> `A90STRCAT-DST-SRC-Q-END` including NUL, post-NUL tail preservation, destination canary
> preservation, source immutability, and `kfree-owned-strcat-buffers`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final resident `version/status` confirmed v2321 and final
> `selftest` confirmed `pass=11 warn=1 fail=0`. One candidate selftest attempt using slow serial input
> hit echo noise before END marker; normal `version` re-synchronized the bridge, and native selftest
> passed before REPL selftest and proof. Function map records `strcat` only under this owned mutable
> destination plus owned NUL-terminated source contract. This does not authorize arbitrary pointers,
> user pointers, undersized destinations, unterminated strings, overlapping strings, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strcpy` owned-buffer copy contract

> ### ✅ STATUS (2026-06-30 live pass) — `strcpy` promoted under owned dst/src string contract only
>
> Twenty-eighth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strcpy`, using one tool-owned destination buffer and one tool-owned
> NUL-terminated source string buffer containing `A90STRCPY-SRC-Q-END`. Static gate:
> `strcpy=0xffffff80099b96d4`, `export-recovery`, direct-BL xrefs `589`, JOPP entry,
> leaf/no-BL, RETs in scan. Source contract:
> `extern char * strcpy(char *,const char *)`, with x0 as the destination buffer pointer
> and x1 as the source string pointer. The call-safety seed is `SAFE-WITH-VALID-PTR`;
> required valid pointer args are x0 `destination-buffer` and x1 `source-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strcpy` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strcpy-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned destination/source allocations, destination
> prefill plus source poke/peek, destination-pointer return contract, source copy including NUL,
> post-NUL tail preservation, destination canary preservation, source immutability, and
> `kfree-owned-strcpy-buffers`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final resident `version` confirmed v2321 and final
> `selftest` confirmed `pass=11 warn=1 fail=0`. The first final selftest read after rollback returned
> only a partial tail, and the next `version` hit serial echo noise; `--input-mode slow` re-synchronized
> the console, then `version` and final selftest both passed. Function map records `strcpy` only under
> this owned destination plus owned NUL-terminated source contract. This does not authorize arbitrary
> pointers, user pointers, undersized destinations, unterminated sources, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strspn` owned-string accept-set span contract

> ### ✅ STATUS (2026-06-30 live pass) — `strspn` promoted under owned NUL-string accept-set contract only
>
> Twenty-seventh one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strspn`, using one tool-owned NUL-terminated haystack string
> (`A90STRSPN-HEAD-Q-TAIL`) and one tool-owned NUL-terminated accept-set string first containing
> only the initial prefix character set (`A90STRSPNHED-`), then rewriting the accept-set buffer to
> cover the whole haystack (`A90STRSPNHEDQIL-`). Static gate:
> `strspn=0xffffff80099b9a6c`, `export-recovery`, direct-BL xrefs `2`, JOPP entry,
> leaf/no-BL, RETs in scan. Source contract:
> `extern __kernel_size_t strspn(const char *,const char *)`, with x0 as the haystack
> string pointer and x1 as the accept-set string pointer. The call-safety seed is
> `SAFE-WITH-VALID-PTR`; required valid pointer args are x0 `haystack-string-buffer`
> and x1 `accept-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strspn` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strspn-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned haystack/accept allocations, prefix accept-set
> poke/peek, prefix return `15`, prefix immutability, full accept-set rewrite, full-case return
> haystack length `21`, full-case immutability, and `kfree-owned-strspn-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final `selftest` confirmed v2321 health with
> `pass=11 warn=1 fail=0`. An initial parallel candidate health/REPL-selftest attempt caused serial
> echo noise before END marker; immediate `version` re-sync and sequential retries passed. The first
> final selftest after rollback also hit serial echo noise, then `version` re-sync and selftest passed.
> Function map records `strspn` only under this owned NUL-terminated haystack plus owned
> NUL-terminated accept-set contract. This does not authorize arbitrary pointers, user pointers,
> unterminated strings, mutable side effects, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strcspn` owned-string reject-set contract

> ### ✅ STATUS (2026-06-30 live pass) — `strcspn` promoted under owned NUL-string reject-set contract only
>
> Twenty-sixth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strcspn`, using one tool-owned NUL-terminated haystack string
> (`A90STRCSPN-HEAD-Q-TAIL`) and one tool-owned NUL-terminated reject-set string (`QZ`),
> then rewriting the reject-set buffer to a missing set (`xy`). Static gate:
> `strcspn=0xffffff80099b9ac4`, `export-recovery`, direct-BL xrefs `8`, JOPP entry,
> leaf/no-BL, RETs in scan. Source contract:
> `extern __kernel_size_t strcspn(const char *,const char *)`, with x0 as the haystack
> string pointer and x1 as the reject-set string pointer. The call-safety seed is
> `SAFE-WITH-VALID-PTR`; required valid pointer args are x0 `haystack-string-buffer`
> and x1 `reject-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strcspn` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strcspn-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned haystack/reject allocations, hit-case poke/peek,
> hit-case return `16`, hit-case immutability, missing reject-set rewrite, missing-case return
> haystack length `22`, missing-case immutability, and `kfree-owned-strcspn-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final `selftest` confirmed v2321 health with
> `pass=11 warn=1 fail=0`. The first candidate standalone selftest command hit serial input noise
> (`ATATAT`) before END marker, then immediate `version` re-sync and retry passed. Function map records
> `strcspn` only under this owned NUL-terminated haystack plus owned NUL-terminated reject-set contract.
> This does not authorize arbitrary pointers, user pointers, unterminated strings, mutable side effects,
> or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `memchr_inv` owned-buffer inverse-search contract

> ### ✅ STATUS (2026-06-30 live pass) — `memchr_inv` promoted under owned initialized buffer plus bounded size contract only
>
> Twenty-fifth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `memchr_inv`, using one tool-owned initialized kernel buffer, scalar fill byte
> `0x5a`, bounded `size=32`, one non-fill byte `0x33` at offset `13`, and a non-fill post-size
> canary. Static gate: `memchr_inv=0xffffff80099b9fc4`, `export-recovery`, direct-BL xrefs `31`,
> JOPP entry, leaf/no-BL, RETs in scan. Source contract:
> `void * memchr_inv(const void *s, int c, size_t n)`, with x0 as the buffer pointer and x1/x2 as
> scalar fill-byte/size args. The call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer
> arg is x0 `buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof memchr_inv` with the C2B verified map.
> Result: `a90-repl-live-call-proof-memchr_inv-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, owned buffer allocation, hit-case poke/peek, return of the owned
> buffer pointer at offset `13`, hit-case immutability, all-fill rewrite with non-fill canary outside
> the bounded size, all-fill return `0x0`, all-fill immutability, and
> `kfree-owned-memchr-inv-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final `selftest` confirmed v2321 health with
> `pass=11 warn=1 fail=0`. The first candidate standalone selftest command hit serial input noise
> (`cmdv1 ststATAT`) before END marker, then immediate `version` re-sync and retry passed. Function
> map records `memchr_inv` only under this owned initialized kernel buffer plus scalar fill-byte and
> bounded-size contract. This does not authorize arbitrary pointers, user pointers, uninitialized
> buffers, unbounded sizes, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strnchr` owned-string bounded-search contract

> ### ✅ STATUS (2026-06-30 live pass) — `strnchr` promoted under owned NUL-string plus bounded count contract only
>
> Twenty-fourth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strnchr`, using one tool-owned NUL-terminated kernel string
> (`A90STRNCHR-HEAD-Q-TAIL-Q`), scalar `count=24`, and scalar search byte `Q`. Static gate:
> `strnchr=0xffffff80099b99a4`, `export-recovery`, direct-BL xrefs `45`, JOPP entry,
> leaf/no-BL, RET in scan. Source contract: `extern char * strnchr(const char *, size_t, int)`,
> with x0 as the string pointer and x1/x2 as scalar count/search-byte args. The call-safety seed is
> `SAFE-WITH-VALID-PTR`; required valid pointer arg is x0 `string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strnchr` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strnchr-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, owned string allocation, hit-case poke/peek, return of the owned
> string pointer at offset `16`, hit-case immutability, boundary-miss count `16` returning `0x0`,
> boundary-miss immutability, and `kfree-owned-strnchr-string-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; the first final selftest command hit serial input noise
> (`cmdv1tATATAT`) and did not produce an END marker, then immediate `version` re-sync and selftest
> confirmed v2321 health with `pass=11 warn=1 fail=0`. Function map records `strnchr` only under this
> owned NUL-terminated kernel string plus scalar bounded count/search-byte contract. This does not
> authorize arbitrary pointers, user pointers, unterminated strings, unbounded counts, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strpbrk` owned-string accept-set contract

> ### ✅ STATUS (2026-06-30 live pass) — `strpbrk` promoted under owned NUL-string accept-set contract only
>
> Twenty-third one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strpbrk`, using one tool-owned NUL-terminated haystack string
> (`A90STRPBRK-HEAD-Q-TAIL-Z`) and one tool-owned NUL-terminated accept-set string (`QZ`),
> then rewriting the accept-set buffer to a missing set (`xy`). Static gate:
> `strpbrk=0xffffff80099b9b34`, `export-recovery`, direct-BL xrefs `40`, JOPP entry,
> leaf/no-BL, RET in scan. Source contract: `extern char * strpbrk(const char *,const char *)`,
> with x0 as the haystack string pointer and x1 as the accept-set string pointer. The
> call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer args are x0
> `haystack-string-buffer` and x1 `accept-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strpbrk` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strpbrk-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, distinct owned haystack/accept allocations, hit-case poke/peek,
> returned haystack pointer at offset `16`, hit-case immutability, missing accept-set rewrite,
> missing-case return `0x0`, missing-case immutability, and `kfree-owned-strpbrk-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final `selftest` confirmed v2321 health with
> `pass=11 warn=1 fail=0`. Function map records `strpbrk` only under this owned
> NUL-terminated haystack plus owned NUL-terminated accept-set contract. This does not authorize
> arbitrary pointers, user pointers, unterminated strings, mutable side effects, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strreplace` owned-mutable-string contract

> ### ✅ STATUS (2026-06-30 live pass) — `strreplace` promoted under owned mutable NUL-string contract only
>
> Twenty-second one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strreplace`, using one tool-owned mutable NUL-terminated kernel string
> (`A90STRREPLACE-Q-Q-END`) plus scalar old/new bytes. Static gate:
> `strreplace=0xffffff80099ba12c`, `export-recovery`, direct-BL xrefs `15`, JOPP entry,
> leaf/no-BL, first RET in scan at offset `0x8`. Source contract:
> `char * strreplace(char *s, char old, char new)`, with x0 as the mutable string pointer and
> x1/x2 as scalar bytes. The call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer
> arg is x0 `mutable-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strreplace` with the C2B verified map.
> Result: `a90-repl-live-call-proof-strreplace-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, owned mutable string allocation, hit-case poke/peek, return of the
> owned NUL terminator pointer at offset `21`, bounded `Q -> Z` replacement, missing-byte rewrite,
> missing-byte return at the same NUL offset, missing-case immutability, and
> `kfree-owned-strreplace-string-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final `selftest` confirmed v2321 health with
> `pass=11 warn=1 fail=0`. Function map records `strreplace` only under this owned mutable
> NUL-terminated kernel string plus scalar old/new byte contract. This does not authorize arbitrary
> pointers, user pointers, unterminated strings, read-only strings, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strim` owned-mutable-string contract

> ### ✅ STATUS (2026-06-30 live pass) — `strim` promoted under owned mutable NUL-string contract only
>
> Twenty-first one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strim`, using one tool-owned mutable NUL-terminated kernel string first with
> leading/trailing ASCII spaces (`   A90STRIM-BODY   `) and then with no leading/trailing spaces
> (`A90STRIM-CLEAN`). Static gate: `strim=0xffffff80099b99f4`, `export-recovery`,
> direct-BL xrefs `59`, JOPP entry, calls `__pi_strlen`, RET in scan at offset `0x6c`.
> Source contract: `extern char * strim(char *)`, with x0 as the mutable string pointer. The
> call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer arg is x0
> `mutable-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0`.
> One REPL selftest attempt hit serial END-marker noise before any proof call; immediate retry passed
> as `a90-repl-v2a1-selftest-pass`. Then `call-proof strim` ran with the C2B verified map. Result:
> `a90-repl-live-call-proof-strim-pass`; checks covered C1 identity, source pointer contract,
> call-safety contract, owned mutable string allocation, trim-case poke/peek, trim return at offset
> `3`, bounded first-trailing-space NUL mutation at offset `16`, clean-string rewrite, clean return at
> offset `0`, clean-string immutability, and `kfree-owned-strim-string-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final slow-mode `selftest` confirmed v2321 health with
> `pass=11 warn=1 fail=0`. Function map records `strim` only under this owned mutable
> NUL-terminated kernel string contract. This does not authorize arbitrary pointers, user pointers,
> unterminated strings, non-ASCII whitespace assumptions beyond this proof, read-only strings, or mass
> calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `skip_spaces` owned-string contract

> ### ✅ STATUS (2026-06-30 live pass) — `skip_spaces` promoted under owned NUL-string contract only
>
> Twentieth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `skip_spaces`, using one tool-owned NUL-terminated kernel string first with
> leading ASCII spaces (`   A90SKIP-SPACES`) and then with no leading spaces (`A90SKIP-NO-LEADING`).
> Static gate: `skip_spaces=0xffffff80099b99d4`, `export-recovery`, direct-BL xrefs `52`,
> JOPP entry, first RET in scan at offset `0x18`. Source contract:
> `extern char * __must_check skip_spaces(const char *)`, with x0 as the string pointer. The
> call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer arg is x0
> `string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof skip_spaces` with the C2B verified map.
> Result: `a90-repl-live-call-proof-skip_spaces-pass`; checks covered C1 identity, source pointer
> contract, call-safety contract, owned string allocation, leading-string poke/peek, leading return
> at offset `3`, leading string immutability, no-leading rewrite, no-leading return at offset `0`,
> no-leading string immutability, and `kfree-owned-skip-spaces-string-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final `selftest` confirmed v2321 health with
> `pass=11 warn=1 fail=0`. Function map records `skip_spaces` only under this owned
> NUL-terminated kernel string contract. This does not authorize arbitrary pointers, user pointers,
> unterminated strings, non-ASCII whitespace assumptions beyond this proof, or mass calls.

## ✅ DONE — REPL post-epic one-target live-call proof — `strstr` owned-substring contract

> ### ✅ STATUS (2026-06-30 live pass) — `strstr` promoted under owned haystack/needle string contract only
>
> Nineteenth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py`
> `call-proof` with `strstr`, using two tool-owned NUL-terminated kernel strings:
> haystack `A90STRSTR-HEAD-NEEDLE-TAIL`, present needle `NEEDLE`, and missing needle `ABSENT`.
> Static gate: `strstr=0xffffff80099b9ebc`, `export-recovery`, direct-BL xrefs `50`,
> JOPP entry, calls `__pi_strlen` and `__pi_memcmp`, RET in scan at offset `0x7c`.
> Source contract: `extern char * strstr(const char *, const char *)`, with x0 as the
> haystack string pointer and x1 as the needle string pointer. The call-safety seed is
> `SAFE-WITH-VALID-PTR`; required valid pointer args are x0 `haystack-string-buffer` and
> x1 `needle-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strstr` with the C2B verified map. Result:
> `a90-repl-live-call-proof-strstr-pass`; checks covered C1 identity, source pointer contract,
> call-safety contract, distinct owned haystack/needle allocations, buffer poke/peek, present-needle
> return at offset `15`, hit-case string immutability, missing-needle rewrite, missing return `0x0`,
> missing-case string immutability, and `kfree-owned-strstr-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final slow-mode `version`/`selftest` confirmed v2321 and
> `pass=11 warn=1 fail=0`. Function map records `strstr` only under this owned haystack/needle
> NUL-string contract. This does not authorize arbitrary pointers, user pointers, unterminated strings,
> or broader substring cases without their own proof.

## ✅ DONE — REPL post-epic one-target live-call proof — `memmove` owned-overlap-buffer contract

> ### ✅ STATUS (2026-06-30 live pass) — `memmove` promoted under same-owned-buffer overlap contract only
>
> Eighteenth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py
> call-proof` with `memmove`, using one tool-owned kernel buffer and deliberately overlapping ranges:
> source offset `0`, destination offset `5`, bounded size `29`, and proof bytes
> `A90MEMMOVE-OVERLAP-0123456789`. Static gate: `memmove=0xffffff80099a8800`,
> `leaf-map-disasm+xref`, direct-BL xrefs `165`, leaf/no-BL, RET in scan at offset `0xc4`.
> Source contract: `extern void * memmove(void *,const void *,__kernel_size_t)`, with x0 as the
> destination pointer, x1 as the source pointer, and x2 as a scalar bounded size. The call-safety
> seed is `SAFE-WITH-VALID-PTR`; required valid pointer args are x0 `destination-buffer` and
> x1 `source-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed clean native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof memmove` with the C2B verified map. Result:
> `a90-repl-live-call-proof-memmove-pass`; checks covered C1 identity, source pointer contract,
> one owned allocation, `dst=src+5` overlap inside the allocation, buffer poke/peek, returned
> destination pointer, final buffer matching overlap-safe snapshot-copy semantics, post-move canary
> preservation, and `kfree-owned-memmove-overlap-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final `version`/`selftest` confirmed v2321 and
> `pass=11 warn=1 fail=0`. Function map records `memmove` only under this same-owned-buffer,
> dst-after-src overlap plus bounded-size contract. This does not authorize arbitrary pointers,
> unbounded sizes, user pointers, or broader overlap shapes without their own proof.

## ✅ DONE — REPL post-epic one-target live-call proof — `memcpy` owned-buffer copy contract

> ### ✅ STATUS (2026-06-30 live pass) — `memcpy` promoted under distinct owned dst/src buffers plus bounded size only
>
> Seventeenth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py
> call-proof` with `memcpy`, using two distinct tool-owned kernel buffers, source bytes
> `A90MEMCPY-SRC-0123456789ABCDEF`, bounded size `30`, initialized destination bytes `0x11`,
> and independent post-size canaries. Static gate: `memcpy=0xffffff80099a8680`,
> `leaf-map-disasm+xref`, direct-BL xrefs `6227`, leaf/no-BL, RET in scan at offset `0x150`.
> Source contract: `extern void * memcpy(void *,const void *,__kernel_size_t)`, with x0 as the
> destination pointer, x1 as the source pointer, and x2 as a scalar bounded size. The call-safety
> seed is `SAFE-WITH-VALID-PTR`; required valid pointer args are x0 `destination-buffer` and
> x1 `source-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof memcpy` with the C2B verified map. Result:
> `a90-repl-live-call-proof-memcpy-pass`; checks covered C1 identity, source pointer contract,
> owned dst/src allocation, non-overlapping allocation ranges, buffer poke/peek, returned
> destination pointer, destination prefix matching source, destination post-size canary preservation,
> source-buffer immutability, and `kfree-owned-memcpy-buffers`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final `version`/`selftest` confirmed v2321 and
> `pass=11 warn=1 fail=0`. Function map records `memcpy` only under the distinct-owned-buffer plus
> bounded-size contract. This does not authorize arbitrary pointers, overlapping ranges, unbounded
> sizes, user pointers, or `memmove`.

## ✅ DONE — REPL post-epic one-target live-call proof — `strncmp` owned-string bounded-compare contract

> ### ✅ STATUS (2026-06-30 live pass) — `strncmp` promoted under two owned NUL strings plus bounded count only
>
> Sixteenth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py
> call-proof` with `strncmp`, using two tool-owned NUL-terminated kernel string buffers sharing the
> prefix `A90STRNCMP-PREFIX`, bounded count `17`, and deliberately different post-count bytes
> (`0x5a` vs `0x40`). Static gate: `strncmp=0xffffff80099a8d44`, `leaf-map-disasm+xref`,
> direct-BL xrefs `590`, leaf/no-BL, RET in scan at offset `0x110`. Source contract:
> `extern int strncmp(const char *,const char *,__kernel_size_t)`, with x0/x1 as string pointers and
> x2 as a scalar bounded count. The call-safety seed is `SAFE-WITH-VALID-PTR`; required valid pointer
> args are x0 `left-string-buffer` and x1 `right-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strncmp` with the C2B verified map. Result:
> `a90-repl-live-call-proof-strncmp-pass`; checks covered C1 identity, source pointer contract,
> owned string allocation, string poke/peek, bounded equal return `0x0` while the first differing
> bytes were immediately after count, string immutability, count-internal mismatch positive return
> `0x98`, second immutability check, and `kfree-owned-strncmp-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `strncmp` only under the two-owned-NUL-string plus scalar bounded-count contract. This does
> not authorize arbitrary pointers, unterminated strings, unbounded counts, user pointers, or other
> string helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `memchr` owned-buffer search contract

> ### ✅ STATUS (2026-06-30 live pass) — `memchr` promoted under owned initialized buffer only
>
> Fifteenth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py
> call-proof` with `memchr`, using one tool-owned initialized kernel buffer containing
> `A90MEMCHR-HIT-Q-END-012345`, scalar search byte `0x51` (`Q`), bounded size `26`, and a
> post-size canary filled with `0x40` (`@`). Static gate: `memchr=0xffffff80099a8488`,
> `leaf-map-disasm+xref`, direct-BL xrefs `25`, leaf/no-BL, RET in scan. Source contract:
> `extern void * memchr(const void *,int,__kernel_size_t)`, with x0 as the buffer pointer, x1 as a
> scalar byte, and x2 as a scalar bounded size. The call-safety seed is `SAFE-WITH-VALID-PTR`;
> required valid pointer arg is x0 `buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof memchr` with the C2B verified map. Result:
> `a90-repl-live-call-proof-memchr-pass`; checks covered C1 identity, source pointer contract,
> owned buffer allocation, buffer poke/peek, hit return at expected first-occurrence offset `14`,
> buffer immutability, missing-byte return `0x0` even though the post-size canary contained `@`,
> second immutability check, and `kfree-owned-memchr-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `memchr` only under the owned initialized buffer plus scalar-search-byte and bounded-size
> contract. This does not authorize arbitrary pointers, unbounded sizes, user pointers, or other
> memory helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `strchrnul` owned-string search contract

> ### ✅ STATUS (2026-06-30 live pass) — `strchrnul` promoted under owned NUL-terminated string only
>
> Fourteenth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py
> call-proof` with `strchrnul`, using one tool-owned NUL-terminated kernel string buffer containing
> `A90STRCHRNUL-Q-B-Q-Z\0`, scalar search byte `0x51` (`Q`), and scalar missing-byte probe `0x40`
> (`@`). Static gate: `strchrnul=0xffffff80099b9984`, `export-recovery`, direct-BL xrefs `7`,
> JOPP entry, leaf/no-BL, RET in scan. Source contract: `extern char * strchrnul(const char *,int)`,
> with x0 as the string pointer and x1 as a scalar byte. The call-safety seed is
> `SAFE-WITH-VALID-PTR`; required valid pointer arg is x0 `string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strchrnul` with the C2B verified map. Result:
> `a90-repl-live-call-proof-strchrnul-pass`; checks covered C1 identity, source pointer contract,
> owned string allocation, string poke/peek, hit return at expected first-occurrence offset `13`,
> string immutability, missing-byte return at the NUL-terminator offset `20`, second immutability
> check, and `kfree-owned-strchrnul-string-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `strchrnul` only under the owned NUL-terminated string plus scalar-search-byte contract.
> This does not authorize arbitrary pointers, unterminated strings, user pointers, or other string
> helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `strchr` owned-string search contract

> ### ✅ STATUS (2026-06-30 live pass) — `strchr` promoted under owned NUL-terminated string only
>
> Thirteenth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py
> call-proof` with `strchr`, using one tool-owned NUL-terminated kernel string buffer containing
> `A90STRCHR-Q-B-Q-Z\0`, scalar search byte `0x51` (`Q`), and scalar missing-byte probe `0x40`
> (`@`). Static gate: `strchr=0xffffff80099a8b48`, `leaf-map-disasm+xref`, direct-BL xrefs `127`,
> leaf/no-BL, RET in scan. Source contract: `extern char * strchr(const char *,int)`, with x0 as
> the string pointer and x1 as a scalar byte. The call-safety seed remains `SAFE-WITH-VALID-PTR`;
> required valid pointer arg is x0 `string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strchr` with the C2B verified map. Result:
> `a90-repl-live-call-proof-strchr-pass`; checks covered C1 identity, source pointer contract, owned
> string allocation, string poke/peek, hit return at expected first-occurrence offset `10`, string
> immutability, missing-byte return `0x0`, second immutability check, and
> `kfree-owned-strchr-string-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `strchr` only under the owned NUL-terminated string plus scalar-search-byte contract. This
> does not authorize arbitrary pointers, unterminated strings, user pointers, or other string helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `strcmp` owned-string compare contract

> ### ✅ STATUS (2026-06-30 live pass) — `strcmp` promoted under two owned NUL strings only
>
> Twelfth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py
> call-proof` with `strcmp`, using two tool-owned NUL-terminated kernel string buffers containing
> `A90STRCMP-PROOF-ZZ\0`, then mutating one right-string byte from `0x5a` to `0x40` for a controlled
> first-difference positive-sign case. Static gate: `strcmp=0xffffff80099a8b6c`,
> `leaf-map-disasm+xref`, direct-BL xrefs `3507`, leaf/no-BL, RET in scan. Source contract:
> `extern int strcmp(const char *,const char *)`, with x0/x1 as string pointer args. The call-safety
> seed remains `SAFE-WITH-VALID-PTR`; required valid pointer args are x0 `left-string-buffer` and x1
> `right-string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strcmp` with the C2B verified map. Result:
> `a90-repl-live-call-proof-strcmp-pass`; checks covered C1 identity, source pointer contract, owned
> string allocation, string poke/peek, equal compare return `0x0`, equal-case immutability, mismatch
> compare positive return `0xd0`, mismatch-case immutability, and `kfree-owned-strcmp-strings`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `strcmp` only under the two-owned-NUL-terminated-string contract. This does not authorize
> arbitrary pointers, unterminated strings, user pointers, locale/ordering assumptions beyond sign, or
> other string helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `memset` owned-destination contract

> ### ✅ STATUS (2026-06-30 live pass) — `memset` promoted under owned dst + bounded size only
>
> Eleventh one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py
> call-proof` with `memset`, using one tool-owned destination buffer, scalar fill byte `0x5a`,
> scalar `size=32`, and a post-size canary. Static gate: `memset=0xffffff80099a8980`,
> `leaf-map-disasm+xref`, direct-BL xrefs `6517`, leaf/no-BL, RET in scan. Source contract:
> `extern void * memset(void *,int,__kernel_size_t)`, with x0 as destination pointer and x1/x2 as
> scalar fill byte/size. The call-safety seed remains `SAFE-WITH-VALID-PTR`; required valid pointer
> arg is x0 `destination-buffer`, with x2 bounded inside the owned destination.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof memset` with the C2B verified map. Result:
> `a90-repl-live-call-proof-memset-pass`; checks covered C1 identity, source pointer contract,
> owned destination allocation, initial poke/peek (`0x11` prefix plus canary), returned destination
> pointer, 32-byte `0x5a` fill, canary preservation, and `kfree-owned-memset-destination-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `memset` only under the owned destination plus scalar-fill-byte and bounded-size contract.
> This does not authorize arbitrary pointers, unbounded sizes, user pointers, or other memory write
> helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `strrchr` owned-string contract

> ### ✅ STATUS (2026-06-30 live pass) — `strrchr` promoted under owned NUL-terminated string only
>
> Tenth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `strrchr`, using one tool-owned NUL-terminated kernel string buffer containing
> `A90STRRCHR-A-B-A-Z\0`, scalar search byte `0x41` (`A`), and scalar missing-byte probe `0x40`
> (`@`). Static gate: `strrchr=0xffffff80099a900c`, `leaf-map-disasm+xref`, direct-BL xrefs `1405`,
> leaf/no-BL, RET in scan. Source contract: `extern char * strrchr(const char *,int)`, with x0 as
> the string pointer and x1 as a scalar byte. The call-safety seed remains `SAFE-WITH-VALID-PTR`;
> required valid pointer arg is x0 `string-buffer`.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strrchr` with the C2B verified map. Result:
> `a90-repl-live-call-proof-strrchr-pass`; checks covered C1 identity, source pointer contract,
> owned string allocation, string poke/peek, hit return at expected offset `15`, string immutability,
> missing-byte return `0x0`, second immutability check, and `kfree-owned-strrchr-string-buffer`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `strrchr` only under the owned NUL-terminated string plus scalar-search-byte contract. This
> does not authorize arbitrary pointers, unterminated strings, user pointers, or other string helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `memcmp` owned-buffer contract

> ### ✅ STATUS (2026-06-30 live pass) — `memcmp` promoted under two owned buffers + bounded size only
>
> Ninth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `memcmp`, using two tool-owned initialized kernel buffers containing
> `A90MEMCMP-PROOF-0123456789ABCDEF`, scalar `size=32`, and one bounded mismatch mutation in the
> right buffer. Static gate: `memcmp=0xffffff80099a84b0`, `leaf-map-disasm+xref`, direct-BL xrefs
> `921`, leaf/no-BL, RET in scan. Source contract:
> `extern int memcmp(const void *,const void *,__kernel_size_t)`, with x0/x1 as pointer args and x2
> as scalar size. The call-safety seed remains `SAFE-WITH-VALID-PTR`; required valid pointer args are
> x0 `left-buffer`, x1 `right-buffer`, with x2 bounded inside both owned buffers.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof memcmp` with the C2B verified map. Result:
> `a90-repl-live-call-proof-memcmp-pass`; checks covered C1 identity, source pointer contract,
> owned left/right allocation, equal-buffer poke/peek, equal return `0x0`, equal-buffer immutability,
> mismatch poke/peek at offset `10` (`0x50` vs `0x40`), positive mismatch return (`0x80` observed),
> mismatch-buffer immutability, and `kfree-owned-memcmp-buffers`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `memcmp` only under the two-owned-buffer plus bounded-size contract. This does not authorize
> arbitrary pointers, unbounded sizes, user pointers, or other memory helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `strncpy` owned-buffer contract

> ### ✅ STATUS (2026-06-30 live pass) — `strncpy` promoted under owned dst/src + bounded count only
>
> Eighth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `strncpy`, using a tool-owned destination buffer, a tool-owned source buffer containing
> `A90STRNCPY\0`, and scalar `count=32`. Static gate: `strncpy=0xffffff80099b96f4`, map/export
> agree, direct-BL xrefs `187`, JOPP entry true, leaf/no-BL. Source contract:
> `extern char * strncpy(char *,const char *, __kernel_size_t)`, with x0/x1 as pointer args. The
> call-safety seed remains `SAFE-WITH-VALID-PTR`; required valid pointer args are x0
> `destination-buffer`, x1 `source-string-buffer`, with the proof bounding x2 inside the destination.
>
> Live path: confirmed rollback images and TWRP, flashed the existing v1-repl boot image
> (`b846ae9f...`) through `native_init_flash.py`, confirmed native selftest `fail=0` and
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof strncpy` with the C2B verified map. Result:
> `a90-repl-live-call-proof-strncpy-pass`; checks covered C1 identity, source pointer contract,
> owned dst/src allocation, source poke/peek, return pointer matching the owned destination pointer
> (redacted publicly), destination prefix match, NUL padding through count `32`, post-count canary
> preservation, and `kfree-owned-strncpy-buffers`.
>
> Candidate selftest after proof was `pass=11 warn=1 fail=0`. Rollback to clean v2321 used the checked
> helper with readback SHA `ca978551...`; final selftest was `pass=11 warn=1 fail=0`. Function map
> records `strncpy` only under the owned destination/source plus bounded-count contract. This does not
> authorize arbitrary pointers, arbitrary counts, or other string/memory helpers.

## ✅ DONE — REPL post-epic one-target live-call proof — `strlcpy` owned-buffer contract

> ### ✅ STATUS (2026-06-30 live pass) — `strlcpy` promoted under owned dst/src + bounded size only
>
> Seventh one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `strlcpy`, using a tool-owned destination buffer, a tool-owned source buffer containing
> `A90STRLCPY\0`, and scalar `size=32`. C1 identity is `export-recovery`:
> `strlcpy=0xffffff80099b9724`, map/export agree, direct-BL xrefs `963`, JOPP entry true. The body
> calls `__pi_strlen` and `__memcpy`, so the proof contract owns both dst/src and fixes size inside
> the destination. Source oracle confirms `include/linux/string.h:28`,
> `size_t strlcpy(char *, const char *, size_t)`, with x0/x1 as pointer args.
>
> Live path: baseline v2321 selftest passed, flashed existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`, confirmed candidate
> `selftest pass=11 warn=1 fail=0` and `a90-repl-v2a1-selftest-pass`, then ran `call-proof strlcpy`
> with the C2B verified map. Result: `a90-repl-live-call-proof-strlcpy-pass`; checks covered
> `export-recovery` C1 identity, source/call-safety contracts, distinct owned dst/src buffers,
> source poke/peek, exact `strlcpy-return-contract` (`0xa` source length), destination prefix match,
> canary after the size boundary preserved, and `kfree-owned-strlcpy-buffers`. Candidate selftest
> after proof stayed `fail=0`.
>
> Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Two serial commands
> during the unit hit known echo/END-marker noise and passed on retry before any unsafe live call was
> attempted or after rollback. Function map records `strlcpy` only under the owned destination,
> owned source, bounded-size contract. Other string/memory copy helpers remain parked. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_STRLCPY_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `strscpy` owned-buffer contract

> ### ✅ STATUS (2026-06-30 live pass) — `strscpy` promoted under owned dst/src + bounded size only
>
> Sixth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `strscpy`, using a tool-owned destination buffer, a tool-owned source buffer containing
> `A90STRSCPY\0`, and scalar `size=32`. C1 identity is the regular export-recovery path:
> `strscpy=0xffffff80099b9794`, map/export agree, direct-BL xrefs `8`, JOPP entry true, leaf/no-BL
> body. Source oracle confirms `include/linux/string.h:31`,
> `ssize_t strscpy(char *, const char *, size_t)`, with x0/x1 as pointer args. The call-safety seed
> requires x0=`destination-buffer` and x1=`source-string-buffer`; the proof owns both and fixes x2
> inside the destination size.
>
> Live path: baseline v2321 selftest passed, flashed existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`, confirmed candidate
> `selftest pass=11 warn=1 fail=0` and `a90-repl-v2a1-selftest-pass`, then ran `call-proof strscpy`
> with the C2B verified map. Result: `a90-repl-live-call-proof-strscpy-pass`; checks covered
> `export-recovery` C1 identity, source/call-safety contracts, distinct owned dst/src buffers,
> source poke/peek, exact `strscpy-return-contract` (`0xa`), destination prefix match, canary after
> the size boundary preserved, and `kfree-owned-strscpy-buffers`. Candidate selftest after proof
> stayed `fail=0`.
>
> Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. One preflight
> command pair briefly contended for the serial bridge and produced an END-marker miss/`rc=-16`;
> rerunning sequentially passed. Function map records `strscpy` only under the owned destination,
> owned source, bounded-size contract. Other string/memory copy helpers remain parked. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_STRSCPY_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `strlen` owned-string contract

> ### ✅ STATUS (2026-06-30 live pass) — `strlen` promoted under owned NUL-terminated string only
>
> Fifth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `strlen`, using a tool-owned kernel buffer containing `A90STRLEN\0`. This target required the
> same narrow C1 extension class as `strnlen` because `strlen` is a non-JOPP arm64 leaf helper:
> `resolve_verified` now accepts only the explicit leaf-map ground-truth row for `strlen` when the
> map target has high direct-BL xrefs (`2073`, threshold `1000`), no BL in the scanned body, a real
> RET, and no zero-return shape. Source oracle confirms `include/linux/string.h:82`,
> `extern __kernel_size_t strlen(const char *)`, with x0 as the only pointer arg.
>
> Live path: baseline v2321 selftest passed, flashed existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`, confirmed candidate
> `selftest pass=11 warn=1 fail=0` and `a90-repl-v2a1-selftest-pass`, then ran `call-proof strlen`
> with the C2B verified map. Result: `a90-repl-live-call-proof-strlen-pass`; checks covered
> `leaf-map-disasm+xref` C1 identity, source/call-safety contracts, `kmalloc-owned-string-buffer`,
> zero-filled owned string poke/peek, exact `strlen-return-contract` (`0x9`), and
> `kfree-owned-string-buffer`. Candidate selftest after proof stayed `fail=0`.
>
> Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. One immediate final
> health attempt hit known serial input/END-marker fragmentation; `version` realigned the bridge and
> the slow-input retry passed. Function map records `strlen` only under the owned NUL-terminated
> kernel string contract. Other string/memory helpers remain parked. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_STRLEN_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `strnlen` owned-string contract

> ### ✅ STATUS (2026-06-30 live pass) — `strnlen` promoted under owned NUL-terminated string only
>
> Fourth one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `strnlen`, using a tool-owned kernel buffer containing `A90STRNLEN\0` and scalar `maxlen=64`.
> This target required a narrow C1 extension because `strnlen` is a non-JOPP arm64 leaf helper:
> `resolve_verified` now accepts only the explicit leaf-map ground-truth row for `strnlen` when the
> map target has high direct-BL xrefs (`473`, threshold `100`), no BL in the scanned body, a real RET,
> and no zero-return shape. Source oracle confirms `include/linux/string.h:85`,
> `extern __kernel_size_t strnlen(const char *,__kernel_size_t)`, with x0 as the only pointer arg.
>
> Live path: baseline v2321 selftest passed, flashed existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`, confirmed candidate
> `selftest pass=11 warn=1 fail=0` and `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof strnlen` with the C2B verified map. Result:
> `a90-repl-live-call-proof-strnlen-pass`; checks covered `leaf-map-disasm+xref` C1 identity,
> source/call-safety contracts, `kmalloc-owned-string-buffer`, owned string poke/peek, exact
> `strnlen-return-contract` (`0xa`), and `kfree-owned-string-buffer`. Candidate selftest after proof
> stayed `fail=0`.
>
> Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Two health attempts
> during the unit hit known serial input/END-marker fragmentation; `version` realigned the bridge and
> slow-input retries passed. Function map records `strnlen` only under the owned NUL-terminated kernel
> string plus scalar `maxlen` contract. Other string/memory helpers remain parked. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_STRNLEN_2026-06-30.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `kernel_read` owned-buffer contract

> ### ✅ STATUS (2026-06-29 live pass) — `kernel_read` promoted under paired owned file/buffer/pos only
>
> Third one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `kernel_read`, using the already proven setup pattern: allocate owned kernel buffers, write
> `/init\0`, call `filp_open(path, O_RDONLY, 0)`, allocate an owned read buffer plus owned `loff_t`
> position, call `kernel_read(file, buf, 16, pos)`, verify the return/buffer/position contract, close
> the file with `filp_close(file, NULL)`, and free all owned buffers.
>
> Static gate: `kernel_read=0xffffff800828bae4` (`export-recovery`, direct BL xrefs `17`), source
> signature `extern ssize_t kernel_read(struct file *, void *, size_t, loff_t *)`, tier
> `SAFE-WITH-VALID-PTR`, x0 requires `struct-file`, x1 requires `buffer`, x3 requires `loff_t-pos`.
> Paired setup/cleanup stayed on verified `filp_open=0xffffff800828a664` and
> `filp_close=0xffffff800828ac14`; allocator orchestration reused verified
> `__kmalloc=0xffffff800826ae34` and `kfree=0xffffff800826b354`.
>
> Live path: baseline v2321 selftest passed, flashed existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`, confirmed candidate
> `selftest pass=11 warn=1 fail=0` and `a90-repl-v2a1-selftest-pass`, then ran
> `call-proof kernel_read` with the C2B verified map. Result:
> `a90-repl-live-call-proof-kernel_read-pass`; observed return `0x10`, buffer prefix `7f454c46`
> (`ELF`), position advanced to `0x10`, `filp_close` returned `0`, and path/read/pos buffers were
> freed. Candidate selftest after proof stayed `fail=0`.
>
> Rolled back to clean v2321
> (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final resident
> `v2321-usb-clean-identity-rodata` and final `selftest pass=11 warn=1 fail=0`. Two immediate health
> commands during the unit hit known serial input fragmentation and missed `A90P1 END`; short
> `version` commands realigned the bridge and slow-input retries passed. Function map now records
> `kernel_read` only under this owned `/init` file/read-buffer/position contract; arbitrary file
> pointers or destination buffers remain parked. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KERNEL_READ_2026-06-29.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `filp_open` owned-pathname contract

> ### ✅ STATUS (2026-06-29 live pass) — `filp_open` promoted to function-map row under owned pathname only
>
> Second one-target live-call proof after the REPL epic close. Codex extended `a90_repl.py call-proof`
> with `filp_open`, using a tool-owned kernel buffer containing `/init\0`, `O_RDONLY`, mode `0`, and
> paired cleanup through `filp_close(file, NULL)`.
>
> Static gate: `filp_open=0xffffff800828a664` (`export-recovery`, direct BL xrefs `48`), source
> signature `extern struct file * filp_open(const char *, int, umode_t)`, tier `SAFE-WITH-VALID-PTR`,
> x0 requires `pathname`; paired cleanup `filp_close=0xffffff800828ac14` (`export-recovery`, direct BL
> xrefs `67`), source signature `extern int filp_close(struct file *, fl_owner_t id)`. Allocator
> orchestration reused verified `__kmalloc=0xffffff800826ae34` and `kfree=0xffffff800826b354`.
>
> Live path: flashed existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`, confirmed
> `a90-repl-v2a1-selftest-pass`, then ran `call-proof filp_open` with the C2B verified map. Result:
> `a90-repl-live-call-proof-filp_open-pass`; checks covered `kmalloc-owned-pathname-buffer`,
> `owned-pathname-poke-peek`, sane non-ERR `struct file *` return, `filp_close` return `0`, and
> `kfree-owned-pathname-buffer`. Candidate selftest stayed `fail=0`. Rolled back to clean v2321 with
> final `selftest pass=11 warn=1 fail=0`.
>
> Function map updated: `filp_open` is live-proven only under the owned `/init` pathname contract;
> `filp_close` gets cleanup-only evidence for the exact file pointer returned by this proof, not a
> general close allowlist. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_FILP_OPEN_2026-06-29.md`.

## ✅ DONE — REPL post-epic one-target live-call proof — `ksize` owned-pointer contract

> ### ✅ STATUS (2026-06-29 live pass) — `ksize` promoted to function-map row under owned input only
>
> Operator-chartered extension after the REPL epic close: one vetted target, static contract first, bounded
> live call, result check, cleanup, rollback. Codex added `a90_repl.py call-proof ksize`, a focused faithful
> fake integration test, runbook coverage, and a redacted public function map:
> `docs/operations/NATIVE_INIT_RUNTIME_KERNEL_REPL_LIVE_CALL_FUNCTION_MAP.md`.
>
> Live path: flashed existing v1-repl image
> `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` via
> `native_init_flash.py`, confirmed `a90-repl-v2a1-selftest-pass`, then ran `call-proof` with the
> C2B verified map. Static gate: `ksize=0xffffff800826b27c` (`export-recovery`, direct BL xrefs `39`),
> source signature `size_t ksize(const void *)`, tier `SAFE-WITH-VALID-PTR`, x0 requires
> `kmalloc-object`; allocator orchestration used verified `__kmalloc=0xffffff800826ae34` and
> `kfree=0xffffff800826b354`.
>
> Result: `a90-repl-live-call-proof-ksize-pass`; the tool allocated an owned `0x1000` object,
> called `ksize(ptr)`, observed return `0x1000` within `[0x1000,0x2000]`, freed the object, and kept
> raw runtime slide/allocation pointer private. Candidate selftest stayed `fail=0`. Rolled back to clean
> v2321 (`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with final
> `selftest pass=11 warn=1 fail=0`. One final selftest retry was needed after serial input fragmentation;
> `version` realigned the bridge and slow-input retry passed. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_LIVE_CALL_PROOF_KSIZE_2026-06-29.md`.
>
> Boundary remains unchanged: this is **not** a mass-call unlock. `ksize` is live-proven only under
> the internally owned `__kmalloc` pointer contract.

## ✅ DONE — REPL U4 — source-scan perf polish + tool runbook; REPL epic CLOSED

> ### ✅ OPERATOR GATE-2 SIGN-OFF (2026-06-29) — U4 DONE; Runtime Kernel REPL epic CLOSED
>
> Independently verified 7993fbba host-only. **Perf:** allocator + read-io family sweeps each complete in **~6s**
> (was ~126s, ~21× faster) via hint-first source lookup (`ksize` resolves with `candidate_file_count<=1`), cached
> file reads, and one-pass BL-xref indexing. **Verdicts byte-identical + regression-pinned**
> (`test_u4_family_sweep_verdicts_are_pinned`): allocator `candidate_safe_ranked==['ksize']` (kfree_const/
> kmem_cache_shrink still dropped DRIVEN BY SOURCE), read-io `==['filp_close','filp_open','kernel_read']`,
> kmem_cache_init/__init + kfree_skb_partial/taint drops hold. `lookup_source_signature('ksize')` still
> found=True/ptr=True. Firewall intact (offline, no device/network/seed mutation); 63/63 tests; U2 invariants hold.
> Runbook `docs/operations/NATIVE_INIT_RUNTIME_KERNEL_REPL_RUNBOOK.md` covers commands + map regen + 4 anchors
> (printk `0xffffff800813adfc`, real-not-twin) + fail-closed/advisory-firewall safety + the operator-gated
> one-target live-call exception; only static link anchors, no runtime pointers/slide. **U4 DoD met.**
>
> **The Runtime Kernel REPL epic (v1-repl → v2a → v2c → U1–U4) is CLOSED.** Delivered: a flash-once named runtime
> kernel REPL (peek/poke/call/slide, C1 fail-closed identity), a triple-oracle-verified kallsyms ground-truth map,
> a disasm+source call-safety classifier with a fail-closed gate, and a broad advisory risk-assessment sweep — all
> host-driven, exploit-free, device on clean v2321. The only future extension is a separately-gated one-target live
> call-proof of a vetted candidate, if ever chartered. Loop HALTED at the epic boundary awaiting the next epic.

> ### ✅ STATUS (2026-06-29 U4 host pass) — perf polish + runbook complete
>
> U4 is host-only complete. `call-safety-sweep` now keeps U3 verdicts while avoiding repeated broad
> source/header scans and repeated whole-image direct-BL xref scans: source lookup tries
> symbol/family hints first (`ksize` now resolves via `candidate_scan_strategy=hint`,
> `candidate_file_count=1`), source file text is cached, non-C local clone names are rejected early,
> and BL xrefs are indexed once per raw image. Re-sweep verdicts are unchanged and regression-tested:
> allocator `candidate_safe_ranked=['ksize']`; read-io
> `candidate_safe_ranked=['filp_close', 'filp_open', 'kernel_read']`; `kmem_cache_init` remains
> `source-__init` dropped; `kfree_const`, `kmem_cache_shrink`, and `kfree_skb_partial` remain dropped
> by the source/disasm pointer-contract firewall. Fresh timings: allocator `6.10s` for 28 rows,
> read-io `4.76s` for 40 rows.
>
> Runbook added: `docs/operations/NATIVE_INIT_RUNTIME_KERNEL_REPL_RUNBOOK.md`. U4 report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_U4_PERF_RUNBOOK_CLOSE_2026-06-29.md`.
> Validation: `py_compile` PASS, `tests.test_a90_repl.CallSafetyClassificationTests` `13/13` PASS,
> full `tests.test_a90_repl` `63/63` PASS, `git diff --check` PASS. No device, no flash, no boot
> image, no network, no live REPL op.
>
> With U1-U4 complete, the Runtime Kernel REPL epic is CLOSED. Any future "call this function and
> check a live result" is a new separately gated one-target live-call unit, not an autonomous mass
> call or continuation of the advisory sweep.

**Operator-chartered 2026-06-29 (user chose "runbook + perf polish 후 close").** U2+U3 core is done/verified;
this is the final unit before the REPL epic closes. Two host-only deliverables, then close.

**Deliverable 1 — source-scan perf polish (correctness-preserving).** The U3 `call-safety-sweep` source oracle
scans ~655 unfiltered files per symbol, so a family sweep takes ~126s (it sat right on the edge of a 2-min
timeout). Fix host-only: pre-index the source tree's function declarations ONCE per run (or cache across symbols
within a sweep) and/or subsystem-scope candidate files (prefer `include/linux/*.h` + the symbol's own subsystem
dir). **Target: a family sweep completes in a few seconds.** HARD REQUIREMENT: identical verdicts to the
operator-verified results — `allocator` candidate_safe_ranked == `['ksize']` (kfree_const/kmem_cache_shrink still
dropped DRIVEN BY SOURCE), `read-io` candidates == `filp_open/filp_close/kernel_read`, `kmem_cache_init` still
`source-__init` dropped, `kfree_skb_partial` still taint-dropped. Add a regression test pinning those two family
results so the speedup can't silently change a verdict. Stay offline/deterministic; `lookup_source_signature('ksize')`
must still return `found=True, has_pointer_arg=True`. No device, no boot image.

**Deliverable 2 — tool runbook.** A concise ops doc (e.g. `docs/operations/NATIVE_INIT_RUNTIME_KERNEL_REPL_RUNBOOK.md`)
covering the whole REPL toolchain so it is usable + safe without re-deriving context: (a) commands —
`a90_stock_kallsyms_extract.py` (verified-map regen), `a90_repl.py` `selftest`/`resolve`/`peek`/`read`/`call`/`poke`/
`call-safety-classify`/`call-safety-sweep`/`ksymtab-ground-truth`; (b) the verified-map regen procedure + the four
anchors (printk `0xffffff800813adfc` not the twin, __kmalloc, kfree, force_no_nap_store) and the 3-oracle ground
truth; (c) the SAFETY model — C1 fail-closed identity resolution, the call-safety tiers, the advisory/auto-call
firewall (swept candidate-SAFE ≠ gate-callable), and that live "call the function + check result" is a SEPARATE
one-target operator-gated step (panic_on_oops=0, bounded, rollback v2321), never an autonomous mass live-call.
Redacted/metadata-only (no raw runtime pointers/slide). Host-only.

**Definition of done for U4:** sweep perf is a few seconds per family with byte-identical verdicts to the verified
allocator/read-io results (regression-tested); the runbook doc is committed and covers commands + map regen + anchors
+ safety/firewall + the separate live-call gate; `py_compile` + focused suite pass; host-only, no device, no boot
image. **On U4 done, the REPL epic CLOSES** (U1–U3 + this); the only thing beyond is a future separately-gated live
call-proof of a vetted candidate, if ever chartered.

**Guardrails:** host-only; the perf change MUST NOT alter any verdict (pin the 2 family results in a test); firewall +
C1 fail-closed preserved; offline/deterministic; keep raw runtime pointers out of commits; scoped `git add`;
fails-twice → STOP + report. Operator Gate-2's by independently re-running both family sweeps (verdicts unchanged +
fast) and reading the runbook; the loop owns host build + tests + commits and does NOT touch the device.

## ✅ DONE — REPL U3 — broad advisory call-safety risk-assessment sweep (operator-verified 2026-06-29)

> ### ✅ OPERATOR GATE-2 SIGN-OFF (2026-06-29) — U3 DONE; source now DRIVES candidacy; verified on 2 families
>
> Independently re-swept against the v2321 image + stock source tree. **Allocator** `candidate_safe_ranked=['ksize']`
> only — `kfree_const` and `kmem_cache_shrink` now DROP (both `src_ptr=True, pointer_arg_indices=[0]`, `disasm_argmem=0`
> → dropped DRIVEN BY SOURCE, exactly the disasm under-approximation source-xref was added to catch). **Read-io**
> (completes in ~126s, 60 symbols) retains only seeded valid-ptr candidates `filp_open/filp_close/kernel_read` — no
> false-SAFE leak. `kmem_cache_init` stays dropped via `source-__init-annotation`; `kfree_skb_partial` via taint.
> Firewall holds on both families (`auto_call_firewall`, offline, no device/network/seed mutation); U2 invariants
> intact (printk=SAFE-WITH-VALID-PTR real-not-twin, __kmalloc=SAFE-SCALAR, kfree=SAFE-WITH-VALID-PTR,
> kallsyms_lookup_name=DENY, commit_creds=BEHAVIOR-CHANGING). All 3 reopened defects resolved. **U3 DoD met.**
>
> **Optional polish (not blocking, deferred):** each family sweep takes ~126s because the source candidate-file scan
> is unfiltered (~655 files/symbol). For the productization/stability theme, pre-index or subsystem-scope the source
> lookup (and/or cache across symbols) to bring a family sweep under a few seconds. Track with the tool runbook.
>
> After U3, only the optional tool runbook (+ this perf polish) remains before the REPL epic can fully close.

> ### ✅ STATUS (2026-06-29 U3 Gate-2 2nd correction host pass) — source pointer verdict wired into candidacy
>
> The remaining source-verdict gap is fixed: advisory candidate blocking now uses
> `source pointer_arg_indices ∪ disasm arg-memory-flow indices` before applying
> `unseeded-arg-memory-flow-without-gate-pointer-contract`. Row output also exposes source evidence directly
> (`source_signature`, `source_annotation_flags`, plus `source_evidence`) instead of only burying it in the nested
> source object. Allocator re-sweep (`--family allocator --limit 80`) now has `candidate_safe_count=1` with only
> `ksize` remaining; `kfree_const` (`extern void kfree_const(const void *x)`) and `kmem_cache_shrink`
> (`int kmem_cache_shrink(struct kmem_cache *)`) both have source pointer indices `[0]`, union indices `[0]`,
> `unseeded-arg-memory-flow-without-gate-pointer-contract`, and `candidate_safe=false`. Read-I/O re-sweep
> (`--family read-io --limit 40`) retains only seeded/contract-backed candidates (`filp_close`, `filp_open`,
> `kernel_read`). Both sweeps stayed `host_only=true`, `device_action=false`, and `network_dependency=false`.
> Validation: `py_compile` PASS, `tests.test_a90_repl.CallSafetyClassificationTests` 12/12 PASS,
> full `tests.test_a90_repl` 62/62 PASS. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_U3_GATE2_SOURCE_VERDICT_WIRING_2026-06-29.md`.

> ### (history) 🛑 OPERATOR GATE-2 (2026-06-29, 2nd pass) — oracle ACTIVATED + 2 defects fixed, but source pointer-arg is found yet NOT applied to candidacy
>
> Verified cbe1d90d host-only. **Fixed ✓:** source oracle now `found=True` for all symbols; `kmem_cache_init`
> drops from candidate-SAFE with flag `source-__init-annotation` (defect #2 ✓); `kfree_skb_partial` drops with
> `unseeded-arg-memory-flow-without-gate-pointer-contract` (defect #3 ✓); firewall holds (candidate-SAFE still
> `gate_tier` unchanged, offline, no device/network/seed mutation); U2 gate tiers intact (__kmalloc=SAFE-SCALAR,
> kfree/ksize=SAFE-WITH-VALID-PTR).
>
> **Remaining gap (defect #1's PURPOSE, half-done): the source pointer-arg verdict is found but inert in the
> candidate decision.** Re-sweep `allocator` leaves `kfree_const` and `kmem_cache_shrink` as `candidate_safe=True`
> with NO pointer contract, even though source reports `has_pointer_arg=True, pointer_arg_indices=[0]` for both
> (they are real pointer-consumers — `kfree_const(x)` frees, `kmem_cache_shrink(cachep)` derefs the cache). They
> survive only because the disasm taint MISSED their deref (`arg_memory_base_use_count=0`), and the candidate-drop
> is keyed on disasm taint, not on source. That is exactly the under-approximation source-xref was added to catch:
> **source must override disasm toward more-restrictive, and it currently does not drive candidacy.**
>
> **FIX (host-only):** make the candidate-SAFE drop ALSO trigger on SOURCE pointer-args — a non-seeded symbol whose
> source has `pointer_arg_indices` and no vetted gate pointer contract MUST NOT be candidate-SAFE (same treatment
> `kfree_skb_partial` got from disasm taint). Equivalently: union the source pointer indices with the disasm
> arg-memory-flow set before the "unseeded-...-without-gate-pointer-contract" check. After the fix, re-sweep
> `allocator` + 1 more family and confirm `kfree_const` and `kmem_cache_shrink` drop out, leaving only seeded/
> contract-backed candidates (e.g. `ksize`). Also surface the source EVIDENCE on each row (`signature` is `None` and
> the row `annotation_flags` is `None` even when the `source-__init-annotation` flag fired) so the DoD's
> "source-signature evidence attached" actually holds. Keep firewall + offline/deterministic; do not touch device.
> Note: this is a NEW adjacent gap (verdict-wiring), distinct from the 1st reopen (oracle-inert) — not a
> fails-twice loop; it is incremental. U3 not done until source drives candidacy.

> ### ✅ STATUS (2026-06-29 U3 Gate-2 correction host pass) — source oracle active; false candidates removed
>
> Gate-2 correction landed in `a90_repl.py`: source candidate ordering now prioritizes subsystem declarations
> such as `include/linux/slab.h`; `lookup_source_signature('ksize')` returns `found=true`,
> `has_pointer_arg=true`, selected `include/linux/slab.h:153` (`size_t ksize(const void *)`), and records
> candidate-file debug evidence. Source `__init`/`__exit` annotations now produce danger flags, so
> `kmem_cache_init` (`void __init kmem_cache_init(void)`, slab.h:121) is `candidate_safe=false` with
> `source-__init-annotation`. Non-seeded symbols with arg-derived memory-base flow and no vetted gate pointer
> contract now get `unseeded-arg-memory-flow-without-gate-pointer-contract`, so `kfree_skb_partial`
> (`arg_memory_base_use_count=3`) is no longer a candidate. Re-sweeps: allocator family swept 28 rows
> (`candidate_safe_count=3`), read-I/O family swept 40 rows (`candidate_safe_count=10`), both
> `host_only=true`, `device_action=false`, `network_dependency=false`. Validation: `py_compile` PASS,
> `tests.test_a90_repl.CallSafetyClassificationTests` 12/12 PASS, full `tests.test_a90_repl` 62/62 PASS.
> Report: `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_U3_GATE2_SOURCE_ORACLE_FIX_2026-06-29.md`.

> ### (history) 🛑 OPERATOR GATE-2 (2026-06-29) — U3 firewall HOLDS, but the source oracle is INERT + advisory list has false-SAFEs. NOT done.
>
> I ran `call-safety-sweep --family allocator` against the v2321 image + the stock source tree and independently
> checked it. **Good (live safety intact):** `auto_call_firewall=sweep-results-do-not-mutate-CALL_SAFETY_SEEDS-or-call-gate`,
> every non-seeded candidate is `gate_tier=DENY / gate_auto_call_allowed=False` (candidate-SAFE ≠ gate-callable ✓),
> `offline_source_oracle=True`, `network_dependency=False`, `device_action=False`. No live danger, no seed mutation.
> **But three advisory-layer defects (the U3 deliverable + the operator-requested enrichment are not working):**
> 1. **The source-xref oracle is completely INERT.** `lookup_source_signature('ksize', source_root=<tree>)` returns
>    `found=None` for EVERY symbol, even though `size_t ksize(const void *)` is at `include/linux/slab.h:153`. I proved
>    the bug is in the ORCHESTRATION layer, not the parser: `_extract_source_signatures_from_file(root, slab.h, 'ksize')`
>    and `_parse_source_signature_statement(...)` BOTH correctly return the signature with `is_pointer=True,
>    pointer_arg_indices=[0]`, and `slab.h` IS in `_source_candidate_files('ksize')` — yet the top-level
>    `lookup_source_signature` discards it and returns None. So the "source overrides disasm" safety net does nothing.
>    **FIX:** make `lookup_source_signature` actually return the file-level extraction it already computes (debug the
>    candidate-iteration/precedence/cache path; note `_source_candidate_files` returns 655 unfiltered files starting at
>    `arch/alpha/...`, so fix the selection too — prefer `include/linux/*.h` declarations and the symbol's own subsystem).
> 2. **No `__init`/`__exit` danger flag.** `kmem_cache_init` is `void __init kmem_cache_init(void)` (slab.h:121) — calling
>    it at runtime executes freed `.init.text` and faults — yet it is listed `candidate_safe=True` with NO flag. Add a
>    danger flag from the source `__init`/`__exit` annotation AND/OR the symbol's address landing in the init section range.
> 3. **Advisory candidate logic ignores the taint arg-memory-base signal for non-seeded symbols.** `kfree_skb_partial`
>    has taint `arg_memory_base_use_count=3 / no_flow=False` (it derefs its skb pointer arg) yet is `candidate_safe=True`
>    with no blocking flag. A non-seeded symbol with arg→memory-base flow and no covering declared pointer args MUST NOT
>    be candidate-SAFE. (Pure disasm taint already flagged it; the advisory just didn't honor it — independent of source.)
>
> Net: the firewall is right, but the advisory candidate-SAFE list is currently polluted with pointer-consumers and an
> `__init` function precisely because the source oracle is dead. Fix #1 (it's the headline enrichment), then #2/#3, then
> re-sweep ≥2 families and confirm pointer-arg/`__init` symbols drop out of candidate-SAFE with source evidence attached.
> Host-only; firewall + offline/deterministic must stay; do not touch the device. U3 is NOT done until this lands.

### (history — U3 charter) broad advisory call-safety risk-assessment sweep

**Operator-chartered 2026-06-29 (U2 DONE/verified; user pre-decided U2→U3).** U2 gave a vetted ~15-symbol
seed + a disasm signal/taint extractor + a fail-closed gate. U3 SCALES that to a large function-family sweep
so we get broad, evidence-backed *risk triage* across the kernel — not just the seed.

> ### ✅ STATUS (2026-06-29 U3 host pass) — source-backed advisory sweep landed
>
> `a90_repl.py` now has `call-safety-sweep`: bounded family/prefix/regex/explicit-symbol selection, stable
> ordering, source-signature xref from the local stock kernel tree, existing U2/C1 static identity+taint
> evidence, danger flags, advisory tiers, and a ranked `advisory-not-auto-callable` candidate list. The
> firewall is explicit: sweep results do **not** mutate `CALL_SAFETY_SEEDS` or the `call` gate. Source
> signatures override toward restriction: pointer args never become `SAFE-SCALAR`; missing/ambiguous source
> downgrades; `__user` / lock / sleep annotations and disasm context calls block candidate promotion. CLI smoke:
> `strlcpy` becomes an advisory `SAFE-WITH-VALID-PTR` candidate while gate tier stays `DENY`; device-specific
> `kgsl_pwrctrl_force_no_nap_store` has missing source and stays advisory `DENY`. Three-family smoke
> (`allocator,string,read-io`, limit 20) swept 20 rows and produced 7 advisory candidates with
> `host_only=true`, `device_action=false`, and `network_dependency=false`. Validation: `py_compile`
> pass, `tests.test_a90_repl.CallSafetyClassificationTests` 11/11 PASS, full `tests.test_a90_repl` 61/61 PASS.
> Host-only, no device action, no boot-image change, no network dependency. Report:
> `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_U3_CALL_SAFETY_SWEEP_2026-06-29.md`.

**Goal:** run the U2 classifier across useful function families (allocator, string/mem, list, bounded
read-I/O, sysfs-`show`, refcount/get-put) and emit ① a signal-bucketed risk profile, ② a ranked
**candidate**-SAFE list, ③ explicit danger flags (held-lock/IRQ/sleep assumption, arg-pointer deref via the
U2 taint flow, variadic-twin prologue, non-leaf with locking). All host-only, disasm-driven, off the
byte-identical verified map.

**HARD CONSTRAINT (the whole point):** the sweep is **descriptive/advisory only**. It MUST NOT auto-promote
anything to an auto-callable tier. Auto-call whitelist promotion stays fail-closed: seed / operator-disasm /
live-proof only. Rationale = the kfree lesson + false-SAFE asymmetry: static signals UNDER-approximate, so a
false-DENY is free (operator can unblock) but a false-SAFE is a device fault. Tune the sweep to **rank
candidates and catch danger**, never to declare auto-SAFE. A swept "candidate-SAFE" verdict is advisory and
carries its evidence; it does NOT enter the gate's SAFE set without an explicit operator-disasm or live-proof
step.

**Deliverables (host-only, in `a90_repl.py` + tests):**
1. A `call-safety-sweep` subcommand: take a family selector (name-prefix/-regex sets or an explicit symbol
   list) + the verified map + v2321 image, classify each via the existing U2 path (identity via C1 first),
   and emit per-symbol records with tier + signals + the danger flags above, plus a summary histogram.
2. A conservative **candidate-SAFE ranking**: only functions that pass the U2 positive proofs
   (SAFE-SCALAR taint-clean, or SAFE-WITH-VALID-PTR with all derefs covered by declared ptr args) AND have
   no danger flag are listed as *candidate*, each tagged `advisory-not-auto-callable` with its evidence.
3. Keep the gate UNCHANGED: swept results never mutate `CALL_SAFETY_SEEDS` or `auto_call_allowed`. Add a test
   asserting a swept candidate-SAFE symbol is still gate-refused for `call` until explicitly seeded/vetted.
4. Bounded + deterministic: cap the swept set per run (e.g. a named family), stable ordering, no network, no
   device. Objdump excerpts optional/private.
5. **SOURCE cross-reference as the PRIMARY oracle (operator-requested enrichment).** We hold the exact stock
   tree at `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel/`. For each swept symbol,
   parse the C prototype/signature from source and use it as ground truth that OVERRIDES disasm
   under-approximation: a pointer-typed arg ⇒ never `SAFE-SCALAR` (this is exactly what the kfree false-SAFE
   needed — `void kfree(const void *)` says "pointer" instantly); `might_sleep()` / `__must_hold()` / lock
   annotations / `__user` ⇒ context/danger flags. Disasm/taint stays as the corroborating second oracle;
   when source and disasm disagree, take the MORE restrictive verdict and flag the disagreement. Record the
   source signature + file:line as evidence. (Source parse is best-effort: missing/ambiguous source must
   DOWNGRADE toward DENY, never upgrade.)
6. **WEB is advisory-only, operator-side, NOT baked into the tool.** Do not add any network/runtime web
   dependency to `call-safety-sweep`; it stays deterministic+offline. General kernel-API semantics from the
   web are an operator aid during Gate-2 only, never a classification authority (our own source tree
   outranks the web).

**NOT in U3 (separate later gate) — live "call the function and check the result."** Classification is
static+source only. Actually invoking a swept candidate on the device to "verify" is a SEPARATE,
explicitly-gated, ONE-TARGET-AT-A-TIME, recoverable step (operator approval, `panic_on_oops=0`, rollback
v2321) — NEVER an autonomous mass live-call sweep (mass false-SAFE = cascading device faults + operator
collision, V2631). The loop MUST NOT live-call functions in U3.

**Prior-art note (operator web check 2026-06-29):** the building-block methods are public and mature — reuse
them, don't reinvent: `vmlinux-to-elf` (symbol ground truth, already used), `drgn`/eBPF `probe_read_kernel`
(read-only kernel introspection), standard known-offset KASLR-slide leak, and static call-graph/side-effect
analysis (SyzScope/DR.CHECKER/B-Side — but those are framed for fuzzing/attack-surface/bug-triage). NO public
off-the-shelf tool produces a fail-closed "which stock-kernel functions are safe to invoke from a runtime
REPL" advisory whitelist, and nothing exists for this device's native-init REPL specifically. So U3 borrows
proven methods (source signatures + disasm taint + call-graph danger reachability) and the integrated
device-specific artifact is ours. Recursive improvement is allowed only as STATIC call-graph propagation
(a function reaching only proven-safe callees with no arg→memory-base flow inherits a safety argument), never
as recursive live-calling.

**Definition of done for U3:** `call-safety-sweep` produces evidence-backed risk profiles + a ranked
advisory candidate-SAFE list + danger flags over at least 2–3 real families, with source-signature evidence
attached and source overriding disasm toward the more-restrictive verdict; the advisory/auto-call firewall is
enforced (swept SAFE ≠ gate-callable) and tested; the tool stays offline/deterministic (no web/network/device);
the U2 invariants still hold; `py_compile` + focused suite pass; host-only, no device action, no boot image.
After U3, the optional tool runbook is the only remainder before the REPL epic can fully close.

**Guardrails:** host-only static analysis; exploit-free framing; BEHAVIOR-CHANGING/DENY families stay
classified, never chained or promoted; keep raw runtime pointers out of commits; scoped `git add`;
fails-twice on the same approach → STOP + report. Operator Gate-2's each commit by independently re-running
the sweep + disasm-spot-checking a sample (especially any candidate-SAFE verdict — false-SAFE is the risk);
the loop owns host build + tests + commits and does NOT touch the device for U3.

## ✅ DONE — REPL U2 (call-safety inventory + fail-closed classifier), operator-verified 2026-06-29

> ### ✅ OPERATOR GATE-2 SIGN-OFF (2026-06-29) — U2 DONE; kfree correction verified
>
> Reran the classifier against the verified map: `kfree=SAFE-WITH-VALID-PTR` (arg-taint `arg_memory_base_use_count=43`
> — would have dropped out of SAFE-SCALAR on the taint proof alone, defense-in-depth ✓), `__kmalloc=SAFE-SCALAR`
> (`arg_memory_base_use_count=0`, disasm = `cmp x0,#0x2000` + arithmetic, no deref ✓). Gate fails closed:
> `require_call_safety_for_call("kfree", ("0x1234",))` RAISES "SAFE-WITH-VALID-PTR requires"; only NULL (`0x0`) and an
> explicit caller-vouched owned kmalloc pointer token passes — you cannot *accidentally* `call kfree <scalar>`.
> Invariants intact: printk = real `0xffffff800813adfc` (not the twin) valid-ptr; kallsyms_lookup_name = DENY;
> commit_creds / prepare_kernel_cred / set_memory_x / call_usermodehelper_exec = BEHAVIOR-CHANGING, never auto-callable.
> 59/59 + 24/24 tests pass. Host-only, no device action, no boot image. **U2 DoD met.**

### (history — U2 charter, DONE 2026-06-29) DELEGATED: REPL U2 — kernel-grade CALL-SAFETY inventory + fail-closed classifier

**Operator-chartered 2026-06-29 (reopens the optional U2 remainder; kernel target ⇒ higher rigor than a
normal tool warrants).** v2c-C2E settled the *address* axis: ~147k symbols, three oracles byte-identical,
exported subset relocation-verified. The remaining real gap is **call-safety**: the REPL knows the address
of 77,561 functions but only **3** are live-call-proven safe (`printk`, `__kmalloc`, `kfree`). Two hard
lessons say "address known" ≠ "safe to call": a live `call kallsyms_lookup_name` **rebooted the device**
(right address, wrong call context), and the `printk` **twin** false-positive showed a working-looking call
can hit the wrong function. C1 fail-closed verifies *identity* but NOT *call-context safety*. U2 closes that.

**This unit is HOST-ONLY static analysis. No device action. No new boot image.** Live call-proof of any
newly-classified-SAFE function is a SEPARATE later unit behind its own explicit gate (bounded, recoverable,
`panic_on_oops=0`, rollback v2321) — do NOT flash or call live in U2.

**Deliverables (all in `a90_repl.py` + tests, host-only):**
1. A `call-safety-classify` subcommand: given the verified System.map + v2321 image, disasm each candidate
   function (objdump aarch64-linux-gnu at its link vaddr) and emit a per-symbol classification record with
   the **disasm evidence** that justifies it. Resolve identity through the existing C1 `resolve_verified`
   first (real symbol, not a twin), so classification never runs on a mislabeled/twin target.
2. Static safety signals to extract per function: (a) early **pointer-arg deref** of x0..x7 before any
   validation (`ldr/ldrb [xN]` on an arg reg) → faults on garbage; (b) **locking/context** assumptions —
   `bl` to spin_lock/mutex_lock/rcu, `lockdep_assert_held`, irq save/restore, `might_sleep`; (c) **variadic
   prologue** (the printk-twin shape) → twin/ABI risk; (d) leaf vs non-leaf; (e) does it return an
   interpretable value. Record the raw signals, not just a verdict.
3. Classification tiers (DENY-by-default):
   - `SAFE-SCALAR` — only scalar args, no arg-pointer deref, no held-lock assumption → callable with
     arbitrary scalars without fault (e.g. `__kmalloc`, `kfree`, `ksize`).
   - `SAFE-WITH-VALID-PTR` — safe **iff** a named arg is a caller-supplied verified pointer of the right
     kind (e.g. `printk` fmt, `kernel_read(file*,…)`); auto-call only when that pointer is provided+verified.
   - `CONTEXT-SENSITIVE` — depends on lock/irq/atomic context that the sysfs-store call context can't
     guarantee → NOT auto-callable; needs explicit context proof.
   - `BEHAVIOR-CHANGING` — technically callable but mutates global/security state (`commit_creds`,
     `set_memory_x`, `call_usermodehelper_exec`) → **never** in any auto-call set; RECON-framed, gated
     behind explicit intent; do NOT build an exploit chain here.
   - `DENY` — derefs args unsafely / known-unsafe (`kallsyms_lookup_name` observed reboot) / destructive.
4. Wire into the REPL `call` path: a `classify_call_safety(symbol)` gate that **fails closed** — `call`
   REFUSES any target not in the vetted SAFE set unless an explicit `--allow-unvetted` override token is
   passed. The 3 proven (`printk`/`__kmalloc`/`kfree`) must classify SAFE; `kallsyms_lookup_name` must
   classify DENY.
5. Seed a small **diverse, useful** vetted set (~10–15) so the surface is actually usable, not just a gate:
   allocator family (`__kmalloc`/`kfree`/`ksize`/`kmem_cache_alloc`/`kmem_cache_free`), logging (`printk`),
   bounded read I/O as `SAFE-WITH-VALID-PTR` (`kernel_read`, `filp_open`/`filp_close`), plus the DENY/
   BEHAVIOR-CHANGING exemplars above as negative anchors. Each seed entry must be operator-disasm-verifiable.

**Definition of done for U2:** `call-safety-classify` emits evidence-backed tiers; the seed whitelist is
vetted and operator-disasm-verifiable; the `call` path fails closed for non-whitelisted targets; tests cover
each tier + the refusal + the 3-proven-stay-SAFE / kallsyms_lookup_name-DENY invariants; `py_compile` +
focused suite pass; host-only, no device action, no boot image. After U2, a tool runbook is the only
remaining optional remainder before the REPL epic can fully close. (U3 was promoted from this backlog note
to the active charter at the top of this section once U2 was operator-verified DONE.)

**STATUS (2026-06-29 U2 host pass) — disasm-backed call-safety classifier + fail-closed call gate landed.**
`a90_repl.py` now has `call-safety-classify`, which C1-resolves identity first and emits evidence-backed
tiers with static signals: early arg-register derefs, BL targets, context-sensitive lock/IRQ/sleep calls,
leaf/non-leaf shape, direct-BL xrefs, printk variadic-prologue matching, return-kind metadata, and optional
`aarch64-linux-gnu-objdump` excerpts. Seed whitelist is DENY-by-default and currently classifies
`__kmalloc`/`kfree` as `SAFE-SCALAR`; `printk` (real `0xffffff800813adfc`, not the `0x813d8cc` twin),
`ksize`, `kmem_cache_alloc`, `kmem_cache_free`, `kernel_read`, `filp_open`, and `filp_close` as
`SAFE-WITH-VALID-PTR`; `commit_creds`, `prepare_kernel_cred`, `set_memory_x`, and
`call_usermodehelper_exec` as `BEHAVIOR-CHANGING`; and `kallsyms_lookup_name` as `DENY`.
The `call` path now runs `require_call_safety_for_call()` before any serial transport action: non-whitelisted
targets fail closed, `SAFE-WITH-VALID-PTR` requires declared `@...` pointer args, BEHAVIOR/CONTEXT require
the exact non-DENY override token, and `DENY` cannot be overridden. Host-only: no device action, no live
call-proof, no boot-image change. Validation: `py_compile` pass, `tests.test_a90_repl` **57/57 PASS**,
focused companion suite **24/24 PASS**, and CLI classifier smoke with objdump evidence PASS. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_U2_CALL_SAFETY_CLASSIFIER_2026-06-29.md`.

> ### 🛑 OPERATOR GATE-2 (2026-06-29) — U2 architecture is GOOD; ONE seed mis-tier to fix: `kfree` is NOT `SAFE-SCALAR`
>
> Independently verified: gate fails closed correctly (DENY non-overridable even with token; SAFE-WITH-VALID-PTR
> demands declared ptr args; non-SAFE refused before transport), and the invariants hold (printk/kernel_read=
> valid-ptr, __kmalloc=SAFE-SCALAR ✓ genuinely scalar — `cmp x0,#0x2000` + arithmetic, no deref; kallsyms_lookup_name=
> DENY; creds-family=BEHAVIOR-CHANGING). **But `kfree` is mis-tiered `SAFE-SCALAR` ⇒ `auto_call_allowed=True`, so the
> gate would wave through `call kfree <arbitrary scalar>` — and `kfree(garbage_nonzero)` faults** (it computes a wild
> `page*` via `virt_to_head_page` and derefs it). That is exactly the "address-known, call-unsafe" footgun U2 exists to
> stop. **Root cause (structural, not just this seed):** the SAFE-SCALAR static check ("no `[xN]` arg deref before the
> first `bl`") UNDER-APPROXIMATES pointer consumption. `kfree` saves `x0→x22`, NULL-checks, then derefs a *derived*
> page pointer after a `bl` — so the early-deref signal is empty and the wrong tier survives. **Fix (host-only, no
> device):**
> 1. Reseed `kfree` as `SAFE-WITH-VALID-PTR` with `required_valid_pointer_args={0: "kmalloc-object-or-NULL"}` (the
>    v2a2 round-trip still works — the caller supplies the real kmalloc'd pointer; this just forces that acknowledgment).
> 2. Strengthen `SAFE-SCALAR` to a POSITIVE proof: an arg register may be SAFE-SCALAR only if it never flows into a
>    memory-base use ANYWHERE in the reachable body (track `mov xN→xM` taint + loads/stores whose base traces to an
>    arg reg + args passed into a deref-ing callee), not merely "no `[xN]` before first `bl`." Equivalently: a
>    pointer-typed arg is NEVER SAFE-SCALAR. Re-audit every current SAFE-SCALAR seed under the stronger rule
>    (`__kmalloc` should remain SAFE-SCALAR; `kfree` should drop out).
> 3. Add a regression test: `call kfree <scalar>` without a declared valid pointer must be REFUSED by the gate.
>
> Keep everything else as-is. Host-only; do not touch the device; this is a classifier-precision fix, not a redesign.

**STATUS (2026-06-29 U2 Gate-2 correction host pass) — `kfree` reseeded; SAFE-SCALAR strengthened.**
`kfree` is now `SAFE-WITH-VALID-PTR` with required `x0=kmalloc-object-or-NULL`; `call kfree 0x1234`
is refused before any serial transport action. SAFE-SCALAR now requires a positive objdump-taint proof:
x0..x7 aliases are tracked through moves/arithmetic/selects, BL clears caller-clobbered aliases, and any
arg-derived register used as a memory base invalidates SAFE-SCALAR. Re-audit result: `__kmalloc` remains
`SAFE-SCALAR` with `0` arg-taint memory-base uses; `kfree` has `43` arg-taint memory-base uses and drops
out of SAFE-SCALAR. Seed inventory now counts `SAFE-SCALAR=1`, `SAFE-WITH-VALID-PTR=8`,
`BEHAVIOR-CHANGING=4`, `DENY=1`. Host-only: no device action, no live call-proof, no boot-image change.
Validation: `py_compile` pass, `tests.test_a90_repl` **59/59 PASS**, focused companion suite
**24/24 PASS**, and CLI classifier smoke PASS. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_U2_GATE2_KFREE_RESEED_2026-06-29.md`.

**Guardrails:** host-only static analysis; exploit-free framing (this is CALL-SAFETY, not weaponization);
`commit_creds`/`prepare_kernel_cred`/etc. stay RECON-classified, never chained; keep raw runtime pointers
out of commits; scoped `git add`; fails-twice on the same approach → STOP + report. Operator (Claude)
Gate-2's each commit by independently disasm-verifying a sample of the classifications against the v2321
image; the loop owns host build + tests + commits and does NOT touch the device for U2.

## ✅ CLOSED — Tier-2 Runtime Kernel REPL (v1-repl → v2a → v2c), DONE at v2c-C2E (2026-06-29)

**CLOSED 2026-06-29 by operator Gate-2 sign-off (commit `fd76bc9a`).** The flash-once named runtime
kernel REPL is live-proven (v2a1 named peek/call, v2a2 kmalloc poke round-trip via recovered exports,
v2c C1 fail-closed + U1 CLI), and the kallsyms ground-truth map is settled with **three independent
oracles byte-identical** (extractor padding-fix map ≡ relocated-`__ksymtab` C2E oracle ≡ `vmlinux-to-elf`,
SHA `9e6a1d6f…`); all four anchors disasm-verified, C1 fail-closed enforced/strengthened, device on clean
v2321. U2 ergonomics + a tool runbook remain the only optional remainders (re-charter if wanted). Loop is
HALTED at this boundary awaiting the next epic. Full sign-off detail + DoD evidence is in the v2c STATUS
blocks below.

<!-- Former heading (epic was ACTIVE 2026-06-28 → 2026-06-29): -->
### (history) DELEGATED: Tier-2 Runtime Kernel REPL (v1-repl → v2a)

**Operator-chartered 2026-06-28. This is the single active epic.** Build a **flash-once runtime kernel
REPL** so future EL1/kernel experiments need NO reflash per step: after one flash, drive runtime kernel
**observe + execute** over the bridge. Exploit-free (NO RKP bypass) — it only reads memory, writes
**non-protected** data, and `call`s **real** kernel function entries; RKP does memory-protection only
(not behavioral monitoring), so this is not RKP-detectable. We already hold EL1 (we flash our own
kernel); this is operator RECON/debug tooling on an owned, bootloader-unlocked, patched device. Full
design + decisions: `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_DESIGN_2026-06-28.md`.

**Already proven (reuse, do not re-derive):**
- Tier-2 `.text` patch boots under RKP; Stage C proved a **new direct `bl printk`** executes under
  RKP_CFP. Plain `printk(fmt,...)` is at vaddr `0xffffff800813d8cc` (NOT `printk_emit` 0x...813c814).
- **`poke`** primitive LIVE-PROVEN (`build_kernel_runtime_poke_agent.py`): hijacks the corrected
  `force_no_nap_store` at file-off `0x8A73C8` / vaddr `0xffffff80089273b4`, room **212 B (53 instr)**,
  magic-guarded (MAGIC `0xA90C0DE5DEADBEEF`), protocol `{u64 magic,u64 addr,u64 val,u64 width}`.
- **`slide`** primitive LIVE-PROVEN (`build_kernel_tier2_repl_v1_slide.py`): a `.text` stub does
  `adr x1,.` + `bl printk` → host derives `slide = runtime_pc − (entry_vaddr + 40)`. This supersedes
  the heavy V2216 perf/codeword method; `/proc/kallsyms` is `%p`-hashed even at `kptr_restrict=0`.
- Reusable host helpers in `build_kernel_tier2_stage_c_direct_bl_printk.py`: `encode_bl`,
  `encode_adr_x0`, `kernel_vaddr`, `locate_printk_variadic_wrapper`, `recompute_boot_id`,
  `parse_boot_layout`, JOPP_MAGIC `0x00BE7BAD`, ROPP eor `0xCA1103D0`/epilogue `0xCA11021E`.

**🚨 BRICK LESSON (binding):** the first poke build bricked because its offset (`0x8A7920`) pointed at
`gpu_busy_percentage_show` (read at boot), and the `eor`+RKP-magic asserts passed because **every ROPP
function** begins that way. **Verify every patch target by its exact function FINGERPRINT (disasm
semantics), never by the generic ROPP shape.** The corrected `force_no_nap_store` asserts: word at
`0x8A73C8` == `0xD10103FF` (`sub sp,#0x40`), next word == `0xCA1103D0` (`eor`), magic at `0x8A73C4`,
next magic at `0x8A749C`. `force_no_nap` is never read/written at boot or by the periodic monitor.

**v1-repl = ✅ DONE / LIVE-PROVEN** (`build_kernel_tier2_repl_v1_repl.py`, image `b846ae9f…`, commit
f44b34c8). One flash-once 212 B stub in `force_no_nap_store`: magic guard + op byte → `op0 slide`,
`op1 peek(addr,len≤8)`, `op2 poke(addr,val,width)`, `op3 call(target,x0..x7)`, plain-`printk` output,
ROPP frame preserving x16+x17, `blr` to JOPP entries. Codex host-built + self-Gate-2'd; operator
re-Gate-2'd (all 48 instrs) + live-validated all four ops + rolled back V2321 `fail=0`: slide leaked,
`peek` of the stub entry returned its own first qword, `call printk(fmt,0xCAFE1234)` printed
`A90Rcafe1234` and captured return `0xc`, `op2` NULL-poke faulted (store path executes). Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V1_REPL_2026-06-28.md`.

**v2a0 = ✅ DONE (kallsyms extractor FIXED, commit ab480fea).** Root cause of the old "garbage map"
(and the original brick-target confusion) was a missing **ULEB128 compressed-name length** decode in
`a90_stock_kallsyms_extract.py` → names drifted off addresses mid-table. Fixed + operator-disasm-verified
(two independent anchors agree: `printk @ 0xffffff800813d8cc`, `force_no_nap_store @ 0xffffff80089273b4`).
Semantic locators are now cross-checks, not overrides.

**v2a1 = ✅ DONE / LIVE-PROVEN (`a90_repl.py` + `tests/test_a90_repl.py`).** Host driver that drives the
**existing** v1-repl image (no new flash) **by symbol name**: `runtime(sym) = link(System.map) + slide`.
Live selftest PASS (then rolled back V2321 `fail=0`): named `peek` of `force_no_nap_store` and `__kmalloc`
== static-image qwords; named `call printk(format, sentinel)` echoed the sentinel. Transport lessons pinned:
USB-ACM bridge is not the console UART (printk only via the ring); busybox `dmesg` is read-and-CLEAR so the
driver writes + reads `A90R` in ONE `run` shell bounded by `tail -n N`; **`call kallsyms_lookup_name` is
unsafe** (faulted/rebooted live, recoverable) → the call proof uses the v1-repl-proven `printk` target.
Report: `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A1_NAMED_DRIVER_2026-06-29.md`.

### ✅ v2a2 = DONE / LIVE-PROVEN — recovered-export `__kmalloc` poke round-trip

**Objective:** prove a real allocator-backed `poke`→`peek` round-trip over the **EXISTING** v1-repl image
(NO new boot image, NO new kernel `.text`). Extend the host driver `a90_repl.py` (commit 5b8aebe6) with a
`poke-roundtrip` subcommand + a faithful unit test, run it live, roll back to v2321, commit. This **reuses
the already-LIVE-PROVEN ops** op1 peek / op2 poke / op3 call — do **not** write any new kernel stub.
The original map-derived allocator addresses in the charter below were later proven to be drifted labels;
the live pass uses the v2a2R' recovered export addresses documented in the current status block.

**Reuse (do not re-derive):**
- Driver `workspace/public/src/scripts/revalidation/a90_repl.py`. Op buffer: `+0x00` u64 magic
  `0xA90C0DE5DEADBEEF`, `+0x08` u8 op, `+0x10` arg0, `+0x18` arg1, `+0x20` arg2, `+0x28..0x50` call x2..x7.
  op1 `peek(addr,len≤8)`, op2 `poke(addr,val,width 4|8)`, op3 `call(target,x0..x7)` → stub prints
  `A90R<x0_return>`. **Reuse `op_sh()`** (write+read in ONE `run` shell, bounded `tail -n N`).
- Live image to flash (already validated): `boot_linux_tier2_repl_v1_repl.img` SHA256
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`.
- System.map: regenerate with `a90_stock_kallsyms_extract.py` against the v2321 image into a PRIVATE dir
  (`workspace/private/runs/kernel/v2a2-*`). Link addrs: `__kmalloc=0xffffff80082724bc`,
  `kfree=0xffffff800827276c`; runtime = link + slide(op0).

**🚨 LIVE TRANSPORT FACTS (pinned from v2a1 live — obey or you WILL burn runs):**
- USB-ACM bridge is **not** the kernel console UART → `printk` only readable via the log ring
  (`dmesg`/`/dev/kmsg`), never inline on serial.
- busybox `dmesg` here is **read-and-CLEAR** (consuming) → write the cmd buffer + read the `A90R` line in
  ONE `run /bin/busybox sh -c` invocation bounded by `tail -n N` (`op_sh()` already does this); do NOT
  split write/read into separate invocations (the ring drains between them).
- Binary writes: `printf '\NNN…' > /sys/class/kgsl/kgsl-3d0/force_no_nap` (octal) via native-init `run`
  (argv `["run","/bin/busybox","sh","-c",SH]`; a90ctl auto cmdv1x-encodes path/space args).
- **DO NOT call `kallsyms_lookup_name`** — it faulted/rebooted the device live (recoverable). Resolve every
  symbol from System.map, never from a runtime lookup call.

**Sequence (run_selftest-style; `panic_on_oops=0` during, restore `1` in `finally`):**
1. `slide = op0`.
2. `ptr = call __kmalloc(size=0x1000, gfp=GFP_KERNEL)` (target=`__kmalloc`+slide, x0=size, x1=gfp). Derive
   `GFP_KERNEL` EXACTLY from kernel headers under `workspace/private/inputs/.../include/linux/gfp.h` for
   this 4.14 tree: `___GFP_IO|___GFP_FS|___GFP_DIRECT_RECLAIM|___GFP_KSWAPD_RECLAIM` =
   `0x40|0x80|0x400000|0x1000000` = **`0x14000c0`**. Do not use the stale `0x6c0` note from older planning.
   The returned x0 is a runtime heap pointer — **keep it OUT of commits** (private evidence only).
   **Sanity-gate:** `ptr` must be non-null and in the kernel lowmem VA range; if not, STOP (do not poke a
   bad ptr).
3. `poke(ptr, sentinelA=0xA90F00D1CAFE0001, width=8)`; `peek(ptr,8)` MUST == sentinelA.
4. `poke(ptr, sentinelB=0x1122334455667788, width=8)`; `peek(ptr,8)` MUST == sentinelB (proves the store
   landed, not a stale read). Optional: 32-bit `width=4` poke+peek to exercise that path.
5. `call kfree(ptr)` (target=`kfree`+slide, x0=ptr). A valid kmalloc'd ptr is a clean slab free; if it
   faults the device reboots into the v1-repl boot partition (recoverable). Do **not** peek-after-free.
6. Restore `panic_on_oops=1`. Roll back to clean v2321 (`native_init_flash --from-native --expect-sha256
   ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`). Final `selftest fail=0`.

**Gate-2 + tests:** extend `tests/test_a90_repl.py` with a faithful-stub poke-roundtrip integration test
(fake transport modelling a kmalloc'd scratch dict: op2 writes it, op1 reads it back, op3 `__kmalloc`
returns a fake ptr, `kfree` no-ops). `py_compile`; run the full `tests/` suite. **No new kernel image is
built** (assert this; confirm the v1-repl image SHA is unchanged) → no operator disasm needed for this unit.

Then v2b (`show`-buf bulk `peek` for arbitrary length) stays BLOCKED until a safe fixed scratch anchor +
cleanup protocol are proven; the printk-loop stays the shipping default. Guardrails below + the v2a2-specific
note: `poke` writes ONLY to the `__kmalloc`'d buffer we own (non-protected) and we `kfree` it.

**STATUS (2026-06-29 v2a2 host/source gate) — host driver was source-ready before live ABI discovery.** Codex extended
`a90_repl.py` with the `poke-roundtrip` subcommand and added a faithful fake-transport integration test
that models `__kmalloc` returning an owned lowmem pointer, two qword `poke`/`peek` checks, the optional
low-32-bit poke path, and `kfree`. The driver keeps raw slide/runtime pointer values out of stdout and
committed artifacts; `--evidence-dir` writes them only to private evidence. It regenerates the v2a2 private
System.map under `workspace/private/runs/kernel/v2a2-repl-poke-roundtrip/`; anchors match `printk`,
`kgsl_pwrctrl_force_no_nap_store`, `__kmalloc`, and `kfree`. Host validation: `py_compile` PASS,
`tests.test_a90_repl` **28/28 PASS**, v1-repl image SHA remains `b846ae9f…`, v2321 rollback SHA remains
`ca978551…`. Full repo `unittest discover` was attempted and remains non-green in this checkout
(`3679` tests, `217` failures, `56` errors, `3` skipped) due to existing private artifact dependencies
outside v2a2; focused v2a2 tests pass. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2_POKE_ROUNDTRIP_SOURCE_2026-06-29.md`.

**STATUS (2026-06-29 v2a2 LIVE attempt) — blocked by allocator ABI mismatch, device recovered.** Codex
flashed the unchanged v1-repl image (`b846ae9f...`) through `native_init_flash.py`; post-flash
`version/status/selftest` were clean. The first `poke-roundtrip` run timed out around the
`panic_on_oops=0` transaction but the device stayed reachable. The retry reached `op3 call __kmalloc`
and faulted before any `poke`: dmesg showed fault address `0x1048`, and static boot-image disassembly
of the recovered `__kmalloc @ 0xffffff80082724bc` shows `ldr x23, [x0,#72]` before the first helper call.
Calling that entry as `__kmalloc(size=0x1000, GFP_KERNEL)` therefore dereferences `0x1000+0x48`, exactly
the observed fault. v2a1 named-peek proved name→address mapping, not allocator call ABI. `panic_on_oops`
was restored to `1`; rollback to clean v2321 via the checked helper passed with readback SHA
`ca978551...`, `version/status` passed, final `selftest verbose` was `pass=11 warn=1 fail=0`, and a direct
check showed `panic_on_oops=1`. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2_LIVE_ALLOCATOR_ABI_BLOCKED_2026-06-29.md`.
`a90_repl.py` now has a host-side guard that rejects scalar allocator candidates whose entry
dereferences `x0` before the first `BL`; the current direct `__kmalloc` path is blocked before live.
**Do not rerun direct `call __kmalloc(size, GFP_KERNEL)` without a newly validated target.**

> ### 🛑 OPERATOR GATE-2 CORRECTION (2026-06-29) — the "allocator ABI" root-cause is a MISDIAGNOSIS; the MAP is mislabeled
>
> Operator re-Gate-2'd the live blocker by disasm + xref analysis of the v2321/v1-repl boot image and
> found the loop chased the wrong problem. **There is no allocator-ABI problem. The kallsyms map (post-v2a0)
> still MISLABELS the mm/slab region**, so `call __kmalloc` called the WRONG function.
> - **Ironclad evidence — bl xref counts:** map `__kmalloc @0xffffff80082724bc`, `kfree @0xffffff800827276c`,
>   and `kmalloc_slab @0xffffff800823eaa4` each have **0 direct `bl` xrefs** in the whole image. `__kmalloc`
>   and especially `kfree` are among the most-called kernel functions (hundreds–thousands of call sites);
>   **0 xrefs is impossible if those addresses were really those functions.**
> - **Disasm corroboration:** the function at the map's `__kmalloc` saves 4 args and does `ldr x23,[x0,#72]`
>   before its first `BL` — impossible for `__kmalloc(size_t size, gfp_t flags)` (source `slab.h:358`; `x0` is
>   a scalar size, never dereferenced). The map's `kmalloc_slab`/`__kmalloc_track_caller` entries likewise do
>   not match their signatures. By contrast `printk @0x813d8cc` and the kgsl/`force_no_nap` region remain
>   correct → this is a **localized residual name↔address decode drift in the mm/slab region**, not a global map break.
> - **Why v2a1 didn't catch it:** v2a1's named-`peek` only checks bytes-at-address; it never tests that the
>   name maps to the right *function*. The first real test of `__kmalloc`'s identity was this `call`, which faulted.
>
> **Consequences / redirect (supersedes v2a2R "ABI locator" and v2a2H "new helper image"):**
> - **Do NOT build a new helper image (v2a2H) and do NOT keep auditing allocator "ABIs."** Both target a
>   non-existent problem. `__kmalloc(size, GFP_KERNEL)` *is* callable via the existing v1-repl `op3` scalar
>   path — once the CORRECT address is used.
> - **New v2a2R' (host-only): get GROUND-TRUTH allocator addresses.** Either (a) decode the **PREL32
>   `__ksymtab` export table** (`struct kernel_symbol { s32 value_offset; s32 name_offset; }`; value =
>   `&entry + value_offset`) to read the real `__kmalloc`/`kfree` addresses, and/or (b) re-audit
>   `a90_stock_kallsyms_extract.py` for the residual mm-region drift. Then **disasm-verify** the chosen
>   `__kmalloc`: `x0` = scalar size (no pre-`BL` `x0` deref), high `bl`-xref count, reaches the slab path; and
>   `kfree`: `x0` = pointer, frees cleanly. Only then re-enable the existing-image `poke-roundtrip`.
> - The loop's `x0`-deref guard is a fine generic safety net — **keep it**, but it must not be read as
>   "allocators are unsafe to call." The guard correctly rejected a *mislabeled* entry.
> - This stays host-only (no device, no collision); operator will cross-check the recovered addresses by
>   independent disasm before any live rerun. Device remains clean on v2321.

**STATUS (2026-06-29 v2a2R' host-only recovery) — ground-truth allocator addresses recovered.**
`a90_repl.py allocator-export-recovery` now bypasses the mislabeled mm/slab System.map entries by finding
exact export strings in the static v1-repl boot image, following aligned qword references to those strings,
and selecting the nearby JOPP text entries with no pre-first-`BL` `x0` dereference and high direct-`BL`
xref counts. Required recovered link addresses:
`__kmalloc=0xffffff800826ae34` (`1765` direct `bl` xrefs) and
`kfree=0xffffff800826b354` (`10596` direct `bl` xrefs). Optional slab helpers also recover:
`kmalloc_order=0xffffff8008238444`, `kmalloc_order_trace=0xffffff8008238484`. The mapped
`__ksymtab___kmalloc`/`__ksymtab_kfree` qwords read as `0x0`, proving those map labels are drifted too.
Focused validation: `tests.test_a90_repl` **31/31 PASS**. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2RP_ALLOCATOR_EXPORT_RECOVERY_2026-06-29.md`.

**STATUS (2026-06-29 v2a2 recovered-export LIVE PASS) — allocator-backed poke round-trip is live-proven.**
Host objdump cross-check confirmed recovered `__kmalloc=0xffffff800826ae34` preserves scalar `x0` until
the first `BL` and recovered `kfree=0xffffff800826b354` preserves `x0` as the pointer argument; direct
`bl` xrefs are `1765` and `10596`. Flashed exact v1-repl image
`b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65` via `native_init_flash.py`; pushed
image SHA and boot readback SHA matched, and post-flash health was clean after one serial-fragment retry.
Ran `a90_repl.py poke-roundtrip --use-recovered-allocator-exports`: decision
`a90-repl-v2a2-poke-roundtrip-pass`; checks `kmalloc-owned-buffer`, sentinel A/B qword `poke`→`peek`,
low32 `poke`→`peek`, and `kfree-owned-buffer` all passed. `panic_on_oops` was restored to `1`; candidate
selftest was `pass=11 warn=1 fail=0`; rollback to v2321
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb` had matching readback SHA; final
`version/status/selftest` were clean (`fail=0`) and final `panic_on_oops=1`. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2_LIVE_RECOVERED_EXPORTS_2026-06-29.md`.
**v2a is now complete.** v2b (`show`-buf bulk `peek` for arbitrary length) remains blocked/optional until
a fixed scratch anchor + cleanup protocol is proven; otherwise the v1-repl printk loop is the shipping
bulk path.

### ✅ v2a2R (HOST-ONLY) — allocator ABI locator / safe owned-buffer plan

Find a replacement for the invalid direct `__kmalloc` plan before any more live `poke-roundtrip` attempts.
This unit is host-only by default: inspect the v1-repl boot image + regenerated System.map, classify candidate
owned-buffer APIs by static ABI, and require a report/test update before live. Acceptable outcomes:

1. a JOPP entry whose first basic block matches a scalar allocator ABI and returns a sane writable pointer,
   paired with a validated free path; or
2. a revised small helper design that returns/owns a scratch buffer under the normal boot-image flash gates.

No live device command is needed unless the static ABI gate produces a concrete, bounded candidate. If the
only viable path is a new helper image, build and Gate-2 it as a new V-iteration; do not mutate the existing
v1-repl image in place. Keep raw runtime pointers and slides out of committed artifacts.

**STATUS (2026-06-29 v2a2R host-only audit) — existing scalar allocator path saturated.** `a90_repl.py`
now exposes `allocator-audit`, which checks 13 plausible owned-buffer allocator/free pairs in the v1-repl
boot image for JOPP shape, pre-helper-call `x0` dereferences, leaf/global-return thunks, and known
pointer-argument wrappers. Result:
`a90-repl-v2a2r-allocator-abi-audit-no-live-ready-scalar`; every candidate is rejected and
`live_ready_candidates=[]`. Focused validation is now `tests.test_a90_repl` **29/29 PASS**. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2A2R_ALLOCATOR_ABI_AUDIT_2026-06-29.md`.
**Superseded by the correction above:** this audit rejected mislabeled map entries, not real allocator
functions. Keep the `x0`-deref guard as a safety net, but use v2a2R' export recovery before any live
allocator-backed round-trip.

### ⛔ SUPERSEDED by the OPERATOR GATE-2 CORRECTION above — v2a2H (new owned-scratch helper image) is NOT the next unit

**The real NEXT BOUNDED UNIT was v2a2R' (host-only), followed by the recovered-export live rerun; both are
now complete.** Do not build a new helper image to work around a map-mislabel. The block below is retained
only as the (now-rejected) ABI-workaround design.

### ~~v2a2H (HOST-ONLY SOURCE GATE) — explicit owned-scratch helper~~ (rejected; see correction)

Design and source-gate a replacement for the invalid direct allocator path. The target is still the original
v2a2 semantic proof: a non-protected owned buffer where `op2 poke` lands, `op1 peek` reads back the value,
and cleanup/rollback leaves the device clean. The implementation must avoid guessing allocator ABIs from
exported names.

Preferred shape:
- Build a new bounded helper image only if the source design can prove an explicit owned scratch location or
  call target with a known ABI. Do not mutate the existing v1-repl image in place.
- Keep all writes recoverable under the boot-partition-only flash gates; no forbidden partitions, no RKP
  bypass, no protected `.text`/rodata/page-table/cred target.
- Gate-2 before flash: diff only `{boot-id, intended helper body}`, disassemble helper body, preserve JOPP/
  ROPP expectations, and prove the scratch target is writable non-protected state.
- Live step, when reached: flash exact SHA, health-check, run `poke` -> `peek` -> cleanup, restore
  `panic_on_oops=1`, rollback to v2321, final `selftest fail=0`.

**Guardrails (hard, RECON / exploit-free):** NO RKP bypass, NO write to RKP-protected memory
(`.text`/rodata/page-tables/cred), NO RWX, NO `ret`/`blr`/CFP-site patch, NO grooming/UAF/spray,
preserve `x17`. Magic-guard every hijacked handler. Boot-partition-only via `native_init_flash.py`
with pinned + readback SHA; rollback target v2321
(`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`). Gate-2 **disasm** every candidate
(objdump the patched body; confirm diff is contained to `{boot-id@0x240, target-function body}`, magics
preserved) BEFORE flashing. Keep raw runtime pointers / the per-boot slide OUT of committed reports.
Fails-twice → STOP and report; anti-churn in force. Report each unit to `docs/reports/`.

**Operator/loop split:** the operator (Claude) did the corrected `poke` agent, `slide`, v1-repl Gate-2,
the v2a0 kallsyms fix, and the v2a1 named host driver (all live-validated, since only the operator can
reach the device bridge + commit). Codex builds host-only/RE units; the operator runs all live flash/
validate + commits. v2a1 was operator-direct (small + protocol-tight). v2a is complete; the next frontier
is the v2c productization epic below.

### ▶ ACTIVE NEXT EPIC = v2c — Tier-2 Kernel REPL PRODUCTIZATION (correctness + stability + usability)

> ### 🛑 OPERATOR GATE-2 CORRECTION (2026-06-29) — the C2A "map-audit" is UNSOUND; do NOT rewrite the kallsyms decoder off it
>
> Operator independently checked the C2A audit (commit 62047499). **Its "`map_match=0`, `12479` mismatches"
> is a TOOL ARTIFACT, not evidence the map is broadly wrong.** The audit treats `export-recovery` as ground
> truth, but recovery is a **noisy heuristic** (it scans for any qword ref to a `"<name>\0"` string), so it
> produces FALSE candidates:
> - **`printk`**: the map address `0xffffff800813d8cc` is CORRECT (operator-verified 3 ways: two independent
>   extractor anchors, `stage_c.locate_printk_variadic_wrapper`, and a LIVE `call printk(fmt,sentinel)` in
>   v2a1 that printed the sentinel — a wrong address could not have). But recovery returns **two candidates,
>   `0x813adfc` and `0x81b8eac`, NEITHER equal to the real printk**, and buckets it "ambiguous". So
>   `map≠recovery` here means **recovery is wrong, not the map**.
> - Recovery happened to be right for `__kmalloc`/`kfree` (single clean candidate, operator-verified by xref
>   + signature), so those map entries ARE wrong — but that does NOT generalize. **The map is verified-CORRECT
>   for printk and the kgsl region, and verified-WRONG only for the mm/slab allocator region.**
>
> **Steer:**
> - **Do NOT rewrite/`root-fix` `a90_stock_kallsyms_extract.py` based on the current audit** (there is an
>   uncommitted extractor edit in flight — drop or gate it). A decoder rewrite driven by a buggy "whole map is
>   drifted" signal can break the regions that are currently correct.
> - **C2 must FIX THE AUDIT (make the oracle sound) BEFORE drawing any map conclusion.** Ground truth must
>   come from a *real* `__ksymtab` parse (locate the actual `__ksymtab`/`__ksymtab_strings` section bounds and
>   walk its entries), not heuristic string-ref scanning; and/or only flag a symbol "map-wrong" when the
>   recovered candidate is HIGH-CONFIDENCE (single, JOPP entry, plausible `bl`-xref count, signature-sane) AND
>   the map address is *independently* shown wrong (e.g. its own xref count is implausibly low / signature
>   mismatched). **Validate the fixed audit against known anchors: `printk` MUST come out `map-match`
>   (truth==map==`0x813d8cc`); `__kmalloc`/`kfree` MUST come out `map-mismatch` with the recovered address as
>   truth.** Only after the audit reproduces those three is its drift count trustworthy.
> - **We are not in danger:** C1 fail-closed already protects `call`/`poke` (a wrong map address cannot be
>   dispatched). So C2 is about *restoring general trust + a correct drift map*, with no safety pressure — take
>   the time to make the oracle correct rather than chase a 12k-mismatch artifact.

**Operator-chartered 2026-06-29 after a maturity review.** v2a proved the capability (flash-once
`slide`/`peek`/`poke`/`call`, named/recovered-address resolution, owned-buffer round-trip), but it is an
operator-driven proof, not yet a *trustworthy, stable, usable tool*. v2c hardens it into one. **No new boot
image is needed** for most of this — it drives the existing v1-repl image (`b846ae9f…`); only bounded live
re-validation flashes, with v2321 rollback. Work the sub-units in priority order; each is a bounded
host-only unit unless it explicitly needs a live check. Report each to `docs/reports/`.

**The #1 gap is CORRECTNESS (the kallsyms map silently mislabels regions — this is what bit v2a2).**

- **C1 — fail-closed resolution (highest priority).** Make the `System.map` *untrusted by default* for any
  `call`/`poke` target. Add `resolve_verified(symbol) -> (link_vaddr, verified: bool, method, evidence)`
  and REQUIRE `verified=True` before any `call`/`poke`; refuse otherwise. Verification ladder:
  (1) export-recovery ground truth (already built, exported symbols only); (2) disasm-signature + `bl`-xref
  sanity (e.g. a callable function entry must be JOPP-shaped, have a plausible xref count, and not match a
  known-bad shape); (3) optional agreement with the map. `peek` of read-only data may use the map but must
  surface `verified=False` in output. This structurally prevents the v2a2 mislabel-call class.

  **STATUS (2026-06-29 v2c C1 host pass) — fail-closed resolution is implemented host-side.**
  `a90_repl.py` now has `VerifiedResolution` + `resolve_verified(...)`: call/poke targets must be verified
  before dispatch, `__kmalloc`/`kfree` resolve through the v2a2R' recovered-export ground truth, `printk`
  is accepted only by map-address disasm/xref sanity, `kallsyms_lookup_name` is explicitly blocked as a
  known unsafe live call, and read-only `peek` surfaces `verified=False`. `run_selftest` verifies its call
  target before transport; `run_poke_roundtrip` verifies allocator call/free targets and rejects stale
  map-derived allocator overrides before any REPL op. Validation: `py_compile` pass,
  `tests.test_a90_repl` **36/36 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C1_FAIL_CLOSED_RESOLUTION_2026-06-29.md`.
- **C2 — map-trust audit + decoder root-fix.** Build a host-only `map-audit` that cross-checks the kallsyms
  `System.map` against export-recovery ground truth for *all* exported symbols, emits a drift report (which
  symbols/address-regions disagree), and quantifies map accuracy. Then use that to find and fix the residual
  `a90_stock_kallsyms_extract.py` name↔address drift in the mm/slab (and any other drifted) region — the
  v2a0 ULEB128 fix did not cover it. Goal: a map that is either correct everywhere or annotated with its
  trustworthy regions. (C2 can be staged: audit first, decoder fix as a follow-up.)

  **STATUS (2026-06-29 v2c C2A host pass) — map-audit landed; decoder fix/fencing remains open.**
  `a90_repl.py map-audit` now builds a one-pass export-name/ref index from the raw v1-repl image and compares
  recovered export-record values against `System.map`. On the current v2a1 map it audits `12628` exported
  symbols: `12490` recoverable candidates, `12479` map mismatches, `11` ambiguous, `138` missing recovery,
  and `0` map matches. Focus rows preserve the v2a2 allocator proof (`__kmalloc` recovered
  `0xffffff800826ae34`, `kfree` recovered `0xffffff800826b354`) and show `printk` as ambiguous rather than
  auto-promoted. Validation: `py_compile` pass, `tests.test_a90_repl` **37/37 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C2_MAP_AUDIT_2026-06-29.md`.
  **Next C2 step:** fix the kallsyms decoder root cause or explicitly fence trusted map regions; do not treat
  this System.map as globally trustworthy.

  **STATUS (2026-06-29 v2c C2C host pass) — C2A audit oracle corrected/fenced.**
  `a90_repl.py map-audit` now defaults to a high-confidence anchor oracle instead of the broad C2A
  string-ref heuristic. It validates the operator-required anchors: `printk` is `map-match`
  (`truth==map==0xffffff800813d8cc`) via the Stage-C plain-`printk` semantic signature plus C1
  `resolve_verified(...)`; `__kmalloc` is `map-mismatch` (`truth=0xffffff800826ae34`,
  map `0xffffff80082724bc`) with a single JOPP/no-`x0`-deref/high-xref export candidate and independent
  map refutation (`0` direct `bl` xrefs plus pre-call `x0` deref); `kfree` is `map-mismatch`
  (`truth=0xffffff800826b354`, map `0xffffff800827276c`) with the same evidence shape. The old whole-map
  scanner remains only as `run_string_ref_map_audit(...)` and must not drive a decoder rewrite. Validation:
  `py_compile` pass, `tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract` **56/56 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C2C_HIGH_CONFIDENCE_MAP_AUDIT_2026-06-29.md`.
  Remaining C2 work: a real `__ksymtab`/`__ksymtab_strings` section parse, or equivalent grounded oracle,
  before claiming any broad drift count or changing `a90_stock_kallsyms_extract.py`.

  **STATUS (2026-06-29 v2c C2D host pass) — noisy C2A ksymtab source fenced.**
  The local Samsung kernel source for this image defines `struct kernel_symbol` as the 16-byte absolute
  pair `{ unsigned long value; const char *name; }`, not the PREL32 `{ s32 value_offset; s32 name_offset; }`
  ABI. `a90_repl.py ksymtab-audit` now checks that source ABI directly and separates it from the large
  24-byte `0x403, pointer, aux` table that C2A had accidentally treated as broad truth. For `printk`,
  `__kmalloc`, and `kfree`, no parseable 16-byte source-ABI ksymtab row exists in the raw v1-repl image;
  all string-ref candidates are inside the single noisy 24-byte `0x403` table (`162763` records). This
  explicitly fences the broad drift count and blocks any decoder rewrite from that table. Validation:
  `py_compile` pass, CLI `ksymtab-audit` pass, `tests.test_a90_repl` +
  `tests.test_a90_stock_kallsyms_extract` **62/62 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C2D_KSYMTAB_ABI_AUDIT_2026-06-29.md`.
  C2 status: known allocator drift is fixed by C1 verified resolution and C2C anchors; broad map drift is
  intentionally **not claimed** unless a future independent oracle is added.
- **S1 — transport stability.** Harden the live op path against the observed serial-fragment noise
  (`ATAT` / missing `A90P1 END`): per-op bounded re-read/realign retry, robust ring read (busybox `dmesg`
  is read-and-clear; keep the single-shell `op_sh` + `tail -n N`), and clear classification of
  transient-noise vs real failure. Ops should self-heal a noisy read instead of aborting the run.

  **STATUS (2026-06-29 v2c S1A host pass) — safe-op retry + transient-noise classification landed.**
  `a90_repl.py` now raises `ReplTransientNoiseError` for no-`A90R` capture, retries replay-safe ops
  (`slide`/`peek`) with bounded `--safe-op-retries`, uses configured `--dmesg-tail`, and exposes
  `--retry-delay-sec`. Generic `call` is deliberately not replayed by default to avoid duplicate
  `__kmalloc`/`kfree` side effects; `run_selftest` marks its `printk` proof call explicitly replay-safe.
  Validation: `py_compile` pass, `tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract`
  **56/56 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_S1A_SAFE_OP_RETRY_2026-06-29.md`.
  Remaining S1 gate: live serial-fragment validation and any extra non-replay re-read/realign handling if
  unsafe ops still see fragment loss.

  **STATUS (2026-06-29 v2c S1 live gate) — sequential REPL live path passed; parallel host commands still noisy.**
  Flashed the unchanged v1-repl image via `native_init_flash.py` with pinned SHA/readback SHA, then ran the
  v2c REPL selftest plus U1 `read`/`call`/owned-`poke` commands with `--safe-op-retries 3`; all passed and
  the device stayed healthy. A deliberately accidental parallel final `a90ctl version`/`selftest` check hit
  host-side serial-lock / `ATAT` fragment noise, then sequential retry passed immediately. Treat this as a
  caller-concurrency constraint: live bridge validation commands remain single-client/sequential unless a
  later transport layer adds explicit concurrency support. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_U1_S1_LIVE_VALIDATION_2026-06-29.md`.
- **U1 — usability surface.** Add first-class CLI: `call SYMBOL [args…]` (verified targets only),
  `read SYMBOL|ADDR --len N` = **arbitrary-length bulk peek by host-side looping op1 in 8-byte chunks**
  (this unblocks the old "v2b" need with NO new image — looping the existing `peek` op suffices for reads),
  and `poke` to a verified-owned buffer. Keep raw runtime pointers/slide out of stdout (private evidence
  only), as today.

  **STATUS (2026-06-29 v2c U1 host pass) — first-class CLI surface landed.**
  `a90_repl.py` now exposes `read`, `call`, and `poke` subcommands on the existing v1-repl image. `read`
  accepts a symbol/link-vaddr/runtime-vaddr and performs arbitrary-length host-side looped op1 reads in
  1..8 byte chunks, reporting SHA256/static-image-match while keeping raw bytes and runtime addresses in
  private evidence only. `call` requires C1 `resolve_verified(..., purpose="call")`, supports private
  runtime-pointer tokens like `@repl_format`/`@symbol`, and rejects unverified symbols before transport; args
  and returns are redacted from stdout. `poke` is owned-buffer-only: verified `__kmalloc` → poke fresh buffer
  → peek verify → verified `kfree`, with no arbitrary-address poke path.
  Validation: `py_compile` pass, CLI `--help` smoke checks pass, `tests.test_a90_repl` +
  `tests.test_a90_stock_kallsyms_extract` **61/61 PASS**. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_U1_CLI_SURFACE_2026-06-29.md`.

  **STATUS (2026-06-29 v2c U1 live pass + rollback clean) — CLI surface is device-proven.**
  Live run over the existing v1-repl image passed: `read kgsl_pwrctrl_force_no_nap_store --len 20`
  reported `chunk_count=3`, `static_image_match=true`, and SHA256
  `5642494b8364c16a197612eba47d416916d4059ae03f5a46a8aeeb285f5184c9`; `call printk @repl_format
  0xa90ca11 --replay-safe` used verified `printk`, private evidence confirmed sentinel echo + stub return;
  `poke --width 8 0xaabbccddeeff0011` allocated a verified `__kmalloc` buffer, matched poke→peek, and
  freed via verified `kfree`. Rolled back to v2321 (`ca978551...`) via the checked flash helper; final
  `version` was `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)` and final `selftest verbose`
  was `pass=11 warn=1 fail=0`. Report:
  `docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_U1_S1_LIVE_VALIDATION_2026-06-29.md`.
- **U2 (optional/stretch).** Small ergonomics: a session that fetches the slide once and reuses it; a
  `--json` machine surface; a short operator runbook for the tool in `docs/operations/`.

**Definition of done for v2c:** named `call`/`poke` cannot target an unverified address (fail-closed);
a map-audit report exists and the known mm/slab drift is fixed or explicitly fenced; arbitrary-length
`read` works; the live op path survives serial-fragment noise without aborting; one bounded live
re-validation passes and rolls back to v2321 `fail=0`; raw pointers/slide never leave private evidence.

**STATUS (2026-06-29) — v2c core DoD DONE.** C1 fail-closed resolution, C2C/C2D map-audit fencing,
U1 CLI `read`/`call`/owned-`poke`, S1 sequential live validation, and rollback-to-v2321 `fail=0` are all
landed and reported. U2 remains optional/stretch only; any future broad map drift claim still requires a
new independent oracle and must not come from the noisy 24-byte `0x403` table.

### ▶ NEXT UNIT = v2c-C2E — real `__ksymtab` ground-truth oracle + authoritative drift map (+ kallsyms decoder root-fix decision)

**Operator-chartered 2026-06-29.** This closes the one real remaining correctness gap: the kallsyms
`System.map` is mislabeled in unknown regions (mm/slab proven), and today only C1 fail-closed + per-symbol
export-recovery protect us. C2E builds a *sound, at-scale* ground-truth oracle and produces an authoritative
map-drift report, then decides whether a decoder root-fix is warranted. **Host-only** until a bounded live
re-validation is explicitly needed; drives the existing v1-repl image; no new boot image.

**Hard lessons to obey (do NOT repeat):**
- The C2A string-ref scanner is UNSOUND (noisy; printk → false candidates `0x813adfc`/`0x81b8eac`, missing
  the real `0x813d8cc`). **Do NOT use name-string-ref heuristics as ground truth.** They stay non-authoritative.
- A correct oracle MUST reproduce the operator anchors or it is wrong: `printk=0xffffff800813d8cc`,
  `force_no_nap_store=0xffffff80089273b4`, `__kmalloc=0xffffff800826ae34` (`cmp x0,#0x2000`, 1765 `bl` xrefs),
  `kfree=0xffffff800826b354` (10596 xrefs). Gate the oracle on these before trusting any drift count.

**Steps:**
1. **Structural `__ksymtab` parse (the sound oracle).** Locate the real export tables by STRUCTURE, not
   names: find the contiguous run of fixed-stride entries where every "name" field points into one
   contiguous `__ksymtab_strings`-like ASCII region and every "value" field resolves to a `.text` JOPP
   function entry (`u32(entry-4)==0x00be7bad`). Determine the exact entry layout empirically (old-style
   `{unsigned long value; const char *name}` vs PREL32 `{s32 value_off; s32 name_off}` vs the observed
   24-byte/`0x403`-stride variant) by which layout makes ALL anchors resolve correctly. Also try to bound it
   via `__start___ksymtab`/`__stop___ksymtab` if those map symbols land in a trustworthy region. Output: an
   authoritative `{addr → exported-name}` table that reproduces every anchor.
2. **Authoritative drift report.** Cross-check that table against `System.map` for all exported symbols;
   emit real match/mismatch counts + the mismatched address-regions. (This is the *trustworthy* version of
   the C2A audit; it must show `printk=match`, `__kmalloc`/`kfree=mismatch`.) Make `run_map_audit` (or a new
   `ksymtab-audit`) use this oracle for exported symbols.
3. **Localize the kallsyms decoder divergence.** Using the ksymtab ground truth, find the exact symbol /
   table position where `a90_stock_kallsyms_extract.py` first pairs a name with the wrong address in the
   mm/slab region (the v2a0 ULEB128 fix covered names-length but something else drifts here). Diagnose the
   root cause (e.g. an offsets-table padding/alignment or ABSOLUTE_PERCPU edge) WITHOUT guessing.
4. **Decoder root-fix DECISION (gated).** Only fix `a90_stock_kallsyms_extract.py` if step 3 yields a
   precise, low-risk cause AND the regenerated map reproduces ALL anchors with **zero regression** on the
   currently-correct regions (printk/kgsl). Operator will independently disasm-verify the regenerated map
   before any reliance. If the cause is not cleanly isolable, DO NOT rewrite the decoder — instead publish a
   trust-region map (which `System.map` regions are ksymtab-confirmed) and keep C1 fail-closed as the
   safety net. Non-exported (static) symbols remain map-only and stay `verified=false` for `call`/`poke`.

**Definition of done for C2E:** a structural `__ksymtab` oracle that reproduces all four anchors; an
authoritative drift report (real counts, `printk=match`/`__kmalloc`+`kfree=mismatch`); the decoder
divergence localized with a root cause; and either a regression-free decoder fix (operator-disasm-verified)
or an explicit, documented decision to keep map-as-is + trust-region fencing. C1 fail-closed stays enforced
throughout. Guardrails unchanged below; keep raw pointers/slide out of commits; fails-twice → STOP + report.
After C2E, U2 ergonomics + a tool runbook are the only optional remainders, then the REPL epic can close.

**STATUS (2026-06-29 v2c C2E host pass) — relocated `__ksymtab` oracle + trust-region decision landed.**
`a90_repl.py ksymtab-ground-truth` reconstructs zeroed 16-byte source `__ksymtab` rows from the 24-byte
`0x403` relocation table by structure (`target+0=value`, `target+8=name`) and selects high-density export
runs. It emits `12518` authoritative exported rows over target range
`0xffffff800a562d60..0xffffff800a594270`. Against current v2a1 `System.map`, the real drift report is
`0` matches / `12518` mismatches / `0` missing. Against the previous C2B padding-fix candidate map, the same
oracle gives `12514` matches / `4` mismatches, validating the 95-zero-u32 padding root-cause at scale while
leaving residual semantic/local-symbol conflicts. Anchors: `__kmalloc=0xffffff800826ae34` and
`kfree=0xffffff800826b354` match relocated ksymtab; `kgsl_pwrctrl_force_no_nap_store=0xffffff80089273b4`
is non-exported and stays a semantic map anchor; `printk=0xffffff800813d8cc` is the live-call semantic
anchor while the export relocation row points at `0xffffff800813adfc`, so the conflict is explicit rather
than hidden. Decoder decision: **do not rewrite/promote `a90_stock_kallsyms_extract.py` in this unit**; keep
map-as-is plus relocated-ksymtab trust-region fencing until the padding fix and semantic exceptions receive
operator disasm verification. Validation: `py_compile` pass, CLI `ksymtab-ground-truth` pass,
`tests.test_a90_repl` + `tests.test_a90_stock_kallsyms_extract` **63/63 PASS**. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_C2E_KSYMTAB_GROUND_TRUTH_ORACLE_2026-06-29.md`.

> ### ✅ OPERATOR GATE-2 (2026-06-29) — C2E oracle is RIGHT; C2B padding fix is VINDICATED; promote it (gated). My earlier C2A-revert conclusion was partly wrong.
>
> Operator independently verified the C2E result and a regenerated C2B map. **The relocated-`__ksymtab`
> oracle is correct, and the current `System.map` really is broadly drifted for exported symbols — my
> earlier "map is mostly right, only mm/slab wrong" was based on a FALSE printk confirmation.**
> - **printk:** `0xffffff800813d8cc` (current map + signature override) and `0xffffff800813adfc` (oracle
>   export row) have **byte-identical variadic prologues** (both are printk-twins), but xref counts settle it:
>   `0x813d8cc` has **14** `bl` xrefs, `0x813adfc` has **44694**. **The real `printk` is `0x813adfc`** (the
>   most-called function in the kernel). The v2a1 live `call printk` "worked" only because it hit a
>   functionally-equivalent twin — that was a false positive, not proof the map address was right.
> - **C2B is a precise, real root-cause and is regression-free.** I regenerated the map with C2B applied
>   (`padding_before_relative_base = 380 = 95×4`, skipping the zero-u32 pad before `kallsyms_relative_base`):
>   `__kmalloc → 0xffffff800826ae34` ✓, `kfree → 0xffffff800826b354` ✓ (both were WRONG in the current map),
>   while `kgsl_pwrctrl_force_no_nap_store → 0xffffff80089273b4` ✓ and `num_pwrlevels_show → 0xffffff80089262dc`
>   ✓ are PRESERVED (no kgsl regression — C2B's early-return guard handles that). This matches the oracle
>   `12514/12518`. **My earlier instruction to revert C2B was the mistake; the loop was right to keep it and
>   build C2E to settle it.**
>
> **Re-authorized direction (supersedes the "do not promote / map-as-is" decision above):**
> 1. **Promote the C2B padding fix** into `a90_stock_kallsyms_extract.py` (re-apply commit 4ba3c52c's
>    `padding_before_relative_base` logic + the kgsl early-return guard). Operator has disasm-verified the
>    four anchors on the regenerated map; gate stands only on the loop reproducing them in-tree.
> 2. **Fix the printk-twin bug (separate from C2B).** `locate_printk_variadic_wrapper` /
>    `apply_printk_signature_decode` currently pick the 14-xref twin `0x813d8cc`; there are ≥2 identical-
>    prologue variadic functions, so the locator must **disambiguate by `bl`-xref count** (the real `printk`
>    is the highest-xref one, `0x813adfc`). After this, the regenerated map's `printk` must be `0x813adfc`
>    and the C2E drift vs the oracle should approach `~12518/12518`. (Note: the live-proven v1-repl IMAGE
>    still calls the twin `0x813d8cc` — that is functionally fine and need NOT be rebuilt; only the
>    host-side map/locator needs the real address.)
> 3. **Re-run the C2E drift report on the promoted map** and confirm: all four anchors correct, printk now
>    `0x813adfc`, near-total oracle agreement, and a fenced residual list (any remaining mismatches are
>    non-exported/local or genuine semantic exceptions, not decode drift). C1 fail-closed stays enforced.
> 4. Operator will independently re-disasm-verify the promoted in-tree map (anchors + a sample of newly-
>    corrected exports) before it is trusted for anything beyond C1-gated use. Guardrails unchanged; this is
>    host-only (no device); keep raw pointers/slide out of commits.
> 5. **FOLLOW-UP (host-only, recommended) — cross-validate against `vmlinux-to-elf`.** Web research
>    (2026-06-29) confirms every bug we hit is a *documented, known* class, and a mature reference tool
>    already handles them: `vmlinux-to-elf` (github.com/marin-m/vmlinux-to-elf, also bkerler fork) recovers a
>    System.map from a raw arm64 `Image` and explicitly handles (a) the variable kallsyms table
>    alignment/padding (our 380-byte `relative_base` pad) and (b) the ksymtab relocation gotcha
>    (pre-4.19 arm64 uses 16-byte `{value,name}` + **24-byte `R_AARCH64_RELATIVE` (`0x403`) RELA** records;
>    the unrelocated section reads as zeros — exactly why our C2E oracle reconstructs from the relocations).
>    Run `vmlinux-to-elf` on the v2321 image as an INDEPENDENT THIRD oracle and require three-way agreement
>    (promoted extractor map ≡ C2E ksymtab-relocation oracle ≡ `vmlinux-to-elf`) on the four anchors + a
>    sample of corrected exports before declaring the map ground-truth. If `vmlinux-to-elf` disagrees, treat
>    that as a STOP-and-investigate signal, not a silent override. (It is a host-only Python tool — vendor it
>    privately if used; do not add a network/runtime dependency to the build.) Refs: kallsyms BASE_RELATIVE
>    `addr = kallsyms_relative_base + (u32)offset` (LWN 673381); ksymtab PREL32/RELA relative refs
>    (LWN 758337). This is a *confidence* step; C1 fail-closed already gates safety regardless.

**STATUS (2026-06-29 v2c Gate-2 host pass) — C2B padding fix promoted; printk twin fixed by BL-xref.**
`a90_stock_kallsyms_extract.py` now skips the `380`-byte zero padding before `kallsyms_relative_base` and
keeps the C2B KGSL early-return guard, so regenerated map anchors are
`printk=0xffffff800813adfc`, `__kmalloc=0xffffff800826ae34`, `kfree=0xffffff800826b354`,
`kgsl_pwrctrl_force_no_nap_store=0xffffff80089273b4`, and
`kgsl_pwrctrl_num_pwrlevels_show=0xffffff80089262dc`. `locate_printk_variadic_wrapper` now selects the
variadic-body candidate with the maximum direct `bl` xref count (`44694`), eliminating the lower-xref
`0xffffff800813d8cc` twin false positive. C1 `resolve_verified(printk)` now resolves through export/xref
ground truth. C2E recheck against the regenerated private promoted map is `12515` matches / `3` mismatches /
`0` missing over `12518` relocated export rows; residuals are `ehci_reset`,
`iio_read_channel_ext_info`, and `iio_write_channel_ext_info`, fenced for operator disasm review. Host-only:
no device action, no boot image change. Validation: `py_compile` pass, focused unittest set **71/71 PASS**,
CLI extractor pass, CLI `ksymtab-ground-truth` pass. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_GATE2_C2B_KALLSYMS_PROMOTION_2026-06-29.md`.

**STATUS (2026-06-29 v2c third-oracle host pass) — `vmlinux-to-elf` independently confirms the promoted
map.** Private `vmlinux-to-elf` clone at commit `19683fb95b29cd31362d49e6f48ab8368f96cbdf` was installed
under `workspace/private/inputs/external_tools/kernel/vmlinux-to-elf` only. `kallsyms-finder` on
`boot_linux_v2321_usb_clean_identity_rodata.img` emitted `147295` symbols and found the same structural
layout: token table `0x02103100`, token index `0x02103500`, markers `0x02101f00`, names `0x01f10700`,
`kallsyms_num_syms` `0x01f10600`, relocation table `0x2699618..0x2a532b8` (`162780` records), and
`kallsyms_offsets` `0x01e80700`. Its output map SHA256 is
`9e6a1d6f322344e3d6fced7e6d29a254e1516cc5163bad8595388a9d0d02ec3a`, byte-identical to the promoted
extractor map. C2E three-way compare gives identical promoted and `vmlinux-to-elf` counts:
`12515` matches / `3` mismatches / `0` missing, with the same fenced residuals
`ehci_reset`, `iio_read_channel_ext_info`, and `iio_write_channel_ext_info`. Four core anchors plus
`kallsyms_lookup_name` agree (`printk=0xffffff800813adfc`, `__kmalloc=0xffffff800826ae34`,
`kfree=0xffffff800826b354`, `force_no_nap_store=0xffffff80089273b4`,
`num_pwrlevels_show=0xffffff80089262dc`, `kallsyms_lookup_name=0xffffff800817cfa4`). Host-only: no device
action, no boot image change. Report:
`docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_V2C_VMLINUX_TO_ELF_THIRD_ORACLE_2026-06-29.md`.

> ### ✅ OPERATOR GATE-2 SIGN-OFF (2026-06-29) — C2E/v2c DONE; operator disasm-review CLEARED; **loop HALTS at this boundary**
>
> I independently regenerated the promoted extractor map from the v2321 image and it is **byte-identical**
> to both the promoted map and the `vmlinux-to-elf` output (all SHA `9e6a1d6f322344e3d6fced7e6d29a254e1516cc5163bad8595388a9d0d02ec3a`).
> I disasm-confirmed all four anchors by independent BL-xref count: `printk=0xffffff800813adfc` (44694 xrefs —
> NOT the 14-xref twin `0x813d8cc`), `__kmalloc=0xffffff800826ae34` (1765), `kfree=0xffffff800826b354` (10596),
> `kgsl_pwrctrl_force_no_nap_store=0xffffff80089273b4` (preserved, no kgsl regression), `num_pwrlevels_show=0xffffff80089262dc`.
> The `locate_printk_variadic_wrapper` disambiguation is **structural** (max direct-BL xref + tie guard + min-1000
> threshold), not a hardcoded address; it independently returns `0x813adfc`. C1 fail-closed is **strengthened**
> (printk now requires export/xref ground truth; the old hardcoded drifted-map expectation table is removed).
> The 3 residuals (`ehci_reset`, `iio_read_channel_ext_info`, `iio_write_channel_ext_info`) are **identical across
> all three oracles** → a semantic export-alias artifact on the oracle side, not decoder drift; correctly fenced.
> **C2E DoD met and exceeded (third independent oracle byte-identical).** The Runtime Kernel REPL side-quest is at
> its epic boundary: the loop should **HALT here and not invent further units.** Operator will re-charter the next
> direction (close the REPL epic / U2 ergonomics + tool runbook / a new epic). Do not flash, do not start a new
> kallsyms/decoder unit, do not touch the device.

**Guardrails: unchanged from below** (RECON / exploit-free; no RKP bypass; no protected-memory write; no
RWX; preserve `x17`; boot-partition-only flashes with pinned+readback SHA; rollback v2321; fails-twice →
STOP + report; keep raw runtime pointers/slide out of commits; scoped `git add`). Operator cross-checks any
recovered/verified address by independent disasm before a live rerun and steers via GOAL.md; the loop owns
host build + (sandbox-disabled) live + commits. v2b "show-buf" bulk peek is **superseded** by U1's
host-side looped `read` (no new image required); only build a new image if a future unit needs new on-device
behavior.

## 🟣 DONE — DELEGATED OPERATOR SIDE-QUEST — Tier-2 Stage C: confirm a patched-in direct `bl` executes under RKP_CFP

**DONE (2026-06-28) — direct `bl printk` executed under RKP_CFP and the device was rolled back to
clean v2321.** Stage A/B had already proven Tier-2 kernel `.text` patching boots and takes runtime
effect. Stage C now proves the last gate: a **new direct `bl` call** injected into reachable kernel
`.text` can execute under RKP_CFP. The loop first tried the wrong variadic target
(`printk_emit(..., fmt, ...)` at `0xffffff800813c814`), which rebooted without marker; it recovered,
rolled back to clean v2321, then corrected the locator to the plain `printk(fmt, ...)` wrapper at
`0xffffff800813d8cc`. The passing candidate SHA was
`21c567f0d3ebaa9d6caaa7c6310463fe7aa1710e5ca6a077305c36e489f16b8a`; `panic_on_oops=0` was set,
reading `/sys/class/kgsl/kgsl-3d0/num_pwrlevels` returned cleanly, and dmesg showed
`A90TIER2C`. `panic_on_oops=1` was restored, then v2321 rollback readback SHA matched
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`; final `version` and
`selftest` were clean (`pass=11 warn=1 fail=0`). Reports:
`docs/reports/KERNEL_SECURITY_TIER2_STAGE_C_DIRECT_BL_PRINTK_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/KERNEL_SECURITY_TIER2_STAGE_C_DIRECT_BL_PRINTK_LIVE_2026-06-28.md`. RECON guardrails
held: no grooming/UAF/EL1, no `ret`/`blr`/CFP-site patches, `x17` preserved, boot-partition-only
via `native_init_flash.py`.

## ✅ CLOSED — SoftAP server-endgame (S0→S4), DONE at V3344 (history below; loop re-chartered to the Runtime Kernel REPL side-quest above)

**STATUS (2026-06-27 S0 charter/recon) — V3336 pivots the loop from GPU to SoftAP and freezes the
target shape before any AP-mode mutation.** The goal is not the existing phone/router lab where A90 is
a Wi-Fi client. The endgame is A90 as the self-contained lab appliance: A90 brings up a WPA2 SoftAP,
serves a bounded local transfer endpoint, accepts a client connection, proves download/upload SHA
integrity, cleans up, and leaves `selftest fail=0`. Existing `wifi status/scan/connect/dhcp/ping`,
profile, autoconnect, `wifiinv`, and `wififeas` are useful prerequisites but are client-mode surfaces;
`docs/operations/A90_PHONE_WIFI_TRANSFER_SERVER.md` remains a client-mode data-path harness, not the
SoftAP target. Current public allowlist policy has `allow_server_exposure=false`, so the next unit must
make AP/server exposure explicit, bounded, private, and cleanup-backed before any daemon start. Report:
`docs/reports/NATIVE_INIT_V3336_SOFTAP_SERVER_ENDGAME_CHARTER_2026-06-27.md`.

**STATUS (2026-06-27 S1 read-only live inventory) — V3337 ran the no-flash, no-mutation SoftAP
inventory gate on resident `0.11.103`.** Bridge was healthy; `version/status/selftest` were clean
(`selftest pass=12 warn=1 fail=0`). `wifi status` reported `wlan0_present=0`, no carrier/IP/default
route, standalone supplicant executable present but stopped, ctrl socket missing, autoconnect disabled,
and `secret_values_logged=0`. `wifiinv` reported `net_total=9`, `wlan_like=0`, `rfkill_wifi=0`,
`module_matches=0`, `paths=9/26`, `file_matches=16`; current visible matches are system Wi-Fi rc/config
surfaces, not a native-visible hostapd AP stack. `wififeas` returned `decision=no-go` with gates
`wlan=no rfkill=no module=no candidates=yes`: do not enable Wi-Fi/AP mode from native-init with current
evidence. A read-only BusyBox applet inventory did show transfer/server helpers (`httpd`, `nc`,
`udhcpd`, `wget`, `sha256sum`) are present, so the server half is not the immediate blocker. **S1 is
DONE; next bounded source unit is S2 status/plan/dry-run plumbing that reports this no-go cleanly and
does not start hostapd/AP mode.** Report:
`docs/reports/NATIVE_INIT_V3337_SOFTAP_S1_READONLY_INVENTORY_LIVE_2026-06-27.md`.

**STATUS (2026-06-27 S2 status/plan source) — V3338 added the first `wifi softap` command surface
without AP bring-up.** `wifi softap`, `wifi softap status`, `wifi softap plan`, `wifi softap prepare
[profile]`, and `wifi softap cleanup` now evaluate `a90_wififeas` and print redaction-friendly
readiness fields, gate counters, plan steps, and explicit `*_attempted=0` fields for config write,
hostapd start, DHCP-server start, listener exposure, interface mode change, and address assignment.
`start_supported=0` and `start_allowed=0` are hard-coded in this S2 source unit while S1 remains
no-go. `prepare` is dry-run/no-op under the current blocker and reports
`softap-prepare-blocked-wlan-gate`; no SSID/PSK config is written. Updated the Wi-Fi lifecycle command
contract and added a focused source test. Host validation: `py_compile`, V3338 source test `5/5`, AArch64
`a90_wifi.c` object compile with `-Wall -Wextra -Werror`, and `git diff --check`. No boot image was
built, no flash was run, and no live Wi-Fi action was attempted. Report:
`docs/reports/NATIVE_INIT_V3338_SOFTAP_S2_STATUS_PLAN_SOURCE_2026-06-27.md`.

**STATUS (2026-06-27 S2 flash/live validation) — V3339 built, flashed, and live-validated the
SoftAP status/plan surface on-device.** Built
`boot_linux_v3339_softap_s2_status_plan.img`
(`sha256=5f23c579ddbcac75cf9859685f638cad3371e2ebf228af8e441c6863fa25858b`) from V3335,
flashed only through `native_init_flash.py`, and booted `A90 Linux init 0.11.104
(v3339-softap-s2-status-plan)` with boot readback SHA match and post-flash selftest
`pass=12 warn=1 fail=0`. After stopping the auto HUD/menu gate, live commands
`wifi softap status`, `wifi softap plan`, and `wifi softap prepare` all returned rc `0`.
They reported `wififeas.decision=no-go`, `gates.wlan=0`, `gates.rfkill=0`,
`gates.module=0`, `gates.candidates=1`, `start_supported=0`, `start_allowed=0`,
and all config/AP/server mutation fields as `0`; `prepare` reported
`prepare_dry_run=1` and `decision=softap-prepare-blocked-wlan-gate`. Follow-up
selftest stayed `pass=12 warn=1 fail=0`. **S2 is DONE; S3 AP bring-up remains blocked
until a future read-only lower-surface unit proves WLAN/AP prerequisites.** Reports:
`docs/reports/NATIVE_INIT_V3339_SOFTAP_S2_STATUS_PLAN_SOURCE_BUILD_2026-06-27.md` and
`docs/reports/NATIVE_INIT_V3339_SOFTAP_S2_STATUS_PLAN_LIVE_2026-06-27.md`.

**STATUS (2026-06-28 S3 lower WLAN/AP gate split) — V3340 proved the blocker is lineage-specific
and narrowed the remaining gate.** Reflashed the existing V3339 SoftAP S2 image and confirmed it still
has no `wlan0`: `wifi softap status` stayed `softap-status-blocked-wlan-gate`, `wifi scan` failed at
link-up with `errno=19`, and a lower probe showed `wlan0_present=0`. Then flashed the Wi-Fi-proven
V2237 fallback: after its normal long helper window, the helper exited cleanly with
`supervisor_result=wlan0-ready` and `wlan0_present=1`; standalone `wpa_supplicant` and BusyBox `udhcpd`
were present, and no station/AP/server worker was running. However, no `iw` binary was visible, so
the required `AP iftype settable` add/delete proof is still unverified. The device was rolled back to
V2321 with post-rollback selftest `pass=11 warn=1 fail=0`. **S3 remains blocked, but the next unit is now
specific: port the V2237 WLAN bring-up route into the current SoftAP baseline and add a tiny cfg80211/
nl80211 AP-iftype probe or stage a minimal private `iw` equivalent, before any `mode=2` AP start.**
Report: `docs/reports/NATIVE_INIT_V3340_SOFTAP_S3_LOWER_WLAN_SPLIT_LIVE_2026-06-28.md`.

**STATUS (2026-06-28 S3 iftype-probe source/build + live miss) — V3341 added the bounded
`wifi softap iftype-probe [timeout_ms]` AP-iftype add/delete proof, but live validation stopped before
AP-iftype because `wlan0` still did not surface.** Built
`boot_linux_v3341_softap_s3_iftype_probe.img`
(`sha256=a0fe07b1f347a2212d375067c442b163b7e6cd68cb7a605ab5dce4c87082c7af`), flashed it through
`native_init_flash.py`, booted `A90 Linux init 0.11.105 (v3341-softap-s3-iftype-probe)`, and kept
health clean (`selftest pass=12 warn=1 fail=0`). The probe preserved the no-start contract
(`config_write_attempted=0`, `wpa_supplicant_mode2_start_attempted=0`, `dhcp_server_start_attempted=0`,
`listener_start_attempted=0`, `address_assign_attempted=0`, `server_exposure_attempted=0`) but timed
out at `wlan0_wait_rc=-110`, `wlan0_present=0`, so `ap_iftype_add_attempted=0`. Helper evidence showed
the post-FW_READY `boot_wlan` trigger succeeded and the kernel requested
`wlan/qca_cld/WCNSS_qcom_cfg.ini`, but the QCACLD firmware_class feeder repeatedly returned
`source_errno=2` and `fed=0`; the remaining blocker is now the read-only Android vendor firmware source
visibility/feed path, not the AP-iftype command itself. **Next bounded unit = V3342: restore a safe
read-only source route for `/vendor/firmware/wlan/qca_cld/*`, then rerun the same iftype probe before
any `wpa_supplicant mode=2` AP start.** Reports:
`docs/reports/NATIVE_INIT_V3341_SOFTAP_S3_IFTYPE_PROBE_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/NATIVE_INIT_V3341_SOFTAP_S3_IFTYPE_PROBE_LIVE_2026-06-28.md`.

**STATUS (2026-06-28 S3 firmware-source + lower AP gate pass) — V3342 restored the safe
read-only QCACLD firmware source route and proved the lower WLAN/AP gate.** Built
`boot_linux_v3342_softap_s3_fwsource_iftype_probe.img`
(`sha256=836f76249d578ef42e25a2d0c7b43cc3ef1d8db9efe5dabc6ee5ce13b10e5502`), flashed it through
`native_init_flash.py`, booted `A90 Linux init 0.11.106 (v3342-softap-s3-fwsource-iftype-probe)`,
and kept health clean (`selftest pass=12 warn=1 fail=0`). Helper evidence showed
`source_policy=qcacld-fwsource-mounted-vendor-first`, `WCNSS_qcom_cfg.ini` `source_rc=0`, `fed=1`,
and `wlan0_present=1`. The bounded `wifi softap iftype-probe 220000` then passed:
`wlan0_wait_rc=0`, `wlan0_present=1`, `sta_supplicant.stoppable=1`, `ap_iftype_add_rc=0`,
`ap_iftype_iface_created=1`, `ap_iftype_cleanup_ok=1`, and `decision=softap-iftype-probe-pass`.
The no-start contract held (`config_write_attempted=0`, `wpa_supplicant_mode2_start_attempted=0`,
`dhcp_server_start_attempted=0`, `listener_start_attempted=0`, `address_assign_attempted=0`,
`server_exposure_attempted=0`). **Next bounded unit = V3343: start a private, cleanup-backed
`wpa_supplicant mode=2` SoftAP on 2.4GHz ch 1/6/11 with BusyBox `udhcpd`, no WAN/NAT/default-route
export, then run `softap cleanup` and keep `selftest fail=0`.** Reports:
`docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_LIVE_2026-06-28.md`.

**STATUS (2026-06-28 S3 mode=2 AP bring-up + cleanup pass) — V3343 started and cleaned up the first
bounded SoftAP service.** Built `boot_linux_v3343_softap_s3_mode2_bringup.img`
(`sha256=601e27287a1b695c326a99e27522e36bb5afde629da5b30b024f7f59ec5068e7`), flashed it through
`native_init_flash.py`, booted `A90 Linux init 0.11.107 (v3343-softap-s3-mode2-bringup)`, and kept
health clean (`selftest pass=12 warn=1 fail=0`). The final `wifi softap start 6` passed with
`wlan0_wait_rc=0`, `wlan0_present=1`, `sta_supplicant.stoppable=1`, `ap_iftype_add_rc=0`,
`ap_iftype_iface_created=1`, `softap_ctrl_reply_category=pong`, `softap.ctrl_status.field.mode=AP`,
`softap.ctrl_status.field.wpa_state=COMPLETED`, `wpa_supplicant_mode2_start_attempted=1`,
`dhcp_server_start_attempted=1`, `dhcp_server_alive=1`, and `decision=softap-start-pass`.
Safety fields stayed closed (`hostapd_start_attempted=0`, `listener_start_attempted=0`,
`server_exposure_attempted=0`, `wan_nat_attempted=0`, `nat_attempted=0`,
`default_route_export_attempted=0`, `dhcp_router_option_exported=0`, `ssid_psk_logged=0`). The final
`wifi softap cleanup` passed (`cleanup.rc=0`, `final_supplicant_count=0`, `final_udhcpd_count=0`,
`final_iface_present=0`, `decision=softap-cleanup-pass`) and post-cleanup selftest stayed
`pass=12 warn=1 fail=0`. **Next bounded unit = S4: start the local transfer server on the private AP,
have a client join, prove HTTP download/raw upload SHA integrity, stop server/AP, and keep public output
redacted.** Reports:
`docs/reports/NATIVE_INIT_V3343_SOFTAP_S3_MODE2_BRINGUP_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/NATIVE_INIT_V3343_SOFTAP_S3_MODE2_BRINGUP_LIVE_2026-06-28.md`.

**STATUS (2026-06-28 S4 private transfer server proof) — V3344 closed the SoftAP server-endgame
with a client transfer integrity proof.** Built `boot_linux_v3344_softap_s4_transfer_server.img`
(`sha256=d24fe3fded67d83a1bd87b13f3459bdaec6d588cb947a5231cc08d6c397515a8`), flashed it through
`native_init_flash.py`, booted `A90 Linux init 0.11.108 (v3344-softap-s4-transfer-server)`, and kept
health clean (`selftest pass=12 warn=1 fail=0`). The final `wifi softap transfer-start 6` passed
with `wlan0_present=1`, `sta_supplicant.stoppable=1`, `ap_iftype_add_rc=0`,
`softap.ctrl_status.field.mode=AP`, `softap.ctrl_status.field.wpa_state=COMPLETED`,
`dhcp_server_alive=1`, `httpd_alive=1`, `upload_receiver_alive=1`,
`download_payload_bytes=1048576`, `server_bind_private_ap_only=1`, and
`decision=softap-transfer-start-pass`. A host client joined the private AP using private runtime
credentials; public artifacts do not record SSID/PSK/client identifiers/concrete network addresses.
HTTP download matched SHA256 `0fb3f6622678efe11f84f3bf032031802a8745d9c8a1f834aece10fe6d1bbd62`.
Raw upload matched SHA256 `3cd6eccfa373a28f7a411ef5cbdc3c407ada3eaf2263ef5879531989d9dc4348`
on both host and device, with `upload_result=pass`, `upload_result.bytes=1048576`, and
`upload_result.truncated=0`. `wifi softap cleanup` passed with `cleanup.final_httpd_count=0`,
`cleanup.final_supplicant_count=0`, `cleanup.final_udhcpd_count=0`, `cleanup.final_iface_present=0`,
and post-cleanup selftest stayed `pass=12 warn=1 fail=0`. **S0→S4 is DONE. Next bounded unit =
post-endgame hardening/reporting cleanup only: decide whether to promote a reusable host-side S4
validation helper and remove stale S2/S3 wording from narrow tests/docs.** Reports:
`docs/reports/NATIVE_INIT_V3344_SOFTAP_S4_TRANSFER_SERVER_SOURCE_BUILD_2026-06-28.md` and
`docs/reports/NATIVE_INIT_V3344_SOFTAP_S4_TRANSFER_SERVER_LIVE_2026-06-28.md`.

- **S0 (host-only charter/recon) = DONE.** Inventory current command/docs/source surface, distinguish
  client-mode Wi-Fi from SoftAP/server mode, and write the bounded ladder + safety recipe.
- **S1 (read-only live AP/server inventory) = DONE / NO-GO BELOW WLAN.** Current resident has no
  wlan-like interface, Wi-Fi rfkill, or module evidence; transfer applets exist.
- **S2 (source contract + config materialization) = DONE / LIVE VALIDATED BELOW AP START.** Added an explicit `wifi softap`
  command surface with
  `status`, `plan`, and dry-run config materialization under `/cache/a90-softap/`; generated SSID/PSK
  remain private-only, public output reports hashes/booleans only. While S1 remains no-go, S2 must stop
  at status/plan/prepare and must not start hostapd/AP mode.
- **S3 (bounded AP bring-up) = DONE / LIVE VALIDATED.** V3342 proved `wlan0` present, STA supplicant
  stoppable, and AP iftype add/delete with cleanup. V3343 then configured a private local AP subnet, started
  `wpa_supplicant mode=2` on a 2.4GHz non-DFS channel, started bounded BusyBox `udhcpd`, exposed no
  WAN/NAT/default route/server listener by default, and validated `softap cleanup` worker/interface removal.
- **OPERATOR RECON (2026-06-27, host-verified — answers the S3 "lower WLAN/AP gate" + corrects the daemon
  choice).** SoftAP is NOT non-viable; all three layers already exist on this device (verified host-only
  from the stock `System.map` + staged userland, no device action):
  1. **Driver/SAP = built into the stock kernel** (qcacld), 84 SAP symbols incl. `hdd_hostapd_open`,
     `hdd_softap_register_sta`/`stop_bss`/`sta_deauth`/`set_channel_change`, `wlan_hdd_cfg80211_change_beacon`,
     `__cfg80211_stop_ap`, `sap_fsm`, and even `hdd_softap_inspect_dhcp_packet` (the AP/tether path is real).
     Concurrency policy is present too (`policy_mgr_allow_sap_go_concurrency`, `policy_mgr_add_sap_mandatory_chan`,
     `hdd_set_sap_ht2040_mode`), but the first bring-up should be single-AP after stopping the STA supplicant.
  2. **AP daemon = DO NOT stage hostapd.** The already-proven Ubuntu `wpa_supplicant 2.11` binary in the
     staged `ubuntu-arm64-wpa` runtime is built with `CONFIG_AP` (117 AP strings incl.
     `hostapd_setup_interface_complete_sync`). Run SoftAP via `wpa_supplicant` **`mode=2`**, reusing the exact
     client-mode binary + libs already working — this skips the whole hostapd cross-compile/stage detour.
  3. **DHCP = busybox `udhcpd`** (`CONFIG_UDHCPD=y`, already built in); no dnsmasq needed.
  4. **Pin the first AP to 2.4GHz ch 1/6/11** to avoid the 5GHz DFS CAC path (`sap_fsm_cac_start`) — DFS adds
     radar-CAC delay/complexity that will stall first proof. No WAN/NAT (`allow_server_exposure=false` stays
     frozen). So the S3 "lower gate" read-only unit just needs to confirm wlan0 present + AP iftype settable +
     supplicant stoppable; the driver capability question is already answered YES here.
- **S4 (server-endgame proof) = DONE / LIVE VALIDATED.** V3344 started the local transfer server on
  the AP, had a host client join, proved HTTP download and raw upload SHA integrity, stopped the
  server/AP, and confirmed follow-up `selftest fail=0` while public artifacts redacted SSID/PSK,
  client identifiers, and concrete network addresses.

`native_gpu_compute_c0_reference_v3299.py` encodes and validates the staged A640 compute dispatch envelope against
`/tmp/a90-mesa-gpu-src/`: CS program regs, `CP_LOAD_STATE6` shader/constant/UAV state, `RM6_COMPUTE`, NDRANGE,
`CP_EXEC_CS`, and WFI/readback ordering all match the Mesa computerator/fd6 references; `kern_invocationid.asm` is fixed
to a 32-lane `buf[i] == i` proof. V3300 then materialized that kernel into verified A640 CS shader words with a bounded
host-only full-NIR freedreno tool build under `/tmp/a90-mesa-c1-fullnir-softpipe-v3300` and `ir3-disasm -g FD640`.
The verified C1 shader is 32 dwords / 128 bytes, `instrlen=1`, `constlen=4`, `local_size=32,1,1`,
`sha256=7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a`, and disassembles to
`mov.u32u32 r0.y, r0.x`; `(rpt5)nop`; `stib.b.untyped.1d.u32.1.imm r0.x, r0.y, 0`; `end`. No boot artifact was built
and no flash was run for V3300. V3301 embeds those verified CS words in native-init, adds
`gpu c1-compute-invocationid-probe`, binds one 32-word R32_UINT UAV descriptor, emits `SP_CS_*`, `LOAD_STATE6`
shader/constants/UAV, `RM6_COMPUTE`, and `CP_EXEC_CS`, then gates success on WFI/readback where all `buf[i] == i`.
V3301 source/build validation produced
`workspace/private/inputs/boot_images/boot_linux_v3301_gpu_compute_c1_invocationid_probe.img`
(`sha256=c4128f367a17f2481866142d79942d958ea19fa34528937dece6edf3d04e7dfa`, size 66052096 bytes);
flash/readback verified the exact artifact, booted `0.11.75`, and the live
`gpu c1-compute-invocationid-probe --timeout-ms 5000 --materialize-devnode` run passed:
`readback0=0`, `readback1=1`, `readback31=31`, `expected_match_count=32`, `mismatch_count=0`, `pass=1`,
`total_elapsed_ms=28`. Post-probe selftest stayed `fail=0`, and the bridge capture fault filter found no GPU
fault/hang/page-fault match. V3302 embeds a verified 32-dword FD640 workgroup-id CS shader
(`sha256=9259cd6e225aba4d1e86fb88527494404617b2aaf753c948379ade2edb18a6d1`, asm
`sha256=1f7f223c66a97975e416dce96b0a960933b7fa21b7bf4c6d380b3eb63e31b0d6`) and dispatches
16,384 one-lane workgroups into a 128x128 R32_UINT UAV. V3302 source/build validation produced
`workspace/private/inputs/boot_images/boot_linux_v3302_gpu_compute_c2_pattern_probe.img`
(`sha256=3f437360d9c428548fb1d89dfa90d56091313375c0b04578c45d95021d43af5a`, size 66117632 bytes);
flash/readback verified the exact artifact, booted `0.11.76`, and the live
`gpu c2-compute-pattern-probe --timeout-ms 5000 --materialize-devnode` run passed:
`readback0=0`, `readback1=1`, `readback127=127`, `readback128=128`, `readback4096=4096`,
`readback8192=8192`, `readback16383=16383`, `expected_match_count=16384`, `mismatch_count=0`,
`pass=1`, `total_elapsed_ms=15`. Post-probe selftest stayed `fail=0`, and the bridge capture fault
filter found no GPU fault/hang/page-fault match. V3303 then added `gpu c3-compute-kms-probe`, which
runs the C2 probe, writes a bounded 64KiB UAV snapshot, verifies the snapshot, expands it into the KMS
dumb framebuffer, presents, and holds. V3303 source/build validation produced
`workspace/private/inputs/boot_images/boot_linux_v3303_gpu_compute_c3_kms_probe.img`
(`sha256=0a041e834cedae3b54bea5c1b4fb70b4be133156e8c9317d8f6c30b304c01e20`, size 66117632 bytes);
flash/readback verified the exact artifact and booted `0.11.77`. The live
`gpu c3-compute-kms-probe --timeout-ms 5000 --hold-ms 30000 --materialize-devnode` run passed:
`snapshot_write_bytes=65536`, `snapshot_expected_match_count=16384`, `snapshot_mismatch_count=0`,
`blit_rect=92,752,896,896`, `blit_scale=7`, `present_rc=0`, `result=compute-pattern-presented`,
`hold_elapsed_ms=30000`, `vis.result=compute-pattern-presented-held`, `rc=0`, `duration_ms=30161`.
Post-probe selftest stayed `fail=0`, and the bridge capture fault filter found no GPU
fault/hang/page-fault match. A later 60 s eye-confirm replay attempt was paused before a new proof could be collected
because the host lost the A90 USB gadget (`serial-missing`, no ACM/ADB/NCM after 90 s); no new flash or rollback was
attempted. USB visibility later recovered; resident `0.11.77` health stayed `selftest fail=0`, and the existing V3303
C3 command was replayed with a 60 s hold: `snapshot_expected_match_count=16384`,
`snapshot_mismatch_count=0`, `present_rc=0`, `result=compute-pattern-presented`, `hold_elapsed_ms=60000`,
`vis.result=compute-pattern-presented-held`, `rc=0`, `duration_ms=60041`; post-replay selftest stayed `fail=0`, and
the GPU fault filter had no match. A final replay again returned `0.11.77`, pre/post `selftest fail=0`,
`present_rc=0`, `vis.result=compute-pattern-presented-held`, 60 s hold, and no GPU fault-filter match. The operator
then visually confirmed the expected held pattern on the panel: "무지개 그라데이션과 네모난 격자무늬 프렉탈 같은검 말하는건가? 보인다".
C3 is therefore closed, and the visible compute-demo C0→C3 ladder is DONE + EYE-CONFIRMED. V3304 then pre-staged a
fresh sparse Mesa freedreno reference at `/tmp/a90-mesa-gpu-src` (commit
`6adb0d5e01dca952fcb04b7773ad92b0ab2e132d`) and added `native_gpu_2d_d0_texture_reference_v3304.py`. The D0 recon
passed against `fd6_texture.cc`, `fd6_texture.h`, `fd6_emit.cc`, `fd6_emit.h`, `fd6_program.cc`, `a6xx.xml`,
`adreno_pm4.xml`, and `ir3-cat5.xml`: sampler descriptors are 4 dwords, TEXMEMOBJ descriptors are 16 dwords, FS texture
state is `FD6_GROUP_FS_TEX`, FS sampler load is `CP_LOAD_STATE6_FRAG` + `ST6_SHADER` + `SB6_FS_TEX`, FS TEXMEMOBJ load
is `CP_LOAD_STATE6_FRAG` + `ST6_CONSTANTS` + `SB6_FS_TEX`, `SP_PS_CONFIG` carries `NTEX/NSAMP`, and the non-bindless
cat5 `sam` contract exposes `s#0/t#0`. V3305 then added
`native_gpu_2d_d1_textured_shader_bytes_v3305.py`, using a local libdrm-backed Mesa tool build under
`/tmp/a90-mesa-d1-texture-build-libdrm` to materialize and `ir3-disasm` verify the minimal FD640 textured FS:
`bary.f r0.x, 0, r0.x`; `bary.f r0.y, 1, r0.x`; `sam (f32)(xyzw)r0.z, r0.x, s#0, t#0`; `end`; padded nops.
The shader is 32 dwords / 128 bytes, `instrlen=1`, `constlen=0`, `max_reg=1`, `max_half_reg=-1`,
`num_samp=1`, `num_tex=1`, `sha256=4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3`, and its
sample output register `r0.z` maps to scalar regid 2, matching the existing H3 color-output contract
(`GPU_H3_PS_OUTPUT_REGID=2`, fullregfootprint covers the payload, RGBA8 MRT contract present). V3310 then closed D1 with
`gpu d1-texture-checkerboard-probe`: a 128x128 static checkerboard sampled through the textured FS, linearized, and
verified with a full 128x128 changed readback plus 64/64 bbox-local checker samples. V3311 then closed D2 with
`gpu d2-realframe-texture-probe --preset badapple --frame-index 515`: the device read the SD-cache Bad Apple mono1
A90VSTR1 stream, expanded frame 515 into a 480x360 RGBA8 texture, rendered it into the 128x128 target, and matched all
64 bbox-local source-frame samples (`source_dark_count=86381`, `source_light_count=86419`, output dark/light positive,
`output_other_count=0`). V3312 then implemented D3 video-present plumbing but live validation found two host-visible
contract bugs: the command rejected the report's `--timeout-ms 120000` because the probe still used the 10 s G0 ceiling,
and the forked child returned through the shell/A90P1 completion path before the parent could print summary telemetry.
V3313 fixed both issues (`GPU_D3_VIDEO_MAX_TIMEOUT_MS=120000`, child writes the summary pipe and `_exit()`s) and passed
the D3 live telemetry gate: 60 Bad Apple frames uploaded as textures, rendered to a 960x720 target, A2D-linearized,
copied into KMS, and presented with `gpu.d3.video.result=video-texture-present-pass`, `presented=60`,
`fps_milli=29969`, `changed_total=41472000`, `copy.avg_us=16653`, `present.avg_us=13924`, post-probe
`selftest fail=0`, and no GPU fault-filter match. A follow-up no-flash eye-confirm replay held the same V3313
GPU-blit path for 60 s and passed again: `gpu.d3.video.result=video-texture-present-pass`, `presented=60`,
`fps_milli=30177`, `changed_total=41472000`, `copy.avg_us=16585`, `present.avg_us=13794`, post-replay
`selftest fail=0`, and no focused dmesg fault-filter match. V3314 then strengthened the close gate by adding
`--start-frame` and final-frame semantic sampling, so the 60 s hold starts from the high-contrast Bad Apple segment
instead of the black intro. The V3314 live run rendered and held 60 frames from frame 515, presented successfully,
produced only black/white output pixels (`semantic_output_other_count=0`), and stayed healthy, but the exact semantic
sample gate returned `63/64` because one source-edge sample expected white while the scaled texture output was black.
V3315 then accepted a bounded 3x3 source-neighborhood match around scaled texture edges while still requiring 64/64
semantic samples and zero non-binary output pixels. The V3315 live run passed with `video-texture-present-pass`,
`presented=60`, `fps_milli=29655`, `changed_total=41472000`, `semantic_sample_count=64`, `match_count=64`,
`exact_match_count=63`, `edge_tolerant_match_count=1`, `mismatch_count=0`, `output_other_count=0`, post-probe
`selftest fail=0`, and no focused dmesg fault-filter match. A follow-up no-flash eye-confirm replay held the same
V3315 GPU-blit path for 60 s and passed again: `video-texture-present-pass`, `presented=60`, `fps_milli=29908`,
`semantic_sample_count=64`, `match_count=64`, `exact_match_count=63`, `edge_tolerant_match_count=1`,
`mismatch_count=0`, `output_other_count=0`, post-replay `selftest fail=0`, and no focused dmesg fault-filter match.
A later attempt to extend the hold to 120 s correctly hit the current guard (`bad-hold max_ms=60000`), then replayed
the supported max 60 s hold again with the same clean result (`video-texture-present-pass`, `presented=60`,
`fps_milli=30005`, `match_count=64`, `edge_tolerant_match_count=1`, `mismatch_count=0`, `output_other_count=0`,
post-replay `selftest fail=0`, no fault-filter match). The operator then visually confirmed the held frame on the
physical panel: "배드애플 보였다 프레임은 정상적으로 나오는거 같았다". D3 and rung ② are therefore DONE +
EYE-CONFIRMED. The next GPU-chain item is ③ modularization/extraction: pull the common KGSL submit/fence/buffer layer
only now that triangle, compute, and accelerated 2D are all real consumers.

**(historical, first-triangle ladder — DONE record)** Threshold from fixed-function plumbing to *real GPU
graphics*: vertex buffer → vertex shader → rasterizer → fragment shader → a shaded triangle, readback-verified, blitted
to KMS. Reuses the proven G0-G3 core (context/buffer/submit/fence/readback) + G5 blit; swaps the 2D fill for a 3D draw.
- **H0** (host-only deep recon): study minimal A6xx 3D pipeline state (mesa fd6 + envytools regs); **hand-assemble the
  minimal ir3 shaders** (passthrough VS + constant-color FS) — do **NOT** bring up the full Mesa ir3 compiler (huge,
  not bounded); the freedreno "first triangle" tradition is hand-coded shaders.
- **H1** upload hand-assembled shaders + set SP (shader processor) state, verify no GPU fault → **H2** set 3D pipeline
  state (VFD/VPC/GRAS/RB) for one triangle into an offscreen buffer → **H3** bind a 3-vertex buffer, `CP_DRAW_INDX_OFFSET`,
  fence, readback → **H4** verify triangle pixels (interior = shaded, exterior = clear) via CPU readback = first-triangle
  proof → **H5** blit the triangle buffer to `/dev/dri/card0`. Each rung device-verifiable; GPU faults are recoverable.
- **Crux = the shader.** If hand-assembled ir3 proves too fiddly that is a real decision point — record it, do not
  escalate to the blob or to a full compiler port.

**STATUS (2026-06-25) — H1/H2 landed, H3 draw-envelope now retires but still draws no pixels.**
V3208 uploaded placeholder VS/FS shader objects and programmed SP shader state with no draw; V3210 programmed A6xx
GRAS/RB/VPC/PC/VFD/SP fixed-function 3D state into a private 128x128 offscreen target and retired cleanly with no draw.
V3212/V3213 added and flashed `gpu h3-draw-envelope-probe`: it binds command/color/event/VS/FS/3-vertex BOs, emits VFD
vertex-buffer/fetch/dest state plus direct non-indexed `CP_DRAW_INDX_OFFSET` (`packet=0x38`, `draw_initiator=0x84`,
`num_indices=3`), and stays inside the child-only KGSL timeout envelope. Live result: submit succeeded
(`submit_rc=0`, `pm4_dwords=170`) but the timestamp did not retire (`wait_rc=-1`, `errno=110`, `retired_timestamp=0`);
cleanup and post-probe selftest stayed clean. V3214/V3215 replaced the zero VS/FS payload with a hand-encoded ir3
`end + nop + nop + nop` stream (`0x0300000000000000`), added a boot-size gate after a rejected oversized image was
rolled back to V2321 cleanly, then flashed the corrected image. Live result: H3 now retires (`wait_rc=0`,
`retired_timestamp=1`, `fence_poll_rc=1`) with no GPU fault/hang signature, but the color readback remains unchanged
(`readback_changed_count=0`). This proves the previous H3 timeout was at least partly a non-terminating shader-stream
boundary, **not** H4 triangle proof. Next unit should replace the terminator-only payload with real minimal
hand-assembled ir3 VS/FS that writes clip-space position and a fragment color; do not claim triangle rendering until
readback changes with interior/exterior verification. V3216/V3217 made that first minimal shader-color attempt: VS uses
cat1 `mov.f32f32` to set `r0.z=0.0` and `r0.w=1.0` while VFD supplies `r0.xy`, FS writes `r0.x=1.0`, and H3 switches MRT0
to `FMT6_32_FLOAT` with output mask `0x1`. Live result still retired cleanly (`wait_rc=0`, `retired_timestamp=1`) but
readback stayed unchanged (`readback_changed_count=0`) and post-probe selftest stayed `fail=0`. This narrows the next
gap away from non-terminating shader streams and toward VS output/VPC destination, FS output/MRT linkage, or missing
draw/raster state required for pixels. V3218/V3219 then applied the concrete Mesa A6xx SP control gap: VS
`SP_VS_CNTL_0=0x00100080` (`FULLREGFOOTPRINT=1|MERGEDREGS`) and FS `SP_PS_CNTL_0=0x81000080`
(`FULLREGFOOTPRINT=1|INOUTREGOVERLAP|MERGEDREGS`). Live result again retired cleanly (`submit_rc=0`, `wait_rc=0`,
`retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=454`) with no GPU fault/hang signature, but readback still
stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) and post-probe
selftest stayed `fail=0`. That removes SP footprint/merged-reg control as the primary blocker; next bounded unit should
focus on FS output/MRT linkage, raster/depth/stencil/coverage enables, or a Mesa-diffed minimal draw-state packet gap.
V3220/V3221 then tested the narrow raster/coverage hypothesis by adding Mesa-derived GRAS defaults:
`GRAS_SC_RAS_MSAA_CNTL=0`, `GRAS_SC_DEST_MSAA_CNTL=0x4`, and `GRAS_SC_SCREEN_SCISSOR_CNTL=0`. Live result again
retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=455`) with
no GPU fault/hang signature, but readback still stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`) and post-probe selftest stayed `fail=0`. That removes the tested GRAS raster coverage
defaults as the primary blocker; next bounded unit should focus on FS output/MRT linkage, VPC/RB output state, or a
Mesa-diffed minimal draw-state packet gap.
V3222/V3223 then tested the narrower VPC position/clip-cull linkage gap by changing `VPC_VS_CNTL` from stride-only
`0x00000004` to `0x00ff0004` (`PSIZELOC=0xff`) and adding `VPC_VS_CLIP_CULL_CNTL=0x00ffff00`,
`VPC_VS_CLIP_CULL_CNTL_V2=0x00ffff00`, plus `GRAS_CL_VS_CLIP_CULL_DISTANCE=0`. Live result again retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=30`) with no GPU fault/hang
signature, but readback still stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`) and post-probe selftest stayed `fail=0`. That removes this tested VPC sentinel linkage
gap as the primary blocker; next bounded unit should focus on FS output/MRT or RB output linkage, or generate a
minimal Mesa-equivalent packet diff for the first draw.
V3224/V3225 then tested the bounded FS/MRT output component-mask hypothesis by changing `GPU_H3_COLOR_OUTPUT_MASK` from
`0x1` to Mesa's full RT0 mask `0xf`, which programs `RB_PS_OUTPUT_MASK=0x0000000f`,
`SP_PS_OUTPUT_MASK=0x0000000f`, and `RB_MRT0_CONTROL.COMPONENT_ENABLE=0x00000780`. Live result again retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=32`) with no GPU fault/hang
signature, but readback still stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`) and post-probe selftest stayed `fail=0`. That removes the tested RT0 component-mask gap
as the primary blocker. The next bounded unit should generate a Mesa-equivalent first-draw packet diff, then test the
smallest resulting RB/CCU/FS-output or shader-output linkage delta before claiming H4.
V3226/V3227 then tested a concrete shader-mode gap from Mesa `fd6_program.cc::emit_shader_regs()` by adding
`SP_MODE_CNTL=0x00000005` and `TPL1_MODE_CNTL=0x000000a2` before the VS/FS program registers. Live result again retired
cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=186`,
`total_elapsed_ms=30`) with no GPU fault/hang signature, but readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) and post-probe selftest stayed
`fail=0`. That removes this tested shader-mode setup gap as the primary blocker. Next bounded unit should continue the
Mesa-equivalent first-draw packet diff and test a small, draw-relevant missing static/init state group such as
`RB_INTERP_CNTL`/`RB_PS_INPUT_CNTL`/sample-position or the minimal `VPC_VARYING_LM_TRANSFER_CNTL`/SIV path.
V3228/V3229 then tested the narrow fragment-input default-state group from Mesa
`fd6_program.cc::emit_fs_inputs()` by adding explicit zero writes for `GRAS_CL_INTERP_CNTL`, `RB_INTERP_CNTL`,
`RB_PS_INPUT_CNTL`, `RB_PS_SAMPLEFREQ_CNTL`, `GRAS_LRZ_PS_INPUT_CNTL`, and `GRAS_LRZ_PS_SAMPLEFREQ_CNTL`. Live result
again retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=198`,
`state_reg_writes=74`, `total_elapsed_ms=30`) with no GPU fault/hang signature, but readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) and post-probe selftest stayed
`fail=0`. That removes this tested fragment-input zero-state group as the primary blocker. Next bounded unit should
continue the Mesa-equivalent first-draw packet diff and test the minimal `VPC_VARYING_LM_TRANSFER_CNTL`/SIV path or
sample-position/static state group before claiming H4.
V3230/V3231 then tested the minimal VPC LM/SIV path from Mesa `fd6_program.cc::emit_vpc()` for the current
position-only linkage by adding `VPC_VARYING_LM_TRANSFER_CNTL[0..3]={0xfffffff0,0xffffffff,0xffffffff,0xffffffff}`,
`VPC_VS_SIV_CNTL=0x0000ffff`, `VPC_VS_SIV_CNTL_V2=0x0000ffff`, and `GRAS_SU_VS_SIV_CNTL=0`. Live result again retired
cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=209`,
`state_reg_writes=81`, `total_elapsed_ms=31`) with no GPU fault/hang signature, but readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) and post-probe selftest stayed
`fail=0`. That removes this tested VPC LM/SIV group as the primary blocker. Next bounded unit should continue the
Mesa-equivalent first-draw packet diff and test a small sample-position/static state group or revisit the hand-assembled
shader output contract before claiming H4.
V3232/V3233 then tested a bounded Mesa `fd6_emit_static_context_regs()` group that was still absent from the hand-built
H3 stream by adding `GRAS_SU_CONSERVATIVE_RAS_CNTL=0`, `VPC_UNKNOWN_9210=0`, `VPC_SO_OVERRIDE=1`,
`VPC_RAST_STREAM_CNTL=0`, `PC_STEREO_RENDERING_CNTL=0`, `TPL1_PS_SWIZZLE_CNTL=0`, and
`SP_REG_PROG_ID_3=0x0000fcfc`. The flashed image booted as `0.11.43 (v3232-gpu-h3-static-context-probe)`, passed
post-flash and post-probe selftest (`pass=12 warn=1 fail=0`), and the H3 draw again retired cleanly (`submit_rc=0`,
`wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=223`, `state_reg_writes=88`,
`total_elapsed_ms=31`) with no GPU fault/hang signature. Readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still not reached. That
removes this tested static-context no-op/disable group as the primary blocker. Next bounded unit should revisit the
hand-assembled shader output contract or compare the remaining Mesa first-draw packet stream for a smaller
shader-output/RB linkage delta before claiming H4.
V3234/V3235 then tested the narrow shader-output/input-register overlap hypothesis by keeping VFD input in `r0.xy` but
moving VS clip-position output to `r1.xyzw`, moving FS color output to `r1.x`, and programming
`SP_VS_OUTPUT_REG0=0x00000f04` plus `SP_PS_OUTPUT_REG0=0x04` from Mesa `fd6_program.cc::emit_vpc()` /
`emit_fs_outputs()` output-regid mapping. The image built and flashed as `0.11.44
(v3234-gpu-h3-shader-output-probe)`, passed post-flash health (`selftest pass=12 warn=1 fail=0`), but the H3 draw
regressed to a child timeout (`result=timeout`, `timed_out=1`, `child_status=0x9`, `rc=-110`, duration about
`5004ms`) before any readback proof. A post-probe selftest still passed and a GPU fault/hang dmesg filter found no
match, but a follow-up `gpu g3-noop-submit-probe` also timed out, so the failed H3 can wedge the KGSL queue until
reboot. This removes r1 output split with the old `FULLREGFOOTPRINT=1` as a valid standalone fix. Next bounded unit
should keep the V3234 r1 split but bump VS/PS full register footprint to `2`; if that still times out, revert the r1
split and move to another Mesa packet delta before claiming H4.
V3236/V3237 then kept that r1 shader-output split and raised VS/PS `FULLREGFOOTPRINT` to `2`, producing
`SP_VS_CNTL_0=0x00100100` and `SP_PS_CNTL_0=0x81000100`. The image flashed as `0.11.45
(v3236-gpu-h3-shader-footprint-probe)` and passed post-flash health (`selftest pass=12 warn=1 fail=0`). The first H3
attempt timed out, but focused dmesg showed the actual blocker was fresh-boot firmware visibility:
`request_firmware(a630_sqe.fw) failed` while `firmware_class.path` pointed at `/vendor/firmware_mnt/image`; `gpu
g0-status` showed the SQE/GMU firmware present in `/cache/a90-runtime/pkg/gpu-g0-fw`. After `gpu g0-fwclass-prepare`,
G0 open returned in `26ms`, G3 noop retired in `9ms`, and the same H3 draw retired (`submit_rc=0`, `wait_rc=0`,
`retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=12`) with no GPU fault/hang signature. Readback still
stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still
not reached. This removes the V3234 timeout as a shader-footprint objection under the correct G0 firmware prep
precondition, and exposes a validation hazard: H3/H4 probes must either run G0 fwclass prep during materialization or
require it as a preflight before KGSL open. Next bounded unit should close that preflight hole, then continue remaining
Mesa first-draw packet deltas around RB/CCU/FS-output or shader-output linkage before claiming H4.
V3238/V3239 then closed that preflight hole by moving `gpu g0-fwclass-prepare` into `gpu_g0_materialize_devnode()`.
The image flashed as `0.11.46 (v3238-gpu-g0-fwclass-materialize-prep-probe)` and passed health. Fresh-boot `gpu
g0-status` intentionally showed the old hazard (`firmware_class.path=/vendor/firmware_mnt/image`, `/dev/kgsl-3d0`
missing, SQE/GMU present only in `/cache/a90-runtime/pkg/gpu-g0-fw`). Without running manual prepare, the H3
`--materialize-devnode` path then emitted `gpu.g0.materialize.fwclass_prepare_attempted=1`,
`gpu.g0.fwclass_prepare.result=ok`, `gpu.g0.materialize.fwclass_prepare_rc=0`, created `/dev/kgsl-3d0`, and the draw
retired (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=31`) with no GPU
SQE timeout/fault/hang signature. Readback still stayed unchanged (`readback_changed_count=0`,
`readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still not reached. This removes firmware-path false
timeouts from future H3/H4 work; next bounded unit should return to the remaining first-triangle packet/linkage gap,
likely RB/CCU/FS-output or shader-output contract, before claiming H4.
V3240/V3241 then tested the Mesa A6xx `sample_locations_disable_stateobj` gap by adding
`GRAS_SC_MSAA_SAMPLE_POS_CNTL=0`, `RB_MSAA_SAMPLE_POS_CNTL=0`, and `TPL1_MSAA_SAMPLE_POS_CNTL=0` to H3. The image
flashed as `0.11.47 (v3240-gpu-h3-sample-location-probe)` with SHA256
`9fc11231bc8267174a8ecc20bb7ba7aac77604ea5fdff8eba7fd406eb4b7501b` and passed post-flash health (`selftest
pass=12 warn=1 fail=0`). Fresh-boot `gpu g0-status` again showed the expected pre-materialization hazard, and the H3
`--materialize-devnode` path automatically ran fwclass prep (`gpu.g0.materialize.fwclass_prepare_attempted=1`,
`gpu.g0.fwclass_prepare.result=ok`, `gpu.g0.materialize.fwclass_prepare_rc=0`). The draw retired cleanly with the new
state counts (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `pm4_dwords=229`,
`state_reg_writes=91`, `total_elapsed_ms=31`) and no focused dmesg timeout/fault/hang/snapshot signature, but readback
still stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes
the tested sample-location disable-state group as the primary blocker; next bounded unit should continue the remaining
Mesa first-draw packet/linkage diff around RB/CCU/FS-output or the shader-output contract before claiming H4.
V3242/V3243 then tested the operator-supplied CP render-mode hypothesis by adding Mesa A6xx
`CP_SET_MARKER(RM6_DIRECT_RENDER)` (`opcode=0x65`, payload `0x00000001`) immediately after the initial WFI and before
H3 3D state, while also keeping sysmem `RB_CCU_CNTL=0x10000000` for Adreno640v2 (`num_ccu=2`, color offset
`0x20000`). The image flashed as `0.11.48 (v3242-gpu-h3-direct-render-marker-probe)` with SHA256
`eb472fa77edfe20cfeeb5dd280279ba1203e2d4e3fd34d236d81e780bcb5ef13` and passed post-flash health (`selftest
pass=12 warn=1 fail=0`). Live H3 telemetry confirmed `gpu.h3.draw.cp_set_marker=0x1`, `pm4_dwords=233`, and
`state_reg_writes=92`; the draw still submitted and retired (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`,
`total_elapsed_ms=31`) with no KGSL/GPU fault/hang/snapshot/timeout signature, but readback still stayed unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes missing
`CP_SET_MARKER(RM6_DIRECT_RENDER)` as the primary no-pixel root cause. Next bounded unit should prioritize the remaining
shader/output contract: prove the hand-assembled ir3 VS writes the clip-space position to the VPC-consumed position
output slot and that the FS output register/MRT linkage matches the current `r1` split, before doing another broad
register sweep. LRZ is already programmed disabled in the state stream and RB CCU sysmem control is present, so keep
those lower priority unless new evidence reopens them.
V3244/V3245 then tested the smallest output-register fallback by keeping the V3242 direct-render marker, RB CCU sysmem,
sample-location, static-context, and fullregfootprint state intact while switching the hand-assembled ir3 contract to
`r0`: VS passes through `r0.xy` and writes `r0.zw=0/1`, FS writes color to `r0.x`, and VS/PS output regids are both
`0` (`SP_VS_OUTPUT_REG0=0x00000f00`). The image flashed as `0.11.49 (v3244-gpu-h3-r0-output-probe)` with SHA256
`9764d950f93ada582b5b853c17dcf480635df0aeffe5ee90d6cab7845533c66d` and passed post-flash health (`selftest
pass=12 warn=1 fail=0`). Live telemetry confirmed the r0 contract (`vs_output_regid=0x0`, `ps_output_regid=0x0`,
`sp_vs_output_reg0=0xf00`) with unchanged envelope counts (`pm4_dwords=233`, `state_reg_writes=92`); the draw again
submitted and retired (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `total_elapsed_ms=29`) with no KGSL/GPU
fault/hang/snapshot/timeout signature, but readback stayed unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`). This removes a simple `r1` output-register mismatch as the primary no-pixel root cause.
Next bounded unit should stop toggling output regid alone and prove the shader execution contract more directly:
disassemble/audit the exact hand-assembled ir3 words including scheduling bits, or replace them with a minimal
known-good compiler/disassembler-derived ir3 payload while preserving the same KGSL-direct envelope.
V3246 then performed that host-side shader-byte audit without changing or flashing a boot artifact. A minimal Mesa
freedreno `ir3-disasm` was built under `/tmp/a90-mesa-h3-build-ir3` and
`native_gpu_h3_shader_byte_audit_v3246.py --require-ir3-disasm` decoded the exact H3 words from
`80_shell_dispatch.inc.c`: VS is `mov.f32f32 r0.x,r0.x`; `mov.f32f32 r0.y,r0.y`;
`mov.f32f32 r0.z,(0.0)`; `mov.f32f32 r0.w,(1.0)`; `end`; `nop`, and FS is
`mov.f32f32 r0.x,(1.0)`; `end`; `nop`; `nop`. All decoded words have no `(ss)`/`(sy)` flags, matching the current
plain hand encoding. The audit also closes two targeted register-side shader contract suspicions: FS writes a full f32
`r0.x` and `SP_PS_OUTPUT_REG0` has `HALF_PRECISION=0`, so the current full-output path is internally consistent; position
is designated by `VPC_VS_CNTL.positionloc=0` plus `SP_VS_VPC_DEST_REG0.OUTLOC0=0`, while `VPC_VS_SIV_CNTL=0xffff` is only
the layer/view sentinel, not the position selector. This makes the exact hand-assembled bytes unlikely to be the
no-pixel root cause. Next bounded unit should compare the remaining first-draw packet/linkage delta outside the already
verified shader bytes, especially render-target/RB linkage or any compiler-emitted minimal-shader state that is still
absent from the KGSL-direct envelope.
V3247/V3248 then tested a concrete remaining Mesa A6xx RB linkage delta by changing the already-emitted
`RB_RENDER_CNTL` value from `0x00000000` to `0x00000010`, matching `fd6_gmem.cc::update_render_cntl()` with
`CCUSINGLECACHELINESIZE=2`, while keeping the V3244 r0 shader contract, V3246 audited ir3 bytes, direct-render marker,
RB CCU sysmem state, sample-location defaults, static-context defaults, and firmware-class materialize preflight intact.
The image built as `0.11.50 (v3247-gpu-h3-rb-render-cntl-probe)` with SHA256
`56ea2b9aa2b46e2c5257db52c4c05a392871bed67fbd6c6a61807a880d3a5f4e`, flashed through `native_init_flash.py`, passed
post-flash health (`selftest pass=12 warn=1 fail=0`), and live telemetry confirmed `gpu.h3.draw.rb_render_cntl=0x10`
with unchanged envelope counts (`pm4_dwords=233`, `state_reg_writes=92`). The draw again submitted and retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=29`) and the focused dmesg
filter found no KGSL/GPU fault, hang, snapshot, or timeout signature, but the readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes the missing
`RB_RENDER_CNTL.CCUSINGLECACHELINESIZE=2` hypothesis as the primary no-pixel root cause. Next bounded unit should
continue outside shader bytes and this RB render-control field, using a remaining Mesa first-draw packet diff to isolate
a narrower render-target/cache/visibility or draw-mode delta before claiming H4.
V3249/V3250 then tested the Mesa A6xx restore-path cache/visibility hypothesis by adding `fd6_cache_inv()` before the
H3 shader/state/draw packets: `CP_EVENT_WRITE(PC_CCU_INVALIDATE_COLOR=0x19)`,
`CP_EVENT_WRITE(PC_CCU_INVALIDATE_DEPTH=0x18)`, `CP_EVENT_WRITE(CACHE_INVALIDATE=0x31)`, then `CP_WAIT_FOR_IDLE`. The
image built as `0.11.51 (v3249-gpu-h3-cache-invalidate-probe)` with SHA256
`167251fa73fa537c8a3c75716a7b7e3061605b62a0fd24494a11805d089c50a6`, flashed through `native_init_flash.py`, and passed
post-flash health (`selftest pass=12 warn=1 fail=0`). Live telemetry confirmed the candidate sequence
(`pre_draw_cache_invalidate_events=0x19,0x18,0x31`) and the expected command growth (`pm4_dwords=240`,
`state_reg_writes=92`) while preserving `rb_render_cntl=0x10`. The draw again submitted and retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, `fence_poll_rc=1`, `total_elapsed_ms=29`), and the focused dmesg
filter found no KGSL/GPU fault, hang, snapshot, or GPU timeout signature, but readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes missing pre-draw
CCU/UCHE invalidation as the primary no-pixel root cause. Next bounded unit should continue with a narrower
first-draw packet diff outside shader bytes, `RB_RENDER_CNTL`, and pre-draw cache invalidation; good remaining targets
are draw-state bootstrap such as `CP_SET_MODE`/`SP_UPDATE_CNTL`/restore state ordering, or another concrete
compiler-emitted program/output state delta if it can be isolated before flashing.
V3251/V3252 then tested the operator-identified shader-binary/load-contract hypothesis. The source unit replaced the H3
VS with the local Mesa reference minimal VS bytes (`mov.u32u32 r0.z, 0x3f800000`; `mov.u32u32 r0.w, 0x3f800000`;
`end`; zero padding), kept the V3246 `ir3-disasm`-audited FS, aligned both shader BO payloads to 128 bytes, and changed
`SP_VS_INSTR_SIZE`, `SP_PS_INSTR_SIZE`, and CP_LOAD_STATE6 shader `NUM_UNIT` to Mesa-style `instrlen=1`. The image
built as `0.11.52 (v3251-gpu-h3-compiler-vs-instrlen-probe)` with SHA256
`ac608fe5914a834b5f895c79ee28b4c4d5212b8fbdbcec0e73408fde92226426`, flashed through `native_init_flash.py`, passed
post-flash health (`selftest pass=12 warn=1 fail=0`), and live telemetry confirmed the new shader-load contract
(`vs_shader_dwords=32`, `fs_shader_dwords=32`, `vs_shader_instrlen=1`, `fs_shader_instrlen=1`, `ir3_instr_align=16`,
`ir3_mov_u32u32_r0z_hi=0x204cc002`, `ir3_mov_u32u32_r0w_hi=0x204cc003`). Two H3 runs submitted and retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`) and the focused dmesg filter found no
KGSL/GPU fault, hang, snapshot, or timeout signature, but the readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes unverified shader bytes
and shader `instrlen`/load unit count as the primary no-pixel root cause. Next bounded unit should stay shader-byte
frozen unless a real disassembler-backed mismatch appears, and instead isolate a concrete Mesa first-draw packet delta
outside shader bytes: draw-state bootstrap ordering, `CP_SET_MODE`/`SP_UPDATE_CNTL`-style restore state, or the sysmem
MRT/CCU visibility path.
V3253/V3254 then tested the next concrete Mesa first-draw packet delta by adding draw-local `SP_UPDATE_CNTL=0x0000009f`
at register `0xbb08` before H3 shader state, matching the local freedreno A6xx draw/program state object pattern
(`VS_STATE|HS_STATE|DS_STATE|GS_STATE|FS_STATE|GFX_UAV`, bindless masks zero). The image built as
`0.11.53 (v3253-gpu-h3-sp-update-cntl-probe)` with SHA256
`1395721839c41ac07ff41379fabaa298d40479b237384add1bcfb6c1837d5769`, flashed through `native_init_flash.py`, passed
post-flash health after a serial bridge restart cleared one stale framing failure (`selftest pass=12 warn=1 fail=0`),
and live telemetry confirmed `sp_update_cntl=0x9f`, `pm4_dwords=242`, and unchanged `state_reg_writes=92`. Two H3 runs
submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`), and the
focused dmesg filter found no KGSL/GPU fault, hang, snapshot, or timeout signature, but readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes the missing draw-local
`SP_UPDATE_CNTL=0x9f` packet as the primary no-pixel root cause. Remaining bounded work should stay outside shader bytes
and now focus on restore-state ordering/`CP_SET_MODE` versus the sysmem MRT/CCU visibility path.
V3255/V3256 then tested the Mesa sysmem render-pass bin-control delta. Source review first ruled out the proposed A640
`RB_CCU_CNTL` magic-value change: local Mesa A640 trace and `config_sysmem` calculation both confirm current
`RB_CCU_CNTL=0x10000000`. V3255 instead added the missing sysmem `set_bin_size` pair,
`GRAS_SC_BIN_CNTL=0x02c00000` and `RB_CNTL=0x02c00000`, built as
`0.11.54 (v3255-gpu-h3-sysmem-bin-control-probe)` with SHA256
`0ccb33c25dcbbf9a8274d2d569c135a48a9ef208bb27e512d0cd73687a651501`, flashed through `native_init_flash.py`, and
passed post-flash health after a host-side serial bridge restart cleared a transaction-lock/framing issue caused by
parallel manual health commands (`selftest pass=12 warn=1 fail=0`). Live telemetry confirmed
`gras_sc_bin_cntl=0x2c00000`, `rb_cntl=0x2c00000`, `pm4_dwords=246`, and `state_reg_writes=94`. Two H3 runs submitted
and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=13`), with no focused
KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature, but readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes missing sysmem
`GRAS_SC_BIN_CNTL/RB_CNTL` as the primary no-pixel root cause. Next bounded unit should avoid broad register sweeping
and diff against fd6 sysmem prep/draw ordering; one concrete remaining mismatch already visible is Mesa
`VPC_SO_OVERRIDE(false)` while current H3 still reports `vpc_so_override=0x1`.
V3257/V3258 then tested that mismatch directly by changing `VPC_SO_OVERRIDE` at register `0x9306` from `0x1` to
Mesa sysmem prep's `0x0` (`VPC_SO_OVERRIDE(false)`). The image built as
`0.11.55 (v3257-gpu-h3-vpc-so-override-probe)` with SHA256
`c308eee87756e5417b6b356a83c4c9c3721b056b4b9f37797b2a3269596db7e1`, flashed through `native_init_flash.py`, and
passed post-flash health after one host-side bridge connection reset was cleared by a short wait and sequential retry
(`selftest pass=12 warn=1 fail=0`). Live telemetry confirmed `vpc_so_override=0x0`, `pm4_dwords=246`, and
`state_reg_writes=94`. Two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`,
`retired_timestamp=1`, warm `total_elapsed_ms=12`), with no focused KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout
signature, but readback remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`). This removes `VPC_SO_OVERRIDE=0x1` as the primary no-pixel root cause. Next bounded
packet delta should continue from `fd6_emit_sysmem_prep()` rather than broad register sweeping: Mesa emits
`CP_SKIP_IB2_ENABLE_GLOBAL=0`, `CP_SKIP_IB2_ENABLE_LOCAL=1`, and `CP_SET_VISIBILITY_OVERRIDE=1` before the large
draw-state CRB, and current H3 does not emit those packets.
V3259/V3260 then tested that exact Mesa sysmem-prep packet trio. V3259 added
`CP_SKIP_IB2_ENABLE_GLOBAL=0`, `CP_SKIP_IB2_ENABLE_LOCAL=1`, and `CP_SET_VISIBILITY_OVERRIDE=1` immediately after the
direct-render marker and before H3 3D state, built as `0.11.56 (v3259-gpu-h3-visibility-packets-probe)` with SHA256
`48854bdd6d11d658254c364456f55e794c247484cb0b8f199065a9354f95f02a`, flashed through `native_init_flash.py`, and
passed post-flash health after one host-side serial bridge framing issue was cleared by restarting the managed bridge
and retrying health checks sequentially (`selftest pass=12 warn=1 fail=0`). Live telemetry confirmed
`cp_skip_ib2_enable_global=0x1d` value `0x0`, `cp_skip_ib2_enable_local=0x23` value `0x1`,
`cp_set_visibility_override=0x64` value `0x1`, `pm4_dwords=252`, and `state_reg_writes=94`. Two H3 runs submitted
and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=11`), with no focused
KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature, but readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes the missing
visibility/IB2 sysmem-prep packet trio as the primary no-pixel root cause. Next bounded unit should stop isolated
packet guessing and capture/diff a real Mesa fd6 sysmem single-triangle command stream against H3; if that capture is
not immediately available, the remaining concrete sysmem-prep gap to test is exact window-offset/order state around
`RB_WINDOW_OFFSET`, `RB_RESOLVE_WINDOW_OFFSET`, `SP_WINDOW_OFFSET`, and `TPL1_WINDOW_OFFSET`.

V3261/V3262 then tested that remaining concrete window-offset/order gap, but the first live artifact did not produce
a valid GPU result: adding Mesa's zero `RB_WINDOW_OFFSET`, `RB_RESOLVE_WINDOW_OFFSET`, `SP_WINDOW_OFFSET`, and
`TPL1_WINDOW_OFFSET` packets raised the expected H3 stream to `260` dwords while the shared command-buffer guard was
still `GPU_G4_CMD_MAX_DWORDS=256`. The flashed image booted and passed health, but the live H3 run failed before
submit (`cmd_write_rc=-1`, `pm4_dwords=0`, `submit_rc=-1`), so V3262 only proved a host-side PM4 assembly guard bug,
not a new no-pixel datapoint. V3263 corrected that guard to `320` dwords and rebuilt from the V3259 ramdisk baseline
as `0.11.58 (v3263-gpu-h3-window-offset-cmdroom-probe)` with SHA256
`f38f2fdb7cb71cabc6603e606bcd28965715e128f8211bf767f47f851da7f3d8`, flashed through `native_init_flash.py`, and
passed post-flash health after one host-side serial bridge framing retry (`selftest pass=12 warn=1 fail=0`). V3264 live
telemetry confirmed the corrected stream assembled and submitted (`cmd_write_rc=0`, `pm4_dwords=260`,
`state_reg_writes=98`, `submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`), with no focused KGSL/GPU/GMU/A640 fault,
hang, snapshot, or timeout signature, but two H3 runs still left readback unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`). This removes the zero window-offset
sysmem-prep packet group and command-buffer room as the primary no-pixel root cause. The next bounded unit should be a
real Mesa fd6 sysmem single-triangle command-stream capture/diff against H3, with special attention to any remaining
per-MRT render-component/write-enable register names that are not equivalent to the already-programmed
`RB_PS_OUTPUT_MASK`, `SP_PS_OUTPUT_MASK`, and `RB_MRT0_CONTROL.COMPONENT_ENABLE` path.

V3265/V3266 then tested the next concrete draw-state bootstrap packet because a real Mesa `.rd` capture was not
immediately available on the host (`meson`/Mesa driver build absent; existing local Mesa build contains freedreno tools
only, not the Gallium driver). V3265 added Mesa restore-path `CP_SET_MODE(0)` (`opcode=0x63`, value `0`) after the
pre-draw CCU/cache invalidation and before the H3 shader/state/draw packets, built from the V3263 baseline as
`0.11.59 (v3265-gpu-h3-cp-set-mode-probe)` with SHA256
`cb8c579aa4cc694de363d7e2334c202f255431bba9e4f1a385fe0f2b3094ba84`, flashed through `native_init_flash.py`, and
passed post-flash health after a managed bridge restart cleared serial fragment noise (`selftest pass=12 warn=1
fail=0`). V3266 live telemetry confirmed `cp_set_mode=0x63`, `cp_set_mode_value=0x0`, `pm4_dwords=262`,
`state_reg_writes=98`, `submit_rc=0`, `wait_rc=0`, and `retired_timestamp=1`; two H3 runs still left readback unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), with no focused
KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature and post-probe health still clean. This removes missing
restore-path `CP_SET_MODE(0)` as the primary no-pixel root cause. Next bounded unit should either build a host-only
freedreno Gallium+drm-shim reference environment to generate an `.rd` for cffdump diff, or, if that remains unavailable,
continue source-grounded diff around remaining A6xx program/RB state that is present in Mesa but absent from H3.

V3267 source-audited the new `RB_CCU_CNTL` magic hypothesis against local Mesa fd6 code before changing H3. Mesa's A640
entry uses `a6xx_base + a6xx_gen2` with `num_ccu=2`; `a6xx_base` gives sysmem depth/color cache sizes of 64KiB per CCU;
`fd6_calc_gmem_cache_offsets()` computes sysmem `depth_ccu_offset=0` and `color_ccu_offset=2 * 64KiB = 0x20000`; and the
A6xx XML encodes `RB_CCU_CNTL.COLOR_OFFSET` as `(offset >> 12) << 23`, yielding exactly `0x10000000`. That matches current
H3 (`GPU_H3_RB_CCU_CNTL=0x10000000`, color offset `0x20000`, depth offset `0`), so no boot delta was built for this
candidate. The same audit confirmed V3255/V3256 already emit the Mesa sysmem `set_bin_size()` equivalents
(`GRAS_SC_BIN_CNTL` and `RB_CNTL`), and that the suggested `RB_RENDER_COMPONENTS`/`SP_FS_RENDER_COMPONENTS` names are not
A6xx register names; the current A6xx write-enable path is `RB_PS_OUTPUT_MASK`, `SP_PS_OUTPUT_MASK`, and
`RB_MRT0_CONTROL.COMPONENT_ENABLE` for MRT0. This removes the CCU-magic replacement, bin-control absence, and A4/A5-style
component-register hypotheses as actionable H3 fixes. Next bounded unit should be the real Mesa fd6 sysmem
single-triangle `.rd`/cffdump diff; if host Mesa Gallium+drm-shim setup remains unavailable, continue source-grounded diff
around remaining A6xx program/RB/static non-context state.

V3268/V3269 used the now-working local freedreno `cffdump` path plus Mesa A6xx rasterizer source to test a concrete
draw-state delta: Mesa emits `VPC_RAST_CNTL=POLYMODE6_TRIANGLES` (`0x3`) and `PC_DGEN_RAST_CNTL=POLYMODE6_TRIANGLES`
(`0x3`), while H3 previously only emitted `VPC_RAST_STREAM_CNTL`. V3268 added both raster polygon-mode registers,
built as `0.11.60 (v3268-gpu-h3-raster-mode-probe)` with SHA256
`8fc356e60545ad36e412367d40b4da6f6f9a9766c6251369684f187c49323240`, flashed through `native_init_flash.py`, and
passed post-flash health after one managed bridge restart cleared serial fragment noise (`selftest pass=12 warn=1
fail=0`). V3269 live telemetry confirmed `vpc_rast_cntl=0x3`, `pc_dgen_rast_cntl=0x3`, `pm4_dwords=266`, and
`state_reg_writes=100`; two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`,
warm `total_elapsed_ms=12`), with no focused KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature and
post-probe health still clean. Readback remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`), so H4 is still not reached. This removes missing A6xx polygon raster-mode state as the
primary no-pixel root cause. Next bounded unit should keep using a real Mesa command-stream/source diff and avoid
re-testing the ruled-out CCU/bin/component/CP_SET_MODE/window-offset/visibility/raster-mode hypotheses.

V3270/V3271 source-audited the round-4 HLSQ/output hypothesis before changing H3. The old `HLSQ_CONTROL_*` /
`HLSQ_*_CNTL` register block is not present in the local A6xx XML/fd6 program path being mirrored here; A6xx shader
payload binding stays through the existing `CP_LOAD_STATE6` preload packets, so the live unit did not blindly write
legacy HLSQ offsets. The source delta instead added the fd6/A640-confirmed program/output defaults that were missing
from H3: `SP_VS_CONST_CONFIG=0x100`, `SP_PS_CONST_CONFIG=0x100`, and `SP_PS_OUTPUT_CNTL=0xfcfcfc00` for invalid
depth/sampmask/stencil regids in a color-only FS. V3270 built `0.11.61
(v3270-gpu-h3-sp-const-fs-output-probe)` with SHA256
`dec8c8f956f75e0d035ec21919e5b2fd2d0fb16a81f191eb1b033d59a0138325`, flashed through
`native_init_flash.py`, and passed post-flash health after one managed bridge restart cleared serial fragment noise
(`selftest pass=12 warn=1 fail=0`). V3271 live telemetry confirmed `sp_vs_const_config=0x100`,
`sp_ps_const_config=0x100`, `sp_ps_output_cntl=0xfcfcfc00`, `pm4_dwords=270`, and `state_reg_writes=100`; two H3 runs
submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`), with no
focused KGSL/GPU/GMU/A640 fault, hang, snapshot, or timeout signature and post-probe health still clean. Readback
remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still
not reached. This removes missing SP const enable and missing invalid FS depth/sampmask/stencil output regids as the
primary no-pixel root cause. Next bounded unit should fall back to the real fd6 sysmem single-triangle `.rd`/cffdump
register-packet diff against H3 instead of continuing isolated downstream register sweeps.

V3272/V3273 then tested the actionable part of the follow-up "HLSQ front-end" claim. The legacy `HLSQ_CONTROL_*` /
`HLSQ_*_CNTL` names still are not an A6xx fd6 draw-state path in the local XML/source, but the real A6xx SP front-end
program-id/system-value group was missing: `SP_PS_INITIAL_TEX_LOAD_CNTL`, `SP_PS_WAVE_CNTL`, `SP_LB_PARAM_LIMIT`, and
`SP_REG_PROG_ID_0..2` (H3 already emitted `SP_REG_PROG_ID_3`). V3272 added the current constant-FS-compatible fd6
mapping: no varyings, `SP_PS_INITIAL_TEX_LOAD_CNTL=0x8`, `SP_PS_WAVE_CNTL=0x0`, `SP_LB_PARAM_LIMIT=0x7`, and invalid
`0xfc` regids for unused front-face/sample/IJ/coord system values (`SP_REG_PROG_ID_0..2=0xfcfcfcfc`,
`SP_REG_PROG_ID_3=0x0000fcfc`). It built `0.11.62 (v3272-gpu-h3-sp-frontend-prog-id-probe)` with SHA256
`6ff91c08ee0a866c251675780a23b94834aed44ccd26a3ead4f3e4e9022b0b96`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`). V3273 live telemetry confirmed
`sp_ps_initial_tex_load_cntl=0x8`, `sp_ps_wave_cntl=0x0`, `sp_lb_param_limit=0x7`,
`sp_reg_prog_id_0=0xfcfcfcfc`, `sp_reg_prog_id_1=0xfcfcfcfc`, `sp_reg_prog_id_2=0xfcfcfcfc`, `pm4_dwords=282`,
and `state_reg_writes=106`; two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`,
`retired_timestamp=1`, warm `total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), so H4 is still not reached. This
removes missing SP front-end/system-value invalid-reg state as the primary no-pixel root cause. Next bounded unit
should continue the real fd6 `.rd`/cffdump diff and focus on direct-sysmem-compatible remaining deltas, especially the
clip/guardband/SU group (`GRAS_CL_CNTL=0xc0`, `GRAS_CL_GUARDBAND_CLIP_ADJ=0x0007fdff`, `GRAS_SU_CNTL=0x814`) before
any broader GMEM/UBWC flag-buffer architecture change.

V3274/V3275 then tested that direct-sysmem-compatible clip/guardband/SU group and re-audited the repeated round-4 HLSQ
claim before live flash. The local A6xx XML/fd6 draw path still does not expose the legacy `HLSQ_CONTROL_*` /
`HLSQ_*_CNTL` block as a safe A6xx register-packet target; V3274 therefore did not guess HLSQ offsets, and instead made
the fd6-confirmed output routing explicit (`RB_PS_OUTPUT_CNTL=0`, `RB_PS_MRT_CNTL=1`, `SP_PS_OUTPUT_CNTL=0xfcfcfc00`,
`SP_PS_MRT_CNTL=1`) while adding `GRAS_CL_CNTL=0xc0`, `GRAS_CL_GUARDBAND_CLIP_ADJ=0x0007fdff`,
`GRAS_SU_CNTL=0x814`, `GRAS_SU_POINT_MINMAX=0xffc00001`, `GRAS_SU_POINT_SIZE=0x10`, and zero
`GRAS_SU_POLY_OFFSET_*` companions. V3274 built `0.11.63 (v3274-gpu-h3-clip-guardband-su-probe)` with SHA256
`b9f85b95fda81edd77f2bc121c940275c4122f5842ba929400c7f49b43bdb313`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`; one serial prompt-fragment selftest attempt was retried after
`version` re-synchronized the bridge). V3275 live telemetry confirmed `pm4_dwords=292`, `state_reg_writes=111`, the
new HLSQ audit/output routing telemetry, and the CL/SU values above; two H3 runs submitted and retired cleanly
(`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`) and post-probe selftest stayed clean.
Readback remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) with no
focused KGSL/GPU/GMU/A640 page-fault, hang, snapshot, or timeout signature, so H4 is still not reached. This removes the
clip/guardband/SU rasterizer-state gap and the rechecked legacy-HLSQ/output-routing gap as primary no-pixel causes. Next
bounded unit should stop isolated register sweeps and mine or capture a real fd6 sysmem single-triangle `.rd`/cffdump
diff against H3, admitting only direct-sysmem-compatible missing packet groups.

V3276/V3277 then used that diff direction for a larger, coherent cffdump-inspired varying/IJ linkage unit rather than a
single-register toggle. V3276 changed H3 so the VS writes clip-space position to regid `8` (`r2`), preserves a four-
component varying stream from regid `0`, and the FS uses verified cffdump `bary.f` instructions with MRT0 color output
from FS regid `2`. It also updated `SP_VS_OUTPUT_CNTL=2`, `SP_VS_OUTPUT_REG0=0x0f000f08`,
`SP_VS_VPC_DEST_REG0=0x400`, `VPC_VS_CNTL=0x00ff0408`, `VPC_PS_CNTL=0xff01ff04`, varying-aware
`SP_PS_INITIAL_TEX_LOAD_CNTL=0x7fc0`, `SP_PS_WAVE_CNTL=3`, `SP_REG_PROG_ID_1=0xfcfcfc00`,
`PC_MODE_CNTL=0x1f`, `PC_VS_CNTL=8`, and invalid VFD sideband regids. V3276 built `0.11.64
(v3276-gpu-h3-varying-ij-probe)` with SHA256
`1cfada71599befc2cd47c5ffb53f1eab4673d5200bbe92c77f8137ed0e86471e`, flashed through
`native_init_flash.py`, and passed post-flash health (`selftest pass=12 warn=1 fail=0`; one normal-input
post-flash selftest attempt lost the serial END marker and passed when rerun with slow input). V3277 live telemetry
confirmed `pm4_dwords=306`, `state_reg_writes=118`, `vfd_reg_writes=14`, `sp_vs_cntl0=0x80100180`,
`sp_ps_cntl0=0x81500100`, `vpc_vs_cntl=0xff0408`, `vpc_ps_cntl=0xff01ff04`, and the cffdump bary shader markers.
Two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm
`total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) with no focused KGSL/GPU/GMU/A640
fault, hang, snapshot, timeout, CP opcode, or hardware-error signature, so H4 is still not reached. This removes the
cffdump varying/IJ/VPC/VFD linkage group as the primary no-pixel cause. Next bounded unit should stop adding isolated
HLSQ/output/raster guesses and compare a real fd6 sysmem single-triangle `.rd`/cffdump packet stream against H3, then
admit only direct-sysmem-compatible missing packet groups.

V3278/V3279 then tested the strongest direct-sysmem cffdump color-target mismatch found in the local `.rd` diff:
the reference A640 sysmem triangle uses `SP_PS_MRT[0].REG=0x00000030` / RGBA8 UNORM for MRT0, while H3 still used
`FMT6_32_FLOAT` (`0x4a`). V3278 changed H3 MRT0 to `FMT6_8_8_8_8_UNORM` (`0x30`) while keeping the V3276 varying/IJ
pipeline intact, added telemetry for `color_format_source`, `sp_ps_mrt_reg0`, `rb_mrt0_buf_info`, and
`offscreen=rgba8-linear-128x128`, and explicitly kept the local A6xx/H3 HLSQ audit: the local XML/generated headers
and cffdump path do not expose a legacy `HLSQ_CONTROL_*` program block to write safely. V3278 built `0.11.65
(v3278-gpu-h3-rgba8-mrt-probe)` with SHA256
`c51ac3a3e10114d605fd5ffb4d0a27b6c6a5a2e4259ab9282389f2f5aa5f8e71`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`). V3279 live telemetry confirmed
`sp_ps_mrt_reg0=0x30`, `rb_mrt0_buf_info=0x30`, `color_format=0x30`, `pm4_dwords=306`, `state_reg_writes=118`, and
`vfd_reg_writes=14`. Two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`,
warm `total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`) with no focused KGSL/GPU/GMU/A640
fault, hang, snapshot, timeout, CP opcode, page-fault, or hardware-error signature; dmesg only showed expected first-use
`a640_zap` load/reset plus an unrelated modem firmware timeout. This removes the cffdump float-vs-RGBA8 MRT mismatch
as the primary no-pixel cause. Next bounded unit should use the real fd6 sysmem single-triangle `.rd`/cffdump packet
diff against current H3 rather than isolated HLSQ/output/raster guesses, and admit only direct-sysmem-compatible missing
packet groups.

V3280/V3281 continued that `.rd`/cffdump direction with the remaining coherent color-target group from local A640
cffdump draw[2], rather than writing speculative legacy `HLSQ_CONTROL_*` registers. V3280 kept the V3278 direct-render,
sysmem, varying/IJ, and RGBA8 baseline but changed the MRT0 target to the cffdump flag-MRT group:
`RB_RENDER_CNTL=0x10010`, `RB_MRT0_BUF_INFO=0x330`, `RB_COLOR_FLAG_BUFFER[0].PITCH=0x4001`, plus a bounded 4 KiB
color-flag BO and telemetry for flag-buffer readback. The source unit built `0.11.66
(v3280-gpu-h3-flag-mrt-probe)` with SHA256
`e295699879f3bb30bff85cfebaeb46b9c4ffd3909d0289bd882e3b2a9decfc19`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`; one verbose selftest attempt lost the serial END marker
after partial output, then a short selftest rerun passed). V3281 live telemetry confirmed `rb_render_cntl=0x10010`,
`rb_mrt0_buf_info=0x330`, `color_flag_buffer_pitch=0x4001`, `pm4_dwords=311`, `state_reg_writes=121`, and
`vfd_reg_writes=14`. Two H3 runs submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`,
warm `total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained unchanged
(`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), and the new flag buffer also
stayed unchanged (`color_flag_changed_count=0`, `color_flag0=0x0`) with no focused KGSL/GPU/GMU/A640 fault, hang,
snapshot, timeout, opcode, SMMU/IOMMU, or page-fault signature. This removes the flag-MRT color-target mismatch as
the primary no-pixel cause. Next bounded unit should continue the real fd6 sysmem single-triangle `.rd`/cffdump diff
against current H3 and admit only direct-sysmem-compatible packet groups; do not return to isolated HLSQ/output/raster
guesses unless the diff proves that packet group is actually missing.

V3282/V3283 then tested the first A640 device-DB init-magic candidate from the operator-staged
`/tmp/a90-mesa-gpu-src/a640_magic_regs.txt`, adding only `RB_DBG_ECO_CNTL=0x04100000` at register `0x8e04` before
H3 shader and draw state while preserving the V3280 flag-MRT target group. The source unit built `0.11.67
(v3282-gpu-h3-rb-dbg-eco-probe)` with SHA256
`f2afd2eda2b8632fff582e79c3defe5b9520ecb63d36e0498f3fced945fa9879`, flashed through `native_init_flash.py`, and
passed post-flash health (`selftest pass=12 warn=1 fail=0`; one immediate verbose selftest attempt lost framing after
prompt noise, then slow-mode `version`/`selftest` passed). V3283 live telemetry confirmed
`a640_magic_mode=rb-dbg-eco-only`, `rb_dbg_eco_cntl_reg=0x8e04`, `rb_dbg_eco_cntl=0x4100000`,
`a640_init_magic_reg_writes=1`, `pm4_dwords=313`, `state_reg_writes=121`, and `vfd_reg_writes=14`. Two H3 runs
submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`) and
post-probe selftest stayed clean. Readback remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`), and the color-flag buffer also stayed unchanged (`color_flag_changed_count=0`,
`color_flag0=0x0`) with no focused KGSL/GPU/Adreno/A6xx/A640 fault, hang, snapshot, timeout, opcode, SMMU/IOMMU, or
page-fault signature in the recent dmesg tail. This removes `RB_DBG_ECO_CNTL` alone as the primary no-pixel cause. Next
bounded unit should follow the operator probe order by adding the rest of the non-zero A640 device-DB magic block
(`SP_CHICKEN_BITS`, `TPL1_DBG_ECO_CNTL`, `VPC_DBG_ECO_CNTL`, `RB_RBP_CNTL`, `PC_MODE_CNTL`, `PC_POWER_CNTL`,
`VFD_POWER_CNTL`, and `UCHE_UNKNOWN_0E12`) while keeping `RB_CCU_CNTL` separate.

V3284/V3285 followed that probe order and added the full non-zero A640/a6xx_gen2 device-DB magic block before H3 shader
and draw state: `RB_DBG_ECO_CNTL=0x04100000`, `SP_CHICKEN_BITS=0x420`, `TPL1_DBG_ECO_CNTL=0x8000`,
`VPC_DBG_ECO_CNTL=0x02000000`, `RB_RBP_CNTL=1`, `PC_MODE_CNTL=0x1f`, `PC_POWER_CNTL=1`, `VFD_POWER_CNTL=1`, and
`UCHE_UNKNOWN_0E12=1`. Because the block raises the expected H3 PM4 size to `329` dwords, V3284 also raised the shared
GPU command-buffer guard from `320` to `384` dwords. The source unit built `0.11.68
(v3284-gpu-h3-a640-magic-block-probe)` with SHA256
`7eacd6670856beaeea681d1df6deb3169bcee68fe730c8dcb050b6fdc28b6572`, flashed through `native_init_flash.py`, and
passed flash-helper version/status plus post-flash health (`selftest pass=12 warn=1 fail=0`; one immediate standalone
selftest attempt lost serial framing after truncated input, then slow-mode `version`/`selftest` passed). V3285 live
telemetry confirmed `a640_magic_mode=nonzero-block`, `a640_init_magic_reg_writes=9`, `pm4_dwords=329`,
`state_reg_writes=121`, and `vfd_reg_writes=14`. Two H3 runs submitted and retired cleanly (`submit_rc=0`,
`wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=12`) and post-probe selftest stayed clean. Readback remained
unchanged (`readback_changed_count=0`, `readback0=0x20202020`, `readback_center=0x20202020`), and the color-flag buffer
also stayed unchanged (`color_flag_changed_count=0`, `color_flag0=0x0`). Focused dmesg showed no GPU fault, hang,
snapshot, opcode, SMMU/IOMMU, or page-fault signature; only an unrelated modem firmware timeout and expected first-use
`a640_zap` load/reset lines matched the filter. This removes the A640 magic-reg block as the primary no-pixel cause.
Next bounded unit should stop isolated magic/register guesses and use the definitive packet-level path: capture or
assemble a real Mesa/freedreno A640 sysmem single-triangle `.rd`/cffdump stream and diff it against current H3,
admitting only remaining direct-sysmem-compatible packet groups.

V3286 converted that packet-level direction into a host-only cffdump/current-H3 diff using the local A640 freedreno
trace at `/tmp/a90-h3-cffdump/triangle_list.rd` (SHA256
`2fe5c6781058bb698e373bef3d2a9cffe4f04503d9fe3c9f81f2938cdb053011`) and decoded
`triangle_summary.txt`. No boot image was built or flashed. The diff confirms the already-tested/closed H3 core state
now matches the reference draw for `RB_RENDER_CNTL`, `RB_MRT[0].CONTROL`, `RB_MRT[0].BUF_INFO`,
`SP_PS_OUTPUT_CNTL`, `SP_PS_MRT[0].REG`, `VPC_VS_CNTL`, `VPC_PS_CNTL`, SP/RB output masks, raster state, and most
program routing. It also separates unsafe/contextual differences from candidates: the trace draw is a GMEM pass with a
later resolve, so `RB_CCU_CNTL`, `GRAS_SC_BIN_CNTL`, `RB_CNTL`, target-size pitches/scissors/viewports, and addresses
are not direct H3 copy targets. The top remaining deltas are now: (1) the coherent VFD/VS input contract
(`VFD_CNTL_0=0x303`, 36-byte stride, three fetch/decode streams, vertex-id in `r2.y`) versus current H3's single
2-float fetch (`VFD_CNTL_0=0x101`, 8-byte stride); (2) the smaller direct-sysmem-compatible blend/output group
(`SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, `RB_MRT[0].BLEND_CONTROL=0x08040804`) versus current zeros; and
(3) `SP_VS_CONST_CONFIG=0x101`, which is coupled to the reference VS constants and should not be copied alone. Next
bounded unit should prefer a coherent reference-contract VFD/VS replay, or, if a smaller live probe is desired first,
test only the blend/output-state group together under the existing H3 timeout/readback guards.

V3287 then implemented the top V3286 packet-diff candidate as a source/build unit while preserving the already-tested
V3284/V3285 A640 non-zero init-magic block. H3 now uses the cffdump-shaped VFD/VS input contract:
`VFD_CNTL_0=0x303`, `VFD_CNTL_1=0xfcfcfc09`, three fetch/decode streams, 36-byte vertex stride, and vertex payload
`r0.xyzw` varying color + `r1.xyzw` clip-space position + `r2.x` integer sideband. The VS was changed from the older
constant-built position path to a constant-free `r1.xyzw -> r2.xyzw` pass-through while preserving `r0` for the existing
cffdump barycentric FS. The source unit built `0.11.69 (v3287-gpu-h3-vfd-vs-contract-probe)` with SHA256
`560538eb253daa013971a2492575f80797082b3359d51e159c3a76e990aa9255`; no device flash or live readback was run in this
build unit. Focused source tests and shader/cffdump audits passed. Next live unit, if selected, should flash V3287
through `native_init_flash.py` under the usual rollback gates and check whether `readback_changed_count` or the
color-flag buffer changes before moving to the smaller blend/output-state group.

V3288 flashed that V3287 candidate through `native_init_flash.py` after reconfirming the rollback images and TWRP
recovery. Flash-helper verification matched local, remote, and boot readback-prefix SHA
`560538eb253daa013971a2492575f80797082b3359d51e159c3a76e990aa9255`; resident came back as `0.11.69
(v3287-gpu-h3-vfd-vs-contract-probe)`, and post-flash/post-probe selftest stayed `pass=12 warn=1 fail=0`. Two H3
draw-envelope runs confirmed the VFD/VS contract was live (`VFD_CNTL_0=0x303`, `VFD_CNTL_1=0xfcfcfc09`, fetch instrs
`0xc8200000/0xc8200200/0x44c00400`, dest cntls `0xf/0x4f/0x81`, stride `36`, `pm4_dwords=335`, `vfd_reg_writes=20`),
submitted and retired cleanly (`submit_rc=0`, `wait_rc=0`, `retired_timestamp=1`, warm `total_elapsed_ms=11`), but
readback and the color-flag buffer remained unchanged (`readback_changed_count=0`, `readback0=0x20202020`,
`readback_center=0x20202020`, `color_flag_changed_count=0`, `color_flag0=0x0`). Focused dmesg showed no GPU fault,
hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature; only the unrelated modem firmware wait timeout and expected
`a640_zap` first-use lines matched. This removes the VFD/VS input-contract mismatch as the primary no-pixel cause. Next
bounded live unit should test the smaller direct-sysmem-compatible blend/output group from V3286:
`SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804`.

V3289 implemented that direct-sysmem-compatible blend/output group as a source/build unit on top of the V3288
live-tested VFD/VS contract. H3 now emits `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and
`RB_MRT[0].BLEND_CONTROL=0x08040804`, while PM4 size and register counts stay unchanged (`pm4_dwords=335`,
`state_reg_writes=121`, `vfd_reg_writes=20`). The source unit built `0.11.70
(v3289-gpu-h3-blend-output-probe)` with SHA256
`10e43f8fc8c751774d830b797b783f3a058f10efaeeccab5d0dd57f806e6f34d`; no device flash or live readback was run in this
build unit. Focused source tests, shader-byte audit, cffdump current-H3 model tests, and the boot build passed. Next
live unit should flash V3289 through `native_init_flash.py` under the usual rollback gates and check whether this
blend/output group changes `readback_changed_count` or the color-flag buffer.

V3290 flashed the V3289 artifact through `native_init_flash.py` after reconfirming the rollback images and TWRP
recovery. Flash-helper verification matched local, remote, and boot readback-prefix SHA
`10e43f8fc8c751774d830b797b783f3a058f10efaeeccab5d0dd57f806e6f34d`; resident came back as `0.11.70
(v3289-gpu-h3-blend-output-probe)`, and post-flash/post-probe health stayed clean (`selftest pass=12 warn=1 fail=0`;
one immediate selftest attempt lost serial framing after truncated input, then slow-mode selftest passed). Two H3
draw-envelope runs submitted and retired cleanly and, for the first time, changed sysmem readback and the color-flag
buffer: run 1 reported `readback_changed_count=672`, `readback_first_changed_index=9216`,
`readback_first_changed_value=0xfb9802e6`, `color_flag_changed_count=32`, `color_flag_first_changed_index=256`,
`color_flag_first_changed_value=0x1010101`, `total_elapsed_ms=30`; warm run 2 repeated the same changed counts and
first-changed values with `total_elapsed_ms=12`. `readback0` and `readback_center` remained the clear value
`0x20202020`, so this is H4 first-pixel/readback proof rather than H5 visible/centered presentation. Focused dmesg
showed no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature; only the unrelated WLAN firmware wait
timeout matched the filter. This confirms the missing load-bearing group was the blend/output state, not the already
ruled-out A640 magic block or VFD/VS input contract alone. Next bounded unit is H5: present or blit the proven offscreen
triangle result to `/dev/dri/card0`, or first inspect/reposition the changed region if a centered display proof is
required.

V3291 implemented the first H5 source/build unit on top of that H4 proof. The new `gpu h5-triangle-kms-probe` /
`gpu triangle-kms-probe` command reuses the V3290-proven H3 draw/readback path, asks the KGSL child to return a bounded
`128x128` color-buffer snapshot before cleanup, keeps KMS ownership in the parent init process, scales the raw H3
readback into the existing `/dev/dri/card0` dumb framebuffer, and presents it with the existing `SETCRTC` path. This is
intentionally a raw tile-order visualization because the H3 target is still `RGBA8 tile6_3`; zero-copy scanout,
scaled-plane presentation, proprietary blob, full Mesa compiler port, and power writes are not attempted. The source
unit built `0.11.71 (v3291-gpu-h5-triangle-kms-probe)` with SHA256
`eea6c10b184ea19ce7c391899dae26c4bbf8b8ed4ac828409355b1d789a67f95`; no device flash or live KMS presentation was run
in this build unit. Focused V3291 source tests, existing H3 source regression tests, `py_compile`, `git diff --check`,
and the boot build passed. One legacy V3204 G5 source test was inspected separately and is stale against the current
shared G4 event helper count, so it was not used as a V3291 pass criterion. Next live unit should flash V3291 through
`native_init_flash.py` under the usual rollback gates and run
`gpu h5-triangle-kms-probe --timeout-ms 5000 --materialize-devnode`, followed by post-probe selftest and focused GPU
dmesg filtering. H5 should only be claimed if the command reports `gpu.h5.kms.result=h3-readback-kms-presented` and the
panel visibly presents the H3 readback proof surface.

V3292 flashed that V3291 artifact through `native_init_flash.py` after reconfirming the rollback images and TWRP
recovery. Flash-helper verification matched local, remote, and boot readback-prefix SHA
`eea6c10b184ea19ce7c391899dae26c4bbf8b8ed4ac828409355b1d789a67f95`; resident came back as `0.11.71
(v3291-gpu-h5-triangle-kms-probe)`, and health stayed clean (`selftest pass=12 warn=1 fail=0`; one immediate standalone
selftest attempt lost serial framing due `AT` fragment noise, then `version` and slow-mode selftest passed). The live
H5 command completed in `53ms` with `gpu.h5.kms.result=h3-readback-kms-presented`: the H3 child returned the full
`66368`-byte payload, H3 again reported `readback_changed_count=672`, `readback_first_changed_index=9216`,
`readback_first_changed_value=0xfb9802e6`, and `color_flag_changed_count=32`, then the parent KMS path reported
`begin_frame_rc=0`, `fb_width=1080`, `fb_height=2400`, `fb_stride=4352`, `blit_rc=0`,
`blit_rect=28,176,1024,1024`, `blit_scale=8`, `present_rc=0`, and
`gpu-h5-triangle-kms: presented framebuffer 1080x2400 on crtc=133`. Post-probe selftest stayed clean, and focused dmesg
showed no GPU fault, hang, snapshot, opcode, SMMU/IOMMU, or page-fault signature; only expected `a640_zap` load/reset
lines matched. This device-proves the H5 KMS presentation path by serial telemetry. The only remaining H5 quality
checkpoint is human visual confirmation of the panel, because this run has no camera/display capture and the current
surface is a raw `RGBA8 tile6_3` readback visualization. If the operator requires a literal centered triangle rather
than the raw proof surface, the next bounded unit should add tile/format conversion or render into a KMS-friendly linear
presentation buffer before moving to after-triangle backlog.

V3293/V3294 implemented and live-tested that literal-presentation direction by adding a bounded A6xx A2D copy from the
V3290-proven `RGBA8 tile6_3` + flag render target into a separate linear RGBA8 snapshot before KMS presentation. The
source unit built `0.11.72 (v3293-gpu-h5-linear-triangle-kms-probe)` with SHA256
`59b7973d99a7d5a44384d3390ad261231f9fab1b16ee21fce48b9f0537e89e70`, raised the shared GPU command-buffer guard to
`512` dwords for the added A2D PM4 stage, and changed H5 telemetry to
`scope=first-triangle-h5-a2d-linearized-h3-readback-to-kms-probe` with raw tile-order visualization disabled. V3294
flashed that exact artifact through `native_init_flash.py` after reconfirming rollback images/TWRP; resident came back
as `0.11.72`, post-flash and post-probe selftest stayed `pass=12 warn=1 fail=0` (one busy/framing hiccup was recovered
by restarting the managed bridge), and the live command completed in `58ms` with
`gpu.h5.kms.result=h3-linear-readback-kms-presented`. H3 still reported the V3290 proof counts
(`readback_changed_count=672`, `readback_first_changed_index=9216`, `color_flag_changed_count=32`), the linear stage
reported `h3_linear_blit_attempted=1`, `h3_linear_readback0=0x0`, and
`h3_linear_readback_center=0xff00b900`, and KMS presented a `1024x1024` scaled region on the `1080x2400` framebuffer
with `present_rc=0`. Focused dmesg showed no GPU fault/hang/snapshot/opcode/SMMU/IOMMU/page-fault signature; only
expected `a640_zap` load/reset lines matched. Caveat: `h3_linear_readback_changed_count=16384` is inflated because the
linear destination was initialized to the old `0x20202020` sentinel while A2D resolves untouched/clear areas to
`0x00000000`; this proves A2D linearization + KMS presentation, but the next bounded unit should zero-clear the linear
buffer and add `linear_nonzero_count`, first-nonzero value, exterior-corner zero samples, and interior sample telemetry
before claiming a strict literal triangle proof and moving to the after-triangle backlog.

V3295/V3296 then removed that caveat and **closed the H0-H5 first-triangle ladder**. V3295 changed the linear
destination to zero-clear and strengthened the H5 gate to require true non-zero pixels, a non-zero center sample, and
zero exterior corner samples before KMS presentation. The source build produced `0.11.73
(v3295-gpu-h5-strict-triangle-kms-probe)` with SHA256
`f20b4ff3ab76fd0c8d854ede72f13079cf0f90fa248dad059768647fa8a7e4ae`. V3296 flashed that artifact through
`native_init_flash.py` after reconfirming rollback images/TWRP; resident came back as `0.11.73`, post-flash and
post-probe selftest stayed `pass=12 warn=1 fail=0`, and the clean rerun of
`gpu h5-triangle-kms-probe --timeout-ms 5000 --materialize-devnode` completed in `55ms` with
`gpu.h5.kms.result=h3-linear-readback-kms-presented`. Strict proof telemetry passed:
`h3_linear_readback_nonzero_count=2016`, `h3_linear_readback_first_nonzero_index=8256`,
`h3_linear_readback_first_nonzero_value=0xff00b900`, `h3_linear_readback_center=0xff00b900`,
`h3_linear_readback0=0x0`, `h3_linear_readback_corner_tr=0x0`, `h3_linear_readback_corner_bl=0x0`,
`h3_linear_readback_corner_br=0x0`, `h3_linear_center_nonzero=1`, `h3_linear_exterior_corners_zero=1`, and
`strict_linear_triangle_sample_proof=1`; KMS reported `present_rc=0` for a `1024x1024` scaled region on the
`1080x2400` framebuffer. Focused dmesg showed no GPU fault/hang/snapshot/opcode/SMMU/IOMMU/page-fault signature
(only expected `a640_zap` load/reset and an unrelated modem firmware wait timeout). This is the first real GPU
triangle proof: vertex buffer + VS + rasterizer + FS + sysmem color/flag write + A2D linearization + KMS presentation,
all within the freedreno/KGSL-direct recoverable envelope. Next work should move to the after-triangle backlog, starting
with a small visible compute/fragment-shader demo or extraction of the now-proven GPU path.

V3297/V3298 then closed the operator sensory H5 gate. V3297 kept the strict proof path but changed presentation from a
raw proof surface to a recognizable KMS screen: it finds the A2D-linearized nonzero triangle bbox, scales that mask into
a centered high-contrast solid triangle, stops autohud before present, and holds the framebuffer on screen. The source
build produced `0.11.74 (v3297-gpu-h5-visual-triangle-hold-probe)` with SHA256
`a0728c476f7fa6793d28fc930d7dcdf8c3eac99dc3db44e7044274c5431f4e80`. V3298 flashed that artifact through
`native_init_flash.py` after reconfirming rollback images/TWRP; resident came back as `0.11.74`, post-flash and
post-probe selftest stayed `pass=12 warn=1 fail=0`, and after `hide` cleared the auto menu the live command
`gpu h5-triangle-kms-probe --timeout-ms 5000 --hold-ms 30000 --materialize-devnode` completed in `30159ms` with
`gpu.h5.kms.result=h3-visual-triangle-kms-presented` and `gpu.h5.vis.result=triangle-presented-held`. Strict proof
telemetry still passed (`h3_linear_readback_nonzero_count=2016`, `h3_linear_readback_center=0xff00b900`,
`h3_linear_exterior_corners_zero=1`, `strict_linear_triangle_sample_proof=1`), the visible bbox was
`64,64,126,126`, and KMS presented a centered `945x945` visual triangle region at `67,727` on the `1080x2400`
framebuffer. The operator confirmed the triangle was visible on the panel during the hold. Focused dmesg again showed
no GPU fault/hang/snapshot/opcode/SMMU/IOMMU/page-fault signature. The first-triangle epic is now closed both by
telemetry and by human visual confirmation; the next rung is the after-triangle backlog.

**GPU roadmap — ORDERED CHAIN after the triangle (operator "full-steam" 2026-06-26; do NOT pre-build, pull each rung
only when reached, but the loop must flow rung→rung and NOT halt between them — re-charter the active-epic to the next
rung as each closes).** Honest ceiling acknowledged and accepted: native-init has NO OpenCL/Vulkan/CUDA (blob/Bionic
wall), so every kernel/shader is hand-assembled ir3 and this never becomes a general GPGPU server — the value is
*device-proven GPU capability + accelerating our own pipeline*, not third-party workloads.

- **① VISIBLE compute demo (DONE = C0→C3, V3303 eye-confirmed; e.g. Mandelbrot/particle → KMS).** Reuses the shader path minus the
  rasterizer; gives GPU compute a *screen consumer*. **Matrix/GPGPU math is absorbed here, NOT a standalone goal** —
  no module/library to load (OpenCL/BLAS = blob/Bionic wall; Mesa rusticl/turnip = full-stack port, unbounded), so any
  kernel is hand-assembled ir3; an abstract matmul with no consumer is the forbidden "capability with no consumer".
- **② GPU-ACCELERATED 2D = texturing + frame blit/scale (DONE + EYE-CONFIRMED, V3315).** Bring up the A6xx texture
  pipe (TPL1 sampler): render a textured fullscreen quad sampling an image, then use the GPU to scale/composite/blit
  frames — the demo player (Bad Apple/DOOM) blits via CPU `memcpy` today, so this makes the GPU a *real consumer of
  existing work* (frees the CPU, enables higher res/fps) and exercises the sampler path. This is the third real call
  site for the rule-of-three extraction and the natural motivator for zero-copy.
- **③ Modularization = EXTRACTION, not an epic.** Do not design a `a90_gpu` API upfront. With triangle + compute +
  accel-blit as three real consumers pulling on the same G0-G3 core (rule of three), *extract* the common KGSL
  submit/fence/buffer layer into an internal helper as a bounded refactor; formalize an API only after the call sites
  reveal its shape.
- **④ zero-copy KMS/dmabuf scanout** (G5 CPU-copy → direct GPU-buffer scanout; crux = A6xx tiling/UBWC ↔ display
  modifier) — efficiency win; do after ② makes CPU-copy the bottleneck. Closing ④ closes the GPU epic.

## Stop conditions

- **CLOSED EPIC (operator-chartered 2026-06-19) = Video PLAYBACK pipeline on the EXISTING KMS display**
  (see the chartered Video section). Audio is DONE: CORE device-proven + promoted `0.10.0` + first demo
  (chime) passing; **audio Tier-C polish is now optional background, NOT the primary track — do not grind
  it.** **The display is ALREADY proven (`a90_kms.c` drives `/dev/dri/card0` for HUD/menu) — this is a
  playback-pipeline problem, NOT a display-feasibility probe.** **Pipeline + Bad Apple demo DONE ✅ (V2947 full-song
  / V2964 smooth, init `0.10.49`):** double-buffer/page-flip/blit, frame+PCM streaming, A/V sync, and the full-song
  Player HUD (0 dropped, ~30 fps, audible synced audio, BEAT FLASH + read-only dashboard). **Remaining is optional,
  non-blocking:** UI polish (dashboard/fonts/beat-flash). **Next chartered rung = 🎯 Nyan Cat (2026-06-20), with
  format-efficiency Tier-1 (compact on-device decode, e.g. palette/RLE) folded in as Nyan's enabler — bound to real
  content, not a standalone format epic.**
  Recoverable boot-partition flashes only, rollback `v2321`. **Bright lines:** no backlight/PMIC/PWM/regulator/GDSC
  writes; no from-scratch panel re-init; forbidden partitions absolute. Venus HW decode NOT needed (pre-rendered frames).
- **GPU EPIC CLOSED = ④ zero-copy KMS/dmabuf scanout (Z0→Z3) is DONE + EYE-CONFIRMED; NEXT = SoftAP server-endgame.**
  Four GPU rungs are CLOSED + EYE-CONFIRMED: first-triangle H0→H5 (GREEN RIGHT-TRIANGLE; `V3295/V3296`, `0.11.73`),
  COMPUTE demo C0→C3 (rainbow/grid pattern; `V3303`, `0.11.77`), GPU-accel 2D D0→D3 (held Bad Apple GPU-blit frame;
  `V3315`, `0.11.87`), and on-panel SYSTEM MONITOR M0→M3 (held GPU-drawn graphs; `V3321`, `selftest fail=0`), which
  DELIVERED the ③ rule-of-three extraction (shared KGSL submit/fence/buffer/texture/present helper). Per the operator
  decision (2026-06-27: "④ 먼저 닫고 SoftAP"), V3335 made the GPU-rendered buffer the full-panel scanout buffer directly
  (G5 CPU-copy → direct GPU-buffer scan-out) through the primary SETCRTC path. KMS present + GPU only, NO power writes
  (bright-line-trivially safe). **NEXT = pivot to the SoftAP server-endgame** (highest-ROI feature toward the
  headless-server-distro). Bluetooth / sensors / haptics remain
  reference-only until separately chartered (attended daytime quick-wins).
  **Z-ladder status (2026-06-27):** Z2 is closed: V3326 rendered the monitor graph directly into a DRM msm scanout GEM
  exported as PRIME/imported into KGSL, with `kms_copy_attempted=0`, `kms_present_attempted=0`, `changed_count=691200`,
  semantic exact match `64/64`, and post-probe `selftest fail=0`. Z3 overlay-plane scanout was intentionally abandoned
  after the overlay wall. V3327 fixed
  the imported render-target shape but hit non-master-fd `EACCES`; V3328 reused the KMS master fd and moved the failure
  to `EINVAL`; V3329 added atomic plane commit; V3330 switched the target to a KMS dumb scanout buffer; V3331 filtered
  for an idle overlay plane (`plane_id=90`, `selected_type=0`); V3332 added `zpos/alpha/rotation`; V3333 proved the
  selected overlay has no `IN_FORMATS` blob and is treated LINEAR-capable while lacking `pixel blend mode`; V3334 proved
  `DRM_MODE_ATOMIC_ALLOW_MODESET` does not change the result (`atomic_flags=0x400`, still `atomic_commit_rc=-22`).
  V3335 then rendered into a full-screen KMS dumb buffer imported into KGSL and presented that same framebuffer through
  primary SETCRTC with `kms_copy_attempted=0`, `present_rc=0`, `restore_rc=0`, semantic exact `64/64`, post-probe
  `selftest fail=0`, and operator eye-confirmation that the held graph was visible and remained on-panel.
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
- **KGSL `/dev/kgsl-3d0` open-block — RESOLVED (V3184, 2026-06-25).** The unbounded-`open()` hang was GPU
  **firmware visibility / GMU cold-start blocking**, fixed cleanly via `firmware_class.path` prep (pure sysfs,
  no power write); bounded open now returns. This unblocked the full G0→G5 GPU first-light ladder (DONE, V3206).
  Still **NEVER** run an unbounded blocking `open()` as a loop unit (use timeout-guarded bounded probes), and GPU
  work stays legitimate driver bring-up — it does **NOT** reopen kernel-security recon (no CVE/UAF/exploit-dev).
- **No doc / metadata / inventory cleanup as a track** (anti-churn trap).
- **Never reopen** external SDX50M/eSoC/PCIe/MHI/GDSC/PMIC/GPIO paths for internal `wlan0`.
