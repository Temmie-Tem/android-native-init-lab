# S22+ M19 Closed Checkpoint/Download Host Build (2026-07-08)

## Verdict

PASS, host-only build.

M19 prepares a no-UART fallback matrix that uses an external behavior as the
proof channel: load a bounded prefix of a dependency-closed USB module list,
then immediately request Samsung download mode. A later host-observed
download-mode return means the checkpoint was reached.

No live flash was executed or authorized by this unit.

## Artifacts

- Source:
  `workspace/public/src/native-init/s22plus_init_m19_closed_checkpoint_download.c`
- Builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_inplace_m19_closed_checkpoint_download.py`
- Private output:
  `workspace/private/outputs/s22plus_native_init/inplace_m19_closed_checkpoint_download_v0_1`
- Top private manifest:
  `workspace/private/outputs/s22plus_native_init/inplace_m19_closed_checkpoint_download_v0_1/manifest.json`

The builder uses the M18 postmortem dependency closure and produces one
boot-only Odin AP per checkpoint. Each AP contains exactly one tar member,
`boot.img.lz4`.

## Module Closure

M18 base list: `141` modules.

M19 closed list: `150` modules.

Added modules:

- `switch_class.ko`
- `usb_notify_layer.ko`
- `common_muic.ko`
- `usb_f_ss_mon_gadget.ko`
- `repeater.ko`
- `qc_usb_audio.ko`
- `redriver.ko`
- `gpi.ko`
- `spu_verify.ko`

Unresolved non-reset dependency edges: `{}`.

Remaining reset/anomaly blocklist edges are intentionally excluded. They are
not counted as unresolved non-reset closure failures.

## Prefix Matrix

| Label | Count | AP.tar.md5 SHA256 | boot.img SHA256 | init SHA256 | Next module |
|---|---:|---|---|---|---|
| C000 | 0 | `d712840f1aa7d4ef9d07a7be404b29e5f5dd8065701db7f3d39d76c71296b9d4` | `0ae71d30257dafdc453db252bd77b11b554202f27c458e3b538d13c61df98ebb` | `7d4f7c8fb30af6aa1e21fe1fe6b24a6597c7385424f5d90e3bf6309a68441135` | `sec_class.ko` |
| C129 | 129 | `e02912e24ab3ebc4be349fa0797d152482dd5f4828005022004f4445d6f6f38d` | `0317e2aa518bacf9e4269400604870d7dd4552ae4af593eb2934332086e723c0` | `097c78297a56671b3e281e43aa84f2b752752a7c54382c819ea92a23722d157d` | `switch_class.ko` |
| C135 | 135 | `1595651b2ad90145ef8a1ddadf72f1167992885108f3e955337bc7e223a912eb` | `c36ee517bf26b1d08b650f7a9be3d36fa4bc5356aa6fce928241990720864bcd` | `c2b55cbcbad7baef7448a43f60087f30fe98c63d8c0f1e9620f4e89b520d8554` | `usb_f_ss_mon_gadget.ko` |
| C137 | 137 | `36446c1071271cf9387c1279ff120bd18b81082a00e8ac279a580e418e824de7` | `fa71ecc2beedc706225b524e9ac516c22bb2ce63c1fa4d0c2d5313cf09d49246` | `f4214a41ce81b2ec172515b0c3b0a5deab22f1e8f88aef2a1144ab0a910e4230` | `repeater.ko` |
| C140 | 140 | `2becf7eb3c9b5ba0dfaa0706e7b22589f8baabcaafd062ea9b672db2ab4beda4` | `6e7a8a27d776973ead71f3b88a85474b2ede55979eee39ea07c11fea839ac0fc` | `de74e5eef3cff90814f333301c8078a521dfcebe0e553bfe12b0321142460c86` | `qc_usb_audio.ko` |
| C144 | 144 | `47b5acdfb6d984173fe7a746ce8f06cd80ad2aef4326a7cc0a5af154c8b60765` | `48d351826294e5cc870f80aa52768c43e6a7926d064526e2c6f73e752bc3bf87` | `e9964ee9fc35bb8222df5773e60b4c63a4927cadf14b267a14f441bda101072b` | `usb_f_ss_acm.ko` |
| C145 | 145 | `424787690ba47439936b702ff7d5e2fb4d0ca117a6cb8a99de1744b8de1f23b8` | `9db9af9f165e1e5133d94153efedababf4f367f39c3b1871a810368ffe30d8bd` | `f64dfce4d9e9bb010d276c705e41d79f4849a524e996c688b322a2ed4ddd2777` | `gpi.ko` |
| C147 | 147 | `5a199c28e68b991eee9c62c3e20083ba8e599111775e8f84b6062e121f0e2e82` | `0a20b0dbdc7697bd275dab8b403ca1a92749e8654e439854a3a0a4e784df511c` | `244f3a35710c9e261da4b6c6edc92c9b1ef99633740dd5a7cf1555a90321ccc1` | `mfd_max77705.ko` |
| C150 | 150 | `53b211795d2357013939e3cadd7f98ecfa9bd57a9b72dd3b7b6eefb77aa2c623` | `6186402aa17ce31354818194b3ffad0a74a5e75df462c8de38b22a495c8f80fd` | `5e201e9ce2b9c721ee1c6cbb60e42ce3ac5c23cdadc7660309bd3f3961868950` | none |

## Safety Properties

- Host-only build, `device_action=false`.
- Live flash authorization: false.
- Any future live use requires a fresh SHA-pinned `AGENTS.md` boot-only
  exception for the exact selected AP.
- Boot-only package: one tar member, `boot.img.lz4`.
- Runtime has no Android/Magisk handoff, no ACM/configfs gadget, no USB role
  forcing, no persistent partition mount, and no block-device writes.
- Module binaries are not injected into the boot ramdisk; only the text module
  list is added. Runtime uses stock vendor ramdisk `/lib/modules`.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m19_closed_checkpoint_download.py \
  workspace/public/src/scripts/revalidation/s22plus_m18_capture_postmortem.py

aarch64-linux-gnu-gcc -nostdlib -static -ffreestanding -fno-builtin \
  -fno-stack-protector -fno-asynchronous-unwind-tables -fno-unwind-tables \
  -Os -Wall -Wextra -Werror -Wl,--build-id=none -Wl,-e,_start \
  -Wl,-z,noexecstack -DM19_PREFIX_LIMIT=150 -DM19_PREFIX_LABEL='"C150"' \
  -o /tmp/s22_m19_closed_checkpoint_test \
  workspace/public/src/native-init/s22plus_init_m19_closed_checkpoint_download.c

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m19_closed_checkpoint_download.py \
  --force
```

Results:

- Python compile passed.
- Static AArch64 compile passed.
- Disassembly contains raw syscall path, reboot syscall number `142`, and
  finit_module syscall number `273`.
- Matrix validation found 9 prefixes, `closed_count=150`, `base_count=141`,
  `added_count=9`, and `unresolved_nonblocked={}`.
- Every AP tar contains exactly `['boot.img.lz4']`.

## Next

No M19 live candidate is authorized by this build. If the operator chooses the
no-UART checkpoint path later, do not run the full matrix blindly. Add a fresh
SHA-pinned boot-only gate for one selected prefix, keep Magisk boot rollback
staged, and treat self-return to download mode as the only positive proof for
that prefix checkpoint.
