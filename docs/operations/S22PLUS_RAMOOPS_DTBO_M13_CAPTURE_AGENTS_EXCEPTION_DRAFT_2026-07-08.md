# S22+ Ramoops DTBO + M13 Capture AGENTS Exception Draft (2026-07-08)

This is an inert draft. It does not authorize live work while it remains in this
document. Copy it into `AGENTS.md` only after explicit operator authorization
for the non-boot `dtbo` write, the M13 boot candidate flash, the patched-DTBO
AVB digest caveat, and the attended rollback/restore flow.

## Copy Block

```text
   **Narrow operator-authorized exception (2026-07-08, S22+ ramoops DTBO + M13 positive-control only):**
   after the DTBO status-only live gate proved that the patched DTBO enables
   live `/proc/device-tree/reserved-memory/ramoops_region/status=okay`, Codex
   may perform one bounded attended S22+ ramoops DTBO + M13 positive-control
   capture run on the Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only
   the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py`
   and live ack token `S22PLUS-RAMOOPS-DTBO-M13-CAPTURE-LIVE-GATE`.
   This exception authorizes exactly two partition classes and no others:
   first flash the patched `dtbo` AP.tar.md5 SHA256
   `4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00`,
   require Android/root to return, require current DTBO SHA256
   `1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab`,
   require live `ramoops_region/status=okay`, then flash the M13 boot
   positive-control AP.tar.md5 SHA256
   `5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa`.
   After the M13 observation window, restore the boot partition using the pinned
   Magisk boot rollback AP.tar.md5 SHA256
   `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
   with stock boot fallback AP.tar.md5 SHA256
   `1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e`,
   collect `pstore`, then restore stock DTBO using the pinned stock DTBO
   rollback AP.tar.md5 SHA256
   `6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa`.
   The stock raw DTBO SHA256 must be
   `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
   the M13 padded boot.img SHA256 must be
   `21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b`,
   the M13 base known-booting Magisk boot SHA256 must be
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`,
   the M13 kernel SHA256 must be
   `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`,
   the M13 `/init` SHA256 must be
   `6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3`,
   and the M13 source SHA256 must be
   `4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8`.
   The DTBO APs must contain exactly one tar member, `dtbo.img.lz4`; the M13,
   Magisk rollback, and stock boot fallback APs must contain exactly one tar
   member, `boot.img.lz4`. If M13 parks, exposes ACM, or no transport appears,
   rollback requires operator manual download-mode entry and the helper mode
   `--rollback-boot-from-download --ack S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD`.
   Stock DTBO restore requires either
   `--restore-dtbo-from-android --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO` or
   `--restore-dtbo-from-download --ack S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO`.
   The capture goal is M13 positive-control `pstore` evidence with the live
   ramoops node enabled through DTBO. This path is the DTBO successor to the
   retired vendor_boot-only route: no vendor_boot write is authorized here.
   This exception does not authorize writing or flashing recovery, vendor_boot,
   vbmeta, vbmeta_system, BL, CP, CSC, super, userdata, persist, EFS, sec_efs,
   RPMB, keymaster, modem, bootloader, raw host `dd`, fastboot, Magisk modules,
   multidisabler, format data, M15/M18/QMP candidates, additional boot
   candidates, additional DTBO candidates, kernel rebuilds, or any A90 action.
```

## Gate Marker Coverage

The draft intentionally includes every authorization marker required by
`s22plus_ramoops_dtbo_m13_capture_live_gate.py`:

```text
S22+ ramoops DTBO + M13 positive-control
workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py
4f82663a7c2175a41760ec099c0f662dd04b8932a5ae82ba46b3ecb401a14a00
6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa
1c90b54577cbb42e029818a0c4248e85ec3a0e40903b0887648d6556355c85ab
97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa
21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3
4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8
d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
S22PLUS-RAMOOPS-DTBO-M13-CAPTURE-LIVE-GATE
S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD
S22PLUS-RAMOOPS-RESTORE-STOCK-DTBO
dtbo.img.lz4
boot.img.lz4
ramoops_region/status=okay
M13 positive-control
pstore
restore stock DTBO
manual download-mode
no vendor_boot
```
