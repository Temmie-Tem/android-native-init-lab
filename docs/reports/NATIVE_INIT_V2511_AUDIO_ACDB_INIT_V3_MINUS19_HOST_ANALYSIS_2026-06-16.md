# NATIVE_INIT V2511 — audio ACDB init_v3 -19 host analysis

## Decision

`v2511-acdb-init-v3-minus19-is-acdb-root-mismatch`

V2511 is host-only.  It explains the V2510 own-process
`acdb_loader_init_v3()` return value `-19` without rerunning the same helper.

The blocker is now classified as an ACDB database root mismatch:

- the V2508 helper calls
  `acdb_loader_init_v3("/vendor/etc/acdbdata", "/data/local/tmp/a90-acdb-ownget/delta", 0)`;
- V2510 live setup showed `/vendor/etc/acdbdata` contains only
  `adsp_avs_config.acdb`;
- the production calibration sets found in the V2324 vendor inventory are under
  `/vendor/etc/audconf/<carrier>/`, including `OPEN`, not under
  `/vendor/etc/acdbdata`;
- Thumb disassembly of `libacdbloader.so` shows `init_v3` is only a thin
  wrapper around `init_v4`, and `init_v4` has an early `-19` return before the
  first `acdb_ioctl()` call when ACDB file initialization cannot proceed;
- V2510 captured zero `acdb_ioctl()` rows, so the failure happened before the
  GET matrix and before any topology/per-device command could run.

Do not rerun V2508/V2510 unchanged.  The next unit should build a corrected
helper variant that supplies `/vendor/etc/audconf/OPEN` first, while keeping the
same pure-read command matrix and the same ban on `/dev/msm_audio_cal` SET
ioctl `0xC00461CB`.

## Scope

No device action ran in this unit:

- no Android handoff;
- no Magisk module;
- no HAL injection;
- no playback;
- no native speaker write;
- no `/dev/msm_audio_cal` open/ioctl;
- no `acdb_ioctl()` call;
- no partition or boot image write.

The analysis used only existing host artifacts and private V2510 evidence.

## Evidence

### V2510 live result

Private run:

- `workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-033836/`

The device-side helper emitted exactly one event:

```json
{"event":"error","stage":"acdb_loader_init_v3","code":-19,"pid":3804,"tid":3804}
```

The helper rc file contained `29`, matching the wrapper's fatal init failure
classification.  No raw payload files were generated.

The live setup command showed the supplied ACDB path exists, but contains only
one tiny ACDB file:

```text
total 4
-rw-r--r-- 1 root root 240 2009-01-01 00:00 adsp_avs_config.acdb
```

That is not the full speaker/handset/headset/general production ACDB set.

### Static loader RE

Input:

- `workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so`

`readelf -Ws` confirms the relevant exported entry points:

```text
acdb_loader_init_v3  @ 0x00009785 size 52
acdb_loader_init_v4  @ 0x0000808d size 3160
acdb_loader_send_common_custom_topology @ 0x00008cf1
acdb_loader_send_audio_cal_v5 @ 0x00009d31
```

Thumb-mode disassembly confirms `acdb_loader_init_v3()` constructs the expected
16-byte argument block and calls `acdb_loader_init_v4(arg, 4)`:

```text
00009784 <acdb_loader_init_v3@@Base>:
  ...
  9794: strd r2, r3, [sp, #12]
  9798: strd r1, r0, [sp, #4]
  979c: add  r0, sp, #4
  979e: movs r1, #4
  97a0: blx  0x15be0   ; PLT -> acdb_loader_init_v4
```

The `init_v4` PLT map shows:

```text
0x15a70 acdb_ioctl
0x15a90 fopen
0x15aa0 fgets
0x15ab0 __open_2
0x15b20 ion_open
0x15d70 opendir
0x15d80 readdir
0x15d90 closedir
```

