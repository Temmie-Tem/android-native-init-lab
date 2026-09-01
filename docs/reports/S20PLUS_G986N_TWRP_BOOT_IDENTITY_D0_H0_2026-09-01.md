# S20+ G986N TWRP boot-identity D0 H0 report

Date: 2026-09-01

Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`

Status: `BINDING_ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE`

## Outcome

A fixed-input attended D0 runner is reviewed and active. Its sole
connected purpose is to bind the S20+ `boot` partition's direct device path,
major/minor, `PARTNAME`, partition number, and exact size while the already
retained T2 recovery is running.

The remote audit opens no block device and reads no partition bytes. It uses
only `lstat`/symlink resolution, block-inode metadata, and fixed sysfs text.
It performs no write, mount, payload staging, reboot, mode transition, Odin
invocation, or transfer. This H0 unit contacted no device.

## Exact predecessor

Before each first ADB command, the runner revalidates the complete retained
T2 run using the committed T2 owner. It requires all 43 journal nodes, the
exact 1,911-byte terminal at SHA-256
`da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05`,
`PROVED_T2_RECOVERY_RETAINED`, the consumed no-replay candidate, the exact T2
host closure, and an absent shared S20+ action guard.

The terminal supplies only SHA-256 forms of the selected serial, physical USB
topology, and predecessor recovery boot. No raw serial, topology, or boot ID is
persisted by this D0 runner. T2 evidence is a selection prerequisite only and
explicitly transfers no T2/F2 command or partition authority.

## Fixed connected sequence

One invocation has exactly seven bounded host commands:

1. global `adb devices -l` inventory;
2. `get-devpath` for the sole row matching the retained T2 serial hash in ADB
   state `recovery`;
3. the exact T2 identity script before the metadata read;
4. one fixed boot-metadata script;
5. the byte-identical T2 identity script after the read;
6. a second selected-target `get-devpath`; and
7. a final global inventory.

The selected serial and topology must match the retained terminal. The live
T2 script must prove root UID 0, exact TWRP version/incremental, security
properties, `mtp,adb`, running adbd, marker hash, and one stable current boot.
The two inventories and two devpath observations must remain identical. A
foreign attached device is retained only as a sanitized inventory digest and
receives zero commands. Any other `model:SM_G986N` row causes ambiguity stop.

There is no internal retry. Any command failure, nonempty stderr, timeout,
oversize output, malformed framing, identity drift, topology drift, or
inventory drift closes that invocation with a no-retry failure receipt.

## Fixed boot metadata read

The 1,916-byte remote script is SHA-256
`1335eeee973bf4a77802c54b0eaff38a15122efe58ff7be0bded6f0557abe09d`.
It accepts no argument and uses only the fixed link
`/dev/block/bootdevice/by-name/boot`.

It requires that link to be a symlink, resolves it below `/dev/block/`, checks
the target inode is a block device, obtains its rdev with `stat`, and reads only
these derived sysfs nodes:

- `/sys/dev/block/<major>:<minor>/uevent`
- `/sys/dev/block/<major>:<minor>/dev`
- `/sys/dev/block/<major>:<minor>/partition`
- `/sys/dev/block/<major>:<minor>/size`

The script extracts only `MAJOR`, `MINOR`, `DEVNAME`, `DEVTYPE`, `PARTNAME`,
and `PARTN`; it never emits `PARTUUID`. It cross-checks the inode rdev against
both sysfs sources, requires the direct basename to equal `DEVNAME`, requires
`DEVTYPE=partition` and `PARTNAME=boot`, and requires the two partition numbers
to agree.

The host parser then requires exactly 14 ordered LF-terminated fields, decimal
bounds, `131072` 512-byte sectors, and exactly 67,108,864 bytes. It also
requires the explicit facts `node_is_block=1`, `block_device_open_count=0`,
and `partition_content_bytes_read=0`.

The pre/post T2 identity script is the already reviewed 1,054-byte script at
SHA-256
`83f594baef14a0709acbf01985697df07ef67c396801180896a4e2d8c8b9e60f`.

## Offline recovery-image support

The exact retained T2 recovery image was unpacked host-only. Its ramdisk
contains the fixed `sh`, `cat`, `readlink`, `stat`, and `awk` executables or
toybox links needed by the script. Its `twrp.flags` exposes exactly one
`flashimg=1` surface, `/boot`, at the same fixed by-name link. This offline
support proves command availability and configuration, not live block identity
or authority.

## Result and claim boundary

A successful result may prove only:

- the current exact T2 recovery identity and stable connection;
- one direct path and rdev pair mapping to sysfs `PARTNAME=boot`;
- the partition number and 64-MiB sysfs size; and
- zero block opens, content reads, writes, reboots, Odin calls, and transfers.

It does not prove a write-capable fd guard, staged-image safety, fsync/readback,
TWRP boot-write feasibility, candidate boot, or PID1. It grants no direct
block write, F1, F2, recovery-partition, `misc`, UI, terminal, mount, format,
install, backup, restore, or replay authority.

## H0 validation

The reviewed dormant runner was 29,864 bytes at SHA-256
`428899d373fce632337f4b552a62e3e593e7f6440fe6f4724322b2a9fd65e013`.
The mechanically activated runner is 29,863 bytes at SHA-256
`a71db531a25778b2dbd38c0b05b897dac33a7cc2f7eef51ba59edd899f9ecec6`.
Its activation-normalized SHA-256 is
`abd40c644e5bbbac8da743bee8e94e427730dca252bfadcbf39f6beb71b7bdfb`.
The mechanically activated 21,208-byte focused test is SHA-256
`5f895be987466257a88c59cec980a329aa1027e90b1ba018325b98fe2b6aad1d`.

Focused tests pass 15/15. They cover the dormant gate, complete current T2
journal, exact fake two-device selection, foreign-device isolation, all field
and cross-check mutations, state/topology/identity/inventory drift, framing and
producer failures, shell syntax, exact T2 ramdisk command/boot-flag surface,
zero content/open surface, no-clobber private publication, and activation
normalization. `py_compile` and `git diff --check` pass.

Independent hostile review returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.
The exact T2-ramdisk command/boot-flag test delta received the same `0/0/0`
result. Mechanical activation changed only the reviewed boolean,
activation-state test assertions, and target-contract status/full-hash wording.
The normalized identity and command surface are unchanged. Activation creates
no invocation or standing authority. Independent review of that exact
activation delta returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`.

## Next gate

The remaining step is one attended `--connected` invocation under the current
direct operator request, followed by exact result review. Even a successful D0
result will return to H0 review before any identical-resident write
qualification is designed.
