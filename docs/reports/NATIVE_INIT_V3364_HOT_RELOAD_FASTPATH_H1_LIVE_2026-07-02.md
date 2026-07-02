# Native Init V3364 Hot-Reload Fast-Path H1 Live (clean + 2.18s)

- Cycle: `V3364` (H1 live)
- Decision: `v3364-hot-reload-fastpath-h1-clean-and-fast`
- Scope: the `A90_RELOADED` fast path makes a hot-reload clean (no re-init errors) and near-instant.
- Device action: TWRP flash V3364, stage its init ELF, `reload` (twice), then rollback to v2321.
- Final device state: resident on v2321 `0.9.285`, `selftest fail=0` (clean checkpoint).

## Background

H0 (V3363) proved PID1 can replace itself via `execve()` with no reboot, but the re-exec'd init
re-ran the FULL boot path and errored on already-live subsystems: `autohud SETCRTC EACCES` (DRM
master re-acquire) and `netservice NCM start failed EIO`. H1 adds an `A90_RELOADED`-gated fast path
in `main()` (v724/90_main.inc.c — the compiled main, not v319/90_main.inc.c) that, on a reload,
skips the boot splash delay and skips re-initializing already-live services (qrtr/ssctl boot-once,
autohud, netservice, rshell, wifi-autoconnect, audio boot chime), going straight to the serial
control shell. Every guard is `if (!a90_reloaded)`, so a normal kernel-spawned boot (A90_RELOADED
unset) is behavior-identical.

## Live sequence

1. TWRP-flashed V3364 (`0.11.125`, `934f7038…`). Normal boot verified `selftest pass=12 fail=0` —
   the fast-path guards do not change normal boot.
2. Staged the running `/init` to `/mnt/sdext/a90/flash-staging/init_reload_h1` (1,789,328 bytes, SHA
   `f2dbb4d6…`).
3. `hide`, then `reload INIT-RELOAD-EXECVE /mnt/sdext/a90/flash-staging/init_reload_h1 f2dbb4d6…`
   (run twice: once to verify clean, once to measure timing).

## Result — clean and fast

- Reload markers: `candidate=ok size=1789328 elf=1`, `expected_sha_match=1`, `execve_now`, no
  `execve=fail` → execve succeeded.
- Host serial by-id NEVER disappeared → no USB re-enumeration, no reboot.
- The re-exec'd init printed `# Hot-reload: skipping autohud/netservice/rshell re-init (already
  live).` and the `0.11.125` banner.
- **H0 degradations fixed**: `SETCRTC failed` count = 0 and `Netservice: start failed` count = 0 in
  the re-exec'd init's output (both were present in H0).
- `version` returns `0.11.125`, `selftest fail=0` after the reload.
- **Timing: `reload` command → new init serial shell ready = 2.18 s** (measured from the reload send
  to the new init's `USB ACM serial console ready` in the bridge capture), with the serial link
  continuous throughout.

## Speed comparison

| path | time | note |
| --- | --- | --- |
| TWRP full flash cycle | ~65 s | recovery round-trip + 2 reboots |
| native self-flash cycle | ~50.7 s | one reboot (V3362 tuned) |
| reboot floor | ~32.5 s | ~17 s kernel (hard floor) + ~14 s native-init |
| **hot-reload (init-only change)** | **2.18 s** | no flash, no reboot, no USB re-enum |

For an init-only iteration (most audio/wifi/gpu/command work), hot-reload is ~15-30x faster than a
reboot/flash cycle. It does not replace the checked flash helper for kernel/ramdisk/boot-image
changes, and a broken new init that crashes early still panics PID1 (recover via reboot/TWRP;
mitigated by SHA-verified own-build + the always-present recovery envelope).

## Boundaries / next

- H1 reloaded a self-staged copy of the exact running init (proves clean+fast mechanism). H2 =
  reload a genuinely-changed init build (version bump only in the reloaded binary) to prove new code
  takes effect across a reload, which is the actual research-cycle use.
- The reloaded init is serial-control-focused: it deliberately does NOT re-init NCM/HUD/rshell (they
  either stay live from the prior init or are simply absent). For iterations that need a fresh NCM or
  a clean HUD, use a normal flash/reboot.
- Rolled back to clean v2321 (`selftest fail=0`). Recovery envelope intact.
