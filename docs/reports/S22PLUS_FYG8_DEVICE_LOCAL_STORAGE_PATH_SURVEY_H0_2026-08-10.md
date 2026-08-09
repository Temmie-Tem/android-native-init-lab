# S22+ FYG8 Device-Local Storage Path Survey H0

Date: 2026-08-10 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` / `S906NKSS7FYG8`)

Verdict: `SURVEY_COMPLETE_DEVICE_LOCAL_STORAGE_PATHS_HOST_ONLY`

## Scope and Authority

Host-only survey of the staged stock FYG8 vendor image. No device was
contacted, no partition was written, no candidate exists, and no F1 is armed.
This report records facts and options only; it grants no device authority and
changes no binding layer. The frozen P3.13 design is untouched by this
document.

The question surveyed: which device-local read/write storage can a custom
native PID 1 use **while stock Android remains installed and required**. This
matters because the A90 method assumed an external microSD slot for coexisting
scratch space, and the S22+ has no microSD slot.

## Provenance

Source: staged stock firmware, host-side only.

- `workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/vendor_boot.img`
  SHA256 `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7`
- `.../unpack-vendor-boot/vendor_ramdisk00`
  SHA256 `41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193`
  (21,813,545 B, LZ4 **legacy** frame, magic `0x184C2102`)
- Decompressed ramdisk: 63,974,144 B, ASCII cpio (SVR4, no CRC)
- Extracted member: `first_stage_ramdisk/fstab.qcom`, 5,846 B,
  SHA256 `fb545c78efeeea3e0a6ef3a01d71bce3331f686dc08f8a9bbb3c4a436bdb80af`

The system has no `lz4` binary and no Python `lz4` module. A minimal
legacy-frame decoder was written in the session scratchpad for this read; it is
not committed and is not part of any build or qualification closure.

Following the A90 TWRP teardown precedent
(`docs/reports/TWRP_RECOVERY_TEARDOWN_DEVICE_REFERENCE_2026-06-13.md`), this
report commits a **metadata-only summary**: mount targets and mount options.
No firmware, ramdisk, binary, or extracted file is committed.

## Finding 1 — `/data` carries both encryption layers, hardware-wrapped

`first_stage_ramdisk/fstab.qcom:47`:

```text
/dev/block/bootdevice/by-name/userdata	/data	f2fs
  noatime,nosuid,nodev,discard,usrquota,grpquota,fsync_mode=nobarrier,
  reserve_root=32768,resgid=5678,inlinecrypt
  latemount,wait,check,,quota,reservedsize=128M,
  sysfs_path=/sys/devices/platform/soc/1d84000.ufshc,
  checkpoint=fs,
  fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0,
  metadata_encryption=aes-256-xts:wrappedkey_v0,
  fscompress,
  keydirectory=/metadata/vold/metadata_encryption
