# S22+ M34 S10B0 Module-Load Prefix Live Result (2026-07-09)

## Verdict

S10B0 was executed once under the bounded `AGENTS.md` boot-only exception and is
now consumed. The first-prefix `/proc/modules` predicate did not HIT.

Result:

```text
download-beacon-miss-parked-manual-download-required
```

Machine-readable evidence:

```text
workspace/private/runs/s22plus_m34_s10b0_live_20260709T103800Z/result.json
workspace/private/runs/s22plus_m34_s10b0_live_20260709T103800Z/timeline.json
```

The selected device serial is intentionally not recorded in this report.

## Candidate

S10B0 starts from the S9/S10A 89-module runtime recipe and narrows the one-bit
beacon to the first prefix predicate only:

```text
stage: S10B0
module_load_probe: proc_modules_prefix_1
prefix_modules: cmd_db
true_action: reboot_download
false_action: park
```

Pinned artifact hashes:

```text
AP.tar.md5 SHA256: c117d8789b4ed990afd047ef3a6bb8d32f0b7b5d76bdce58eecf8ae98725d47c
Padded boot.img SHA256: a30120d094d3484b6b4234e0a285f6c26e95120f032ed9ec3671fd287661b610
/init SHA256: 50bd942c92d6aad3b143e1f215c0e7a313819994f5dbfa580c11666d32d5f761
Module-list SHA256: c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26
Template source SHA256: 6ac888ddf29e559a9a9b7522eda4edd54c5a38264782dddd2bd5c80d6d8e21a6
Known booting Magisk base boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The candidate did not proceed to downstream configfs, UDC bind, TypeC role
writes, ssusb role writes, soft_connect, FunctionFS, stock composite, display,
Android handoff, Magisk handoff, persistent mounts, or block writes.

## Live Result

The helper passed default dry-run first, then flashed only the pinned S10B0 boot
AP. The original Odin endpoint disconnected after candidate transfer. No new
Odin Download endpoint appeared during the 90 second observation window.

The candidate therefore parked and required manual Download rollback. The
operator reported RDX then Download entry. The helper detected the manual
Download endpoint and flashed the pinned Magisk boot-only rollback AP.

Result JSON summary:

```text
schema: s22plus_m34_s10b0_result_v1
stage: S10B0
result: download-beacon-miss-parked-manual-download-required
rc: 5
rollback_target: magisk
base_boot_sha256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Timeline events recorded by the live helper:

```text
live_session_start: 2026-07-09T10:38:03.943709Z
candidate_flash_start: 2026-07-09T10:38:15.142650Z
candidate_flash_done: 2026-07-09T10:38:16.646490Z
candidate_boot_ready: 2026-07-09T10:38:17.930470Z
rollback_flash_start: 2026-07-09T10:40:12.828004Z
rollback_flash_done: 2026-07-09T10:40:14.190451Z
live_session_end: 2026-07-09T10:44:15.093255Z
```

The timeline lacks `rollback_boot_ready` because the old verifier timed out on
PATH `su`; see the correction below.

## Correction

The live helper's `rc=5` was a verifier false-negative, not proof that rollback
failed. After the run, Android was booted and the boot partition matched the
known Magisk baseline:

```text
sys.boot_completed: 1
ro.product.device: g0q
ro.build.version.incremental: S906NKSS7FYG8
ro.boot.boot_recovery: 0
ro.boot.verifiedbootstate: orange
boot SHA256: 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Root was present through `/debug_ramdisk/su`, while PATH `su` was absent:

```text
su -c id: /system/bin/sh: su: inaccessible or not found
/debug_ramdisk/su -c id: uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

Codex fixed the shared S22 live-gate helper to:

```text
1. Try PATH su first.
2. Fall back to /debug_ramdisk/su.
3. Prefix root payloads with runtime core dump suppression:
   printf /dev/null > /proc/sys/kernel/core_pattern 2>/dev/null || true
```

A follow-up S10B0 default dry-run against the current Android baseline passed:

```text
workspace/private/runs/s22plus_m34_s10b0_root_fallback_dryrun_20260709T110121Z/
root_probe=debug_ramdisk_su
current_boot_hash_rc=0
```

## Storage Cleanup

The post-run storage warning was caused by ART core dumps under `/data/log/core`,
not by `/sdcard` media.

Measured before cleanup:

```text
/data: 223G used, 0 available, 100%
/data/log/core: 231172340 KiB apparent du
core files: 1393
logical core bytes: 3261044846390
```

Public-safe triage was preserved before deletion:

```text
workspace/private/runs/s22plus_core_dump_triage_20260709T105028Z/
workspace/private/runs/s22plus_core_regen_probe_20260709T105514Z/
```

Representative core evidence:

```text
ELF 64-bit LSB core file, ARM aarch64
psargs: /system/bin/app_process /system/bin com.android.commands.content.Content call -
signal: SIGSEGV
fault address: 0
```

After explicit operator approval, `/data/log/core/core-*` was deleted and
runtime `core_pattern` was set to `/dev/null` to suppress immediate
regeneration from Magisk/ART helper crashes.

Measured after cleanup:

```text
/data: 223G total, 2.9G used, 220G available, 2%
core_pattern: /dev/null
core files: none observed after root fallback dry-run
```

This is a runtime Android cleanup only. It did not write boot, recovery, DTBO,
vendor_boot, vbmeta, EFS, modem, bootloader, RPMB, keymaster, or any other
forbidden partition.

## Interpretation

S10B0 MISS is sharper than S10A MISS: the first prefix predicate itself did not
HIT. Under the current one-bit channel, this means either `cmd_db` did not
appear in `/proc/modules` under native-init or `/proc/modules` cannot be trusted
at that point.

Do not advance to S10B1+ from this evidence alone. The next useful unit should
recover a stronger module-load observation channel, such as:

```text
first failed finit_module/insmod rc
per-module retained bitmask
retained text log before park
positive control proving /proc/modules readability under native-init
```

Only after that should the S10B ladder continue.

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m3_root_fallback.py \
  tests/test_s22plus_m34_s10b0_module_load_prefix_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py \
  --run-dir workspace/private/runs/s22plus_m34_s10b0_root_fallback_dryrun_20260709T110121Z
```

Result:

```text
py_compile: OK
unit tests: Ran 8, OK
S10B0 root-fallback dry-run: OK
```
