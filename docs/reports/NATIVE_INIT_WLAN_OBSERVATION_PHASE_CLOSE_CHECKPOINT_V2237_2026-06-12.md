# WLAN / Kernel-Observation Phase Close + Pre-Pivot Checkpoint (2026-06-12)

Closes the WLAN native-init and kernel-observation phases at a known-good checkpoint
before pivoting the project to kernel security research. No device flash was performed
to set this checkpoint — the resident, proven baseline is locked as-is.

## Checkpoint identity (the rollback/restore point)

- Baseline: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` — **RESIDENT and proven** (`version`/`status`/`selftest` clean at close).
- Image: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
- SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- Known-good fallback below it: `boot_linux_v48.img`.

Why v2237 and not the later v2254: v2254 (Wi-Fi detail surface, 0.9.272) is the most
complete promoted *artifact*, but it is not resident, its connect/DHCP/ping was not
re-validated on-image, and Wi-Fi credentials are currently absent (cannot run the N=3
both-band validation now). A safety checkpoint must favor reliability over completeness,
so the proven resident v2237 is the checkpoint. v2254 remains available in `boot_images/`.

## What is complete at this checkpoint

- **WLAN native-init: functional + deterministic.** `wlan0` connects end-to-end
  (associate → DHCP → external ping) on both bands; on-device command surface
  (`wifi status/scan/connect/dhcp/ping/cleanup`). V2236 strict success gating
  (`wpa_state=COMPLETED` required), V2237 bounded supplicant-exit poll + SIGKILL
  escalation (terminate-race retired).
- **Kernel observation: core goal achieved.** Exact KASLR slide solved
  (V2216 `codeword-slide-exact`; V2276 explained residual PC mismatches as ARM64 UAO
  alternatives). Observation toolkit built and proven: BPF read probes, `current_task`
  → cred read-chain (V2194), stackmap raw-IP recovery (V2195), stock kallsyms recovery
  under `kptr_restrict=4` (V2197), CFP/JOPP/ROPP characterization (V2198+). Firmware-class
  / workqueue load path observed and closed (V2280, target hits 0).

## Parked (documented future options, not abandoned)

- **WLAN structural epic** — move from spawn-per-connect imperative polling to a
  supervised long-lived `wpa_supplicant` + event subscription (ctrl-iface events +
  netlink). Would retire the timeout-ceiling and missing-reconnect gaps structurally
  rather than by patch. Real improvement, but a multi-iteration detour; deferred in
  favor of the kernel-research pivot. Re-validate with N=3 both-band regression (needs
  credentials) before promoting if revived.
- **Timeout-ceiling tuning + continuous link-health / auto-reconnect** (the V2235 hold
  exposed the drop-not-detected gap) — subsumed by the structural epic if revived.

## Boundary reached (not parked — out of read-only scope)

- **ROPP full-stack symbolization** needs the per-boot RKP-protected key (SYSREGKEY).
  Reading it requires kernel-write / RKP bypass / exploit = outside the read-only
  observation charter. This is a security-boundary stop, not a device-brick stop.

## Restore procedure (if the next phase destabilizes the device)

1. If native init still runs: re-flash the checkpoint via the checked helper —
   `python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
   workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img --from-native`
   then `a90ctl version/status/selftest`.
2. If the device fails to boot / drops to download mode: enter TWRP manually and flash
   the checkpoint image (or `boot_linux_v48.img` as the deeper fallback).
3. Verify SHA256 of the flashed image matches the identity above.

## Next phase

Kernel security research, recon-first (host-only, safe): device attack-surface
enumeration from the stock `.config` (enabled drivers / ioctls, esp. Samsung/Qualcomm),
and patch-level → unpatched `4.14.190` LPE (n-day) feasibility mapping, to assess whether
EL1 (kernel R/W) is realistically attemptable before any exploitation work. Exploit
confirmation / weaponization is interactive (not an unattended bypass loop) and framed
for responsible disclosure (the device is owner-operated). The WLAN/observation autonomous
loop contract (`GOAL.md`/`AGENTS.md`) is retired for this phase.
