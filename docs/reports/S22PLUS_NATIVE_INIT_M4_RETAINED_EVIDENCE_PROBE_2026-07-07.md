# S22+ Native-Init M4 Retained-Evidence Probe - 2026-07-07

## Scope

Host-controlled, read-only rooted-Android probe after the M3.2 live incident.
No flash, reboot, Odin transfer, partition write, Magisk module install, module
load/unload, sysfs/configfs write, or recovery action was performed.

The purpose was to verify the evidence channel before designing the next
native-init proof. M3.2 already showed that the direct-PID1 self-return design
can bootloop without host-visible USB or Odin, so the next proof must not rely
on the candidate returning itself to download mode or exposing Android/USB as
the first proof channel.

## Added Helper

```text
workspace/public/src/scripts/revalidation/s22plus_retained_evidence_probe.py
```

The helper:

- pins the target as `SM-S906N` / `g0q` / `S906NKSS7FYG8`;
- reads `/proc/config.gz`;
- reads live DT retained-memory properties under `/proc/device-tree`;
- captures `/sys/fs/pstore` listing, `/proc/last_kmsg`, and dmesg tail;
- searches retained logs for known `S22_NATIVE_INIT` markers;
- writes raw captures only under `workspace/private/runs/`;
- redacts the device serial in the committed summary.

## Validation Command

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_retained_evidence_probe.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_retained_evidence_probe.py \
  --serial <redacted>
```

Private run:

```text
workspace/private/runs/s22plus_retained_evidence_probe_20260706T192800Z/
```

## Result

Current Android baseline:

```text
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
boot_completed=1
boot_recovery=0
verifiedbootstate=orange
root_id_contains_uid0=true
getenforce=Enforcing
```

Kernel config confirms pstore support is built:

```text
CONFIG_PSTORE=y
CONFIG_PSTORE_CONSOLE=y
CONFIG_PSTORE_PMSG=y
CONFIG_PSTORE_RAM=y
```

Live DT confirms a ramoops node exists, but it is disabled:

```text
/proc/device-tree/reserved-memory/ramoops_region/compatible = "ramoops"
/proc/device-tree/reserved-memory/ramoops_region/status = "disabled"
/proc/device-tree/reserved-memory/ramoops_region/size = 0x200000
/proc/device-tree/reserved-memory/ramoops_region/pmsg-size = 0x200000
```

Samsung retained-debug regions are also present:

```text
sec_debug_region_log@8001FF000/reg  = 0x00000008 0x001ff000 0x00000000 0x00901000
sec_debug_region_pool@800100000/reg = 0x00000008 0x00100000 0x00000000 0x000ff000
google_debug_kinfo_region@800B00000/reg = 0x00000008 0x00b00000 0x00000000 0x00001000
```

Runtime evidence:

```text
/sys/fs/pstore listing: total 0
/proc/last_kmsg captured bytes: 2097136
dmesg read: allowed in the current Magisk-root context
S22_NATIVE_INIT marker hits: none
```

Follow-up baseline check after the operator reported manual download-mode entry
due to a confirmed bootloop:

```text
adb transport: normal Android
boot_completed=1
boot_recovery=0
verifiedbootstate=orange
root_id_contains_uid0=true
live boot partition SHA256:
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The live boot-partition hash matches the pinned Magisk boot-only rollback
payload, so the device is currently recovered to the rooted Android baseline.

## Interpretation

`/sys/fs/pstore` is not a reliable standalone negative proof on this device.
The kernel has pstore support and the DT contains a `ramoops` node, but the live
node reports `status=disabled`, and the pstore filesystem remains empty after
the relevant download/rollback path.

`/proc/last_kmsg` is the stronger retained channel currently available. It
retains the normal Android `reboot,download` path and ABL `reboot_reason = 0x9`
records, but the M3.2 post-rollback capture did not contain any
`S22_NATIVE_INIT` marker or panic/oops signature.

Therefore:

- absence from `/sys/fs/pstore` alone proves nothing;
- absence from both `/sys/fs/pstore` and `/proc/last_kmsg` is stronger, but
  still not a definitive "custom /init never ran" proof if the candidate dies
  before the retained backend commits;
- the next native-init proof must be designed around a non-self-reboot recovery
  assumption: the operator may need to force download mode, then the host rolls
  back and immediately collects a retained evidence bundle.

## Next Design Boundary

Do not flash another long-dwell M3.x direct-PID1 self-return candidate.

After this retained-evidence probe, the operator clarified that the observed
loop is fast. That demotes the M4A fast-dwell/watchdog hypothesis behind a
cleaner floor probe: M4 TEST 0 instant-download. In M4T0, direct `/init`'s first
candidate action is `reboot(..., "download")`, before marker writes, dwell,
watchdog handling, modules, USB, configfs, Android handoff, or retained-log
assumptions.

The next bounded unit should therefore be M4T0 host-only design/build:

1. replace `/init` with a static direct-PID1 binary;
2. make the first action a Samsung download reboot;
3. write no marker before the reboot syscall;
4. avoid USB/NCM/modules/configfs/Android/Magisk handoff;
5. treat fast self-entry to download mode as proof that the kernel executed
   custom `/init` and that the download reboot path works;
6. treat another fast loop/no download as proof that the floor is below
   marker/dwell logic, then move to minimal-delta boot or UART.

M4A remains useful only as the next layer after M4T0 proves the `/init` floor.
UART remains the clean real-time channel that can distinguish "custom `/init`
never ran" from "custom `/init` ran but retained logging failed" without
another ambiguous persistence result.
