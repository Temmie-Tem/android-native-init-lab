# S22+ M18 P00 Prefix-Download AGENTS Exception Draft (2026-07-08)

This document is inert until copied into `AGENTS.md`.

Scope: one bounded attended S22+ M18 P00 prefix-download native-init boot-only
run, followed by rollback to the pinned Magisk boot baseline.

Helper:

```text
workspace/public/src/scripts/revalidation/s22plus_m18_p00_prefix_download_live_gate.py
```

Ack tokens:

```text
S22PLUS-M18-P00-PREFIX-DOWNLOAD-LIVE-GATE
S22PLUS-M18-P00-ROLLBACK-FROM-DOWNLOAD
```

Pinned candidate:

```text
AP.tar.md5 SHA256  b79ac94aac341ab5e4c08cb3c568c20be28bb71ccd4f1b047f712bd1dcf5225b
boot.img SHA256    f8f362bdd0d0f75ae9ae0ce69d86bcfe47362f246504b02fc6175a4aa0a83133
base boot SHA256   2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel SHA256      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
/init SHA256       467947f7ba0c4b4088c9a21a19e5202609b833298f2e95256b1f011eb9af034e
```

Runtime:

- P00 loads no modules.
- It sets up only the minimal native-init runtime from the existing M18
  prefix-download artifact.
- If it reaches the checkpoint, it requests Samsung download mode.
- The host must wait for the original Odin endpoint to disconnect before
  treating a later Odin endpoint as the candidate self-download proof.

Allowed:

- flash exactly the pinned P00 boot-only AP through Odin4;
- observe for one later download-mode endpoint;
- rollback through the pinned Magisk boot-only AP;
- if Magisk rollback fails and Download mode remains available, use the pinned
  stock boot-only fallback AP;
- manual download-mode rollback through `--rollback-from-download` may be used
  after operator manual Download entry.

Forbidden:

- no vendor_boot, DTBO, vbmeta, recovery, BL, CP, CSC, super, userdata, EFS,
  RPMB, keymaster, modem, or bootloader action;
- no raw host partition writes;
- no fastboot;
- no EUD sysfs write;
- no configfs;
- no ACM;
- no module binary injection;
- no broad module permutation.

If no self-download appears, stop and require manual rollback. Do not continue
to P10 until P00 self-download has been observed and rollback is clean.
