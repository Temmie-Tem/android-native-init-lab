# S22+ Native-Init M3.2 Live Gate Preflight - 2026-07-07

## Scope

Prepared and dry-ran the guarded live gate for the M3.2 marker-only
native-init candidate. No live flash, Odin transfer, reboot, partition write,
sysfs/configfs write, module load, Magisk module install, or recovery action was
performed.

## Added Helper

```text
workspace/public/src/scripts/revalidation/s22plus_m32_marker_live_gate.py
```

The helper is fail-closed:

- dry-run is the default;
- live mode requires `--live --ack S22PLUS-M32-MARKER-LIVE-GATE`;
- `AGENTS.md` must contain the exact M3.2 SHA-pinned exception;
- candidate AP must match the exact M3.2 AP hash and contain only
  `boot.img.lz4`;
- candidate manifest must confirm marker-only safety:
  `module_insertions=false`, `configfs_runtime_gadget=false`,
  `auto_reboot=download-after-10s-observation`;
- candidate manifest must confirm stock-format ramdisk packaging:
  `format=legacy-lz4`, `magic_hex=02214c18`, and a roundtrip hash matching the
  uncompressed cpio hash;
- rollback APs must match the pinned Magisk boot-only AP and stock boot-only
  fallback AP;
- current Android must be a single `SM-S906N` / `g0q` / `S906NKSS7FYG8`
  device with boot completed, orange verified boot, and Magisk root;
- post-rollback retained-evidence collection searches both `/sys/fs/pstore`
  and `/proc/last_kmsg` for `S22_NATIVE_INIT_MARKER_ONLY_M32`.

## AGENTS Update

Added a narrow M3.2 exception for exactly one attended boot-only live gate:

```text
candidate AP.tar.md5 SHA256=6073e4988a98f741fa207df4efb8a05e144ad16b3a90f43db2ec408657936fc2
candidate boot.img SHA256=0bb1ef280e42aa2c6069538e77fc21b5330cf9419a19785f79d05da8429bf1fc
primary rollback Magisk AP.tar.md5 SHA256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
fallback rollback stock AP.tar.md5 SHA256=1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

It authorizes only the M3.2 marker-only behavior: legacy-LZ4 ramdisk package,
create `/dev/kmsg` and fallback `/dev/pmsg0`, emit
`S22_NATIVE_INIT_MARKER_ONLY_M32`, briefly dwell, attempt `download` reboot, and
park if that syscall returns. It does not authorize USB/NCM, display, distro,
module insertion, configfs gadget work, recovery/vendor_boot/vbmeta/non-boot
flash, format data, or any A90 action.

## Dry-Run Command

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m32_marker_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m31_marker_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m32_marker_live_gate.py
```

Private dry-run log:

```text
workspace/private/runs/s22plus_m32_marker_live_gate_20260706T185328Z/
```

## Dry-Run Result

PASS:

```text
agents_exception_missing=[]
m32_candidate_sha256=6073e4988a98f741fa207df4efb8a05e144ad16b3a90f43db2ec408657936fc2
m32_candidate_members=['boot.img.lz4']
m32_manifest_auto_reboot=download-after-10s-observation
m32_manifest_module_insertions=false
m32_manifest_configfs_runtime_gadget=false
m32_manifest_ramdisk_format=legacy-lz4
m32_manifest_ramdisk_magic=02214c18
m32_manifest_ramdisk_roundtrip=matches-ramdisk-cpio
magisk_boot_rollback_sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock_boot_fallback_sha256=1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
android_preflight=model SM-S906N, device g0q, bootloader S906NKSS7FYG8,
  boot_completed 1, verified boot orange, Magisk root uid 0
```

## Pstore / Last-Kmsg Addendum

The operator reported a bootloop and manual download-mode recovery after the
M3.x work. By the time the host checked, Android was reachable again with
boot completed, orange verified boot, `boot_recovery=0`, and Magisk root. No
new M3.2 live flash was executed by this helper.

Private capture:

```text
workspace/private/runs/s22plus_bootloop_recovery_capture_20260706T185950Z/
```

Host-only evidence:

- shipped/live kernel config has `CONFIG_PSTORE=y`,
  `CONFIG_PSTORE_CONSOLE=y`, `CONFIG_PSTORE_PMSG=y`, and
  `CONFIG_PSTORE_RAM=y`;
- the captured vendor-boot DTB contains ramoops / reserved-memory strings,
  including `pmsg-size` and `alloc-ranges`;
- current Android mounts pstore at `/sys/fs/pstore`, but the directory is
  empty;
- `/proc/last_kmsg` is readable and was captured at 2,097,136 bytes;
- `S22_NATIVE_INIT` marker strings were not found in that captured
  `last_kmsg`;
- panic signatures `Kernel panic`, `not syncing`, `Unable to mount root`, and
  `Oops` were not found;
- the retained log does contain the operator-relevant `reboot, download` path
  and repeated ABL `reboot_reason = 0x9` records.

Interpretation: pstore infrastructure is present, but empty `/sys/fs/pstore`
alone is not a trustworthy negative proof on this device. Future M3.x live
results must treat marker evidence as "retained marker found in pstore OR
last_kmsg"; absence from only pstore is ambiguous.

## Live Boundary

Live M3.2 is now gated but not executed. The live command shape is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m32_marker_live_gate.py \
  --live \
  --ack S22PLUS-M32-MARKER-LIVE-GATE
```

Expected live flow:

1. Helper verifies rooted Android preflight and uses `adb reboot download`.
2. Helper flashes the exact boot-only M3.2 AP.
3. M3.2 should write kmsg/pmsg marker, dwell briefly, and attempt `download`
   reboot.
4. Helper rolls back with the pinned Magisk boot-only AP when download mode
   appears.
5. Helper verifies rooted Android returns and collects pstore plus
   `/proc/last_kmsg` marker evidence.

If M3.2 does not reach download mode, physical recovery remains required.
