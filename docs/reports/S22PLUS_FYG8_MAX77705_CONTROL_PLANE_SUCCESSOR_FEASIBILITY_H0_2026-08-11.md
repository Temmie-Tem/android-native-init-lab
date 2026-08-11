# S22+ FYG8 Max77705 Control-Plane Successor Feasibility H0

Date: 2026-08-11 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`)

Verdict:
`BASE_CARRIER_RECOVERABLE_STOCK_67_UNADJUDICATED_CUSTOM_SUCCESSOR_CONDITIONALLY_FEASIBLE`

Review state:
`PRIMARY_SOURCE_AUDIT_CORRECTED_GATES_OPEN_INDEPENDENT_REVIEW_REQUIRED`

Repository analysis base:
`97be0e488b62cec8228e50ab7997e1e52cd5ba96`

## Scope and authority

This is host-only source, artifact, and retained-evidence analysis. No device
was contacted, no module was inserted, no sysfs control was written, no
candidate or rollback artifact was created, and no D0, D1, or F1 action was
performed. P3.15 remains consumed and non-replayable. A90 identity, files,
devices, authority, and evidence are outside this unit and were not touched.

This report follows the closed discussion in
`S22PLUS_FYG8_MAX77705_USB2_MUX_HYPOTHESIS_AND_FALSIFICATION_H0_2026-08-11.md`.
It does not promote the MUX hypothesis to fact. It resolves or narrows that
report's open MFD, bootloader-evidence, module-artifact, and observer-design
questions and introduces a distinct hazard class:

```text
MAX77705_CONTROL_PLANE_BRINGUP
```

The hazard is broader than one D+/D- MUX write. Loading the required MFD and
PDIC modules initializes a combined PMIC/MUIC/CC/PD interrupt and command
plane. The exact write and observation contract therefore requires an
independent review before any successor can be packaged.

Nothing in this report grants live authority. The provisional module count is
dependency arithmetic only, not a qualified plan.

## Executive result

The source-level MUX mechanism is real and remains compatible with the P3.15
signature:

- Max77705 `CONTROL1` selects the D+ and D- switch paths;
- USB, CDP, timeout-open, and OTG detection can explicitly queue `COM_USB`;
- P3.15 loaded Samsung notifier consumers but omitted the GENI-I2C/MFD/PDIC
  producer path; and
- the P3.15 host sidecar observed no candidate attach after Download departure
  despite the retained controller-side gadget-start, RUN_STOP, QSCRATCH,
  state, and event-configuration witnesses.

The stock MFD firmware-setting call is not a newly discovered or
candidate-only action. This device is `MAX77705_PASS5`, for which every
successful MFD probe calls `max77705_usbc_fw_update()`. A retained normal
Android boot proves that the stock driver reached that function and took its
no-update branch. That baseline substantially lowers the novelty of a stock
successor, so this report no longer labels stock MFD categorically
inadmissible.

It does not make the stock path automatically qualified. The updater
overwrites the return code from its first firmware-version read, ignores both
charger-status read results, and applies its voltage and TA-mode guards only
on the first pass. Once either retry counter becomes nonzero, the retry path
can reset the IC and re-enter with those guards disabled. With valid PC-VBUS
status reads, the first pass exits before charger reconfiguration, secure-mode
writes, IC reset, or firmware records; read failure or a retry invalidates
that protection. This is the actual stock-path hazard boundary.

The PDIC probe is also not a passive observer. It initializes MUIC, CC, PD,
interrupts, notifier plumbing, automatic-VBUS policy, audio detection, sink
capabilities, and the opcode queue before unmasking the USBC interrupt source.

Two successor shapes therefore remain under H0 comparison:

- a stock 67-module path, whose updater behavior is stock-equivalent but not
  yet adjudicated against the exact candidate context and safety contract;
  and
- a bounded custom path that removes the updater from the probe-time reach
  set and adds tagged MUX readback, at the cost of custom-module build and
  boot-ramdisk staging complexity.

The safer custom shape is:

1. preserve the fixed Image;
2. isolate the exact GENI wrapper, GPI controller, and I2C controller before
   loading their global platform drivers;
3. stage an exact-source custom MFD under a unique boot generic-ramdisk path
   and load it instead of opening the stock vendor-ramdisk module; it prevents
   the boot-time firmware updater from executing;
4. stage and select an exact-source custom PDIC the same way; it preserves the
   normal initial-detect path and records tagged pre/post `CONTROL1` reads;
5. retain the result through a bounded read-only interface and the existing
   Process-v2 carrier/host-sidecar path; and
6. fail closed on any module, bind, queue, response, order, integrity, or
   health contradiction.

This shape appears technically feasible without changing the fixed Image. It
is not yet implementation-ready. The six stock additions and the complete
P3.15 base remain recoverable from the pinned vendor ramdisk, so wholesale
module reconstruction is not a blocker. The normal Android second-stage
`vendor_dlkm/modules.load`, exact target-only binding, stock-versus-custom
selection, complete PMIC/PDIC write inventory, telemetry encoding, and
independent review remain open gates.

## Evidence authority and hashes

The primary source and artifact inputs were rehashed during this H0 unit.

| Authority | SHA-256 |
|---|---|
| P3.15 materialized 61-module plan | `d5ec1423cd47aba29c935512690c4e0b9af3302e4df1b91e50ed1cc816199005` |
| P3.15 candidate-A artifact result | `8bc2379bcaec094eea37659ef226ad2bbfa8fcbbcdd1f2dc23373e74419ffaa6` |
| FYG8 `modules.dep` | `21eae389f1d8b0a9fc93cec0b12d36e736cfac656d91ae55055c793f2ed67b27` |
| vendor-ramdisk first-stage `modules.load` | `8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232` |
| vendor-ramdisk recovery `modules.load.recovery` | `616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10` |
| pinned `vendor_ramdisk00` | `41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193` |
| pinned raw `vendor_boot.img` | `096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7` |
| complete FYG8 firmware ZIP | `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8` |
| `drivers/mfd/maxim/max77705.c` | `523fe8b765f53b775efc9f51a9cc1ddfc67088e8375894fe43d273bbde23db46` |
| `drivers/mfd/maxim/max77705-irq.c` | `5ddbe1dee81c5756fc86c8c47264d77b4049c1ca7063647abbdc5c1cbc5cfabc` |
| `include/linux/mfd/max77705-private.h` | `a205dfc0743d38f7684a046f5aef26d466f5feef3713fe0d19bc58134a7c441e` |
| `drivers/usb/typec/maxim/max77705_usbc.c` | `4dabc4b25e99e26c662748934a6a98775073683832f08652e15762f4689a3e3d` |
| `drivers/usb/typec/maxim/max77705-muic.c` | `bfdb034d7571ca233202221cdc8cdfe68bab3e837afea9c4b5a37378ed7acbab` |
| `drivers/usb/typec/maxim/max77705_pd.c` | `4818b54be4a4616f44ed3e993cf9e5e55d394b966b0202a1c6616c59cfce47ac` |
| `drivers/usb/typec/maxim/Makefile` | `8055a9480971e835edccb441ce0554940a1d211be5bc1d1702ebc4587580c91d` |
| `include/linux/usb/typec/maxim/max77705_usbc.h` | `1cc7e211c50685c3eed3d1b4582869d0a65a559a2114c0087fac2646f4fc883e` |
| `include/linux/usb/typec/maxim/max77705-muic.h` | `3f7f2b9790940d61ec6bb636f87fd750f7971f1c609c06e6380d11907f701cb1` |
| `drivers/i2c/busses/i2c-msm-geni.c` | `2d062f016c1481984aaf9108883a940be3907b8ca48d13031324348c68b29c7a` |
| `drivers/base/platform.c` | `3aa156b25f4acd8e327a887e209a2eaa9d8c53ef3bc4e2ba74876c1447f04569` |
| `drivers/base/dd.c` | `ce68320e68f0978f854e3c8b0fa52e7f6837c08f2fcf3417400d15fe521578d0` |
| `drivers/spu_verify/spu-sign-verify.c` | `889c37137c2beb7c6cf3d299cd8b2f0ffb9b4a5af858da8733f693d3d7bc110a` |
| g0q r12 DTS | `aff997ab764b7be8ff66d57b0633fa11c881a108f8fabea186cf5a4216844822` |
| `waipio-gki_defconfig` | `de7373038099658387dea7f2168be3c63268c554c645067e255492cb836276c7` |
| fixed P3.10-derived `.config` | `6adf58c7204695e6f5a8deaf0f5995bca91a79ce4cc5f7b74e7b247128e0673b` |
| tracked super module inventory | `5ad69e151efbe48ba0348608120da3001f9e11d481b13a498177e080771c6d37` |
| retained stock/XBL `baseline_last_kmsg.bin` | `9a58a0c8486723c31f9cf8ac7d8b8be2586969bb8f167cd76907e3b82db0c7cb` |
| P3.15 USB-sidecar result | `a075c7014e9d0524fd0b7f18fe14a263639ad27ced386a4801e4c9856caf19fa` |

All kernel-source paths above are relative to:

```text
workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/
kernel_platform/msm-kernel/
```

The retained boot log stays under `workspace/private/` and is not a tracked
artifact.

### Source locator map

The hashes above identify the source objects; the following ranges identify
the statements that carry the principal load in this report. Line numbers are
for the hashed source snapshot, not for an unpinned upstream tree.

| Finding | Source locator |
|---|---|
| exact 61-entry P3.15 module plan and notifier/UCSI tail | `workspace/private/outputs/s22plus_fyg8_p315/intent/materialized-sources/s22plus_fyg8_p286_e3_plan.h:20-85` |
| exact 61-module hashes and unchanged vendor-ramdisk reuse | `workspace/private/outputs/s22plus_fyg8_p315/candidate-a/artifact-result.json`, hash-pinned above |
| first-stage/recovery order inputs | pinned `modules.load` and `modules.load.recovery`, hash-pinned above |
| PDIC, MFD, SPU, GENI-I2C, GPI, and GENI-SE dependency edges | pinned `modules.dep:91`, `:176`, `:181`, `:235`, `:305`, `:388` |
| switch bit layout and the values that evaluate to `COM_OPEN=0x3f`, `COM_USB=0x09` | `include/linux/usb/typec/maxim/max77705-muic.h:293-301`, `:359-405` |
| `CONTROL1` write construction and software-only previous-state assumption | `drivers/usb/typec/maxim/max77705-muic.c:326-349`, `:437-464` |
| initial cable detection during MUIC probe | `drivers/usb/typec/maxim/max77705-muic.c:2484-2644` |
| read failure leaves destination unchanged | `drivers/mfd/maxim/max77705.c:127-165` |
| overwritten first firmware-version read and exact first-pass error condition | `drivers/mfd/maxim/max77705.c:879-902` |
| first-pass voltage/TA guards, ignored charger-status errno, and pre-write boundary | `drivers/mfd/maxim/max77705.c:915-1009` |
| retry counters, IC reset, and guard-bypassing retry edges | `drivers/mfd/maxim/max77705.c:1016-1054` |
| void firmware-setting wrapper discards updater status | `drivers/mfd/maxim/max77705.c:1157-1182` |
| PASS5 value and updater dispatch | `include/linux/mfd/max77705-private.h:42-48`, `drivers/mfd/maxim/max77705.c:1167-1179` |
| parent updater before IRQ init and MFD child creation | `drivers/mfd/maxim/max77705.c:1311-1349` |
| exact three compiled MFD cells and module-only child drivers | `drivers/mfd/maxim/max77705.c:98-121`, `arch/arm64/configs/vendor/waipio-gki_defconfig:1095`, `:1153`, `:1165-1168`, `:1201-1204` |
| parent IRQ GPIO, masks, nested IRQs, and charger/USBC top-mask behavior | `drivers/mfd/maxim/max77705-irq.c:408-515` |
| automatic-VBUS disable and audio-enable opcode initialization | `drivers/usb/typec/maxim/max77705_usbc.c:1652-1663` |
| broad PDIC probe order and final USBC unmask | `drivers/usb/typec/maxim/max77705_usbc.c:3663-3913` |
| PD workqueue/IRQs and boot-time RID, IBUS, sink-capability, data-role, and short checks | `drivers/usb/typec/maxim/max77705_pd.c:1878-1984` |
| command-data copies and FIFO append/dequeue semantics | `drivers/usb/typec/maxim/max77705_usbc.c:1747-1828` |
| command/response pair construction and command dispatch | `drivers/usb/typec/maxim/max77705_usbc.c:2410-2554` |
| MUIC object inclusion in `pdic_max77705.ko` | `drivers/usb/typec/maxim/Makefile:5-10` |
| target g0q Max77705 node and `support-audio` property | `arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts:11624-11634` |
| platform `driver_override` precedence over OF matching | `drivers/base/platform.c:1150-1161` |
| pinctrl binding occurs after match but before probe | `drivers/base/dd.c:520-541` |
| hardware-selected GSI versus FIFO/SE-DMA mode | `drivers/i2c/busses/i2c-msm-geni.c:602-634` |
| SPU support module's side-effect-minimal module init | `drivers/spu_verify/spu-sign-verify.c:197-209` |
| target build inputs enabling Full LTO, CFI, and modversions | `arch/arm64/configs/vendor/waipio-gki_defconfig:97-101` |
| fixed build permits modules and modversions but does not enable kernel module signatures | `workspace/private/outputs/s22plus_fyg8_p310/immutable-a-v6/.config:804-817`, hash-pinned above |

The retained binary log has no stable source line numbers. Its SHA-256 above
is the authority; `strings -a` locates the XBL `ccic_init`, `muic_init`,
`BC_CTRL1_READ` values `0x00c5` and `0x00e5`, opcode `0x06`/`0x05`, ABL
`SetPath: 1`, and healthy Linux MFD version/update messages quoted below.
Mapping XBL opcode `0x06`/`0x05` to
Linux `COMMAND_CONTROL1_WRITE`/`READ` is an explicit cross-firmware ABI
inference, not a direct symbol attribution from XBL. `BC_CTRL1_READ` is the
separate opcode `0x01` and its logged `0x00c5` value is not a `CONTROL1`
readback.

### Evidence-strength partition

| Class | Established in this H0 | Not established |
|---|---|---|
| source fact | `CONTROL1` controls the D+/D- switch and the MUIC initial-detect path can queue `COM_USB` | that the queue ran in P3.15 |
| plan/artifact fact | P3.15 omitted the six-entry GENI/Max77705 producer closure; all six stock payloads and the P3.15 61-module base are recoverable from the pinned vendor ramdisk | Android second-stage load order and loadability of custom successor modules |
| retained-evidence fact | the combined retained log contains two XBL MUIC-init blocks that touch opcodes `0x06` and `0x05`, one explicitly followed by Odin `SetPath: 1`, while one stock Linux boot read `6E.00` and skipped update | the XBL write payload, returned `CONTROL1` value, exact provenance of the second bootloader block beyond its non-Odin context, or value inherited at Linux probe |
| hazard fact | every PASS5 MFD probe invokes the updater; valid PC-VBUS first-pass state exits before firmware writes, but ignored read errors and guard-free retries prevent structural nonreachability; PDIC probe performs broad control-plane initialization | that the firmware-write branch would occur in a successor, or that stock-equivalent invocation is disallowed |
| causal inference | an open/non-USB `CONTROL1` state is compatible with controller-side success plus complete host silence | that it caused P3.15 |
| successor feasibility | fixed-Image stock-67 and target-isolated custom-module experiments both have source-supported shapes | second-stage stock-order recovery, stock/custom selection, implementation, qualification, independent review, D0 inventory, or live authority |

## Exact P3.15 gap and provisional module arithmetic

The exact P3.15 plan contains 61 entries. It already carries the relevant
Samsung consumers:

```text
usb_notify_layer.ko
switch_class.ko
common_muic.ko
vbus_notifier.ko
if_cb_manager.ko
pdic_notifier_module.ko
usb_typec_manager.ko
usb_notifier_qcom.ko
```

It also carries `ucsi_glink.ko`, but the separately established P3.15 UCSI
activation path lacks its ADSP remoteproc/firmware transport and cannot act as
the live role producer.

The exact source/symbol/DT additions for the Max77705 producer are:

```text
gpi.ko
msm-geni-se.ko
i2c-msm-geni.ko
spu_verify.ko
mfd_max77705.ko
pdic_max77705.ko
```

`ucsi_glink.ko` is not removed. Its absence is not required by the MUX
hypothesis, and removing an inert module would weaken the P3.15 A/B baseline;
if it is not inert, removing it would add a second causal variable. Therefore:

```text
61 existing entries + 6 Max77705/GENI entries = 67 entries
```

This is provisional capacity and order arithmetic, not a qualified 67-module
plan. The stock path uses all six stock additions. The custom path uses the
four stock substrate/support additions and two custom modules loaded from
unique boot-ramdisk paths while the stock vendor-ramdisk copies remain
present but unopened.

The exact dependency facts are:

- `i2c-msm-geni.ko` requires `gpi.ko`, `msm-geni-se.ko`, and dependencies
  already in P3.15;
- `mfd_max77705.ko` requires `abc.ko`, `usb_notify_layer.ko`, and
  `sec_class.ko`, all already present;
- `pdic_max77705.ko` requires the MFD, `spu_verify.ko`, DWC3/USB helpers, and
  notifier consumers already present; and
- `spu_verify.ko` has no listed hard dependency and its module init only logs
  and returns zero. It is still required by the compiled PDIC symbol
  reference even though the successor must never request a firmware update.

### Base/order authorities are distinct

The retained vendor ramdisk contains two different order inputs:

- `modules.load`: 140 first-stage entries;
- `modules.load.recovery`: 446 recovery entries.

The P3.15 planner uses first-stage order, then recovery order, then
`modules.dep` order as tie-break authorities. It does not claim that its
61-entry plan is Android's complete normal-boot order. Of the P3.15 61 names,
36 are in first-stage `modules.load` and all 61 are in
`modules.load.recovery`. Of the six proposed additions, only
`msm-geni-se.ko` is in the first-stage list; all six are in the recovery list.

Android's later `vendor_dlkm/lib/modules/modules.load` is a separate authority
inside `super.img` and its bytes have not been recovered. The tracked super
inventory proves that file existed at 5,843 bytes with SHA-256
`8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360`;
an inventory row cannot reconstruct its line order. The full 9,680,091,538-byte
firmware ZIP is present and contains an 11,499,653,242-byte AP tar whose
`super.img.lz4` member is 8,875,694,170 bytes. At audit time the filesystem had
about 4.0 GiB free, so an ordinary full extraction could not be performed
safely.
Recovering that second-stage list, by a bounded streaming extractor or after
explicit space provisioning, is Gate 0 for stock-order comparison. It is not
a prerequisite for recovering the module bytes themselves.

### The module payload base is recoverable

The six stock artifact identities recorded by the module map are:

| Module | Size | SHA-256 |
|---|---:|---|
| `gpi.ko` | 121368 | `97276e3257755b3031aac27021199b38ed273f3be4b4f004bbd865a8931cdb5f` |
| `msm-geni-se.ko` | 98328 | `b3fc1b679b5539047471aeee6dae9b634fb2f5439000bdba4361d252cc38f1f8` |
| `i2c-msm-geni.ko` | 122248 | `c90278d222632b6e7f93f45aa40fae18668d9356c4bef374f2899b2263ead9be` |
| `spu_verify.ko` | 18608 | `d670a944288dffcc5fbf67a76550dc8a746665113f6ee4354521e482489f4b84` |
| stock `mfd_max77705.ko` | 125840 | `26f238730604789293db237b2bcdc4d44c5f63c263e4298f6e8e28b85d0f6f94` |
| stock `pdic_max77705.ko` | 423456 | `27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db` |

Only the stock MFD and PDIC payloads appear as individually extracted files in
the small convenience directory. That directory is not the artifact
authority. The pinned `vendor_ramdisk00` is present, and all six modules were
extracted from it during this audit. Their six size/hash pairs matched the
table exactly. The P3.15 candidate artifact independently records the exact
61-module closure and proves `vendor_ramdisk_modules_reused=true` with
`module_binaries_injected=0`.

The absence of 51 plan modules as loose `.ko` files therefore does not make
P3.15 unreproducible. A successor must rematerialize stock modules from the
hash-pinned vendor ramdisk and verify every selected byte against the module
inventory; it must not substitute an unbound file merely because its basename
matches.

## CONTROL1 is the physical USB2 switch under test

The FYG8-matched header defines `CONTROL1` as:

```text
bit 7     NoBCComp
bit 6     RCPS
bits 5:3  D+ switch
bits 2:0  D- switch
```

The switch codes are:

```text
000 Open
001 / 100 USB
011 / 101 UART
```

With the exact source constants:

```text
COM_OPEN = 0x3f
COM_USB  = 0x09
```

`max77705_switch_path()` constructs `COMMAND_CONTROL1_WRITE` (`0x06`) with
the selected one-byte value and queues it through
`max77705_usbc_opcode_write()`.

The initial attach path is:

```text
max77705_muic_init_detect()
  -> max77705_muic_detect_dev(MUIC_IRQ_INIT_DETECT)
  -> status read and classification
  -> ATTACHED_DEV_USB / CDP / TIMEOUT_OPEN / OTG
  -> max77705_muic_attach_usb_path() or com_to_usb_ap()
  -> max77705_switch_path(COM_USB)
  -> CONTROL1 write queue
