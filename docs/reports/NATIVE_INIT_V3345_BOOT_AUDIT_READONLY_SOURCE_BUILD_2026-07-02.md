# Native Init V3345 Boot-Audit Read-Only Source Build

- Cycle: `V3345`
- Decision: `v3345-boot-audit-readonly-source-build-pass`
- Init: `A90 Linux init 0.11.109 (v3345-boot-audit)`
- Boot image: `workspace/private/inputs/boot_images/boot_linux_v3345_boot_audit.img`
- Boot SHA256: `cedf60194330cf958f423d8b027e3946ec718fd7c032bf7b9206328543b09503`
- Helper SHA256: `fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef`
- Base boot: `workspace/private/inputs/boot_images/boot_linux_v3335_gpu_z3_primary_setcrtc.img`

## Change

- Adds the read-only `boot-audit [target-path]` native-init command (`a90_boot_audit.c`): opens the boot block `O_RDONLY|O_NONBLOCK`, reads the first 4096 bytes, and reports fd-derived identity (rdev, canonical via `realpath`, size, sector, PARTNAME, diskseq) as `A90BOOTAUDIT key=value` lines.
- No write path: this is the §7.1 read-only auditor for the fast self-dd boot-flash tool (`docs/plans/FAST_SELF_DD_BOOT_FLASH_TOOL_DESIGN_2026-07-02.md`). It answers §0.1 (can native-init read `sda24` under RKP) and produces the host-confirmed `BootTargetPin`.
- Non-default targets are flagged `authoritative=0` so the host wrapper never promotes them to a write-authorizing pin.
- Inherits the full V3344 SoftAP S4 transfer-server surface unchanged; only the init version and this command are added.

## Validation Contract

- PASS requires post-flash `selftest fail=0`, `version` reporting 0.11.109, and `boot-audit` emitting `open=ok`, `read=ok`, `authoritative=1`, `partname=boot`, `size_bytes=67108864` for the default target.
- Read-only: the command MUST NOT contain any write/dd/O_WRONLY path (verified in source). Rollback baseline is `v2321`.

## Metadata

- Helper flags: `-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1`
- Init extra flags: ``
- Candidate type: `boot-audit-readonly-candidate`.
