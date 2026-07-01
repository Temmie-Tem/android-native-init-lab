# Native Init V3347 §0.2 Write-Probe Rung E-open (open-only) Source Build

- Cycle: `V3347`
- Decision: `v3347-boot-write-open-probe-source-build-pass`
- Init: `A90 Linux init 0.11.111 (v3347-boot-write-open-probe)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3347_boot_write_open_probe.img`
- Boot SHA256: `84382ac5909d9efade68e83f8e01f7e6ccf083147fb8006cbcc8a90ab479d66e`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Adds the token-gated `boot-write-open-probe <token>` command (`a90_boot_write_probe.c`), the first rung (E-open) of the §0.2 write-probe ladder. It resolves the boot partition from sysfs `PARTNAME=boot`, materializes the node, calls `open(O_WRONLY)` then `close()` with **NO** `write`/`pwrite`/`dd`/`O_TRUNC`/`O_CREAT`, confirms the fd identity (block + rdev==sysfs + PARTNAME=boot + size==64MiB), and unlinks the node.
- Answers half of §0.2 — whether RKP/the kernel permits a writable open of the boot block from normal-boot PID1 — with **zero bytes written**. `open_wronly=fail EROFS/EPERM` means blocked (keep TWRP); `open_wronly=ok` means writable open is permitted (advance the ladder).
- The probe file contains no write primitive; verified in source.

## Validation Contract

- PASS requires post-flash `selftest fail=0`, `version` 0.11.111, and `boot-write-open-probe BOOT-WRITE-OPEN-PROBE-E-OPEN` emitting `rung=E-open`, `resolve=sysfs-partname`, a recorded `open_wronly=ok|fail`, `no_write_performed=1`, `cleaned=1`, then rollback to `v2321` with `selftest fail=0`.
- No write to any partition. No vbmeta/AVB/PIT/bootloader/forbidden-partition access.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `boot-write-open-probe-candidate`.
