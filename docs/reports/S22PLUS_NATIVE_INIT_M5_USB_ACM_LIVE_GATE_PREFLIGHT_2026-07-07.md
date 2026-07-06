# S22+ Native-Init M5 USB-ACM Live Gate Preflight - 2026-07-07

## Scope

Host-side preflight for the M5 USB-ACM live gate. No live flash was run, no
device partition was written, and no reboot was requested in this unit.

This unit added the guarded M5 live helper plus the SHA-pinned `AGENTS.md`
exception required before any M5 boot-only Odin live test.

## Helper

```text
workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py
```

Live ack token:

```text
S22PLUS-M5-USB-ACM-LIVE-GATE
```

Rollback-only ack token:

```text
S22PLUS-M5-ROLLBACK-FROM-DOWNLOAD
```

Dry-run command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py
```

Dry-run private log:

```text
workspace/private/runs/s22plus_m5_usb_acm_live_gate_20260706T210911Z/s22plus_m5_usb_acm_live_gate.txt
```

## Pinned Candidate

```text
AP.tar.md5                  8af4fd29a4268d30ac988ede6d32852837301ca80d3295ad41e539ae4913a170
boot.img                    aeed53543fb277765ddb1657e6b8da33b27db876257b41a95e965a26f7cf1afb
base Magisk boot            2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
M5 /init                    f677ede617bbf243686a58517260c5b025bc03efbfc012087c72f17ee5e39f41
module bundle manifest      1c22c93496e03a7df6dd74959511797b6d033b74361d3d3733d7be8269a5fa05
```

The candidate AP contains exactly:

```text
boot.img.lz4
```

## Rollback Payloads

```text
Magisk boot-only AP          d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot-only fallback AP  1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

Both rollback APs were verified as single-member `boot.img.lz4` packages.

## Dry-Run Result

The dry-run passed:

```text
agents_exception_missing=[]
m5_candidate_sha256=8af4fd29a4268d30ac988ede6d32852837301ca80d3295ad41e539ae4913a170
m5_candidate_members=['boot.img.lz4']
magisk_boot_rollback_sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock_boot_fallback_sha256=1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

Current Android preflight passed:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
Magisk root available
```

The helper also recorded the current Android ACM baseline. That baseline is
the normal Samsung Android composite ACM:

```text
path=/dev/ttyACM0
vendor=04e8
product=6860
model=SAMSUNG_Android
driver=cdc_acm
```

The M5 live detector therefore does not treat plain `/dev/ttyACM*` existence
as success. It looks for the M5-specific gadget identity:

```text
vendor=04e8
product=685d
serial=S22M5ACM0001
model=S22_Native_Init_M5_ACM
```

If it sees that ACM device, it opens the tty non-blocking and attempts to read
the M5 readiness banner:

```text
S22_NATIVE_INIT_USB_ACM_M5 READY
```

## Live Flow Prepared

The live helper is intentionally attended:

1. Verify `AGENTS.md` exception, candidate hashes, manifest safety, rollback
   AP hashes, current Android identity, root, and ACM baseline.
2. Reboot the rooted Android baseline to download mode.
3. Flash only the exact M5 boot-only AP through Odin.
4. Observe host USB for the M5 ACM gadget.
5. If ACM appears, keep the device running so the operator can inspect it.
6. When the operator enters download mode, roll back to the pinned Magisk
   boot-only AP and verify Android/root returned.
7. If ACM does not appear, stop and require manual download-mode entry plus
   `--rollback-from-download`.

The helper does not claim a completed live pass unless rollback returns Android
with the expected rooted baseline. If ACM is observed but rollback has not yet
been performed, it exits with a distinct rollback-still-required path.

## Validation

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py
git diff --check
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py
```

All passed.

## Next

The next live command, if supervised, is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py --live --ack S22PLUS-M5-USB-ACM-LIVE-GATE
```

If the phone is already in download mode and only rollback is needed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m5_usb_acm_live_gate.py --rollback-from-download --ack S22PLUS-M5-ROLLBACK-FROM-DOWNLOAD
```

Do not run this unattended. M5 has no auto-reboot path; manual download-mode
entry is still the fallback until the ACM channel is proven and expanded into a
real command channel.
