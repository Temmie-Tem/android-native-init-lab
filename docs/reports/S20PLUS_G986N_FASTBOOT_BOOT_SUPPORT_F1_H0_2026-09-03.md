# S20+ G986N fastboot-boot support F1 H0

State: **CONSUMED - NO_PROOF - HEALTHY RETURN; TERMINAL OWNER ONLY**

## Question

Determine only whether the proved S20+ classic bootloader implements the
optional RAM-only `fastboot boot` command. This unit does not attempt native
PID1 and does not reuse the consumed P0 candidate.

## Fixed experiment

- Target: exact `SM-G986N/y2q/y2qksx/G986NKSS8IYC2`.
- Tool: the already pinned official Google Platform-Tools fastboot 37.0.1.
- Payload: the previously proved healthy resident-Magisk rollback `boot.img`,
  67,108,864 bytes, SHA-256
  `d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc`.
- Sole fastboot command:
  `fastboot -s <bound-serial> boot <bound-resident-boot.img>`.
- Planned RAM payload transfer attempts: one. Partition/persistent writes and
  all other fastboot commands: zero.

The runner pins the P0 rollback/healthy terminal, the completed classic-
fastboot census, the census helper and its raw-capture/ADB-parser sources, the
ADB and fastboot executables, and the payload. A new journal digest makes each
approval unique. The operator must return the exact approval before the
one-use entry intent is published.

All command streams are captured privately before parsing. Exact
`Booting OKAY` without a contradictory failure is `COMMAND_ACCEPTED`; only a
same-line remote unsupported response is `UNSUPPORTED`; everything else is
`UNCERTAIN`. No branch permits replay.

## Recovery and claims

If transient boot is accepted, wait for Android. If it remains in fastboot or
the transient boot fails, use physical `START` or power-cycle into the
unchanged persistent resident boot. The finalizer requires the fastboot
endpoint absent and a fresh same-target healthy Android boot before releasing
the guard. A pre-entry zero-effect abort is separately available before the
consumed entry exists.

This experiment can prove only whether the bootloader accepts `fastboot boot`.
It cannot prove that an arbitrary candidate executed, native PID1, or safety
of another image. A later PID1 attempt requires a fresh byte-distinct candidate
and separate review.

Current focused validation: 20 tests pass. Independent review returned
`PASS_GO` with CRITICAL/MAJOR/MINOR `0/0/0`. The dormant runner was 45,133
bytes with SHA-256
`1b46c561cb0742d3b97ac0086588ae8e0d39d32aa96e2831e43735fa0cf7bdb1`;
the mechanically activated runner is 45,132 bytes with SHA-256
`e675b9941b45f663aa1512a5cfbbfd815f1883101b7b1f79d83d94ac9fdf0f76`.
The sole approved invocation is consumed. The exact command returned 1 and the
private raw capture contains `Sending 'boot.img' ... FAILED (remote: 'unknown
command')` followed by `fastboot: error: Command failed`. The reviewed parser
preserved `UNCERTAIN` because this failure did not match its fixed `Booting`
line grammar; no replay occurred. The sole allowed invocation did not
establish a usable standard transient-boot path, and no retry is authorized.

Physical `START` returned the unchanged resident boot to fresh healthy Android.
The 590-byte command result has SHA-256
`04e77076e7b54b5b88abf2a69911aa531d8ed48413d3522b7d629edf6e43f367`;
the 1,426-byte terminal has SHA-256
`97d6af22b11dddba6e515d859c08525bab1549ea49d62970f64fdb6f116cf52e`
and verdict `NO_PROOF_S20PLUS_G986N_FASTBOOT_BOOT_RETURNED_HEALTHY`. The shared
guard is absent. The result records one RAM payload-transfer attempt, zero
partition writes, zero persistent mutation, and no native PID1 proof.

## Exact stock ABL host-only analysis

This follow-up used only the retained exact `G986NKSS8IYC2` stock firmware.
It sent no ADB or fastboot command and caused no device effect. The firmware
contains BL member
`BL_G986NKSS8IYC2_G986NKSS8IYC2_MQB93855401_REV00_user_low_ship_MULTI_CERT.tar.md5`,
whose SHA-256 is
`c79ee6599055cb094bc2342a3c44c1411e7ee5c511e016e05bff1249e94e7a1d`.
That member contains `abl.elf.lz4`, `xbl.elf.lz4`, `xbl_config.elf.lz4`, and
the other signed Qualcomm/Samsung BL components.