```

This is a source-real mechanism capable of producing the exact host silence
seen when the controller-side DWC3/PHY path runs but the connector D+/D- path
is not USB. It remains compatibility, not causality, until the inherited and
post-command values are measured.

## Stock MFD is baseline-real but not yet adjudicated

### Probe ordering

The exact MFD probe:

1. reads PMIC ID and revision;
2. creates dummy MUIC, charger, and fuel-gauge I2C clients;
3. calls `max77705_usbc_fw_setting(max77705, 0)`;
4. creates the debug dummy client;
5. initializes the Max77705 IRQ controller; and
6. creates every compiled MFD child platform device.

The firmware-setting call therefore occurs before the PDIC child can probe.
No module ordering can load stock PDIC while bypassing the parent call.

### PASS5 means the updater runs on stock too

`MAX77705_PASS5` is `0x5`. The retained normal Android boot reports
`device found: rev:5`, then the exact live and bundled versions, and finally
the updater's no-update message:

```text
device found: rev:5 ver:0
chip : 6E.00(PID 0x8), FW : 6E.00(PID 0x8)
Don't need to update!
```

The PASS5 switch arm calls `max77705_usbc_fw_update()` on every successful
MFD probe. Thus merely entering the updater is stock behavior on this unit,
not a candidate-only exposure. The retained boot is a positive control for
one healthy no-update execution; source control flow establishes the call for
every successful PASS5 probe. Neither fact proves that every future execution
takes the same no-update branch.

### First-pass guards and their exact boundary

The updater has three early protections:

1. a firmware/product-ID mismatch returns before IRQ masking;
2. on the first pass, `vcell < 3600` exits with `-EAGAIN`; and
3. in non-factory builds, a first-pass nonzero CHGIN or WCIN detail exits as
   TA mode unless `enforce_do == 2`.

For a healthy PC-supplied-VBUS first pass with valid charger-status reads,
these conditions prevent charger-mode changes, secure-mode writes, IC reset,
and firmware records. If the version already matches, as in the retained
stock boot, the updater does even less: it reads charger configuration, masks
four USBC interrupt groups, reads the two version registers, updates its
in-memory bin-version metadata, takes the no-update branch, re-enables the
parent Linux IRQ, and returns. It does not restore those four internal mask
registers in the updater; the later PDIC bring-up installs its own masks and
eventually unmasks the parent USBC source.

If the version predicate is true but valid PC-VBUS status reaches the TA-mode
exit, the bounded first-pass effects before that exit are still active:
parent-IRQ disable/re-enable, four internal mask writes, PD/USBC and
fuel-gauge reads, two charger-detail reads, and one wireless-power-control
off/on pair. They do not include charger-mode reconfiguration, secure-mode
writes, IC reset, or firmware records. That calibrated first-pass inventory
is materially smaller than the retry path, but it is not a passive read.

The protection is not structural. The return values from both
`MAX77705_CHG_REG_DETAILS_00` reads are ignored, while `chgin_dtls` and
`wcin_dtls` start at zero. A failed status read can therefore be interpreted
as battery-only and bypass the TA exit. PC VBUS makes the benign first-pass
branch expected; it does not make the later write branch unreachable.

### Lost first-read errno

The update routine performs:

```c
ret = max77705_read_reg(... REG_UIC_FW_REV, &FW_Revision);
ret = max77705_read_reg(... REG_UIC_FW_MINOR, &FW_Minor_Revision);
if (ret < 0 && (try_count == 0 && try_command == 0)) ...
```

The second assignment overwrites the first return code. The parent structure
is zero-allocated. If the first read fails and the second succeeds,
`FW_Revision` can remain zero while `ret` is non-negative. The normal update
predicate then treats a lower revision, mismatched product ID, or `0xff` as a
reason to enter the firmware-update branch.

This is not merely a logging defect, but it is also not proof that a firmware
write would occur in the PC-VBUS experiment. It is one way to enter the update
predicate with stale input; the first-pass voltage and TA guards still apply
if their own reads succeed.

### Retry is the stronger stock-path hazard

The read-error, voltage, and TA guards all test
`try_count == 0 && try_command == 0`. The two retry edges increment one of
those counters, call `max77705_reset_ic()`, sleep for one second, and jump to
`retry`. Every subsequent pass therefore masks the interrupts again but skips
both the voltage guard and the TA-mode guard. The secure-mode and verify
counters are each bounded by ten attempts, so this is bounded active behavior,
not an infinite loop; it can nevertheless reset the IC repeatedly and reach
firmware records without re-establishing the first-pass power predicates.

This retry geometry, not the mere existence of a stock updater call, is the
strongest technical reason to prefer a custom MFD for a narrow discriminator.
Whether stock-equivalent risk is admissible remains an explicit independent
review decision rather than a conclusion smuggled into this H0 report.

The status boundary is also closed in the wrong direction:
`max77705_usbc_fw_setting()` is `void`, discards the integer return from
`max77705_usbc_fw_update()`, and the parent probe proceeds to IRQ and child
creation. Thus neither the lost first-read error nor a later updater failure
can be propagated through the parent probe call site.

### Bounded custom-MFD option

The minimum custom correction is to prevent the parent probe's boot-time call
from entering `max77705_usbc_fw_update()`. This is a preferred risk reduction,
not proof that an unchanged stock path violates a permanent boundary.

The correction must be exact and auditable:

- no version-based, force-based, or fallback firmware write may execute;
- the custom PDIC must omit or permanently reject its writable `fw_update`
  attribute, built-in/request-firmware worker, and misc firmware callback;
  merely promising that PID 1 will not write the stock endpoints is not an
  execution-closure proof;
- the exported MFD updater ABI must either be absent with the custom PDIC
  linked accordingly, or remain only as a typed fail-closed stub that cannot
  reach firmware, charger, wireless-power, or reset effects;
- no fake `FW_UPDATE_END` state may be written; the ordinary no-update branch
  leaves the zero-initialized state at `FW_UPDATE_START` as well;
- the omission of `store_ccic_bin_version()` metadata must either be accepted
  explicitly or preserved with a side-effect-free metadata-only operation;
  it must not disappear unnoticed; and
- the custom module must retain the exact exported ABI required by the PDIC.

Skipping this call does not make the MFD passive.

### Remaining MFD effects

`max77705_irq_init()`:

- requests and configures the IRQ GPIO;
- writes `0xff` to each valid per-group mask register;
- registers nested IRQ descriptors;
- changes the top-level `INTSRC_MASK`;
- requests the threaded parent IRQ; and
- leaves the charger source unmasked while the USBC source remains masked
  until the PDIC later unmasks it.

The exact config compiles three MFD cells here: USBC, fuel gauge, and charger.
Their three drivers are module-only (`=m`); no Max77705 regulator, vibrator,
RGB, or flash cell is compiled by the pinned target fragment. The 67-entry
design loads PDIC/USBC but not the charger or fuel-gauge driver, so no built-in
child driver is expected to bind those two cells. Runtime must still prove the
two remain unbound and that no alias/autoload path supplied their modules.
This child-cell result does not make the parent updater passive: it directly
uses the parent's dummy charger and fuel-gauge I2C clients without those child
drivers.

One detailed-design decision remains open: retain the stock parent IRQ-mask
behavior exactly, or narrowly keep unrelated non-USBC top sources masked. The
latter reduces unrelated activity but changes stock behavior and therefore
needs source-derived justification and a separate fixture. It must not be
introduced casually as part of the firmware-update fix.

## PDIC probe is broad control-plane bring-up

The PDIC/USBC child probe performs at least the following actions before it
returns:

1. allocates opcode and notifier workqueues;
2. rereads HW/FW version information and stores the live CCIC version;
3. registers USBC interrupt handlers;
4. initializes MUIC IRQs and performs initial cable detection;
5. initializes CC and PD state and their IRQs;
6. writes PD and VDM interrupt masks;
7. queues an opcode disabling automatic VBUS;
8. because the exact g0q DT has `max77705,support-audio`, queues a CCCTRL1
   write enabling audio/debug accessory detection;
9. initializes external notifier and PDIC misc plumbing; and
10. unmasks the parent USBC interrupt source.

The PD initialization also checks RID, queues the no-auto-IBUS policy,
programs sink capabilities, runs an initial data-role handler, checks CC/SBU
short state, and registers PD-message callbacks.

The MUIC initialization sets software defaults, initializes IRQs, reads cable
status, and can queue `COM_USB`. The software assignments
`attached_dev = NONE` and `switch_val = COM_OPEN` do not read the hardware
switch and cannot establish the inherited state.

Accordingly, the future action must be described as Max77705 control-plane
bring-up with a MUX discriminator. Calling it a one-register MUX observation
would understate the effect surface.

The support-audio CCCTRL1 write is retained only because it is exact stock
probe behavior, not because it is inert. It changes accessory-detection policy
and can classify a connection away from ordinary USB. A successor must record
its command/response outcome and may not silently remove or relabel it as a
harmless initialization write.

## Bootloader inheritance is partly observed, not resolved

The retained combined boot log contains two XBL MUIC-initialization blocks.
Both issue opcodes `0x06` and `0x05`. The first quoted block is later followed
by the explicit Odin `SetPath: 1` sequence and reports:

```text
[XBL] ccic_init
[XBL] Max77705 HW i2c init
[XBL] muic_init
[XBL] BC_CTRL1_READ : 0x00C5
[XBL] muic_command_polling: OP 0x06 Response OP 0x06
[XBL] muic_command_polling: OP 0x05 Response OP 0x05
```

The second block reports `BC_CTRL1_READ : 0x00E5` and the same `0x06`/`0x05`
pair, without an adjacent Odin `SetPath` in that block. The capture therefore
disproves “only the Download-specific ABL command ever touches this opcode
pair,” but the combined log does not carry a direct per-block label that alone
proves the second block's full boot mode.

Thus the previous statement that no normal-boot bootloader evidence exists is
false. Reading XBL opcode `0x06`/`0x05` as the Linux-defined
`CONTROL1` write/read pair relies on the shared Max77705 firmware command ABI;
the XBL binary does not expose the Linux enum names. The numerical match and
the adjacent MUIC context make the inference strong, but it remains an
explicit cross-firmware inference.

`BC_CTRL1_READ : 0x00C5` is separate. Linux defines BC-control read as opcode
`0x01`; neither that label nor `0x00c5` is a `CONTROL1` D+/D- switch value and
it must not be used as pre-MUX evidence.

The log does not contain the write payload or read value. It therefore cannot
distinguish:

1. XBL leaves `CONTROL1=COM_USB` and Linux inherits it;
2. XBL leaves `CONTROL1=COM_OPEN` or another path;
3. XBL writes USB but a later PMIC/IC transition changes it; or
4. the Max77705 firmware autonomously changes the switch after XBL.

The explicit Download block adds an ABL `SetPath: 1` marker and then enumerates
Odin. This is a strong positive control that the physical connector path can
work in that mode, but it does not reveal the normal-boot value.

The bootloader question is therefore narrowed from “does it touch the MUX?” to
“what exact value survives immediately before Linux's COM_USB command?” The
tagged pre-read is the direct discriminator.

## GENI/GPI/I2C drivers have a global bind surface

The exact active DT composition contains:

- three enabled QUPv3 wrapper devices;
- three enabled GPI DMA devices; and
- nine enabled GENI I2C controllers.

Those counts were derived during this audit from a host-generated merged FYG8
DT, not from a retained live inventory. The temporary merged file is not
evidence authority. Successor qualification must regenerate the exact merged
topology from the pinned r12 input, hash a durable private receipt, and prove
the same 3/3/9 count before it constructs the override set. A different count
or target path stops the design rather than being normalized to this report.

The target chain is:

```text
9c0000 QUPv3 wrapper
  -> 900000 GPI DMA
  -> 994000 GENI I2C
  -> max77705@66
