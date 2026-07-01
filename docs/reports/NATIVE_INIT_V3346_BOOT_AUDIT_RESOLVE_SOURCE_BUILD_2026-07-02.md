# Native Init V3346 Boot-Audit sysfs-PARTNAME Resolve Source Build

- Cycle: `V3346`
- Decision: `v3346-boot-audit-resolve-source-build-pass`
- Init: `A90 Linux init 0.11.110 (v3346-boot-audit-resolve)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3346_boot_audit_resolve.img`
- Boot SHA256: `86875df34b286b1b35f58a2039014e57fb6d0acca6d34540ae310e014e2e0523`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- `boot-audit` with no explicit target now resolves the boot partition from sysfs: it scans `/sys/class/block/<X>/uevent` for the SINGLE partition with `PARTNAME=boot`, materializes `/dev/block/<X>` via `mknod` (device node in /dev tmpfs, NOT a partition write), audits it `O_RDONLY`, cross-checks the fd `st_rdev` against the sysfs major:minor, and `unlink`s the node. Only a unique authoritative resolution emits `authoritative=1`.
- A duplicate `PARTNAME=boot` (>1 match) is refused fail-closed (`resolve=ambiguous`). An rdev mismatch on a pre-existing node downgrades to `authoritative=0`.
- This closes the last read-only precondition: the host wrapper can now propose a confirmed `BootTargetPin` from a real native-init `boot-audit` run. Still NO partition write.

## Validation Contract

- PASS requires post-flash `selftest fail=0`, `version` 0.11.110, and no-arg `boot-audit` emitting `resolve=sysfs-partname`, `materialized=1`, `open=ok`, `read=ok`, `authoritative=1`, `partname=boot`, `size_bytes=67108864`, `cleaned=1`.
- Read-only: NO write/dd/O_WRONLY on the partition (verified in source). Rollback is `v2321`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `boot-audit-resolve-readonly-candidate`.
