# V3419 S22+ O3R1 Native Retained SysRq Live Gate

## Verdict

`LIVE GATE READY; OFFLINE AND CONNECTED DRY-RUN PASS; ONE-SHOT EXCEPTION ACTIVE`.

The O3R1 helper pins the exact V3418 artifact, the rooted Android baseline,
Samsung sec_debug MID state, both boot-only rollback APs, intentional panic
classification, continuous host observers, mandatory attended rollback, and
the canonical eight-event timeline.

No candidate flash or intentional panic occurred in this unit. The one-shot
exception remains unconsumed until `candidate_flash_start` is recorded.

## Checked Helper

```text
workspace/public/src/scripts/revalidation/s22plus_o3r1_native_retained_sysrq_live_gate.py
```

The helper supports:

- artifact-only `--offline-check` without device access;
- connected read-only dry-run as the default;
- one exact `--live` path requiring live, rollback, and MID confirmation tokens;
- one emergency `--rollback-from-download` path;
- automatic Magisk boot rollback with stock boot fallback only on transfer
  failure;
- post-rollback pstore and `/proc/last_kmsg` collection and exact classification.

## Exact Pins

```text
candidate_ap_sha256=2a92008b4632a8907fec96f0d8194a8461c16060cb1d919aeba7446020c4beda
candidate_boot_sha256=fc0dce090f454b621ed90e63dd11cfe29dad8de0fe04d3c1f138a004d9d2f6aa
candidate_init_sha256=44d70f3d7ee534b6701a5a912e07febdaf21b0b4d7fabf0368c4a6f942499fdc
candidate_source_sha256=a51fd1d87732bbcc3fa4b6ea2c9ede7ff78d423736ce3e168c059cef50626968
magisk_rollback_ap_sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock_boot_fallback_ap_sha256=2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94
baseline_boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

All three APs contain exactly one member, `boot.img.lz4`.

## Dry-Run Evidence

Artifact-only run:

```text
workspace/private/runs/s22plus_o3r1_native_retained_sysrq_live_gate_20260709T215658Z
result=offline-pass
```

The first connected run correctly failed closed because DEBUG LEVEL had
returned to LOW (`20300 / 0x4f4c / LO`). Direct Activity and secret-code
broadcast routes were blocked. The standard dialer was then opened and
`*#9900#` was injected as normal key events; the operator selected MID and the
phone rebooted normally.

Connected read-only pass:

```text
workspace/private/runs/s22plus_o3r1_native_retained_sysrq_live_gate_20260709T220014Z
target=SM-S906N/g0q/S906NKSS7FYG8
adb_serial=RFCT519XWGK
boot_completed=1
bootanim=stopped
root=uid=0(root) context=u:r:magisk:s0
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
debug_level=18765 / 0x494d / MI
sec_debug_enable=1
sys_boot_reason=reboot,debug0x494d
stability_samples=4/4
concurrent_odin_devices=[]
result=dry-run-pass
```

## PASS Contract

Only this retained bundle is exact O3R1 PASS:

```text
S22_NATIVE_INIT_O3R1_RETAINED_SYSRQ ... phase=before-sysrq-c ...
sysrq: Trigger a crash
Kernel panic - not syncing: sysrq triggered crash
```

Marker plus `Attempted to kill init` proves native kmsg retention but is not
the exact SysRq PASS. Init-death panic without the marker, unrelated panic, or
no retained marker/panic is FAIL. Candidate Odin disconnect and RDX display are
never promoted to internal phase proof.

## Validation

The O3R1 build, gate, O3F regression, and retired M22 policy suites pass 20
tests. `git diff --check` passes. The active exception pins all hashes, all
three confirmation tokens, MID/enabled preconditions, boot-only scope,
intentional crash behavior, mandatory manual-Download rollback, and explicit
non-authorization of O3R2 or any additional candidate.

## Attended Live Sequence

1. Run the exact helper with all three confirmation tokens.
2. The helper requests Download, flashes only the pinned O3R1 boot AP, and
   verifies the original Odin endpoint disconnected.
3. The candidate emits markers and intentionally panics. The operator may see
   Samsung RDX/PMIC panic output.
4. If no Download endpoint appears automatically, the operator manually enters
   Download mode when prompted.
5. The helper restores the pinned Magisk boot AP, verifies Android/root and
   MID state, collects retained logs, and emits the exact classification.

The one-shot exception becomes consumed at `candidate_flash_start` regardless
of the candidate result.