```

The target I2C adapter also contains `fsa4480@42` and `pca9481@57`. Their
drivers are not part of the provisional 67-entry plan, but their bind absence
must be included in the terminal contract.

The three substrate modules register global OF platform drivers. Loading them
without narrowing can bind all matching enabled devices, select their pinctrl
states, configure DMA, request IRQs, and create unrelated I2C buses. That is
not proportional to one Max77705 discriminator.

The source-supported narrowing mechanism is a pre-load `driver_override`
sentinel on every non-target matching platform device:

```text
2 non-target QUPv3 wrappers
2 non-target GPI devices
8 non-target enabled GENI I2C controllers
-------------------------------------------
12 transient overrides
```

`platform_match()` consults `driver_override` before OF matching. This is
important because `really_probe()` binds pinctrl before it invokes the driver
probe. A probe-local address check would therefore be weaker: unrelated
devices could already have changed pinctrl or DMA state before returning.

The override proposal is not D0 and is not yet authorized. Before design, a
bounded exact-target D0 must read:

- the exact 15 target/non-target sysfs device names;
- whether any already has a `driver` symlink;
- whether every required `driver_override` file exists;
- the current override contents; and
- the exact target `994000.i2c` and `max77705@66` topology.

The candidate must write and read back all 12 sentinel overrides before any
of the three substrate drivers are loaded. It must then prove:

- only the target wrapper, target GPI device, and target I2C controller bound;
- all 12 non-target devices remain unbound with the exact sentinel;
- exactly one `*-0066` Max77705 client appears on the target adapter; and
- no non-target I2C client driver bound as a side effect.

Any pre-existing bind, missing override, ambiguous device name, write/readback
mismatch, or extra bind is a pre-effect or runtime contradiction. It is not a
reason to continue with global binding.

## GPI use must be observed rather than assumed

`geni_i2c_prepare()` reads `GENI_IF_FIFO_DISABLE_RO` on first use:

- nonzero selects `GSI_ONLY` and GSI DMA;
- zero selects `FIFO_SE_DMA` and configures the GENI FIFO path.

GSI mode requests TX and RX DMA channels from the GPI driver. FIFO mode does
not require those channels for the transfer. The dependency closure may still
load and target-bind GPI, but the result contract must record the selected I2C
mode. It must not claim that a successful Max77705 transfer proves a GPI data
path unless the hardware-selected mode was GSI.

## Tagged CONTROL1 pre/post observer

### Why ordinary logs and cached state are insufficient

The normal MUIC path writes `CONTROL1` but does not read it before or after the
write. `write_vps_regs()` derives its previous switch from software state and
assumes `COM_OPEN` when there is no prior software cable. It is not hardware
readback.

The generic response handler reads `CONTROL1_R` data but discards ordinary
values unless the command is an update-sequence operation. A log line saying
that `COM_USB` was selected proves only source-path reach. A successful queue
call proves only that the request was enqueued.

### Queue ordering that makes the observation possible

The PDIC probe initializes its workqueues and IRQ handlers before
`max77705_muic_probe()`. The parent USBC interrupt source remains masked until
the end of child probe.

A bounded custom PDIC can therefore:

1. queue a tagged `CONTROL1_R` immediately after child IRQ setup and before
   `max77705_muic_probe()`;
2. let normal MUIC initialization and initial detection run unchanged;
3. when the first normal `COM_USB` write is queued, queue one tagged post-read
   immediately behind its write/response pair; and
4. record the completed initial-detect classification even when no `COM_USB`
   branch occurs; and
5. allow the existing final USBC unmask to drain the FIFO in causal order.

The expected relevant queue order is:

```text
PRE CONTROL1_R command
PRE CONTROL1_R response
... ordinary preceding MUIC initialization commands, if any ...
COM_USB CONTROL1_W command
COM_USB CONTROL1_W response
POST CONTROL1_R command
POST CONTROL1_R response
```

The pre-read command can be sent while the parent source is masked; its
response remains queued for interrupt service. Subsequent commands append
behind the pending response. This produces a hardware pre-value immediately
before the queued COM_USB transition rather than relying on bootloader logs.

### Tag propagation requirements

Adding a field to `usbc_cmd_data` is not sufficient. The read helper creates
separate command and response queue entries and copies only selected fields.
The observer tag must be propagated through all of:

```text
caller read_op
  -> max77705_usbc_opcode_read() outgoing command entry
  -> max77705_usbc_opcode_read() response entry
  -> enqueue_usbc_cmd()
  -> copy_usbc_cmd_data()
  -> front/dequeue/run path
  -> max77705_response_opcode()