The first `acdb_ioctl()` calls inside `init_v4` appear after the early ACDB file
setup region, for example:

```text
0x81e6 -> acdb_ioctl
0x822c -> acdb_ioctl
0x842e -> acdb_ioctl
0x8596 -> acdb_ioctl
```

`init_v4` also has an early `-19` return before the later success path.  The
relevant instruction pattern is:

```text
83da: log failure
83e8: mvn.w r6, #18     ; r6 = -19
83ec: b     8aa4        ; return r6
```

Because V2510 captured zero `acdb_ioctl()` rows, all failure branches after the
first `acdb_ioctl()` are eliminated for that run.  The only live-consistent
class is an early initialization failure before the command matrix.

### ACDB file layout mismatch

V2324 host inventory found 33 `.acdb` files in the vendor image:

```text
/etc/audconf/SKC/{Bluetooth,Codec,General,Global,Handset,Hdmi,Headset,Speaker}_cal.acdb
/etc/audconf/OPEN/{Bluetooth,Codec,General,Global,Handset,Hdmi,Headset,Speaker}_cal.acdb
/etc/audconf/LUC/{Bluetooth,Codec,General,Global,Handset,Hdmi,Headset,Speaker}_cal.acdb
/etc/audconf/KTC/{Bluetooth,Codec,General,Global,Handset,Hdmi,Headset,Speaker}_cal.acdb
/etc/acdbdata/adsp_avs_config.acdb
```

Therefore `/vendor/etc/acdbdata` is a real directory, but it is not the root for
the full production calibration set.  The full set is the carrier-scoped
`/vendor/etc/audconf/<carrier>` tree.  `OPEN` is present and is the safest first
own-process read target.

Prior audio analysis already recorded that `libacdbloader.so` uses both
`/vendor/etc/acdbdata` and `/vendor/etc/audconf/OPEN`; V2510 proves that passing
only `/vendor/etc/acdbdata` as the `init_v3` scan root is insufficient for the
own-process helper.

## Consequence

V2510 did **not** disprove:

- the V2508 exec-linked loader strategy;
- the `init_v3` ABI;
- the topology command IDs;
- the per-device direct-GET plan;
- the V2474 replay scaffold.

It only proved that the first own-process helper supplied the wrong ACDB scan
root for the full calibration database.

## Next unit

V2512 should be host-only implementation first:

1. Add an exec-linked own-process helper variant whose ACDB root is configurable
   or compiled as `/vendor/etc/audconf/OPEN`.
2. Extend the live runner setup inventory to list:
   - `/vendor/etc/acdbdata`;
   - `/vendor/etc/audconf`;
   - `/vendor/etc/audconf/OPEN`;
   - available carrier subdirectories.
3. Keep the direct-GET matrix pure-read:
   - topology GET candidates: `0x11394`, `0x12E01`, `0x130DA`, `0x130DC`;
   - per-device GET candidates only if they are direct read commands;
   - no `/dev/msm_audio_cal` SET ioctl `0xC00461CB`.
4. Rerun live only after the helper and runner are rebuilt and statically
   validated.

If `/vendor/etc/audconf/OPEN` still returns `-19`, the next discriminator is a
live recursive metadata-only inventory of `/vendor/etc/audconf/*` and the
system-property/carrier selection that the stock HAL uses.  Do not return to
in-HAL preload/wrapper-exec paths unless the operator explicitly reopens them.

## Validation

Host-only commands used:

```bash
readelf -Ws workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so
aarch64-linux-gnu-objdump -d -M force-thumb --start-address=0x808c --stop-address=0x8cf0 \
  workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so
aarch64-linux-gnu-objdump -d -M force-thumb --start-address=0x9784 --stop-address=0x97fc \
  workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so
rg -n "\\.acdb|acdbdata|audconf" workspace/private/runs/audio/v2324-aud0-inventory/
```

No public report contains raw ACDB bytes or vendor shared-library contents.
