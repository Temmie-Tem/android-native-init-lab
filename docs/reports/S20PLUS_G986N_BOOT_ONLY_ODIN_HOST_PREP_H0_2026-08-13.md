# S20+ G986N boot-only Odin host preparation H0

Date: 2026-08-13

Status: **PASS HOST PREPARATION - NOT LIVE AUTHORIZED**

## Trigger and connected state

The exact S20+ `enter-download` routine control was dispatched once. The
operator then reported “다운로드 모드 진입”, which was treated as the required
screen observation. The host-only control finalizer recorded
`download-observed` and cleared the guard without replaying the reboot. The
private dispatch result SHA-256 is
`0f62006aa71e5d1a76e87f994d2c465fa47a8d550f2fe0e3fe99c5ab18418e84`.

No Odin enumeration or transfer was performed.

## Unsafe full AP finding

The retrieved Magisk output is not boot-only. Its exact TAR membership includes
`recovery.img.lz4`, `dtbo.img.lz4`, `super.img.lz4`, `persist.img.lz4`,
`vbmeta.img`, `vbmeta_samsung.img.lz4`, carrier/misc payloads, metadata, and
`boot.img`. Passing that archive directly to Odin would cross the permanent
boot-only boundary, so it was rejected as a live candidate.

## Host-only outputs

`s20plus_g986n_boot_only_odin_prep.py` pins the full patched AP, stock boot,
stock boot LZ4, LZ4 tool, and `/usr/bin/odin4` by exact size and SHA-256. It
validates the full source membership, extracts only the exact 64 MiB
`boot.img`, performs LZ4 round trips, and creates canonical Samsung TAR+MD5
archives. Candidate and rollback outputs each have exactly one regular member:
`boot.img.lz4`.

The host-only builder SHA-256 is
`0ba7df69fefc72392750094a63896dd903f005c4b60eacf752b4ac345770c577`.

- candidate boot SHA-256:
  `d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`
- candidate AP SHA-256:
  `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`
- stock rollback boot SHA-256:
  `29fde3a189b906ea20ed0e14fcd7a448e005597b82e3adceea64196284bd31ab`
- stock rollback AP SHA-256:
  `48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b`
- private artifact result SHA-256:
  `a2d7919d56f0b903c2b480f866f5122e33a898c8ce41b835f834e0b79a60543d`

Official Magisk v30.7 `magiskboot`, SHA-256
`a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e`,
accepted the candidate as Android boot header v2 with raw kernel, gzip ramdisk,
DTB, Samsung marker, and VBMeta footer. `magiskboot cpio ramdisk.cpio test`
returned `1`, the Magisk-patched classification.

## Boundary and next gate

This unit is H0 artifact construction only. The result explicitly records
`device_contact=false`, `odin_invoked=false`, `live_flash_authorized=false`, and
`f1_defined=false`. No bytes were sent to Odin or a partition.

Before any flash, S20+ still needs a target-specific F1 contract, exact Odin
transport isolation, demonstrated stock boot-only recovery, known healthy
starting state, durable no-replay journal, bounded post-transfer observation,
independent review of the live runner, and fresh exact operator authority.
Current Download mode and host artifacts do not grant those conditions.