```

Only the two observer reads may carry nonzero tags. Ordinary commands and
responses must remain tag zero. Missing, duplicate, reordered, overwritten,
or unexpected tagged responses fail closed.

The preferred userspace boundary is one read-only cached-result interface,
for example a custom 0444 module-parameter getter. The getter must return only
cached state and must never initiate I2C. IRQ/workqueue updates and the getter
must use an explicit synchronization rule. Raw kmsg text alone is not a
sufficient retained authority because an observer parser defect would again
destroy the only evidence.

The exact carrier representation is a later detailed-design obligation. It
must preserve at least:

- pre command queued / response received;
- initial detect entered/completed and its bounded cable classification;
- COM_USB branch and command queued;
- post command queued / response received;
- pre and post one-byte values;
- first failure stage and bounded error bucket;
- duplicate/order/foreign-response contradiction flags;
- MFD, PDIC, target I2C, and target platform bind witnesses; and
- host-side attach/enumeration correlation.

### Result matrix

| Device result | Host sidecar | Permitted interpretation |
|---|---|---|
| pre `0x3f`, post `0x09` | exact enumeration | strong causal support that Linux's MUX transition enabled the path |
| pre `0x3f`, post `0x09` | silent | the switch transition occurred but was insufficient; continue only from another bounded hypothesis |
| pre `0x09`, post `0x09` | exact attach or enumeration | the MUX was already USB; any improvement came from another newly loaded control-plane effect, so MUX causality is refuted and the witnessed notifier/session delta becomes the next boundary |
| pre `0x09`, post `0x09` | silent | missing Linux MUX initialization is strongly refuted for that run |
| pre other, post `0x09` | silent or attach | inherited state classified; Linux transition succeeded, but causality follows host result |
| exact pre, completed initial detect, no `COM_USB` branch | silent or attach | valid classification/control-plane result; retain the bounded attached-device/status class and do not require a post tag |
| any pre, post non-`0x09` | silent | Max77705 command/response/control-path failure boundary |
| any pre, post non-`0x09` | exact attach or enumeration | device/host attribution contradiction; preserve both facts but make no MUX-causal claim |
| missing, duplicate, wrong-order, malformed, or foreign tag | any | `NO_PROOF_OBSERVER`; no MUX conclusion |
| exact attach without completed device evidence | attach | preserve host fact, but do not invent the missing device-side transition |

The no-`COM_USB` row is valid only when the initial-detect entry, terminal
classification, and queue state are all complete. Once a `COM_USB` branch is
recorded, a missing post command or response remains `NO_PROOF_OBSERVER`; the
valid absence branch must not become a generic escape from tag loss.

No negative row proves an analog PHY, cable, connector, or host fault.

### Host-sidecar positive control

The ACM endpoint observer and the USB-event sidecar are different observers.
P3.15's ACM file was zero bytes, but its USB sidecar was not blind: in the same
session it recorded the exact S22+ stock-Android endpoint departing, the
Download-mode endpoint appearing, and that Download endpoint departing before
the candidate window. Its udev source was nonempty, untruncated, and exited
cleanly. The candidate then produced no new S22+ USB connection.

That retained same-session evidence is a positive control for the host USB
event collector, not for candidate ACM. A successor must promote it from
supporting evidence to a packaging/runtime gate: the bound sidecar must prove
one exact-target stock or Download event and the exact Download departure
before candidate silence can be interpreted. A missing, ambiguous,
wrong-topology, truncated, or uncorrelated positive control yields
`NO_PROOF_OBSERVER`, not host silence.

## Historical S7A2 is not a clean refutation

M34 S7A2 previously carried an 86-module recipe containing GENI I2C and the
stock Max77705 chain and remained host-silent. That history is mandatory
counterevidence, but it did not retain the facts required for causal reuse:

- no per-module `finit_module` return vector survives;
- no exact wrapper/GPI/I2C bind proof survives;
- no unique `994000.i2c` adapter/client proof survives;
- no MFD or PDIC probe-complete witness survives;
- no initial classification, COM_USB queue, low-level write, response, or
  CONTROL1 readback survives; and
- the private raw S7A2 run directory referenced by the report is no longer
  present.

Later S8/S9/S10 work showed that even module-list presence and early module
boundaries were uncertain in that campaign. S7A2 therefore proves that the old
recipe did not produce host-visible enumeration. It does not prove that the
Max77705 chain executed the transition now under test.

A current Process-v2 successor with exact load/bind/control/readback evidence
is a distinct experiment, not a replay of S7A2.

## The 86-module closure remains forbidden

The provisional phone-VBUS 86-module closure pulls in
`sec_qc_dbg_partition.ko`, a previously recorded candidate-side partition
writer. That closure is not an acceptable fallback.

The narrow discriminator uses PC-supplied VBUS in the existing UFP cable
configuration and does not need charger, fuel-gauge, battery, wireless-power,
or debug-partition modules. The successor must not expand from 67 to the old
86-name dependency closure merely because `modules.dep` lists it under charger
consumers.

Specifically excluded:

- `sec_qc_dbg_partition.ko` and its partition path;
- `sec-battery.ko`, `max77705_charger.ko`, and
  `max77705-fuelgauge.ko` for this UFP discriminator;
- manual VBUS sourcing or forced host mode;
- raw I2C, `/dev/mem`, EUD/UART writes, or debugfs register pokes; and
- any invocation of the Max77705 firmware-update sysfs/callback path.

## Build and fixed-Image implications

The mechanism does not require a fixed-Image source change. The fixed Image
can remain the P3.10-derived base inherited by P3.15.

That does not make this a userspace-only repackaging. The pinned target
configuration inputs enable:

```text
CONFIG_LTO_CLANG_FULL=y
CONFIG_CFI_CLANG=y
CONFIG_MODVERSIONS=y
```

The two custom modules, if selected, must therefore be built twice from the
exact FYG8 source/config/toolchain closure and prove:

- byte-identical A/B module output;
- exact module name and vermagic;
- preserved exported symbol names and CRC requirements;
- CFI-compatible indirect-call types;
- no unexpected undefined symbol or dependency drift;
- linked source and final `.ko` hashes;
- correct `modinfo` dependency list;
- exact generic-ramdisk staging under two unique selected filenames;
- direct loader selection of those two files before either stock module is
  opened; and
- absence of any attempted load, alias autoload, or fallback to the stock
  vendor-ramdisk MFD/PDIC files.

The fixed build has `CONFIG_MODULES=y`, `CONFIG_MODVERSIONS=y`, and
`CONFIG_MODULE_SIG` unset. Kernel signature enforcement therefore does not
block an exact custom-module experiment. This does not relax the harder ABI,
CFI, trimmed-export, reproducibility, or package-binding requirements above.

If the repository cannot produce isolated exact modules under that closure,
the build may need to invoke the full kernel build infrastructure. Even then,
the candidate must keep the fixed Image unchanged unless a separately reviewed
Image change is explicitly selected. A successful source compile alone is not
a loadability qualification.

Boot is the only permitted partition payload. The stock modules physically
remain under stock `vendor_boot` `/lib/modules`, so “replace the stock files”
is not a valid boot-only construction. The custom artifacts must instead be
added to the generic boot ramdisk under collision-free paths such as
`/lib/modules/p3xx_mfd_max77705.ko` and
`/lib/modules/p3xx_pdic_max77705.ko`. Their ELF module names and exported ABI
may remain source-correct even though the carrier filenames are unique.

The P3.15 runtime currently constructs `/lib/modules/` plus the plan filename.
A successor must bind that loader input to the two generic paths, prove the
effective-rootfs composition contains each selected custom byte exactly once,
and prove the stock vendor paths are never opened. The inherited
`no_duplicate_override_or_alias` rule remains valid at the filesystem-path
level; it cannot be satisfied by placing same-path replacements into the
generic ramdisk and hoping archive order wins.

## Required module and bind order

The provisional order is:

```text
existing P3.15 substrate and notifier consumers
  -> retain ucsi_glink.ko in its inherited position
  -> apply/read back 12 non-target platform driver overrides
  -> msm-geni-se.ko
  -> gpi.ko
  -> i2c-msm-geni.ko
  -> prove only target wrapper/GPI/I2C bound and target adapter exists
  -> spu_verify.ko
  -> selected stock or custom mfd_max77705 module path
  -> prove one max77705@66 parent and no unintended child-driver binds
  -> selected stock or custom pdic_max77705 module path
  -> wait for exact tagged observer terminal state
  -> correlate with the already bounded host USB sidecar
