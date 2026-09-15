# S22+ native UFS V1

Status: **REVIEW_GATED_F1_PROFILE**. This fixed FYG8 driver-initialization
profile is prospective until the current independent V3 capability review
covers its source closure and an actual finite task grant is returned. It is
limited to `SM-S906N/g0q/S906NKSS7FYG8` and boot-only V3 images.

## Purpose and implementation

The current native baseline does not initialize Qualcomm UFS. A future native
data partition and a userdata-independent restoration environment need storage
access. This profile qualifies that prerequisite without changing GPT or
formatting a filesystem. Storage access alone does not prove GPT restoration.

The existing E3 module plan, kernel executable code, ramdisk inventory,
authenticated console, thermal service and original-A recovery remain the
baseline. The new supervised renderer calls one fixed loader after the
existing display-provider initialization and before its existing privilege
drop. The loader opens the existing root/lib/modules directories without
following symlinks. Each fixed file must be regular, root-owned, mode 0644,
one link and its declared size. The sealed vendor-ramdisk digest and H0 module
digests bind the exact bytes; files are neither copied nor changed on-device.

The declaration in `s22plus_native_ufs_source_v1.py` supplies this order:

1. `phy-qcom-ufs.ko`
2. `phy-qcom-ufs-qmp-v4-waipio.ko`
3. `tmecom-intf.ko`
4. `hwkm.ko`
5. `crypto-qti-hwkm.ko`
6. `crypto-qti-common.ko`
7. `ufshcd-crypto-qti.ko`
8. `ufs_qcom.ko`

The loader invokes `finit_module` once per file with empty parameters and zero
flags. It emits bounded index-only start/completion lines. Any open, metadata,
insertion or close failure ends that process; it never retries or unloads a
module. Existing parent supervision and V3 failure/recovery rules remain.
Successful insertion does not claim that a LU is ready or readable.

## Actual hardware scope

This is F1 hardware initialization, not D0. The exact stock UFS driver/core
perform controller/PHY/ICE register setup, UFS device initialization, supported
device-attribute/feature configuration and ordinary SCSI LU discovery. Kernel
partition discovery may inspect partition metadata on the enumerated LUs;
it is not restricted to the later explicit LU0 census range. Initialization
can configure reference clocks, active-current limits, exception/BKOPS behavior
and supported Samsung stream-ID/WriteBooster flush flags. Enabled HPB can reset
its state, inactivate buffer regions through `WRITE_BUFFER` and read mapping
buffers. These are buffer-management operations, not partition-data
`WRITE(10/16)` commands. These are ordinary driver actions,
not a claim of zero device-state changes or zero internal storage activity.

The added loader has no block-write, discard, format, filesystem-mount, key,
RPMB data-transaction, firmware-download or partition-table-update operation.
It sends no caller-supplied SCSI command. Loading crypto dependencies registers
their callbacks; the profile does not issue encrypted I/O or request key
programming, unwrap, export or raw-secret derivation. Existing prohibitions on
partition payloads outside boot, fuse writes and unreviewed recovery remain.

Discovery registers UFS-device, BOOT and RPMB well-known LUs as well as scanning
ordinary LUs; this does not authorize authenticated RPMB data access. Normal
reboot subsequently traverses storage shutdown, cache synchronization and
power/reset handling. Stock driver retries, controller resets and conditional
fault/panic paths remain possible. Renderer supervision cannot contain a
kernel, IRQ or SCM stall. `finit_module` may itself wait for asynchronous
discovery. Such uncertainty uses the existing attended original-A recovery
path where reachable, or stops for physical intervention; it never permits
another candidate transfer or a claim of automatic stall recovery.

## Qualification and execution

H0 checks the fixed vendor files and dependency order, actual module import
CRCs against the unchanged kernel and preceding providers, the generated
loader's actual ARM64 file/flag/error behavior, and the actual A/B boot images.
The new image profile is `thermal-v3-reconnect-ufs-v1`. Its dedicated H0
exporter leaves the historical exporter bytes and old artifact provenance
unchanged. The live owner accepts only its separately reviewed source closure.

A finite task may include attended bootstrap and one following storage census.
Preparation may begin with no admission/tail when bootstrap is selected;
the census operation cannot prepare or execute until that task has actually
published and rederived N admission and a healthy unused native tail. The
grant does not renew its clock or capacity after bootstrap.

The subsequent fixed native census retains its existing first-six/last-five
LU0 capture and alias rules. Its actual block read and authenticated health
are reported separately from strict GPT qualification. Known original duplicate
GUIDs or missing backup-table bytes remain `NO_PROOF`; they are not repaired
or relabelled to qualify a storage read. No arbitrary console command is added.

This profile adds no GPT writer, formatting lane or recovery guarantee for a
modified GPT. A later mutation needs an exact reviewed method, preservation of
all non-userdata entries, demonstrated execution reachability for its declared
failure cases and its own applicable authority. Intentional GPT corruption is
not authorized as a shortcut to that evidence.
