# S22+ M20A Raw-Reboot Live Result (2026-07-08)

## Verdict

RECOVERED, but automatic raw-reboot proof failed.

The guarded M20A live gate flashed the raw first-action `reboot(download)`
candidate and rolled back to the rooted Magisk baseline. The helper observed a
later Odin endpoint and completed Magisk boot rollback, but the operator
reported bootloop behavior and manual download-mode entry during the candidate
window. Therefore this result must be interpreted as:

`bootloop / operator-manual-download / rollback-ok / no automatic raw-reboot proof`

Do not count the helper's raw `m20a_self_download_seen=1` as an automatic M20A
self-download PASS.

## Candidate

- Helper:
  `workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py`
- Candidate AP.tar.md5 SHA256:
  `795e071107fdd7011a5acdc48ca7415273e5f2a3e19af45386702617292021fc`
- Candidate boot.img SHA256:
  `4fada63c986abc774e2a41eebc590f0635f1f1dcc8a207baa8d02cbfeb20eeb5`
- Candidate `/init` SHA256:
  `4b27b050b11a4f0f28f340172515a397f65e1d151507e149bc9cbe47c6beab17`
- Runtime shape: raw assembly PID1; first action is one raw
  `reboot(..., "download")`; no fs setup, marker, modules, configfs, or USB
  role work.

Private run directory:

`workspace/private/runs/s22plus_m20a_raw_reboot_live_gate_20260707T174109Z`

## Timeline

UTC timestamps from the helper log and operator observation:

- `2026-07-07T17:41:09Z`: M20A live gate started.
- Preflight passed: current boot SHA matched the Magisk baseline
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
- Host commanded Android into download mode for candidate flash.
- M20A candidate Odin flash completed with `candidate_odin_rc=0`.
- The original post-flash Odin endpoint disconnected
  (`post-candidate-disconnect_odin_absent=1`).
- `2026-07-07T17:41:47Z`: helper observed a later Odin endpoint and recorded
  `m20a_self_download_seen=1`.
- Operator concurrently reported bootloop behavior and manual download-mode
  entry. This overrides the helper's automatic inference.
- Magisk boot-only rollback flashed with `magisk_rollback_odin_rc=0`.
- Android returned with `boot_completed=1`, orange verified boot,
  `boot_recovery=0`, and Magisk root.

## Post-Rollback State

Read-only verification after rollback:

- `ro.product.model=SM-S906N`
- `ro.product.device=g0q`
- `ro.boot.bootloader=S906NKSS7FYG8`
- `ro.build.display.id=AP3A.240905.015.A2.S906NKSS7FYG8`
- `ro.boot.verifiedbootstate=orange`
- `sys.boot_completed=1`
- `ro.boot.boot_recovery=0`
- Magisk root available
- current boot SHA256:
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`

Retained evidence:

- `/sys/fs/pstore`: empty
- `/proc/last_kmsg`: 2,097,136 bytes
- `S22_NATIVE_INIT_M20A`: absent
- `S22_NATIVE_INIT`: absent
- `Kernel panic`: absent
- `not syncing`: absent
- `Unable to mount root`: absent
- `Oops`: absent
- `reboot,download`: present
- `reboot_reason`: present

## Interpretation

M20A removes the M19 C000 freestanding C runtime, minimal fs setup, kmsg marker,
module-list read, and checkpoint logic. The remaining candidate action is a raw
assembly PID1 `reboot(..., "download")` syscall.

Because the operator had to manually enter download mode, the live run does not
prove that the M20A raw reboot syscall worked. The failure is now below the C000
floor and may be one of:

- raw direct-PID1 execution not reaching the syscall reliably;
- raw reboot syscall returning/failing before visible proof;
- host/operator timing ambiguity around bootloop vs self-download;
- retained logging channel not capturing this early failure mode.

Do not advance to M20B/M20C or M19 module prefixes from this result. The next
unit should improve the discriminator before adding code back, for example by
making the raw PID1 state externally distinguishable without relying solely on
Samsung download-mode timing.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m20a_raw_reboot_live_gate.py \
  --live --ack S22PLUS-M20A-RAW-REBOOT-LIVE-GATE

adb shell 'getprop ro.product.model; getprop ro.product.device; \
  getprop ro.boot.bootloader; getprop ro.boot.verifiedbootstate; \
  getprop sys.boot_completed; getprop ro.boot.boot_recovery; \
  su -c id 2>/dev/null || true'

adb shell su -c 'dd if=/dev/block/by-name/boot bs=4096 2>/dev/null | sha256sum'
```

Result:

- Candidate flash: Odin rc=0.
- Helper rollback: Odin rc=0.
- Final Android/root baseline: restored.
- Functional proof: failed / operator-corrected manual-download.

## Next

Stop M20B/M20C. The next step should be a host-only redesign of the floor
discriminator, not another immediate boot candidate.
