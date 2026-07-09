# S22+ M34 S10C0 Active Exception + Dry-Run

Date: 2026-07-09 20:55 KST / 2026-07-09 11:55 UTC

## Verdict

S10C0 is ready for an explicit operator-approved live attempt. The exact
S10C0 active exception is present in `AGENTS.md`, and the default no-flash
dry-run passed against the current rooted Android/Magisk baseline.

No `--live`, Odin transfer, reboot, partition write, or rollback was performed.

## Policy State

Inserted the exact helper-generated active exception for:

```text
S22+ M34 S10C0 direct-finit loader-audit download-beacon native-init boot-only
```

Validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py \
  --verify-agents-candidate AGENTS.md
```

Result:

```text
verify-agents-candidate ok: exact M34 S10C0 active exception is present
```

## Dry-Run

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py \
  --run-dir workspace/private/runs/s22plus_m34_s10c0_default_dryrun_20260709T115447Z
```

Result:

```text
dry-run ok: M34 S10C0 candidate, rollback APs, AGENTS exception, Android, and boot hash verified
```

Run directory:

```text
workspace/private/runs/s22plus_m34_s10c0_default_dryrun_20260709T115447Z
```

The run captured host snapshots under `host_observation/`. Raw device serials
remain only in private run logs and are intentionally not reproduced here.

## Baseline Proven

Dry-run preflight proved:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
root_probe=debug_ramdisk_su
su_id=uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
android_stability_result=ok samples=2
current_boot_hash=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

Note: normal PATH `su` was inaccessible, but `/debug_ramdisk/su` returned
root and is the accepted root path for the updated helper.

## Pinned Artifacts

```text
S10C0 candidate AP.tar.md5
9221cfa3ea3ce0776860a5041981e23a84d0be9b833203401dab771897266c6f

S10C0 boot.img
8d77e1434cd47fe47f4723c948e4ff6db759cbe4bf75dd21e9e0c265d928c6df

S10C0 /init
cd80d5923c94f8a423821bc6dee4547f22763e177fbcc637d1bcb101c4b8c39b

S10C0 module-list
c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26

Magisk boot rollback AP
d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56

S10C0-specific stock boot fallback AP
2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94
```

## Next Gate

The next live command must still be explicitly approved by the operator at the
time of execution:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m34_s10c0_direct_finit_loader_audit_live_gate.py \
  --live \
  --ack S22PLUS-M34-S10C0-DIRECT-FINIT-LOADER-AUDIT-LIVE-GATE
```

Expected live outcomes:

```text
HIT  = cmd-db.ko direct finit_module rc is 0 or -EEXIST; candidate self-enters Download.
MISS = no new Odin endpoint during bounded observation; candidate parks and manual Download rollback is required.
```

This gate remains boot-partition-only and does not authorize non-boot
partition writes, raw host `dd`, fastboot, Magisk modules, DTBO/vendor_boot/
recovery/vbmeta writes, or any A90 action.