```

(line wrapped for readability; the on-device entry is a single line)

Consequences:

1. **Two independent layers.** FBE (`fileencryption=`) sits above a
   `dm-default-key` block layer (`metadata_encryption=`). Removing FBE alone
   leaves the block device itself ciphertext; the f2fs superblock is not
   visible.
2. **Both use `wrappedkey_v0`** — hardware-wrapped keys via Qualcomm ICE/TEE.
   The key never leaves the TEE. This is the same wall recorded for A90, where
   the conclusion was that reading `/data` requires KeyMaster/TEE cooperation
   and bumps the permanent "never touch keymaster" boundary.
3. The metadata key blob lives on the `metadata` partition
   (`keydirectory=/metadata/vold/metadata_encryption`).
4. Additional options hostile to a minimal init writing this filesystem:
   `fscompress` (f2fs compression), `checkpoint=fs`, `inlinecrypt`.

A rooted-Android-side helper cannot bridge this either: with FBE active, a
pre-placed plaintext file is not locatable from a custom init, because the
block layer beneath it is also encrypted.

## Finding 2 — the governing fstab lives inside `vendor_boot`

The fstab quoted above is a member of the `vendor_boot` vendor ramdisk, not a
file under `/vendor/etc/` in `super`.

`multidisabler` defeats force-encrypt by editing the fstab. On this device that
edit lands in **`vendor_boot`**, and possibly additionally in a second-stage
copy under `/vendor/etc/` inside **`super`**. Both are named in the permanent
forbidden list at `AGENTS.md:141`.

Therefore removing force-encrypt on this target is not a single rule
amendment. It breaks the "boot payload only" invariant that the entire S22+
campaign infrastructure is built on. It is still a **recoverable** class —
Odin plus stock firmware restores both partitions, unlike a partition-table
edit, whose recovery path cannot be demonstrated in advance and which
`docs/plans/S22PLUS_EARLY_RECON_AND_RESUME_PREP_2026-07-06.md:139` already
records as a precondition of the download-mode backstop rather than something
the backstop covers.

**Not established:** whether a second-stage `/vendor/etc/fstab.qcom` copy
exists in `super`, and which copy actually governs the `latemount` of `/data`.
Resolving this requires unpacking `super` and was not done; it is only needed
if the plaintext-`/data` path is actually selected.

## Finding 3 — mount-target inventory

Non-comment entries, first field and mount point only:

```text
system system_ext product vendor vendor_dlkm odm   (logical, f2fs/ext4/erofs)
metadata      /metadata                ext4
userdata      /data                    f2fs
cache         /cache                   ext4
persist       /mnt/vendor/persist      ext4
misc          /misc                    emmc
apnhlos       /vendor/firmware_mnt     vfat
modem         /vendor/firmware-modem   vfat
efs           /mnt/vendor/efs          ext4
sec_efs       /efs                     ext4
dsp           /vendor/dsp              ext4
carrier       /carrier                 ext4
abl tz hyp xbl vendor_boot             emmc
vm-bootsys    /vendor/vm-system        ext4
prism         /prism                   ext4
optics        /optics                  ext4
```

Plus two removable-media rules:

```text
:68  /devices/platform/soc/*.ssusb/*.dwc3/xhci-hcd.*.auto*  /storage/usbotg  vfat  nosuid,nodev  wait,voldmanaged=usbotg:auto
:69  /devices/platform/soc/8804000.sdhci/mmc_host*          auto             vfat  defaults      voldmanaged=sdcard:auto
```

Line 69 is an SD-card rule inherited from a shared fstab; the S22+ has no
physical microSD slot, so it is inert on this target. Line 68 is **USB-OTG mass
storage**, and it is live hardware on this target.

No unencrypted partition of useful size is available. `cache` and `metadata`
are unencrypted but small, and both fall under the `AGENTS.md:141` "or any
other partition" clause.

## Finding 4 — the rebuilt kernel already supports the OTG path

From
`workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/arch/arm64/configs/vendor/waipio-gki_defconfig`:

```text
:293  CONFIG_BLK_DEV_LOOP=y
:299  CONFIG_SCSI=y
:301  CONFIG_BLK_DEV_SD=y
:470  CONFIG_USB_OTG=y
:471  CONFIG_USB_XHCI_HCD=y
:477  CONFIG_USB_STORAGE=y
:479  CONFIG_USB_DWC3=y
:498  CONFIG_TYPEC=y
:499  CONFIG_TYPEC_TCPM=y
:500  CONFIG_TYPEC_TCPCI=y
:501  CONFIG_TYPEC_UCSI=y
:559  CONFIG_EXT4_FS=y
:564  CONFIG_F2FS_FS_COMPRESSION=y
:577  CONFIG_VFAT_FS=y
:1059 CONFIG_USB_DWC3_MSM=m
```

`CONFIG_F2FS_FS=y` (`:562`) and `CONFIG_DM_DEFAULT_KEY=y` (`:313`) are also
present. The complete `usb-storage -> SCSI -> sd -> vfat/ext4` chain is
built in; `dwc3-msm` is a **module** and must be loaded by the candidate.

## Finding 5 — runtime levers for role, speed, and orientation

`drivers/usb/dwc3/dwc3-msm-core.c` exposes three sysfs attributes relevant to
a host-mode attempt, alongside the `mode` node P3.13 already drives:

- `:4868` `DEVICE_ATTR_RW(mode)` — the role lever P3.13 writes
  `none`/`peripheral` to; it also accepts host.
- `:4923` `DEVICE_ATTR_RW(speed)` — accepts `full`, `high`, `super`, `ssp`;
  sets `override_usb_speed`. Writing `high` keeps the SuperSpeed path out of
  the attempt entirely, so a USB 3.x device negotiates down to high speed and
  no SS PHY, orientation, or redriver state participates.
- `:4817` `DEVICE_ATTR_RW(orientation)` — accepts `A`, `B`, or none, setting
  `orientation_override`. This removes any dependence on CC detection for
  lane selection if SuperSpeed is ever wanted.

An ordering constraint is stated in the driver at `:4907`:

```text
/* restart usb only works for device mode. Perform manual cable
 * plug in/out for host mode restart. */
