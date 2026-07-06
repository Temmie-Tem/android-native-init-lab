# S22+ Native-Init M3.1 Live Gate Preflight - 2026-07-07

## Scope

Prepared and dry-ran the guarded live gate for the M3.1 marker-only native-init
candidate. No live flash, Odin transfer, reboot, partition write, sysfs/configfs
write, module load, Magisk module install, or recovery action was performed.

## Added Helper

```text
workspace/public/src/scripts/revalidation/s22plus_m31_marker_live_gate.py
```

The helper is fail-closed:

- dry-run is the default;
- live mode requires `--live --ack S22PLUS-M31-MARKER-LIVE-GATE`;
- `AGENTS.md` must contain the exact M3.1 SHA-pinned exception;
- candidate AP must match the exact M3.1 AP hash and contain only
  `boot.img.lz4`;
- candidate manifest must confirm marker-only safety:
  `module_insertions=false`, `configfs_runtime_gadget=false`,
  `auto_reboot=download-after-10s-observation`;
- rollback APs must match the pinned Magisk boot-only AP and stock boot-only
  fallback AP;
- current Android must be a single `SM-S906N` / `g0q` / `S906NKSS7FYG8`
  device with boot completed and orange verified boot;
- post-rollback pstore collection searches for
  `S22_NATIVE_INIT_MARKER_ONLY_M31`.

## AGENTS Update

Added a narrow M3.1 exception for exactly one attended boot-only live gate:

```text
candidate AP.tar.md5 SHA256=999beeb67f73c39eaa0b637bc3c62fe2d8474fa707110640ae51adca0fbd2cfb
candidate boot.img SHA256=f3dea68c02be295141265820f4acdd425a12460e05957edf75c83a62c4a617c5
primary rollback Magisk AP.tar.md5 SHA256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
fallback rollback stock AP.tar.md5 SHA256=1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

It authorizes only the M3.1 marker-only behavior: create `/dev/kmsg` and
fallback `/dev/pmsg0`, emit `S22_NATIVE_INIT_MARKER_ONLY_M31`, briefly dwell,
attempt `download` reboot, and park if that syscall returns. It does not
authorize USB/NCM, display, distro, module insertion, configfs gadget work, or
any non-boot partition.

## Dry-Run Command

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py \
  workspace/public/src/scripts/revalidation/s22plus_m31_marker_live_gate.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m31_marker_live_gate.py
```

Private dry-run log:

```text
workspace/private/runs/s22plus_m31_marker_live_gate_20260706T183532Z/
```

## Dry-Run Result

PASS:

```text
agents_exception_missing=[]
m31_candidate_sha256=999beeb67f73c39eaa0b637bc3c62fe2d8474fa707110640ae51adca0fbd2cfb
m31_candidate_members=['boot.img.lz4']
m31_manifest_auto_reboot=download-after-10s-observation
m31_manifest_module_insertions=false
m31_manifest_configfs_runtime_gadget=false
magisk_boot_rollback_sha256=d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock_boot_fallback_sha256=1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
android_preflight=model SM-S906N, device g0q, bootloader S906NKSS7FYG8,
  boot_completed 1, verified boot orange, Magisk root uid 0
```

## Live Boundary

Live M3.1 is now gated but not executed. The live command shape is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m31_marker_live_gate.py \
  --live \
  --ack S22PLUS-M31-MARKER-LIVE-GATE
```

Expected live flow:

1. Helper verifies rooted Android preflight and uses `adb reboot download`.
2. Helper flashes the exact boot-only M3.1 AP.
3. M3.1 should write kmsg/pmsg marker, dwell briefly, and attempt `download`
   reboot.
4. Helper rolls back with the pinned Magisk boot-only AP when download mode
   appears.
5. Helper verifies rooted Android returns and collects pstore marker evidence.

If M3.1 does not reach download mode, physical recovery remains required.
