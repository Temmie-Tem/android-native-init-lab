# S22+ M18 P00 Prefix-Download Live Result (2026-07-08)

## Verdict

P00 live gate ran once and failed the self-download proof. The device was
recovered to the pinned Magisk boot baseline, and a read-only Android baseline
preflight passed after rollback.

The P00 AGENTS exception is now consumed/retired. P10 is not authorized.

## Live Result

- Candidate: M18 P00 prefix-download boot-only AP.
- Candidate AP SHA256:
  `b79ac94aac341ab5e4c08cb3c568c20be28bb71ccd4f1b047f712bd1dcf5225b`.
- Candidate Odin flash: `rc=0`.
- Original post-flash Odin endpoint: disconnected.
- Later Odin endpoint during the bounded self-download window: not observed.
- Result: no self-download endpoint observed (`m4t3_self_download_seen=0` in
  the shared observer log).
- Interpretation: P00 did not prove that the minimal native-init runtime reached
  the checkpoint that requests Samsung Download mode.

No P10, wider module prefix, DTBO, vendor_boot, recovery, vbmeta, or non-boot
flash was performed.

## Recovery

After the missing self-download proof, the operator entered Download mode
manually. The rollback helper flashed the pinned Magisk boot-only rollback AP:

- Rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
- Rollback Odin flash: `rc=0`.
- Android returned with `boot_completed=1`.
- Magisk root returned: `uid=0(root)`.
- `boot_recovery=0`, `vbstate=orange`.

Retained evidence after rollback:

- `/sys/fs/pstore`: empty.
- `/proc/last_kmsg`: readable, marker not found.
- P00 marker found in retained logs: no.

## Post-Rollback Baseline

Read-only baseline preflight after rollback passed:

```text
boot SHA256 = 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo SHA256 = 97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
boot_completed = 1
bootanim = stopped
root_available = true
ramoops_region/status = disabled
result = pass
```

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py \
  --offline-check

offline-check ok: M18 P00 candidate and rollback APs verified; no device action

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m18_p00_prefix_download_live_gate.py

Ran 3 tests in 0.013s
OK

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_ramoops_android_baseline_preflight.py

result = pass
```

After retiring the one-shot AGENTS exception, the live gate is fail-closed
again because active AGENTS markers are missing.

## Next

Do not run P10. The M18 prefix-download fallback did not establish a viable
checkpoint channel. The current frontier should return to an observation path
that can report the early failure point, not another blind prefix expansion.
