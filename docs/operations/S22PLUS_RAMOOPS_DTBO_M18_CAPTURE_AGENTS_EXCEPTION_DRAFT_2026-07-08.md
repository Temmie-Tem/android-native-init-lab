# S22+ Ramoops DTBO + M18 Capture AGENTS Exception Draft (2026-07-08)

This is an inert draft. It does not authorize live work while it remains in this
document. Copy it into `AGENTS.md` only after explicit operator authorization
for the non-boot `dtbo` write, the M18 boot candidate flash, the patched-DTBO
AVB digest caveat, and the attended rollback/restore flow.

## Copy Block

```text
   **Narrow operator-authorized exception (2026-07-08, S22+ ramoops DTBO + M18 capture only):**
   after the operator explicitly accepts the non-boot DTBO write risk and the
   patched-DTBO AVB hash-descriptor mismatch under the already-proven
   disabled-vbmeta/orange state, Codex may perform one bounded attended
   S22+ ramoops DTBO + M18 capture run on the Samsung S22+ `SM-S906N`/`g0q`
   `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m18_capture_live_gate.py`
   and live ack token `S22PLUS-RAMOOPS-DTBO-M18-CAPTURE-LIVE-GATE`.
   This exception authorizes exactly two partition classes and no others:
   first flash the patched `dtbo` AP.tar.md5 SHA256
   `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`,
   then flash the M18 boot candidate AP.tar.md5 SHA256
   `9382f91bf2cd3235410368ca08208b9343d8584da48c29b25c46a931b1f42805`;
   after capture, restore the boot partition using the pinned Magisk boot
   rollback AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   with stock boot fallback AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`,
   then restore stock DTBO using the pinned stock DTBO rollback AP.tar.md5
   SHA256 `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`.
   The patched raw DTBO SHA256 must be
   `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`,
   the stock raw DTBO SHA256 must be
   `97a4864fee4e61892d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
   the M18 padded boot.img SHA256 must be
   `a99a09fa062d1aaa848a41037c649a43abc983f177714dfc24c39d0df4d84083`,
   and the M18 base known-booting Magisk boot SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   The DTBO APs must contain exactly one tar member, `dtbo.img.lz4`; the M18,
   Magisk rollback, and stock boot fallback APs must contain exactly one tar
   member, `boot.img.lz4`. The helper must verify all AP hashes and both
   manifests before live work, verify current Android root and the current boot
   hash, flash patched DTBO first, require Android/root to return, then flash
   M18 for pstore capture. If M18 loops or no transport appears, rollback
   requires operator manual download-mode entry and the helper mode
   `--rollback-boot-from-download --ack S22PLUS-RAMOOPS-M18-ROLLBACK-BOOT-FROM-DOWNLOAD`.
   Stock DTBO restore requires either
   `--restore-dtbo-from-android --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO` or
   `--restore-dtbo-from-download --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO`.
   The capture goal is to read `pstore` / `/sys/fs/pstore` after the M18 boot
   failure, then restore stock DTBO for a clean state. This exception does not
   authorize writing or flashing recovery, vendor_boot, vbmeta, vbmeta_system,
   BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem,
   bootloader, raw host `dd`, fastboot, Magisk modules, multidisabler, format
   data, additional boot candidates, additional DTBO candidates, kernel rebuilds,
   or any A90 action.
```

## Gate Marker Coverage

The draft intentionally includes every authorization marker required by
`s22plus_ramoops_dtbo_m18_capture_live_gate.py`:

```text
S22+ ramoops DTBO + M18 capture
4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00
6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab
97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
9382f91bf2cd3235410368ca08208b9343d8584da48c29b25c46a931b1f42805
a99a09fa062d1aaa848a41037c649a43abc983f177714dfc24c39d0df4d84083
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
S22PLUS-RAMOOPS-DTBO-M18-CAPTURE-LIVE-GATE
S22PLUS-RAMOOPS-M18-ROLLBACK-BOOT-FROM-DOWNLOAD
S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO
dtbo.img.lz4
boot.img.lz4
disabled-vbmeta
pstore
restore stock DTBO
manual download-mode
```

Note: the copy block above contains the full
`1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`
patched-DTBO SHA. The marker checklist intentionally exists only for coverage
review; the copy block is the authoritative text.
