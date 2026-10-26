# S22+ FYG8 ABL device-tree handling: static H0 and live D0

Date: 2026-10-27. Target firmware: `SM-S906N / g0q / S906NKSS7FYG8`.
Status: **H0 COMPLETE; D0 COMPLETE — one bounded read-only session on the exact
target under direct operator approval; no write, mount, block read, transfer,
reboot or mode change**. A90 and S20+ device commands: zero.

This answers how the exact FYG8 bootloader (ABL `LinuxLoader`) chooses, overlays
and rewrites the device tree before the kernel starts, for both the normal boot
partition and the recovery partition. It prepares a later mainline or
recovery-carrier decision; it does not establish that either works, and it
changes nothing about the current Debian path. The static model was then
checked against the live effective tree; see [Live D0 result](#live-d0-result).

## Inputs

| Input | SHA-256 |
| --- | --- |
| `LinuxLoader.efi` from FYG8 `abl.elf` (BL archive `e5aeb59d…`) | `b1ee37a2be13a557fa05a6e603fa81c827b3d8be410df1a61145f050c67cde28` |
| Stock `boot.img` (header v4) | `4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae` |
| Stock `vendor_boot.img` (v4) | `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7` |
| Stock `recovery.img` (header v2) | `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4` |
| Stock `dtbo.img` | `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c` |
| vendor_boot DTB section (4 SoC DTBs) | `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e` |

`LinuxLoader.efi` and its provenance are the same as in the
[July reboot-reason RE](S22PLUS_FYG8_BOOTLOADER_REBOOT_REASON_AND_RETAINED_MEMORY_STATIC_RE_2026-07-11.md).
Addresses below are RVAs in that PE. Disassembly used Capstone through
[`s22plus_abl_dt_index.py`](../../workspace/public/src/scripts/analysis/s22plus_abl_dt_index.py)
(string xrefs, function starts, call graph; 2,361 functions, 3,063 referenced
strings) and
[`s22plus_abl_dt_func.py`](../../workspace/public/src/scripts/analysis/s22plus_abl_dt_func.py)
(annotated per-function listing). Private outputs are under
`workspace/private/outputs/s22plus-abl-dt-h0-20261027-1/`.

Function roles are named from their log strings and control flow, cross-read
against Qualcomm's public ABL structure. Samsung additions are identified only
from this binary.

## Findings at a glance

1. **The DT pipeline is one function, `0x18078`**, in this order: SoC DTB
   selection → board DTBO (only if the SoC DTB was not an exact match) →
   hypervisor-supplied overlays → `user_dtbo` override overlay → Samsung EDtbo
   (signature- and version-gated) → one combined overlay apply → final version
   record. An overlay-apply failure returns an error status from the pipeline.
2. **Recovery images carry their own DT inputs.** Stock FYG8 `recovery.img` is
   header v2 and embeds a DTB section byte-identical to `vendor_boot`'s and a
   `recovery_dtbo` byte-identical to the stock DTBO table. For a v1/v2 recovery
   boot, ABL reads the overlay table from the image, not from the `dtbo`
   partition, and does not add `vendor_boot`.
3. **An exact SoC+board match skips the Samsung board overlay.** If the selected
   DTB matches both `qcom,msm-id` and `qcom,board-id` exactly, ABL clears its
   "DTBO needed" flag and never loads a board DTBO. An empty overlay list
   applies successfully.
4. **EDtbo comes from the `spu` partition**, not from a dedicated partition. It
   must pass Samsung's system-update signature check and must declare a higher
   `dtbo-version` than the board DTBO to be applied. Whether this device's
   `spu` holds one is unknown offline.
5. **`user_dtbo` is always attempted but absent.** The gate before it always
   returns false in this build, so ABL always tries to load a `user_dtbo`
   partition. The FYG8 PIT has no such partition.
6. **ABL rewrites the tree after overlay**: memory, `/chosen`, Samsung uH
   hypervisor reservations, DDR regions, boot-device node status, partial-goods
   disables and display regions. A mainline tree receives these too.
7. **Hardware-key recovery entry on this KOR build requires a USB data cable**
   unless the sales code is `XAR`. The device's recorded sales code is `SKC`.

## Image layouts

| Image | Header | DTB source | Overlay table | Kernel cmdline |
| --- | --- | --- | --- | --- |
| `boot` + `vendor_boot` | v4 + vendor v4 | `vendor_boot` DTB section (4 DTBs) | `dtbo` partition | boot cmdline + vendor cmdline; parameters in a 164-byte bootconfig section |
| `recovery` | v2 | own DTB section, identical to `vendor_boot`'s | own `recovery_dtbo`, 7,777,237 bytes, identical to the stock DTBO table | single cmdline with the vendor cmdline and the bootconfig parameters flattened inline |

The `dtbo` partition image is the 7,777,237-byte table followed by a Samsung
signer block (`SignerVer02`, build/model strings) and an AVB footer. There is no
second DT table in it.

The recovery kernel is byte-identical to the stock boot kernel (already recorded
in [P319](S22PLUS_FYG8_P319_USB_EXTERNAL_CORPUS_AND_RECOVERY_CONTROL_H0_2026-08-23.md)).
A recovery image is therefore a self-contained kernel + ramdisk + DTB + DTBO
carrier. This also confirms that the current Debian `N` image (v4, depends on
`vendor_boot`) is not a drop-in recovery image.

## Selection keys

| Blob | `model` | `qcom,msm-id` | `qcom,board-id` |
| --- | --- | --- | --- |
| SoC DTB 0 | Waipio v2 SoC | `<0x1c9 0x20000>` | `<0 0>` |
| SoC DTB 1 | Waipio SoC | `<0x1c9 0x10000>` | `<0 0>` |
| SoC DTB 2 | WaipioP v2 SoC | `<0x1e2 0x20000>` | `<0 0>` |
| SoC DTB 3 | WaipioP SoC | `<0x1e2 0x10000>` | `<0 0>` |
| DTBO entries 0–10 | `Samsung G0Q PROJECT (board-id,NN)` | `<0x1c9 0x10000 0x1e2 0x10000>` | `<0x10008 rev>`, rev = 1, 2, 4–12 |

All entries carry `dtbo-version = <0>`. Earlier work treats G0Q revision 12
(entry 10) as this device; the live `androidboot.dtbo_idx` would confirm it.

The SoC match (`0x1d480`, `0x1eb20`, `0x21ac0`, `0x21fe0`, `0x22678`) compares
SoC id, SoC revision, foundry, variant, subtype, board major/minor and PMIC
model/revision, logging `Best match DTB tags …`. If nothing matches it fails with
`ERROR: Couldn't find the suitable DTB!`.

## The pipeline (`0x18078`)

| Step | Call | Behaviour |
| --- | --- | --- |
| Get overlay table | `0x37168` | `recovery_dtbo` from the image (`0x37808`) when the image is a v1/v2 recovery boot and the multi-slot test permits it. Otherwise the `dtbo` partition image. |
| SoC DTB | `0x1cbe0`, `0x1e700` | Single appended DTB for legacy images, otherwise best match from the DTB section. On an exact match `0x1e700` clears the byte at `0x12d100` and logs `Exact DTB match found. DTBO search is not required`. |
| Board DTBO | `0x1cb90` → `0x1fff0` | Runs only when `0x12d100` is 1. Otherwise control jumps to the hypervisor step at `0x188b0`. |
| Hypervisor overlays | `0x3b798`, `0x3bf10` | Overlays handed over by the hypervisor (`HYP MAGIC`, `HypInfo`), each added to the list. The stock DTB contains Gunyah nodes (`qcom,qrtr-gunyah`, `qcom,gunyah-vsock`). |
| Override DTB | `0x1b528` → `0x1f8d8` | `0x1b528` always returns 0, so `GetOvrdDtb` always runs and tries the `user_dtbo` partition. A missing partition only skips this step. |
| EDtbo | `0x4d948` → `0x1f548` → `0x1ba90` | `0x4d948` reads the `edtbo` item from the `spu` partition and verifies its signature (`SYSTEMUPDATE: Signature …[edtbo]`). `0x1ba90` applies it only if its root `dtbo-version` is greater than the board DTBO's. On failure ABL logs `EDTBO check fail` and continues. |
| Apply | `0x1be38` | One `ufdt_apply_multi_overlay` over the list. An empty list logs `Overlay DT is NULL` at verbose level and returns success. A failed apply logs `Error: Dtb overlay failed` and returns that status. |
| Version | `0x1c280` | Records `Final Dtb version`. The kernel cmdline later receives `androidboot.edtbo_ver` and `androidboot.edtbo_offset` (`0x42ca8`). |

## Runtime rewrites after overlay (`0x24aa0` and callees)

| Area | What ABL writes |
| --- | --- |
| `/memory` | `reg` from the RAM partition table, `ddr_device_type`, DDR rank / HBB properties (`0x24aa0`, `0x27e00`, `0x260f8`) |
| `/chosen` | `bootargs`, `rng-seed`, `kaslr-seed`, `linux,initrd-start`, `linux,initrd-end` |
| `/reserved-memory` | Samsung uH hypervisor `uh_heap_region` and `uh_guest_region` via a uH call (`0x232f0` → `0x22ba0`, `0x22e30`, `no-map`), a KASLR region, and `splash_region` / `demura_region_*` updates (`0x26340`, `0x269a8`) |
| New nodes | `/ddr-regions` (`0x28fb8`), `/mem-offline` granule (`0x28150`) |
| Status edits | boot-device node selection (`%x.ufshc` / `%x.sdhci`, `0x26f90`), partial-goods disables for CPU clusters and multimedia (`0x39da8`) |
| Display | `/soc/dsi_pll_codes`, `qcom,demura-panel-id`, DSI primary/secondary (`0x3e168`, `0x269a8`) |
| Samsung | `sec_ap_param` (`0x24340`) |

None of `uh_*`, `/ddr-regions` or the seeds exist in the stock DTB; they are
runtime-only. A replacement tree must tolerate these writes. In particular it
must not use the memory that ABL reserves for uH.

## Recovery entry

- Recovery boots through the shared loader `0x59f0`. A recovery partition
  without a kernel would fall back to `Booting into Recovery Mode via Boot`. The
  stock recovery has its own kernel. For header versions below 3 the loader logs
  `Boot header %d, not add vendor_boot`.
- The key-entry path in `0x4b8d8` compares the build country `KOR` with
  `USA`/`CAN`/`JPN`. On no match it reads `Is_Data_Cable`. Only cable types 1–2
  continue. Otherwise, unless a 3-byte local value equals `XAR`, it logs
  `Block Recovery, Usb Not Connect!` and blocks. The local value is most likely
  the sales code read earlier in the same function; that link is inferred, not
  traced. This device records
  `ro.boot.sales_code=SKC`
  ([vbmeta fix](S22PLUS_STOCK_VBMETA_BOOT_RECOVERY_LOOP_FIX_2026-07-06.md)).
  Unattended key-combo recovery entry is therefore not available. The
  software reset-reason path (PON `0x01` → mode 2, July RE) is a separate branch
  and was not re-analysed here.
- A non-stock recovery has booted on this exact device. TWRP 3.7.0 (v2, own
  5.10.81 kernel) ran on 2026-07-06/07 with disabled vbmeta. That run also
  showed a persistent return-to-recovery loop until stock vbmeta was restored.
  Stock recovery was later observed without any recorded restore (P319 evidence
  gap). Recovery persistence across Android boots remains unresolved.

## Implications

**Current Debian path:** none. The `N` image keeps the stock kernel envelope,
`vendor_boot` and DTBO path, as the
[display compatibility review](S22PLUS_FYG8_NATIVE_DISPLAY_BOOTLOADER_COMPATIBILITY_H0_2026-09-06.md)
required.

**Mainline (pre-hardware feasibility only):**

- The upstream `sm8450-samsung-r0q.dts` has no `qcom,msm-id` or `qcom,board-id`.
  As shipped it would fail SoC selection. A carrier would have to add
  `qcom,msm-id` (live: SoC 0x1c9, revision 2.2, matched by DTB 0's
  `<0x1c9 0x20000>`) and a `qcom,board-id` to its tree.
- With an exact match, the Samsung board overlay is skipped (step 3). The
  Tab S8+ report of ABL "merging overlay fragments" corresponds to the
  non-exact path. On this device the stock selection is a best match: entry 10
  (rev 12) for a revision-16 board. Which `board-id` value produces an exact
  match for these platform values has not been derived yet. If an exact match
  is not achieved, a v2 recovery carrier can instead supply its own
  `recovery_dtbo`.
- Two inputs remain outside the carrier's control: the hypervisor overlay and
  the runtime rewrites above. **The live tree shows hypervisor-attributed
  changes on this device.** These are a new `/hypervisor` node and edits to
  `/firmware/qcom_scm`, `/soc/timer` and `/soc/qcom,qup_uart@99c000`. Those
  paths differ from mainline naming. If the hypervisor overlay targets them by
  path or label, a mainline tree without matching targets fails the apply step.
  Capturing that overlay blob is the next mainline-relevant item.
- A uniLoader-style shim avoids all DT handling, because ABL only sees the stock
  tree. The cost is a second loader. The exact-match route is a cheaper first
  hypothesis, not a demonstrated one.

**Recovery as a Debian carrier:** structurally possible (own DTB/DTBO, header
v2, custom recovery previously booted). It is not unattended by key entry on
this build. BCB/persistence behaviour and AVB acceptance of the specific image
remain open, consistent with the
[Astra second opinion](#provenance-of-this-unit) recorded in the session.

## Live D0 result

Scope: one read-only session on 2026-10-27 06:11–06:15 KST, under the
operator's direct approval of device reads. Only the exact S22+ was attached. It
was in healthy rooted Android with `sys.boot_completed=1` and `orange` verified
boot. The same boot ID was observed at start and end. No task owner or approved
terminal task was active. Reads used `getprop`, `cat` of procfs/sysfs, `dmesg`,
`ls`, and `grep` of the vendor fstab. Magisk `su` was used for reads only. Raw
outputs and a receipt with file hashes are private under
`workspace/private/outputs/s22plus-abl-dt-d0-20261027-1/`. Serial-bearing
bootconfig/cmdline fields are not reproduced here.

**Selection, as reported by ABL in bootconfig and the kernel:**

| Key | Value | Meaning |
| --- | --- | --- |
| `androidboot.dtb_idx` | 0 | SoC DTB 0, Waipio v2 (`msm-id <0x1c9 0x20000>`) |
| `/sys/devices/soc0` | soc_id 457 (`0x1c9`), revision 2.2, foundry 7 | consistent with DTB 0 |
| `androidboot.dtbo_idx` | 10 | DTBO entry 10, `board-id <0x10008 0x0c>` |
| `androidboot.revision` | 16 | The board is revision 16 and the table stops at 12, so this is a best match, not an exact one |
| `androidboot.edtbo_ver` / `sec_sysup.edtbo_ver` | 0 | No EDtbo overlay applied: version 0 is not greater than the board DTBO's 0 |
| `androidboot.edtbo_offset` | 9438216 | ABL reports a location. Its contents were not read. |

`spu` is a 50 MiB partition. Its fstab entry is commented out and it is not
mounted, so an `edtbo` item was not listed. Doing so would need a mount or a raw
block read; neither was performed.

**Live tree vs host merge.** `/sys/firmware/fdt` (980,251 bytes) was compared
with a fresh `fdtoverlay` merge of SoC DTB 0 + DTBO entry 10. That merge is
byte-identical to the September thermal-census merge. The comparison used the
node/property tool
[`s22plus_fdt_semantic_diff.py`](../../workspace/public/src/scripts/analysis/s22plus_fdt_semantic_diff.py).
The result: 4,934 → 4,942 nodes, none removed.

- **Tool differences only** (`libufdt` in ABL vs host `fdtoverlay`):
  - Overlay labels are not merged into the live `__symbols__`.
  - Overlay-added nodes have different phandle numbers. All 12 changed phandle
    references resolve to the same target paths.
  - The root `model`, `compatible`, `qcom,msm-id` and `qcom,board-id` come from
    the overlay's root node in the live tree (`Samsung G0Q PROJECT (board-id,12)`).
- **Added at boot, absent from both inputs:**
  - `/hypervisor`: Gunyah `qcom,gunyah-hypervisor-1.0`, VM node `qcom,vmid = 3`,
    `qcom,gh-watchdog`, resource-manager RPC node.
  - `/reserved-memory/uh_heap_region`, `uh_guest_region`, `kaslr_region`.
  - `/soc/sec_ap_param`.
  - `/chosen` `kaslr-seed` and initrd range; `/ddr-regions` `region0/1`;
    `/memory` `ddr_device_type`.
- **Changed at boot:**
  - `/memory` `reg` becomes five ranges; `/chosen` `bootargs`.
  - `/firmware/qcom_scm` becomes `qcom,scm-v1.1` with `interrupts` and
    `qcom,max-queues = 2`.
  - `/soc/timer` gains `always-on`.
  - `/soc/kryo-erp` and `/soc/qcom,qup_uart@99c000` become `disabled`.

The `/hypervisor` node is not produced by any `LinuxLoader` string path seen in
the static pass. Together with the `scm`/timer/UART changes, it is consistent
with the hypervisor-overlay step (`HypInfo`) having supplied at least one
overlay on this device. That attribution is inferred; the hypervisor overlay
blob itself was not captured. The live kernel has Gunyah drivers loaded
(`gh_rm_drv`, `hvc_gunyah`, `gh_virtio_backend_trustedvm`, `qrtr_gunyah`) and no
`/dev/kvm`, although the cmdline carries `kvm-arm.mode=protected`.

No ABL log is exposed under `/proc` (`boot_stat`, `enhanced_boot_stat`,
`reset_klog` and `uh_log` contain no DT lines). The pipeline's own messages
therefore remain unobserved.

The Debian `N` boot uses the same `vendor_boot` DTB, DTBO partition and ABL path.
Only the ramdisk and cmdline differ. A separate `N`-side FDT read would need an
F1 transfer and was not performed.

## Exact-match condition

A follow-up static pass and a second read-only session settle most of this.
The second session ran 06:28–06:40 KST, after P463 closed
`ANDROID_CLOSED_HEALTHY` and released its F1 owner; it had a fresh boot ID and
the same boot at the end. Evidence is under
`workspace/private/outputs/s22plus-abl-dt-d0-20261027-2/`.

**Predicate.** `0x1f4e8` returns exact iff every bit of `0x0035555555550000` is
set in the candidate's `DtMatchVal`. The setters are:

| Bit(s) | Set by | Condition |
| --- | --- | --- |
| 53 | `0x21ac0` | SoC id matches (`msm-id` cell 0 [15:0]) |
| 52 | `0x21fe0` | board variant = platform type (`board-id` cell 0 [7:0]) |
| 50 (49 = default) | `0x21fe0` | `board-id` cell 0 [31:24] equals `GetBoardRev()` (49 if the DT value is 0) |
| 16 (15 = default) | `0x21ac0` | foundry exact (`msm-id` cell 0 [23:16]) |
| 2i+18 for i = 0–14 (2i+17 = DT model 0) | `0x22678` | `qcom,pmic-id` slot i model equals the board's PMIC i model |

SoC revision (bits 13/14), board major/minor (9–12) and DDR size (51) are not
in the mask.

**Board values.**
- `soc_id` 457, foundry 7, `hw_platform` MTP (type 8).
- `platform_version` 0x10000, Qualcomm `platform_subtype_id` 0.
- PMIC slot 0 model 0x2F (PMK8350), die revision 2.0.
- SPMI bus 0 has PMICs at SIDs 0, 1, 2, 4, 5 and 7.
- `GetBoardRev()` (`0x40768`) reads 32 bytes of SMEM item 0x87
  (`SMEM_ID_VENDOR1`) and returns byte 0x10. In Samsung's
  `sec_smem_id_vendor1_v7_t` that is `share.hw_rev[0]` (main), after a 16-byte
  magic/version header. It is not the Qualcomm platform subtype. The
  kernel-visible `androidboot.revision=16` is the same main revision; that
  equality is inferred, not separately read.

**Consequences.**
- No stock SoC DTB can ever be an exact match. Each has `board-id <0 0>`
  (subtype 0 against revision 16), foundry 0 and no `qcom,pmic-id`. The stock
  path therefore always applies a board DTBO.
- An exact-match tree needs `qcom,msm-id` cell 0 = `0x000701c9` and `qcom,board-id`
  cell 0 = `0x10000008` (subtype 16, type 8; major/minor free). It also needs a
  `qcom,pmic-id` whose 15 slot models equal the board's array, including empty
  slots.
- Only slot 0 of that array is visible from Android sysfs. Kernel logs no longer
  hold the PMIC probe lines, and debugfs is not mounted. Mounting it would
  change kernel state and was not done. **The PMIC array is the one input not
  derivable read-only.**
- The exact match is not needed for the recovery-carrier route. A non-exact v2
  recovery boot takes its DTBO from the image's own `recovery_dtbo`, so a
  carrier can supply a matching entry whose overlay is a no-op. The boot
  partition route cannot use a custom DTB anyway, because its DTB comes from
  `vendor_boot`. The hypervisor overlay remains the real constraint.

## Confidence

| Claim | Basis | Confidence |
| --- | --- | --- |
| Image layouts, byte identities, selection keys | direct parse of the retained images | high |
| Pipeline order, exact-match skip, empty-list success | annotated disassembly of the named functions | high |
| `recovery_dtbo` use for v1/v2 recovery | branch at `0x371c4`–`0x371f4`; the multi-slot flag name is inferred from public ABL structure | medium-high |
| EDtbo from `spu`, signature and version gates | strings and calls in `0x4d948`, `0x1ba90` | high for the mechanism; live `edtbo_ver=0` shows none applied |
| Key-entry USB block for KOR/non-XAR | branch at `0x4bbec`–`0x4bcc4` | high for the branch; the cable-type encoding is inferred |
| Selected SoC DTB 0 and DTBO entry 10 on this device | live bootconfig and soc0 | high |
| Runtime additions/changes listed under the live result | live FDT vs host merge, phandle-resolved | high for what changed; medium for hypervisor attribution |
| KVM unusable on this kernel | Gunyah drivers loaded, no `/dev/kvm` | high for this boot |

## Provenance of this unit

This unit was selected after an operator discussion of mainline feasibility and
an independent read-only second opinion (Codex GPT-6 Astra, xhigh). That opinion
flagged that recovery uses header v2 with an embedded DTB, and that ABL DT
processing is the main mainline risk. Both points are confirmed and extended
above. No device action was taken.