```

Speed must therefore be selected **before** the role switch to host; changing
it afterwards requires a physical re-plug.

`dwc3_otg_start_host` (`:6438`) returns `0` silently when `mdwc->xhci_pm_ops`
is unset. Any host-mode design must treat a silent no-op as an expected
failure mode and witness it explicitly rather than inferring success from the
absence of an error.

## Finding 6 — VBUS sourcing is a separate subsystem; it works on this unit under stock Android only

`dwc3-msm-core.c` contains no VBUS regulator. Every `vbus_active` reference is
a *sense* flag; sourcing 5 V outward in host mode is done by the PMIC/Type-C
stack, which the peripheral path never required. A host-mode attempt therefore
adds a dependency the gadget path does not have, and without a baseline a
negative result could not distinguish "shared USB layer is dead" from "the
boost regulator was never enabled".

That baseline now exists. Operator report, 2026-08-10, on the exact S22+ unit
booted to stock rooted FYG8 Android: a dual-connector USB 3.0 stick was
detected as storage **both** plugged directly as USB-C and through a USB-A
OTG adapter. The same stick and adapter were first confirmed on a separate
non-target phone; that observation is recorded only as evidence about the
stick and adapter, not about this target.

This is ordinary owner use of the device under stock Android. It is **not** a
campaign device action, carries no Process-v2 journal entry, and grants no
authority. Its value is as an interpretation baseline: on this unit, host role
entry, PMIC VBUS sourcing, xhci, `usb-storage`, `sd`, and filesystem mount are
all demonstrably functional under the full Android stack.

The consequence for a later OTG unit is that failure becomes single-valued —
"native init does not do something Android does" — which is the same shape as
the existing P3.x question. An externally powered hub is no longer needed to
disambiguate a negative.

Care is still required in the other direction: a negative host-mode result
would be *suggestive* against the gadget-specific P3.13 hypothesis family but
not conclusive, because host mode has its own prerequisites — `dwc3-msm`
module load, `dwc3_host_init`, and `xhci_pm_ops` — that can fail
independently. Those must be witnessed before any such inference.

## Option comparison

| | plaintext `/data` | USB-OTG storage |
|---|---|---|
| partition write | `vendor_boot`, possibly `super` | none |
| encryption defeat | required, TEE-wrapped keys | not required |
| permanent-boundary contact | yes | no |
| pinned rollback identity | changes (Magisk repack) | unchanged |
| one-time cost | full `/data` wipe, re-root, new health baseline | none |
| standing cost | none | dongle attached; port occupied |
| host observation during candidate window | retained | lost |
| capacity | partition size | arbitrary |

Repartitioning was also considered and is **rejected**: it is the one class
where naming a new rollback point does not satisfy `AGENTS.md:146`, because the
recovery path cannot be demonstrated without taking the exact risk it insures
against, and SM8450 EDL recovery requires a Samsung-signed Firehose programmer
that is not available.

## The single-port constraint

The S22+ has one USB-C port and DWC3 holds one role at a time, so OTG storage
and the PC link cannot coexist. They can be sequenced, because the F1 evidence
channel is the DRAM retained carrier rather than USB:

```text
PC attached      -> Odin candidate flash
dongle attached  -> candidate boot, result written to retained carrier, park
PC attached      -> rollback flash, Android boot, carrier read
```

F1 is already attended, so the swap costs nothing procedurally. What it costs
is **host observation during the candidate window** — no CDC ACM observer, no
ModemManager guard, no host event record. That must be a declared design
choice, not a `NO_PROOF_OBSERVER` outcome.

The measured value of what is given up is low: all fourteen closed campaigns
saw host silence, and "zero host events for the complete candidate window" is
already PROVED at row 75 of `docs/operations/CAMPAIGN_LEDGER_S22PLUS.md`
(2026-08-04).

## Secondary value of an OTG attempt

Every closed campaign tested a hypothesis inside the peripheral/gadget path. A
host-mode attempt is the first test of a **different controller role**, and
both outcomes are informative:

- **Enumerates** — controller, PHY, clocks, VBUS supply, and the connector data
  path are functional under native init; the fault is confined to the gadget
  side.
- **Does not enumerate** — native init is failing to establish something the
  stock Android stack establishes, at or below the role split, subject to the
  host-specific prerequisites in Finding 6. This points toward shared setup
  and, if those prerequisites are witnessed as reached, toward the parked
  P3.02 external-measurement decision.

A host-mode success would also narrow P3.02's remaining question. It would not
prove the device-side USB2 pull-up, but data flowing through the connector
removes connector, trace, and joint faults from the candidate set without an
inline breakout.

Role selection does not need CC detection: the same `mode` sysfs node P3.13
writes `none`/`peripheral` to can be driven to `host` (Finding 5).

## Open questions

1. Whether USB **host** mode operates under native init. Unverified, and it is
   the only remaining question in this chain — Finding 6 establishes that the
   whole path works on this unit under stock Android, so the uncertainty is
   confined to what native init does or omits. Host-specific prerequisites
   (`dwc3-msm` module load, `dwc3_host_init`, `xhci_pm_ops`) must be witnessed
   separately so that a negative result is interpretable.
2. Whether a second-stage `/vendor/etc/fstab.qcom` exists in `super` and which
   copy governs the `/data` `latemount`.
3. Whether Android 15 / One UI on this target tolerates a plaintext `/data`
   after an fstab edit, and how many Odin round-trips that costs. External
   precedent for S22-generation `multidisabler` has not been surveyed.
4. What replaces "boot final rooted FYG8 Android and verify health" as the
   closing health condition once Android is eventually retired.

## Sequencing

1. P3.13 proceeds unchanged. Do not attach an OTG probe to it; it is a frozen
   bounded unit.
2. After the USB frontier closes, evaluate the OTG storage path as its own
   candidate unit. It is the only shared-storage option that contacts no
   permanent boundary, and its design cost is one declared observer-absence.
3. The cheapest input to that unit's design is a read-only capture of what the
   stock Android stack does while the OTG stick is attached — `mode`, `speed`,
   `orientation`, xhci appearance, and the power path — giving native init an
   explicit target state to reproduce. That capture is a connected read-only
   observation and requires the ordinary D0 authority; it is not authorized
   here.
4. Plaintext `/data` is the fallback if host mode does not work, with the
   `vendor_boot`/`super` write cost understood and decided explicitly.
5. Resolve open question 2 only when option 4 is actually selected.

## Non-conclusions

This survey does not authorize any device action, does not modify the P3.13
design or its qualification gates, does not change any binding contract, and
does not establish that USB host mode works under native init. The stock
Android observation in Finding 6 is an interpretation baseline only; it is not
Process-v2 evidence and does not transfer to the native-init boot. The permanent forbidden partition
and primitive lists in `AGENTS.md` remain absolute and are not amended by this
document.