Decompressing `abl.elf.lz4` produced an exact 4,194,304-byte ARM ELF with
SHA-256
`fe07db573ed1b0060c54d8bec068d9e83975b170ae8a1fd47328c04f5477979a`.
The apparent lack of plain fastboot strings in that outer image was compression,
not proof of encryption: a UEFI firmware volume begins at file offset
`0x3000`. Extracting its guided and nested FFS volumes produced four ARM64 EFI
applications named `LinuxLoader`, `Odin`, `Cryptest`, and `QuestSOD`.

The relevant `LinuxLoader` PE is 3,301,376 bytes with SHA-256
`591649004cb7a04353648ce7f14c46ad7789cbfde9c4758b22e430dfebc07fe3`.
It is stripped but directly disassemblable. Samsung's exact open-source
package contains `Kernel.tar.gz` and `Platform.tar.gz`, not this bootloader
source, so the exact command result necessarily comes from binary analysis;
the public package listing is available from
[Samsung Open Source](https://opensource.samsung.com/uploadSearch?searchValue=G986NKSS8IYC2).

### Registered classic-fastboot commands

The `LinuxLoader` registration loop at RVAs `0x58f34` through `0x58f50`
uses table base `0xc7e88`. It skips the empty sentinel, loads one 16-byte
name/handler pair per iteration, and stops after exactly two pairs:

| Registered prefix | String RVA | Handler RVA | Meaning |
|---|---:|---:|---|
| `reboot-fastboot` | `0xc79cb` | `0x591bc` | request userspace fastbootd handoff |
| `getvar:` | `0xc79db` | `0x5922c` | query a named published variable |

This is registration evidence, not a mere strings census. The exact command
table does not register `download:`, `boot`, `flash:`, `erase:`, `set_active`,
ordinary `reboot`, `reboot-bootloader`, `continue`, `flashing ...`, or any
`oem ...` prefix. Some generic handler code and log text remain linked in the
PE, but an unregistered handler is not reachable through the fastboot command
dispatcher.

The upstream Qualcomm ABL source shows why strings alone would be misleading:
its larger command list is compile-time guarded by options such as
`ENABLE_UPDATE_PARTITIONS_CMDS` and `ENABLE_BOOT_CMD`, then only the resulting
list is registered. It is a reference implementation, not evidence that the
Samsung build enabled those options. See
[Qualcomm FastbootCmds.c](https://git.codelinaro.org/clo/le/abl/tianocore/edk2/-/blob/LU.UM.3.5.1.r1-00700-QCS6490.0/QcomModulePkg/Library/FastbootLib/FastbootCmds.c).

### Published `getvar` surface

The prior live census proved only these four queries on this exact endpoint:

- `product=kona`;
- `is-userspace=no`;
- `version-bootloader` returned successful empty data; and
- `max-download-size=805306368` (`0x30000000`, 768 MiB).

The exact PE additionally contains the publish and lookup surface for
`kernel`, `snapshot-update-status`, `serialno`, `secure`, `variant`,
`logical-block-size`, `erase-block-size`, `version-baseband`,
`battery-voltage`, `battery-soc-ok`, `charger-screen-enabled`,
`off-mode-charge`, `unlocked`, `hw-revision`, `parallel-download-flash`,
`slot-count`, `current-slot`, `slot-successful:*`, `slot-unbootable:*`,
`slot-retry-count:*`, `has-slot:boot`, `has-slot:system`, `has-slot:modem`,
`partition-size:*`, and `partition-type:*`. Runtime and partition conditions
can determine whether an individual value is published. The generic handler
also contains its `all` branch, but `getvar all` was not invoked live. Raw
serial output remains private.

### Why the transient boot stopped

The host-side `fastboot boot` operation first sends `download:<size>`, waits
for a `DATA<size>` response, transfers the image, and only then sends `boot`.
That sequence is defined by the
[AOSP fastboot protocol](https://android.googlesource.com/platform/system/core/+/master/fastboot/README.md).
The observed `Sending 'boot.img' ... FAILED (remote: 'unknown command')`
therefore stopped at the unregistered `download:` command. No accepted data
phase or subsequent `boot` command was observed. This exact static result
explains the live failure without inferring anything from the image's size or
contents.

## Recovery fastbootd structure

The same exact stock package's 82,694,144-byte recovery image has SHA-256
`dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e`.
Its ramdisk contains:

- `/system/bin/fastbootd`, 303,160 bytes, SHA-256
  `a47c7b7911912b84490510cae9f08458bfaffb7815925ea4a8f9894f3e24a89c`;
- the fastboot HAL libraries and fastbootd resources;
- an init service that starts fastbootd when `sys.usb.config=fastboot`; and
- recovery routing for `boot-fastboot` and `--fastboot`.

The retained TWRP T2 recovery image is also 82,694,144 bytes, with SHA-256
`d46a1f72743a28acc4c820184d7318df9801ee43d425c22d092778e4b63d1f89`.
Its ramdisk still contains `/system/bin/fastbootd`, 1,244,528 bytes, SHA-256
`38331e9550ac5c3f274a5075426454e665b37c67d27bd482e1abff4d0f11c392`,
the generic system-init fastboot service, `--fastboot`, `ro.twrp.fastbootd`,
and the donor UI page. That is not the retained T2 runtime route, however.
The exact T2 builder replaces root `init.recovery.usb.rc` with `SAFE_USB_RC`,
which creates only `ffs.adb`, contains no fastboot FunctionFS mount or
`start fastbootd`, and redirects `sys.usb.config=fastboot` back to `adb`.
`validate_safe_usb_rc()` explicitly rejects a fastboot function, mount, or
service start. The earlier conclusion that retained T2 itself exposes a
structural fastbootd handoff was therefore too broad.

The exact classic `reboot-fastboot` handler and stock-recovery route establish
a structural handoff for exact stock recovery. They do not establish a usable
fastbootd entry through the currently retained, deliberately ADB-only T2
recovery. A T2 fastbootd census cannot honestly be classified as read-only
entry: it first needs either a separately reviewed volatile recovery-control
profile or a new recovery image. Neither is authorized by this report.

For reference, Android 12.1 fastbootd registers `set_active`, `download`,
`getvar`, shutdown/reboot variants, `erase`, `flash`, logical-partition
create/delete/resize, `update-super`, `oem`, `gsi`, `snapshot-update`, and
`fetch`; see the
[AOSP fastbootd command map](https://android.googlesource.com/platform/system/core/+/refs/tags/android-12.1.0_r27/fastboot/device/fastboot_device.cpp).
The exact TWRP binary contains corresponding handler and command evidence,
including `fetch`, but runtime support remains unproved until a bounded live
census. Notably that fastbootd map has no RAM `boot` handler, so the structural
fastbootd path is not itself a replacement for the failed PID1 transient-boot
path. AOSP describes the bootloader/fastbootd split in
[Move fastboot to userspace](https://source.android.com/docs/core/architecture/bootloader/fastbootd).

## Evidence state and bounded next question

- **Proved statically:** the exact stock classic-fastboot dispatcher registers
  only `getvar:` and `reboot-fastboot`; `download:` and `boot` are absent.
- **Observed live:** the four-query classic census, rejection at the
  `download:` phase, physical `START` return, and healthy Android terminal.
- **Structurally present:** stock-recovery fastbootd route and the retained T2
  fastbootd binary/generic system-service bytes.
- **Proved statically absent from the retained T2 entry profile:** a stable
  fastboot FunctionFS route; T2's exact root USB policy redirects fastboot to
  ADB.
- **Unproved:** any separately enabled current-device fastbootd endpoint, its
  USB identity, its runtime command/variable surface, and every write-capable
  result.

There is no honest live read-only census to run against retained T2 as-is.
If fastbootd mapping remains useful, the smallest successor is one separately
reviewed attended profile that first enables only the volatile T2 FunctionFS
and service path, then proves `is-userspace=yes`, collects a bounded private
`getvar` inventory, and returns to healthy Android. It must invoke no
`download`, `flash`, `erase`, `set_active`, logical-partition, OEM, or other
fastboot mutation command and must treat the volatile enable itself as a D1
control effect rather than a read. A recovery-image T3 is unnecessary for
that question. This report defines neither successor nor live authority.
