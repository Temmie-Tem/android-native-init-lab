# S22+ Native-Init M3 Postmortem And M3.1 Direction - 2026-07-07

## Scope

Host-only postmortem after the M3 v0.2 live gate. No flash, reboot, Odin
transfer, partition write, module load/unload, or Android sysfs/configfs change
was performed in this unit.

## Inputs Reviewed

Reports:

```text
docs/reports/S22PLUS_NATIVE_INIT_CHAINLOAD_CANDIDATE_2026-07-06.md
docs/reports/S22PLUS_NATIVE_INIT_P1_MAGISK_CHAINLOAD_HOST_BUILD_2026-07-07.md
docs/reports/S22PLUS_NATIVE_INIT_P2_MAGISK_CHAINLOAD_LIVE_2026-07-07.md
docs/reports/S22PLUS_NATIVE_INIT_P3_DIRECT_PID1_LIVE_INCIDENT_2026-07-07.md
docs/reports/S22PLUS_OBSERVABLE_NATIVE_INIT_M3_HOST_BUILD_2026-07-07.md
docs/reports/S22PLUS_OBSERVABLE_NATIVE_INIT_M3_V02_LIVE_RESULT_2026-07-07.md
```

Code/build paths:

```text
workspace/public/src/native-init/s22plus_init_chainload.c
workspace/public/src/native-init/s22plus_init_magisk_chainload.c
workspace/public/src/native-init/s22plus_init_observable_m3.c
workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py
workspace/public/src/scripts/revalidation/build_s22plus_observable_m3_boot.py
```

## Facts

Boot-only packaging is not the primary blocker:

- Odin accepted multiple boot-only AP packages containing exactly
  `boot.img.lz4`.
- Earlier chainload v0.2 booted Android from a modified boot image, although it
  did not produce a readable proof marker.
- M3 v0.2 candidate and Magisk rollback Odin transfers both completed with
  `rc=0`.

Direct-PID1 observability is the blocker:

- P3 direct PID1 produced no collectable marker and required recovery.
- M3 v0.2 direct PID1 produced no ADB, no NCM link, no pstore marker, and
  returned to Odin/download visibility roughly 33 seconds into observation.
- That 33 second return is too early to be the programmed M3 v0.2
  `download` reboot after about 90 seconds.

M3 marker is not early enough to distinguish all early failures:

- M3 calls `setup_minimal_fs()` before `write_markers()`.
- The first `emitf()` happens at the end of `setup_minimal_fs()`, after mkdirs,
  proc/sysfs/devtmpfs or tmpfs setup, `/dev/kmsg` creation, pmsg major lookup,
  pstore mount, and configfs mount.
- If the candidate fails, panics, or triggers a Samsung fallback before or
  during that setup, the current marker never lands.

Current rooted Android shows pmsg exists:

```text
/proc/devices: 507 pmsg
/proc/filesystems: nodev pstore
/sys/fs/pstore mounted on Android
```

The raw Android kernel cmdline was not copied into this public report because
it contains device identifiers.

## Interpretation

The M3 v0.2 failure should not be treated as a USB module-order failure yet.
The candidate did not provide evidence that it reached module insertion or
configfs gadget setup. The failure is above that layer:

```text
bootloader/kernel -> direct /init exec -> earliest marker
```

The next useful proof is therefore not another USB/NCM candidate. It is a
smaller marker-only candidate that proves whether direct `/init` is executing
at all and whether pmsg survives rollback.

## M3.1 Direction

Design the next candidate as marker-only, host-only first:

1. Keep boot-only packaging and rollback discipline unchanged.
2. Remove USB module insertion and configfs gadget setup from the candidate.
3. Make the first operations as close to syscall-only as possible:
   - `mkdir("/dev")`;
   - `mknod("/dev/kmsg", makedev(1, 11))`;
   - `mknod("/dev/pmsg0", makedev(507, 0))` as a target-specific fallback;
   - write `S22_NATIVE_INIT_MARKER_ONLY_M31` to kmsg and pmsg.
4. Only after the marker, optionally mount proc/sysfs and log secondary
   diagnostics.
5. Use a short bounded dwell, then `reboot(..., "download")`.
6. If the reboot syscall returns, park.

This design intentionally avoids USB, display, Android handoff, persistent
partitions, block writes, and configfs. It answers one question only:

```text
Does S22+ direct /init execute early enough to write a durable pmsg marker?
```

## Safety Boundary

No M3.1 live flash is authorized by this report. Before any live use, the
candidate must be built host-only, SHA-pinned in `AGENTS.md`, dry-run gated, and
reviewed as a new bounded boot-only unit with the same rollback preconditions.
