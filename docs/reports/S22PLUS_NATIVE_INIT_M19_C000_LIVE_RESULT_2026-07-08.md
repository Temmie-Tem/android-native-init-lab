# S22+ M19 C000 Live Result (2026-07-08)

## Verdict

RECOVERED, but native-init checkpoint proof failed.

The M19 C000 boot-only live gate flashed and rolled back cleanly. The helper
observed a later Odin endpoint and completed Magisk boot rollback, but the
operator reported bootloop behavior and manual download-mode entry during the
candidate window. Therefore this result must be interpreted as:

`bootloop / operator-manual-download / rollback-ok / no automatic checkpoint proof`

Do not count this as M19 C000 self-download PASS.

## Candidate

- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m19_c000_checkpoint_live_gate.py`
- Candidate AP.tar.md5 SHA256:
  `d712840f1aa7d4ef9d07a7be404b29e5f5dd8065701db7f3d39d76c71296b9d4`
- Candidate boot.img SHA256:
  `0ae71d30257dafdc453db252bd77b11b554202f27c458e3b538d13c61df98ebb`
- Prefix: `C000`
- Runtime module loads: `0`
- Intended proof: host-observed download-mode return after the original Odin
  endpoint disconnects.

Private run directory:

`workspace/private/runs/s22plus_m19_c000_checkpoint_live_gate_20260707T171848Z`

## Timeline

UTC timestamps from the helper log:

- `2026-07-07T17:18:48Z`: Android preflight passed on
  `SM-S906N` / `g0q` / `S906NKSS7FYG8`, `vbstate=orange`, Magisk root.
- `2026-07-07T17:18:48Z`: current boot SHA matched the Magisk baseline
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
- `2026-07-07T17:19:00Z`: candidate Odin endpoint appeared.
- `2026-07-07T17:19:00Z`: M19 C000 candidate flash completed with Odin rc=0.
- `2026-07-07T17:19:03Z`: original Odin endpoint disappeared.
- `2026-07-07T17:19:03Z` through `2026-07-07T17:19:34Z`: no ADB and no Odin
  endpoint observed.
- `2026-07-07T17:19:35Z`: Odin endpoint appeared and the helper recorded
  `m19_c000_self_download_seen=1`.
- Operator concurrently reported bootloop observation and manual download-mode
  entry. This overrides the helper's automatic inference.
- `2026-07-07T17:19:35Z`: Magisk boot-only rollback AP flashed with Odin rc=0.
- `2026-07-07T17:20:21Z`: Android returned with `boot_completed=1`, orange
  verified boot, `boot_recovery=0`, and Magisk root.

## Post-Rollback State

Read-only verification after rollback:

- `ro.product.model=SM-S906N`
- `ro.product.device=g0q`
- `ro.boot.bootloader=S906NKSS7FYG8`
- `ro.boot.verifiedbootstate=orange`
- `sys.boot_completed=1`
- `ro.boot.boot_recovery=0`
- Magisk root available
- current boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Retained evidence:

- `/sys/fs/pstore`: empty
- `/proc/last_kmsg`: 2,097,136 bytes
- `S22_NATIVE_INIT_M19`: absent
- `S22_NATIVE_INIT`: absent
- `Kernel panic`: absent
- `not syncing`: absent
- `Unable to mount root`: absent
- `Oops`: absent
- `reboot,download`: present
- `reboot_reason`: present

## Interpretation

C000 loaded no modules, so this result is not a USB PHY, DWC3, type-C, or
dependency-closure failure.

The candidate still failed to produce an unambiguous automatic checkpoint
download before operator manual download-mode entry. The retained channels also
did not preserve the M19 marker. The failure is therefore in or before the M19
C000 pre-reboot path:

1. direct PID1 entry;
2. freestanding C runtime;
3. minimal fs setup (`proc`, `sysfs`, `devtmpfs`/`tmpfs`, `run`);
4. `/dev/kmsg` marker emission;
5. `modules_prefix_skipped`;
6. `reboot(..., "download")`.

This points away from expanding to C129/C135/etc. The next useful unit should
split C000 itself. A minimal next branch is:

- M20A: first-action raw reboot again as a positive control against the current
  helper timing and operator/manual-download ambiguity;
- M20B: add only `setup_minimal_fs`, then reboot;
- M20C: add `/dev/kmsg` marker after fs setup, then reboot.

Each split should keep the same boot-only/Odin/rollback discipline and should
not load modules or attempt ACM/configfs.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m19_c000_checkpoint_live_gate.py \
  --live --ack S22PLUS-M19-C000-CHECKPOINT-LIVE-GATE

adb -s RFCT519XWGK shell 'getprop ro.product.model; getprop ro.product.device; \
  getprop ro.boot.bootloader; getprop ro.boot.verifiedbootstate; \
  getprop sys.boot_completed; getprop ro.boot.boot_recovery; \
  su -c id 2>/dev/null || true; \
  su -c "dd if=/dev/block/by-name/boot bs=4096 2>/dev/null | sha256sum"'
```

Result:

- Candidate flash: Odin rc=0.
- Helper rollback: Odin rc=0.
- Final Android/root baseline: restored.
- Functional proof: failed / operator-corrected manual-download.

## Next

Do not run C129 or any wider M19 prefix from this result. Split the C000 floor
before returning to module work.