```

The exact relative placement inside the P3.15 module loop remains a detailed
design item. It must preserve `ucsi_glink.ko`, preserve the existing USB
notifier consumers before PDIC initial detection, and be checked against stage
capacity and every position/bind gate. P3.04's stale-position-table incident
must be reproduced as a qualification regression. Removing UCSI requires a
separate causal justification; inertness is a reason to keep the A/B baseline,
not to subtract it.

## Remaining H0 gates

The following are host-only and must close before a live candidate is
prepared:

0. **Carrier and normal-order authority**
   - treat the pinned vendor ramdisk and its verified six-module extraction as
     the stock-byte authority; loose-file counts are not provenance;
   - recover Android's second-stage
     `vendor_dlkm/lib/modules/modules.load` from the pinned AP/super input, or
     obtain the exact same file under a separately authorized read-only
     capture;
   - distinguish vendor_boot first-stage, recovery, and vendor_dlkm
     second-stage order rather than calling the 446-entry recovery list
     “normal boot”; and
   - bind the resulting 67-entry order and every module byte before choosing
     stock versus custom MFD/PDIC.

1. **Custom MFD patch contract**
   - exact removal or bypass of the probe-time updater;
   - decision on side-effect-free bin-version metadata;
   - complete retained/changed IRQ-mask behavior;
   - machine-readable forbidden-call proof for every parent, sysfs, worker,
     misc-callback, and exported update path.

2. **Custom PDIC observer contract**
   - exact pre/post queue points;
   - tag propagation through both queue nodes and every copy site;
   - first-only COM_USB selection;
   - absence or fail-closed replacement of every firmware-update write
     surface and callback registration;
   - cached read-only export and synchronization;
   - bounded timeout and registered failure details.

3. **Complete write inventory**
   - MFD dummy clients, per-group masks, INTSRC mask, IRQ setup, and MFD cells;
   - MUIC/CC/PD masks and opcode writes;
   - auto-VBUS disable, audio enable, no-auto-IBUS, sink capability, and
     initial-detect writes;
   - explicit keep/remove decision for every nonessential write.

4. **Exact module artifacts**
   - rematerialize the four stock substrate/support modules from the pinned
     vendor ramdisk and recheck their already confirmed identities;
   - reproducibly build and qualify the two custom modules;
   - stage custom modules in the generic boot ramdisk under unique selected
     paths while proving the stock vendor copies are never opened;
   - recompute dependency, stage, and package closure.

5. **Runtime and telemetry**
   - target-only override machinery and readback;
   - module load and bind witnesses;
   - selected FIFO/GSI mode;
   - tagged observer terminal state;
   - same-session exact-target stock/Download positive control before any
     candidate-side host-silence interpretation;
   - host-sidecar correlation;
   - carrier encoder/decoder/generation-position exhaustive tests through the
     real Process-v2 adapter.

6. **Historical and safety regression**
   - S7A2 must remain a prior negative recipe result, not disappear from the
     result contract;
   - the 86-module/debug-partition path must be mechanically rejected;
   - no charger, battery, raw-I2C, forced-host, VBUS, EUD, or UART path may
     enter the candidate source closure;
   - a custom selection must prove the updater is unreachable from its parent
     probe and from every later exported/sysfs entry point; and
   - a stock selection must instead bind the exact stock updater call,
     first-pass inputs, retry state, and terminal result to its separately
     reviewed risk disposition. It may not borrow the custom nonreachability
     claim.

Gate 1 and the custom portions of Gates 2 and 4 apply only if the custom path
is selected. A stock-67 selection instead requires a reviewed finding that
the stock-equivalent updater/control-plane risk is admissible for this exact
context; it does not inherit an approval merely because stock Android has run
the same probe.

## Required D0 gate

One bounded exact-target read-only inventory remains necessary before the
override design can be materialized. It must capture only:

- exact platform device names for the three QUPv3 wrappers, three GPI devices,
  and nine enabled GENI I2C devices;
- each `driver`, `driver_override`, modalias, and current binding state;
- the target `994000.i2c` topology and existing Max77705 client path;
- current loaded state of the six proposed modules; and
- exact stock health and USB inventory.

It must not write `driver_override`, bind/unbind a driver, load a module,
change a service, reboot, or trigger any Max77705 control. Ambiguity or a
pre-existing unexpected bind stops the proposed narrowing design.

## Independent review boundary

One proportional independent review is required because the successor changes
execution-critical module artifacts, introduces transient platform override
writes, and activates a new PMIC/PDIC control-plane hazard.

The review must cover at least:

- exact custom-module source diffs and linked outputs, if the custom path is
  selected;
- custom updater nonreachability, or for a stock selection the exact
  stock-equivalent updater inputs, retry/outcome evidence, and explicit risk
  disposition;
- platform override scope and rollback-by-reboot behavior;
- complete I2C/IRQ/opcode write inventory;
- tag and queue-order proof;
- telemetry carrier and Process-v2 adapter round trip;
- module/stage capacity and position-table regression;
- 86-module and forbidden-writer rejection; and
- unchanged boot-only transfer, rollback, and final-health machinery.

A review pass qualifies the named capability and hashes only. It does not
authorize a run or revive P3.15.

## Stop conditions

The successor is not admissible if any of the following remains true:

- stock MFD is selected without an explicit reviewed disposition of its
  stock-equivalent updater and retry hazard;
- custom MFD/PDIC is selected and exact A/B or modversion/CFI closure fails;
- any selected stock module cannot be rematerialized from the pinned vendor
  ramdisk with the exact inventory identity;
- the candidate order is inferred from `modules.load.recovery` while the
  Android second-stage authority remains unexamined;
- target-only platform narrowing cannot be proven before driver registration;
- the MFD/PDIC write inventory contains an unbounded power, firmware, storage,
  panic, EUD, UART, or raw-register effect;
- tagged read responses cannot be retained without relying solely on raw log
  parsing;
- the package cannot distinguish pre, completed initial detect without
  `COM_USB`, COM_USB, post, and observer failure;
- `ucsi_glink.ko` is removed without a separately proven causal need;
- the old 86-module closure reappears; or
- exact rollback, physical recovery, attendance, or final health is not
  available under the binding S22+ process.

On any such result, remain H0. Do not silently switch between stock and custom
MFD, use manual I2C, widen to the 86-module closure, or launch another blind
F1.

## Validation performed

This report was closed at H0 with the following host-side checks:

- all source, plan, dependency, inventory, DTS, configuration, and retained-log
  SHA-256 values in the authority table were recomputed from the named files;
- the materialized P3.15 plan was parsed as exactly 61 module entries;
- retaining `ucsi_glink.ko` and adding the six named producer/substrate entries
  produced exactly 67 unique entries;
- the pinned `modules.dep` graph was evaluated for each of those six entries
  and produced zero dependencies outside the 67-entry set;
- all six added stock modules were extracted from the hash-pinned
  `vendor_ramdisk00` and matched the six inventory size/hash pairs exactly;
- the P3.15 artifact result independently proved the exact 61-module closure,
  unchanged stock vendor-ramdisk reuse, and zero injected module binaries;
- the 140-entry first-stage and 446-entry recovery lists were counted and kept
  distinct; all 61 P3.15 modules occur in recovery order, while 36 occur in
  first-stage order;
- the tracked super inventory was checked to prove only the 5,843-byte
  second-stage `modules.load` identity, not its missing line order;
- the complete FYG8 ZIP and nested AP/super member sizes were read without
  extraction; second-stage vendor_dlkm order remains an explicit open gate
  because full super extraction exceeds current free space;
- the source ranges in the locator map were read directly rather than inferred
  from symbol names or a parallel upstream tree;
- the exact MFD-cell conditionals were evaluated against the target fragment:
  only USBC, charger, and fuel-gauge cells compile, and all three child drivers
  are module-only;
- the fixed P3.10-derived config proves kernel module signatures are disabled
  while modversions, CFI, Full LTO, and trimmed-export constraints remain;
- the retained binary log markers were found in the hash-pinned file, while
  the absent opcode payload/read value was kept explicitly unresolved;
- the P3.15 USB sidecar was verified nonempty and untruncated and its private
  udev stream was confirmed to contain exact-target stock and Download-mode
  transitions before candidate silence; this was not confused with the
  zero-byte ACM observer;
- `python3 -m unittest tests.test_device_action_process_v2_docs` passed 19/19;
  and
- tracked and new-report whitespace checks passed with a terminating newline.

The transient merged-DT count is deliberately not promoted to a durable
qualification result. Its required regeneration and receipt are an explicit
successor gate above.

## Final conclusion

The Max77705 MUX hypothesis survives the detailed audit, but the naive test
does not.

The evidence now supports these exact statements:

1. `CONTROL1` is the connector-side USB2 switch and the normal MUIC path can
   command `COM_USB`.
2. P3.15 omitted the exact producer path that would perform that command.
3. Retained XBL blocks issue the shared-ABI `CONTROL1` write/read opcode pair,
   including one explicit Odin block and a second non-Odin-context block, but
   retained logs do not reveal the write payload, read result, or inherited
   Linux value.
4. The historical S7A2 negative lacks the bind and command evidence required
   to refute the mechanism cleanly.
5. Stock MFD probe runs the updater on this PASS5 device during normal Android
   boot; valid PC-VBUS first-pass state is protective, but ignored status-read
   errors and guard-free reset/retry passes keep the active write branch
   structurally reachable. Stock use is unadjudicated, not automatically
   rejected or approved.
6. PDIC load is broad Max77705 control-plane bring-up, not a passive MUX read.
7. The P3.15 base and all six stock additions are recoverable from pinned
   local firmware; Android's separate vendor_dlkm second-stage load order is
   still missing.
8. A fixed-Image successor is technically plausible with target-isolated GENI
   binding and a tagged MUX observer. The stock-67 and custom-module variants
   require separate risk/build dispositions, exhaustive telemetry fixtures,
   a sidecar positive-control gate, and independent review.

Until those H0 and D0 gates close, the correct state is:

```text
MUX_CAUSALITY_UNPROVEN
BASE_MODULE_BYTES_RECOVERABLE_SECOND_STAGE_ORDER_OPEN
STOCK_67_UNADJUDICATED
CUSTOM_SUCCESSOR_CONDITIONALLY_FEASIBLE_NOT_READY
```
