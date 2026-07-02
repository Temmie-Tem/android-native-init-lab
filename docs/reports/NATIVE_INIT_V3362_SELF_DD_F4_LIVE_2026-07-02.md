# Native Init V3362 Self-dd F4-live Host Self-Flash (live pass)

- Cycle: `V3362`
- Decision: `v3362-self-dd-f4-live-host-self-flash-pass`
- Scope: first bounded F4-live host-orchestrated self-flash validation through
  `native_init_flash.py --experimental-self-write`.
- Device action: TWRP bootstrap flash of V3360, then host-orchestrated native self-flash of v2321.
- Final device state: resident on self-written v2321 `0.9.285`, `selftest fail=0` (clean checkpoint).

## Context

E1–E5 (identity writes) and F0–F3 (content-changing self-write, incl. F2 booting a self-written
candidate and F3 self-rollback to v2321) were already live-proven. F4 is the opt-in host integration
so a single host command orchestrates the proven device commands. Design §12.1 was amended
(2026-07-02, F4-live) to authorize exactly one bounded F4-live validation, locked to the v2321
rollback image with `boot-flash-f3` self-rollback semantics so both success and any restore converge
on the clean checkpoint. The live path stays fail-closed without `--self-write-live-authorized`.

## Pre-live gates

- Codex adversarial pre-live review: NO-GO (1 MUST-FIX: post-reboot version check used a substring
  match) → exact `version:` field parse applied → GO (0 MUST-FIX). WARN 1 (added plan JSON keys) and
  WARN 2 (unsealed local staging path, bounded because the device re-verifies SHA/version/header and
  fails closed) accepted as non-blocking.
- Rollback images present: v2321 `ca978551…`, v2237 `b2ea2d26…`, v48 `1c87fa59…`.
- Focused tests: `native_init_flash` 25 OK; `test_native_self_dd*` 14 OK; `git diff --check` clean.

## Live sequence

1. Bootstrap: `native_init_flash.py --from-native` flashed V3360 (`0.11.123`,
   `2989c292…`) through the checked helper/TWRP. Elapsed **65.3 s** (TWRP round-trip baseline).
   Resident verified `0.11.123`, `selftest pass=12 fail=0`, SD staging mounted rw.
2. F4-live host self-flash: `native_init_flash.py --experimental-self-write --self-write-mode f3
   --self-write-live-authorized --self-write-skip-stage` with the v2321 candidate.

Two attempts:

- Attempt 1 (tcpctl staging): failed at the staging step with `ConnectionRefused` from the device
  netcat listener (a tcpctl transport race; host NCM `192.168.7.1/24` and ping to the device were
  healthy). This is a transport-only failure and stopped **before** `boot-flash-plan` and any boot
  write; the device stayed on V3360 with the boot partition untouched. Also surfaced a preflight
  menu-busy on `pstore summary`.
- Host-only fixes: added a hide/settle before the preflight `pstore` group and before
  `boot-flash-plan` (the auto-menu returns `rc=-16 status=busy` for non-menu-allowed commands), and
  added `--self-write-skip-stage` to rely on the device-side `boot-flash-plan` SHA/version/header
  re-verification of an already-staged candidate (transport-independent, fails closed on mismatch).
- Attempt 2 (skip-stage, v2321 already present in the approved SD staging root at the identical
  size): full success.

## Result (attempt 2)

Event timeline (host-orchestrated, single command):

```text
preflight_start -> preflight_ok        (hide, version/status/selftest fail=0, pstore entries=0)
candidate_stage_start -> _done         (skipped: candidate pre-staged)
source_plan_start -> _done             (boot-flash-plan: expected_sha_match=1 version_marker_found=1
                                        result=ok source-plan-only)
self_write_start -> _done              (boot-flash-f3: expected_sha_match=1
                                        target_full_sha_after=b4abab92… target_full_match=1
                                        reboot_required=1 result=ok rollback-written-ready-to-reboot)
system_reboot_requested -> rollback_boot_wait -> rollback_boot_ready
```

- Device-side F3 target full SHA: `b4abab92a80674dbcccc410f089da77b303200c42c2c3f6a9e56a585348cc456`
  (v2321 image bytes overlaid on V3360 `before.full`; matches the V3360 §12.16 F3 target SHA).
- Measured timing: `self_flash_elapsed_sec` (boot-flash-plan + boot-flash-f3) = **18.0 s**;
  `reboot_boot_elapsed_sec` (reboot + re-enumerate + exact version + selftest) = **32.4 s**;
  total host command = **59.0 s**.
- Post-run independent Gate-2 verify: `version 0.9.285 build=v2321-usb-clean-identity-rodata`,
  `selftest pass=11 warn=1 fail=0`, serial identity `A90-LNX`.

## Interpretation

- The host tool orchestrated a real content-changing native self-flash end-to-end (preflight →
  source-plan → f3 self-write → host reboot → exact post-reboot verify) and landed on a clean,
  self-written v2321. F4-live passes.
- The self-write itself is fast (**18 s** for the deliberately full-64MiB proof-mode write, which a
  future prefix-only production write could shorten). The **reboot floor dominates** total time
  (32 s), so the self-flash total (59 s) is only modestly under the TWRP round-trip baseline (65 s);
  the structural win is avoiding the recovery round-trip and second reboot, not the write time.
- The self-written v2321 boot content equals the v2321 Android boot image (60,882,944 bytes) with the
  V3360 tail slack preserved past the image, exactly as a TWRP flash of a shorter image behaves; it
  is functionally the clean rollback checkpoint (`selftest fail=0`).

## Boundaries retained

- F4-live remains a bounded validation, locked to the v2321 candidate. It does not make self-write
  the default flash path; `native_init_flash.py` through TWRP stays the default recovery-grade path.
- Prefix-only production optimization, arbitrary non-v2321 self-flash candidates, raw host `dd`,
  fastboot, and any non-boot partition write remain gated by a future explicit amendment.
- Live tcpctl candidate staging is a separate transport-robustness item (attempt-1 netcat race); it
  was not required for this validation because the candidate was pre-staged and the device re-verifies
  it before any write.
