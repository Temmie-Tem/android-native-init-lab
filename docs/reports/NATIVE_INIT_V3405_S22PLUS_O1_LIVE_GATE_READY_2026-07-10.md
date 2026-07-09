# NATIVE_INIT V3405 — S22+ O1 live gate ready

Date: 2026-07-10 04:03 KST / 2026-07-09 19:03 UTC

## Verdict

LIVE GATE READY. The V3404 O1 artifact now has a fresh narrow SHA-pinned
boot-only exception, a default-dry-run checked helper, and explicit operator
approval. No flash or reboot occurred in V3405.

## Candidate And Rollback Pins

```text
candidate AP.tar.md5
  sha256=388d35c12e9f5024f053837444da46254db6a6177c046400549148e24eaeec29
candidate boot.img
  sha256=df7a166752f78aa07bea10aef53de1ba2737abf43bb041fe01738cce36113070
candidate boot.img.lz4
  sha256=26af084cca0cf23525e8786a50a49b270d60ae7b2fa7f4ed8d652bc9e102bb21
Magisk rollback AP.tar.md5
  sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot fallback AP.tar.md5
  sha256=2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94
```

Every AP contains exactly `boot.img.lz4`. The active exception authorizes no
other partition payload or action.

## Live Gate Contract

Before candidate flash:

1. verify active unconsumed O1 policy markers and both ack tokens;
2. verify candidate AP, raw boot, LZ4, manifest, source, kernel, and `/init` pins;
3. verify Magisk rollback and stock boot fallback APs;
4. require one normal rooted `SM-S906N/g0q/S906NKSS7FYG8` Android target;
5. require current boot SHA equal the known Magisk baseline;
6. require stock `DR-daemon` running and owning ttyGS0;
7. require one Samsung CDC ACM tty and no simultaneous Odin endpoint.

After candidate flash, PASS requires:

```text
requests=128 completed=128
payload_equality=true
sequence_continuity=true
host_reopen_at=64 host_reopen_completed=true
candidate_boot_sha256=df7a166752f78aa07bea10aef53de1ba2737abf43bb041fe01738cce36113070
volatile result=pass daemon_rc=0 restore_rc=0
DR-daemon=running ddexe_tty_owner_count>0
```

The helper runs continuous udev/kernel-journal observers across the candidate
window. It writes the canonical timeline `events:[{name,timestamp_utc}]` and
requires the eight standard live phases before a PASS result.

Mandatory boot-only rollback follows both candidate PASS and FAIL. If candidate
Android cannot issue `adb reboot download`, the helper waits for attended manual
Download entry. Missing protocol/status remains FAIL; it is never replaced with
a source-intent claim.

## Validation

```text
python py_compile: PASS
git diff --check: PASS
combined O0/O1 tests: Ran 25, OK
offline artifact/policy gate: PASS
connected Android/Magisk dry-run: PASS
```

Connected dry-run evidence:

```text
workspace/private/runs/s22plus_o1_stock_first_stage_control_live_gate_20260709T190326Z
```

The dry-run verified current Android/root stability, boot SHA, stock tty owner,
candidate and rollback artifacts, policy markers, and transport uniqueness. It
performed no reboot, flash, configfs/sysfs write, module load, or service handoff.

Tracked files:

- `workspace/public/src/scripts/revalidation/s22plus_o1_stock_first_stage_control_live_gate.py`
- `tests/test_s22plus_o1_stock_first_stage_control_live_gate.py`
- `AGENTS.md` active O1 exception

## Next

Run the helper once with both exact ack tokens. After `candidate_flash_start`,
the exception is consumed regardless of the technical result. Complete or
recover the mandatory Magisk boot-only rollback, then convert the exception to
consumed and record the live measurements in GOAL/report/commit.
