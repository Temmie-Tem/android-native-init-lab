# S22+ M25 HS-Only USB2 ACM Live Runbook (2026-07-08)

This runbook is the operator-facing sequence for the already prepared M25
HS-only USB2 ACM live gate. It does not authorize live execution by itself; the
active authorization is the SHA-pinned M25 exception in `AGENTS.md`, and the
helper still requires the live ack token.

## Scope

Target:

```text
SM-S906N/g0q/S906NKSS7FYG8
```

Helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
```

Live ack:

```text
S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE
```

Rollback ack:

```text
S22PLUS-M25-HS-ONLY-ROLLBACK-FROM-DOWNLOAD
```

Stock-DTBO-only restore ack:

```text
S22PLUS-M25-RESTORE-STOCK-DTBO
```

## Preflight

Run the dry-run immediately before live:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
```

Required dry-run result:

```text
dry-run ok: M25 boot/DTBO candidates, rollback APs, AGENTS exception, Android stability, boot/vendor_boot/stock-DTBO hashes verified
```

The dry-run must prove:

```text
agents_exception_missing=[]
boot_completed=1
vbstate=orange
Magisk root uid=0(root)
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
dtbo        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
```

Stop before live if any of these fail.

## Live Command

Only run this after the operator explicitly approves the live write:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  --live --ack S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE
```

The helper performs two flashes:

1. DTBO high-speed cap AP.
2. M25 boot AP, only after Android/root returns and the patched DTBO hash is
   verified.

Do not interrupt between the DTBO flash and its Android/root verification unless
the helper has already timed out and requested manual recovery.

## Expected Outcomes

### A. ACM appears

Expected proof:

```text
m25_acm_seen=1
```

The helper intentionally stops with manual Download-mode required because the
M25 ACM path is the proof surface, not a trusted rollback transport yet.

Operator action:

1. Put the phone into Download mode manually.
2. Run rollback-from-download:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  --rollback-from-download --ack S22PLUS-M25-HS-ONLY-ROLLBACK-FROM-DOWNLOAD
```

### B. Candidate returns to Download/Odin by itself

The helper should detect Odin and rollback automatically in the same live run.
No manual command should be needed unless the helper reports failure.

### C. Candidate unexpectedly returns to Android/ADB

The helper should reboot it to Download mode and rollback automatically. Treat
this as an unexpected result and inspect the run log before deciding the next
unit.

### D. No ACM, no ADB, no Odin

Operator action:

1. Put the phone into Download mode manually.
2. Run rollback-from-download:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  --rollback-from-download --ack S22PLUS-M25-HS-ONLY-ROLLBACK-FROM-DOWNLOAD
```

### E. DTBO step fails before boot candidate flash

If Android/root does not return after the DTBO high-speed cap, the M25 boot
candidate has not been flashed yet. Restore stock DTBO only:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py \
  --restore-dtbo-from-download --ack S22PLUS-M25-RESTORE-STOCK-DTBO
```

Use this only after manually entering Download mode if the helper cannot reach
Download mode itself.

## Post-Rollback Verification

After any rollback path, verify Android state:

```text
adb devices -l
adb shell getprop sys.boot_completed
adb shell getprop ro.boot.verifiedbootstate
adb shell getprop ro.boot.boot_recovery
adb shell su -c id
adb shell su -c 'sha256sum /dev/block/by-name/boot /dev/block/by-name/dtbo /dev/block/by-name/vendor_boot'
```

Expected Magisk baseline:

```text
sys.boot_completed=1
verifiedbootstate=orange
boot_recovery=0
su uid=0(root)
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
dtbo        97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
```

If stock boot fallback was explicitly selected or used after Magisk rollback
failure, Magisk root is not expected. In that case, document it as stock boot
fallback and do not claim Magisk baseline restored.

## Timeline

The canonical `timeline.json` must keep a single top-level `events` array.
Expected live event families:

```text
live_session_start
dtbo_candidate_flash_start
dtbo_candidate_flash_done
candidate_flash_start
candidate_flash_done
candidate_boot_ready
rollback_flash_start
rollback_flash_done
rollback_boot_ready
dtbo_rollback_flash_start
dtbo_rollback_flash_done
dtbo_rollback_boot_ready
live_session_end
```

Not every failure path reaches every event. In particular, a DTBO-only failure
should have DTBO rollback events but no M25 boot candidate events.

## Forbidden During This Run

- no vendor_boot, vbmeta, recovery, BL, CP, CSC, super, userdata, EFS, RPMB,
  keymaster, modem, or bootloader action;
- no raw host `dd`;
- no fastboot;
- no EUD sysfs write;
- no EUD enable/open;
- no Magisk module install;
- no format data;
- no broad module permutation;
- no second M25 attempt under the same exception after one live run.
