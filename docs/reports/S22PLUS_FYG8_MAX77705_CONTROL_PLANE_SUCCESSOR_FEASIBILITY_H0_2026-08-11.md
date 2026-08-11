# S22+ FYG8 Max77705 Control-Plane Successor Feasibility H0

Date: 2026-08-11 KST

Last H0 continuation: 2026-08-12 KST

Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`)

Verdict:
`BASE_CARRIER_NORMAL_ORDER_AND_EXACT_SYSFS_GEOMETRY_RECOVERED_STOCK_67_UNADJUDICATED_FULL_PDIC_CUSTOM_66_REJECTED_CUSTOM_65_P316_HOST_QUALIFIED_PROCESS_V2_READY_LIVE_UNAUTHORIZED`

Review state:
`PRIMARY_SOURCE_491_MODULE_NARROW_LINKED_ABI_OVERRIDE_QEMU_AND_P316_CHANGED_CLOSURE_REVIEWS_CLOSED`

Repository analysis base:
`0dd0981d960aa74681f5965c021c740cb1eab393`

Correction input commit:
`30d8e918316961ff6e42cc729b0c13ab24f618aa`

Narrowing continuation base:
`f958e3f0da5bc883846fcb5cdca32561cec378aa`

Implementation/build continuation base:
`22398d48007086e995b64317406c1e2aa800a00b`

QEMU observer-repair continuation base:
`90810df8d2d1ee0e8e6a4386cd2f0a1d30253d84`

## Scope and authority

The original analysis and its build continuations were host-only. A final
2026-08-12 continuation performed one separately directed, bounded read-only
D0 on the exact S22+ solely to close the sysfs-inventory gate below. It wrote
no sysfs control, inserted no module, changed no service, rebooted nothing, and
created no candidate or rollback artifact. No D1 or F1 action was performed.
P3.15 remains consumed and non-replayable. A90 identity, files, devices,
authority, and evidence are outside this unit and received zero commands.

This report follows the closed discussion in
`S22PLUS_FYG8_MAX77705_USB2_MUX_HYPOTHESIS_AND_FALSIFICATION_H0_2026-08-11.md`.
It does not promote the MUX hypothesis to fact. It resolves or narrows that
report's open MFD, bootloader-evidence, module-artifact, and observer-design
questions and introduces a distinct hazard class:

```text
MAX77705_CONTROL_PLANE_BRINGUP
```

The stock/full-PDIC hazard is broader than one D+/D- MUX write. Loading MFD
and PDIC initializes a combined PMIC/MUIC/CC/PD/alternate-mode/AFC interrupt
and command plane. That source audit rejects the former full-PDIC custom-66
shape as disproportionate for this discriminator. The selected H0 design is
instead one direct polling I2C diagnostic with a bounded three-read/optional-
one-write effect set. Its source, linked ABI, target-only binding runtime,
observer schema, deterministic boot-only package, Process-v2 promotion, ready
manifest, and changed hazard closure are now host-qualified. Actual GENI/I2C,
Max77705, MUX, and host behavior remain live-only unknowns; no live authority
follows.

This audit also names one narrower source-level failure class:

```text
MAX77705_FIRMWARE_UPDATEWARD_READ_FAILURE_DEFAULTING
```

`max77705_read_reg()` leaves its destination unchanged on error. In the
updater, both the zero-initialized firmware revision and the explicitly
zero-initialized charger-detail locals are therefore failure defaults that
favor entering or continuing the firmware-update path. This class identifies
the direction of failed-read interpretation; it does not claim that a
firmware record was written in any retained run.

Nothing in this report grants live authority. The provisional module count is
dependency arithmetic only, not a qualified plan.

The later Gate 0 continuation in this same H0 unit remained host-only. It
streamed the pinned AP/super input, wrote only the 57,610,240-byte
`vendor_dlkm` extent, and recovered Android's exact second-stage
`modules.load`; it did not contact a device or create a boot payload.

The subsequent custom-surface continuations also remained host-only. They
temporarily expanded the exact 441-module vendor ramdisk and read the 50
`vendor_dlkm`-only modules from the already authenticated F2FS image, scanned
the resulting 491-name stock union, and removed every temporary extraction
after producing private receipts. The second continuation pinned the complete
PDIC composite surface and the I2C command/match authorities, then registered
the custom-65 single-module diagnostic. That historical continuation did not
write, build, or package the module. The later H0 implementation/build
continuation created the bounded source and reproducibly linked it twice
against the exact fixed P3.10 ABI. The P3.16 continuation then materialized the
64-plus-late-only runtime, actual topology/lifecycle fixtures, retained observer
authority, two reproducible boot-only packages, independent artifact closure,
Process-v2 promotion, and canonical ready bundle. It did not contact a device
or load the module. The valid current state is
`CUSTOM_65_P316_HOST_QUALIFIED_PROCESS_V2_READY_LIVE_UNAUTHORIZED`.

## Executive result

The source-level MUX mechanism is real and remains compatible with the P3.15
signature. `CONTROL1` selects D+/D-, its full register bytes are
`COM_OPEN=0x3f` and `COM_USB=0x09`, P3.15 omitted the GENI-I2C/Max77705
producer closure, and the host sidecar remained candidate-silent despite the
controller-side digital witnesses.

The stock 67-module comparison remains source-supported but unadjudicated.
Every successful PASS5 stock MFD probe invokes the updater; retained Android
evidence proves a healthy no-update pass, but failed reads default toward old
firmware/battery-only classification and later reset/retry passes no longer
apply the first-pass voltage/TA guards. Stock equivalence reduces novelty; it
does not establish admissibility.

The full PDIC composite is also much broader than the question. Its linked
objects carry parent IRQ/mask programming, MFD children, MUIC classification,
BC/DCD, CC/PD, source-VBUS coordination, sink-capability/no-auto-IBUS writes,
alternate-mode/VDM/Dex, AFC/QC, audio/accessory, notifier, writable sysfs,
misc, and debug surfaces. Removing only firmware and obvious callbacks leaves
that runtime matrix intact. The former custom-66 full-PDIC design is therefore
rejected as disproportionate, not promoted to implementation.

P3.12/P3.15 already established the controller/gadget side through clocks,
PHY resume, QSCRATCH session-valid, gadget-start, RUN_STOP, and halted exit
without PDIC. Reproducing Android's complete Type-C control plane is not a
prerequisite for the remaining connector-MUX discriminator. The selected H0
shape is now custom-65:

1. keep the P3.15 61-module base and fixed Image;
2. add the exact stock `msm-geni-se.ko`, `gpi.ko`, and `i2c-msm-geni.ko`;
3. add one purpose-built `s22plus_max77705_mux_diag.ko` and load no stock or
   custom MFD/PDIC/SPU module;
4. bind that module directly to the otherwise-unbound
   `max77705@66` I2C client via `compatible="maxim,max77705"`;
5. create only the USBC/MUIC dummy client at `0x25`, read and validate PMIC
   identity, perform one pre `CONTROL1_R`, conditionally perform exactly one
   non-retried `CONTROL1_W(0x09)`, perform immediate post1 `CONTROL1_R`, hold
   one exact 30-second MUX retention/correlation interval, and perform terminal
   post2 `CONTROL1_R`; and
6. retain the complete cached result through one read-only 0444 interface and
   the Process-v2 carrier/USB-sidecar correlation.

The command protocol is source-real: UIC interrupt `0x02` carries
`APCmdResI=BIT(7)`, AP output occupies `0x21..0x41`, AP response begins at
`0x51`, and `CONTROL1_R/W` are `0x05/0x06`. Because no other Max77705 driver
is loaded, the bounded read-to-clear UIC polling has no competing Linux
consumer. The registered transaction contains three read commands and at most
one conditional write; firmware, reset, IRQ, MFD-child, power, notifier,
CC/PD/MUIC/AFC/alternate, and writable user-control effects are excluded.
The diagnostic is loaded only after the gadget path and host sidecar are
ready, so its bounded probe dwell overlaps the declared host-correlation
interval without adding a workqueue or writable trigger.

The diagnostic source and linked module now exist as H0 artifacts. The exact
source validator, two same-path clean builds, linked ELF/relocation audit,
modversion audit, CFI callback audit, and independent audit-mode replay all
pass. This is not a runtime or packaging claim. Remaining gates are exact
target-only GENI/I2C bind, no competing driver/client proof,
command/timeout/no-retry fixtures, carrier/result-matrix coverage,
host-sidecar positive control, capacity/package proof, and one proportional
independent review.

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
| `drivers/usb/typec/maxim/max77705_alternate.c` | `d6812fd27e0612d8c09a1462b9a39c4b1aee0d0eb0bc88f81611bb97e79a4228` |
| `drivers/usb/typec/maxim/max77705-muic-afc.c` | `7b8a775af9fa13f65a042a651e87b6d4cb4e5e735f43e358a5d04d89bd88e4d5` |
| `drivers/usb/typec/maxim/max77705-muic-ccic.c` | `6cdb78864ce17eb1a70c093a73fd993f62884d4eabafb0b02813eb1b0eadff80` |
| `drivers/usb/typec/manager/if_cb_manager.c` | `044b2b6aae5e9c9c042f5c9c2d5ecba53d275639057002893306b0106b554f6f` |
| `drivers/usb/dwc3/dwc3-msm-core.c` | `1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021` |
| `drivers/muic/common/muic_sysfs.c` | `eaa86d77f2ae0d8e554aa80a68a87afaba797fe63d5c8f7ae2cfff9a7b7d2f80` |
| `drivers/muic/common/muic-core.c` | `962d841eb2e8097eefc79a0769b844c168f4d21c37f7fc3d0365ae72b224eec1` |
| `drivers/usb/typec/class.c` | `992f17dc0e69f96b77d477d9e47dd4ad46e205683ade0533fbf54279e885508c` |
| `drivers/usb/typec/maxim/Makefile` | `8055a9480971e835edccb441ce0554940a1d211be5bc1d1702ebc4587580c91d` |
| `include/linux/usb/typec/maxim/max77705_usbc.h` | `1cc7e211c50685c3eed3d1b4582869d0a65a559a2114c0087fac2646f4fc883e` |
| `include/linux/usb/typec/maxim/max77705-muic.h` | `3f7f2b9790940d61ec6bb636f87fd750f7971f1c609c06e6380d11907f701cb1` |
| `include/linux/usb/typec/maxim/max77705.h` | `ff2498061ddb20c1891cb9fe6611edde655c3e1cda8fa4446d0c876a476ff1c7` |
| `drivers/i2c/i2c-core-base.c` | `0292f223758b3d9eb74889e986cf2e67588b97874d54bcfbf257b15a5906ffa5` |
| `drivers/i2c/busses/i2c-msm-geni.c` | `2d062f016c1481984aaf9108883a940be3907b8ca48d13031324348c68b29c7a` |
| `drivers/base/platform.c` | `3aa156b25f4acd8e327a887e209a2eaa9d8c53ef3bc4e2ba74876c1447f04569` |
| `drivers/base/dd.c` | `ce68320e68f0978f854e3c8b0fa52e7f6837c08f2fcf3417400d15fe521578d0` |
| `drivers/spu_verify/spu-sign-verify.c` | `889c37137c2beb7c6cf3d299cd8b2f0ffb9b4a5af858da8733f693d3d7bc110a` |
| g0q r12 DTS | `aff997ab764b7be8ff66d57b0633fa11c881a108f8fabea186cf5a4216844822` |
| `waipio-gki_defconfig` | `de7373038099658387dea7f2168be3c63268c554c645067e255492cb836276c7` |
| fixed P3.10-derived `.config` | `6adf58c7204695e6f5a8deaf0f5995bca91a79ce4cc5f7b74e7b247128e0673b` |
| tracked super module inventory | `5ad69e151efbe48ba0348608120da3001f9e11d481b13a498177e080771c6d37` |
| tracked `vendor_dlkm/modules.load` identity (5,843 bytes) | `8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360` |
| streamed Gate 0 result | `f24d593219dd775d51230b7b271a90fd67f14a1ab360ca060fb64e33e90d6241` |
| recovered 67-module order audit | `5c64cbe9dc4f8c6569248b8c8e9affb3d7f721a3854f4aa2c93a238b32c7241a` |
| exact 441-module vendor-ramdisk inventory | `35f1a7b903fc3582d3d51c4f119b993d154874e632465b2e212e0bf56a37ab7b` |
| exact 63,974,144-byte expanded vendor-ramdisk CPIO | `a96c362103eeab52fd639fd1bfc06d5f9a30972a18d8086c26d20a86a0309afd` |
| Max77705 custom-surface authority helper v3 | `a7b93309561550bb0c1389375c309024b30d832d54cc0b9b0986fb1ae5bb640d` |
| private 491-module/custom-65 receipt | `22a873e71677be9b5d7a6f02266c0614bd83cfcf210916bf3eb8470ec23a0808` |
| registered custom-65 diagnostic contract | `8ec62cd19d033f93336ebc83b8fa245b522c008835527a55c9bfff09e80819f5` |
| implemented diagnostic source (11,470 bytes) | `2cdc1e58bc77d804f61cd7e5e4efeb1bfa6fd285b7e7160b6d834cc9dc741f24` |
| diagnostic external-module Makefile | `fd9878269e29f517f685ed8643682190419ab537eefaf1a930a1196409dea1ab` |
| exact-ABI A/B build and linked-audit helper | `2e226da99b90ed914d99f5ebed34424dae3223f0b629b5f7a76a97569bb8bea9` |
| A/B linked-build receipt (19,492 bytes) | `5ea484ae1381b23c42c71163a8bb5add2e54f8b936e7730aee7b87e6a8ffeadd` |
| independent audit-mode replay receipt | `ce6a1310d1d07b9b6733e4129fecdc41dd4d2bb3ff03247fbe8df2fe9019894b` |
| A/B diagnostic module (293,400 bytes each) | `4f4f485a35cdb12206b814390b56674ca6a6d691c9a1d7a29c97030053231849` |
| custom-surface authority helper v10 plus P3.16 closure pins | `a59c68b8f9c4d92f3914555bc6e2b16d07acc309b08b12292ebcee527d91c4bd` |
| linked-qualified custom-surface receipt v10 | `2da2f53c981440663a1626024125bcced789872f664b0f4c59b7b07b14ecc339` |
| Max77705 retained-envelope v2 encoder | `812fabbc6e269ba8ac0167b910b77ac0a367b8c56f33d432c2b8de12a694054b` |
| Max77705 Carrier-v2 decoder policy v2 | `18263bf199436898fb2f8cdc25de15891b65974ea50305dae4c5bcbd6de03ae7` |
| allocation-free PID1 result parser | `8c02d0e9e55aed5dcea65d0ced830ba03985886517c73774cec7f2cf9cc1da4c` |
| PID1 parser host C fixture | `3093151c9f613ed781a9c7fa00efcede4148f061bb25e30c8c992cbd789d9f92` |
| PID1 parser executable audit source | `5d2b0e504f1850093ece544c9e05cb27a71ef79a3b94363f03a7691b3cb65bce` |
| PID1 parser private receipt | `692325e9e16a600b8ca8f62d3196d8304a3dab24301f26a266096ec0288ff209` |
| request-v3 checkpoint transform | `0cd6a7c0f02148125b9891efa9918ffbf5aea131c3ffec84fcd0f4bfe3bc3edd` |
| actual C request-v3 fixture | `a6a2184b9a292353cc4d31c3f647c95b9bfeb870db23d1c46848fe4a00c80ccf` |
| real Process-v2 adapter fixture | `57128106dd0ee43313dea9d1e66592742badeeba6c278ad95b4fc418f8504b92` |
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
| bounded sparse/range extraction and exact second-stage file | `workspace/private/outputs/s22plus_fyg8_max77705_gate0/order-authority-20260811-01/result.json` and `modules.load`, hash-pinned above |
| 67-name stage, position, and dependency-order audit | `workspace/private/outputs/s22plus_fyg8_max77705_gate0/order-authority-20260811-01/max77705-67-order-audit.json`, hash-pinned above |
| all-stock export-consumer audit, full-PDIC rejection evidence, linked-qualified custom-65 diagnostic, and parser receipt gate | `workspace/private/outputs/s22plus_fyg8_max77705_gate0/custom-surface-authority-20260812-15.json`, hash-pinned above |
| actual PID1 parser, Python-summary parity, mutation rejection, and pinned AArch64 compile | `workspace/private/outputs/s22plus_fyg8_max77705_gate0/runtime-parser-20260812-01.json`, hash-pinned above |
| exact P3.10 ABI A/B build plus precompile-source/CFI/modversion/import/relocation audit | `workspace/private/outputs/s22plus_fyg8_max77705_gate0/custom-module-build-20260812-07/build-audit.json`, hash-pinned above |
| strict allocation-free module-result grammar and poll summary | `workspace/public/src/native-init/s22plus_fyg8_max77705_result_parser.inc.c`, hash-pinned above |
| actual host execution plus pinned AArch64 freestanding compile | `workspace/public/src/scripts/revalidation/s22plus_fyg8_max77705_runtime_parser_fixture.py`, hash-pinned above |
| PDIC, MFD, SPU, GENI-I2C, GPI, and GENI-SE dependency edges | pinned `modules.dep:91`, `:176`, `:181`, `:235`, `:305`, `:388` |
| switch bit layout and the values that evaluate to `COM_OPEN=0x3f`, `COM_USB=0x09` | `include/linux/usb/typec/maxim/max77705-muic.h:293-301`, `:359-405` |
| `CONTROL1` write construction and software-only previous-state assumption | `drivers/usb/typec/maxim/max77705-muic.c:326-349`, `:437-464` |
| initial cable detection during MUIC probe | `drivers/usb/typec/maxim/max77705-muic.c:2484-2644` |
| read failure leaves destination unchanged and parent state is zero-allocated | `drivers/mfd/maxim/max77705.c:127-165`, `:1219-1226` |
| overwritten first firmware-version read and exact first-pass error condition | `drivers/mfd/maxim/max77705.c:879-902` |
| zero-initialized charger-detail inputs and first-pass voltage/TA guards, ignored charger-status errno, and pre-write boundary | `drivers/mfd/maxim/max77705.c:847-849`, `:915-1009` |
| retry counters, IC reset, and guard-bypassing retry edges | `drivers/mfd/maxim/max77705.c:1016-1054` |
| void firmware-setting wrapper discards updater status | `drivers/mfd/maxim/max77705.c:1157-1182` |
| PASS5 value and updater dispatch | `include/linux/mfd/max77705-private.h:42-48`, `drivers/mfd/maxim/max77705.c:1167-1179` |
| parent updater before IRQ init and MFD child creation | `drivers/mfd/maxim/max77705.c:1311-1349` |
| exact three compiled MFD cells and module-only child drivers | `drivers/mfd/maxim/max77705.c:98-121`, `arch/arm64/configs/vendor/waipio-gki_defconfig:1095`, `:1153`, `:1165-1168`, `:1201-1204` |
| parent IRQ GPIO, masks, nested IRQs, and charger/USBC top-mask behavior | `drivers/mfd/maxim/max77705-irq.c:408-515` |
| automatic-VBUS disable and audio-enable opcode initialization | `drivers/usb/typec/maxim/max77705_usbc.c:1652-1663` |
| broad PDIC probe order and final USBC unmask | `drivers/usb/typec/maxim/max77705_usbc.c:3663-3913` |
| common sysfs firmware-update worker/imports and misc firmware callback | `drivers/usb/typec/maxim/max77705_usbc.c:573-707`, `:955-1027`, `:1343-1422`, `:3814-3868` |
| distinct parent-local `fw_update` CONTROL1 interface | `drivers/usb/typec/maxim/max77705_usbc.c:1562-1629`, `:3707-3713` |
| common PDIC property filtering and CHIP_NAME read-only special case | `drivers/usb/typec/common/pdic_core.c:105-126`, `drivers/usb/typec/common/pdic_sysfs.c:47-150` |
| `/dev/ccic_misc` and `/dev/pdic_fwupdate` registrations | `drivers/usb/typec/common/pdic_misc.c:635-703` |
| linked raw Max77705 debug misc/sysfs surface | `drivers/usb/typec/maxim/Makefile:5-10`, `drivers/usb/typec/maxim/max77705_debug.c:373-507` |
| PD workqueue/IRQs and boot-time RID, IBUS, sink-capability, data-role, and short checks | `drivers/usb/typec/maxim/max77705_pd.c:1878-1984` |
| command-data copies and FIFO append/dequeue semantics | `drivers/usb/typec/maxim/max77705_usbc.c:1747-1828` |
| command/response pair construction and command dispatch | `drivers/usb/typec/maxim/max77705_usbc.c:2410-2554` |
| exact UIC latch bit assignments (`APCmdResI=0x80`, detection mask `0x7b`, DCD/charger-type subset `0x0a`) | `include/linux/usb/typec/maxim/max77705.h:102-110` |
| direct parent OF match and USBC/MUIC dummy-client precedent | `drivers/mfd/maxim/max77705.c:1311-1316`, `:1391-1397`, `:1454-1476` |
| I2C OF match and exported managed dummy-client helper | `drivers/i2c/i2c-core-base.c:95-116`, `:1034-1064` |
| UIC/AP command registers and response bit | `include/linux/mfd/max77705-private.h:172-190`, `:192-226`; `include/linux/usb/typec/maxim/max77705.h:101-110`, `:508-517` |
| broad alternate-mode, AFC/QC, and CCIC-notifier linked surfaces | `drivers/usb/typec/maxim/max77705_alternate.c`, `drivers/usb/typec/maxim/max77705-muic-afc.c`, `drivers/usb/typec/maxim/max77705-muic-ccic.c`, all hash-pinned above |
| MUIC object inclusion in `pdic_max77705.ko` | `drivers/usb/typec/maxim/Makefile:5-10` |
| target g0q Max77705 node and `support-audio` property | `arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts:11624-11634` |
| platform `driver_override` precedence over OF matching | `drivers/base/platform.c:1150-1161` |
| pinctrl binding occurs after match but before probe | `drivers/base/dd.c:520-541` |
| I2C registration synchronously probes every matching unbound client before return | `drivers/i2c/i2c-core-base.c:1790-1815`; `include/linux/device/driver.h:33-48` |
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
| plan/artifact fact | P3.15 omitted the six-entry stock GENI/Max77705 producer closure; all six stock payloads and the P3.15 61-module base are recoverable; the stock 67 names split exactly into 37 first-stage and 30 `vendor_dlkm` names; the exact 356-line second-stage order is recovered; the proposed stock sequence has zero forward dependency edges; and the complete 491-name stock union makes PDIC the sole consumer of the removable updater exports | loadability or linked correctness of custom successor modules |
| retained-evidence fact | the combined retained log contains two XBL MUIC-init blocks that touch opcodes `0x06` and `0x05`, one explicitly followed by Odin `SetPath: 1`, while one stock Linux boot read `6E.00` and skipped update | the XBL write payload, returned `CONTROL1` value, exact provenance of the second bootloader block beyond its non-Odin context, or value inherited at Linux probe |
| hazard fact | every PASS5 MFD probe invokes the updater; valid PC-VBUS first-pass state exits before firmware writes, but updateward read-failure defaults and guard-free retries prevent structural nonreachability; PDIC probe performs broad control-plane initialization | that the firmware-write branch would occur in a successor, or that stock-equivalent invocation is disallowed |
| causal inference | an open/non-USB `CONTROL1` state is compatible with controller-side success plus complete host silence | that it caused P3.15 |
| successor feasibility | fixed-Image stock-67 remains source-supported; the full-PDIC custom-66 shape is rejected as disproportionate; direct-polling custom-65 is source-supported and machine-registered | diagnostic implementation and linked proof, qualification, independent review, D0 inventory, or live authority |

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
plan. The stock path uses all six stock additions. The selected diagnostic
path instead uses the three stock GENI/GPI/I2C substrate additions and one
custom direct-I2C module, for 65 total. It opens no stock MFD, PDIC, or
`spu_verify.ko`; those vendor files remain present but unused.

The exact dependency facts are:

- `i2c-msm-geni.ko` requires `gpi.ko`, `msm-geni-se.ko`, and dependencies
  already in P3.15;
- `mfd_max77705.ko` requires `abc.ko`, `usb_notify_layer.ko`, and
  `sec_class.ko`, all already present;
- stock `pdic_max77705.ko` requires the MFD, `spu_verify.ko`, DWC3/USB helpers,
  and notifier consumers already present; and
- `spu_verify.ko` has no listed hard dependency and its module init only logs
  and returns zero. It remains required by stock PDIC's linked updater
  reference but is irrelevant to the direct diagnostic because neither MFD
  nor PDIC enters that closure.

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
inside `super.img`. The initial audit had only its tracked 5,843-byte identity,
SHA-256
`8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360`,
not its line order. At that time only 4,246,401,024 bytes were available, so an
ordinary full extraction was unsafe.

The exact S22+ cleanup closed that capacity blocker without deleting an
authority input. Gate 0 then used
`s22plus_fyg8_vendor_dlkm_order_gate.py` to authenticate the
9,680,091,538-byte firmware ZIP, stream the AP tar's 8,875,694,170-byte
`super.img.lz4` member, validate the complete 10,352,130,812-byte sparse super
and 12,475,957,248-byte logical raw-super identities, and materialize only the
57,610,240-byte `vendor_dlkm` extent at raw offset 10,367,270,912. The extent
matched SHA-256
`e5386d68ccf9ad1a12cfa4cf447e704bddcef94b0442e61765f3dba580186b26`.
F2FS inode 144 then yielded exactly 5,843 bytes, 356 unique newline-terminated
module names, and the expected `modules.load` SHA-256. The operation required
57,610,240 output bytes plus an explicit 1,073,741,824-byte margin and published
its private result directory only after every identity passed.

The proposed 67 names were also compared across the two normal-load
authorities rather than only against themselves:

- 37 names occur in the vendor-ramdisk first-stage `modules.load` and have no
  row in the tracked `vendor_dlkm` inventory;
- the other 30 names have a tracked `vendor_dlkm` row and do not occur in the
  first-stage list;
- all 30 of those rows match the expected size and SHA-256 from the P3.15
  artifact/six-module vendor-ramdisk extraction and carry
  `reference_status=byte-identical`; and
- the overlap and uncovered sets are both empty.

Thus the proposed byte set is not inferred from two copies of the same list:
it is an exact 37/30 carrier partition backed by the hash-pinned P3.15 artifact,
vendor ramdisk, and tracked super inventory. At the initial audit boundary,
Gate 0 remained necessary for the missing order of the 30 second-stage names,
not for their identities.

That last sentence records the initial audit boundary; the streaming Gate 0
continuation has now closed it. The 30 selected second-stage names all occur
exactly once in the recovered 356-line file. The six additions occur at these
stock-order locations: `msm-geni-se.ko` is first-stage line 132; `gpi.ko`,
`i2c-msm-geni.ko`, `mfd_max77705.ko`, `pdic_max77705.ko`, and `spu_verify.ko`
are second-stage lines 32, 145, 261, 265, and 291 respectively.

The Android lists are stage/priority authority, not a direct `finit_module`
recipe. The 140-line first-stage and 446-line recovery files each contain the
same five duplicated names and have 135 and 441 unique names respectively;
the recovered second-stage file is unique. Within the selected 67-name set,
concatenating first-stage first occurrences and second-stage order creates 126
forward dependency edges because Android's loader resolves dependencies. The
native-init direct-loader sequence instead preserves the qualified P3.15
61-module order and appends:

```text
msm-geni-se.ko
gpi.ko
i2c-msm-geni.ko
spu_verify.ko
mfd_max77705.ko
pdic_max77705.ko
```

The exact `modules.dep` graph proves that sequence has zero missing selected
dependencies and zero dependency-after-consumer edges. The sequence hash is
`f95799b175e81283cab834282c1166e3d5664a21bfa322f5844f48442191a8a3`.
This closes order arithmetic, not the runtime override/bind timing that must
surround the GENI-I2C/MFD/PDIC loads.

Before the host extractor closed Gate 0, a live read-only alternative would
have been self-authenticating at the artifact boundary. An exact-target D0
capture of only
`/vendor_dlkm/lib/modules/modules.load` is acceptable only if it returns
exactly 5,843 bytes and hashes to
`8411620a0384d07fed491a2f8f7c146e354d022c8446940fc59f49cb2d98d360`.
Any length/hash mismatch stops the order claim. The tracked identity makes
the captured bytes comparable to the pinned firmware; it does not itself
authorize the D0 or waive exact-target and read-only requirements. That D0 is
no longer needed because the pinned host artifact supplied the exact bytes.

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

### Named subhazard: updateward read-failure defaulting

The updater contains two manifestations of the same failure direction:

1. the parent object is zero-allocated, a failed firmware-major read leaves
   `FW_Revision` at zero, and the following minor read overwrites the first
   errno; zero is then classified as older firmware; and
2. `chgin_dtls` and `wcin_dtls` are initialized to zero, both charger-status
   read returns are ignored, and zero/zero is classified as battery-only
   rather than TA mode.

Both defaults point toward entering or continuing the firmware-update path.
They are therefore one source-level class,
`MAX77705_FIRMWARE_UPDATEWARD_READ_FAILURE_DEFAULTING`, rather than two
unrelated local mistakes. The class is a reachability bias, not a claim that
all remaining voltage, product, secure-mode, or record-write conditions have
been satisfied.

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

### Retry removes the first-pass guards

The read-error, voltage, and TA guards all test
`try_count == 0 && try_command == 0`. The two retry edges increment one of
those counters, call `max77705_reset_ic()`, sleep for one second, and jump to
`retry`. Every subsequent pass therefore masks the interrupts again but skips
both the voltage guard and the TA-mode guard. The secure-mode and verify
counters are each bounded by ten attempts, so this is bounded active behavior,
not an infinite loop; it can nevertheless reset the IC repeatedly and reach
firmware records without re-establishing the first-pass power predicates.

The named updateward read-failure-defaulting class and this retry geometry are
complementary reasons not to import the stock/full MFD/PDIC stack into a narrow
discriminator. The first makes failed I/O lean toward the active branch; the
second means a retry does not re-establish the initial power guards. The mere
existence of a stock updater call is not the reason. Whether stock-equivalent
risk is admissible remains an explicit independent review decision rather
than a conclusion smuggled into this H0 report.

The status boundary is also closed in the wrong direction:
`max77705_usbc_fw_setting()` is `void`, discards the integer return from
`max77705_usbc_fw_update()`, and the parent probe proceeds to IRQ and child
creation. Thus neither the lost first-read error nor a later updater failure
can be propagated through the parent probe call site.

### Rejected bounded custom-MFD intermediate

An earlier intermediate proposed preventing the parent probe's boot-time call
from entering `max77705_usbc_fw_update()`. That reduces updater risk but does
not reduce the rest of the MFD/PDIC control plane and is no longer selected.

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

### Full-stock linked surface and rejected full-PDIC custom-66 contract

This subsection preserves the source audit that rejected the former design.
Its removal claims are valid facts about what a custom MFD/PDIC pair could
omit; they are not current implementation requirements. The selected design
below bypasses both modules entirely.

The updater ABI can now be removed rather than retained as a stub. A bounded
host audit scanned every unique stock module payload name in the two normal
module stores:

```text
exact vendor_ramdisk module corpus       441
exact vendor_dlkm module corpus          356
byte-identical overlap                   306
vendor_dlkm-only payloads                 50
unique stock union                       491
```

The audit expanded the hash-pinned 63,974,144-byte vendor-ramdisk CPIO only
inside a temporary directory, checked all 441 files against the tracked exact
inventory, and extracted only the 50 `vendor_dlkm`-only inodes from the
already authenticated F2FS image. The 306 common names inherit the existing
byte-identical corpus proof. This is the complete absence-search scope; the
earlier seven preserved `.ko` files under `vendor/extract/lib/modules` alone
were not treated as a stock-union authority.

Across those 491 unique modules, each of these MFD exports has exactly one
consumer, `pdic_max77705.ko`:

```text
BOOT_FLASH_FW_PASS2
max77705_usbc_fw_setting
max77705_usbc_fw_update
```

The former custom pair could therefore remove all three exports, the
53,055-byte linked firmware payload, the parent firmware response workqueue,
and the PDIC imports together. `spu_verify.ko` is required only by the stock
PDIC update path, so it also leaves the former closure:

```text
P3.15 base 61
  + msm-geni-se.ko
  + gpi.ko
  + i2c-msm-geni.ko
  + custom mfd_max77705.ko
  + custom pdic_max77705.ko
  = rejected full-PDIC custom 66
```

This does not alter the stock comparison: stock MFD/PDIC still needs
`spu_verify.ko` and remains the separately adjudicated 67-module shape.

The rejected custom MFD source contract was:

- remove every firmware header/payload, update/reset/response helper, probe
  updater call, and exported updater symbol;
- preserve bin-version reporting only by calling `store_ccic_bin_version()`
  with the pinned PASS5 bytes `6e 40 15` and `sw_boot=0`, without hardware I/O;
  and
- retain the ordinary dummy clients, IRQ initialization, and MFD child
  creation unchanged unless a later complete write-inventory review says
  otherwise.

The stock PDIC exposes more writable entry points than the earlier report
listed. They are separate mechanisms, not one sysfs alias:

1. the common PDIC `fw_update` property and worker can call
   `request_firmware()`, SPU verification, and the MFD updater;
2. `/dev/pdic_fwupdate` feeds arbitrary firmware bytes to the registered
   firmware callback;
3. `/dev/ccic_misc` exposes UVDM/PPS control callbacks;
4. the parent-local attribute also named `fw_update` is a distinct
   `CONTROL1` debug read/write path; and
5. `CONFIG_CCIC_MAX77705_DEBUG=y` links `max77705_debug.o`, whose
   `/dev/mxim_dev` and `mxim/debug0` `reg`/`opcode` surfaces perform raw I2C
   register or opcode operations.

Those five surfaces were not exhaustive. The stock linked PDIC also creates a
separate Max77705 MUIC attribute group on `switch_device` with seven writable
attributes: `uart_sel`, `usb_sel`, `uart_en`, `otg_test`, `apo_factory`,
`afc_disable`, and `hiccup` (`max77705-muic.c:1054-1098,2552-2555`). The
former custom contract removed that entire group. The similarly named
common-MUIC sysfs helper is not a second active group for this path:
`muic_sysfs_init()` has no C call site outside its own definition and the
stock linked PDIC imports neither `muic_sysfs_init` nor
`muic_sysfs_deinit`.

The Type-C class is another independent mutation surface. Stock PDIC supplies
`max77705_dr_set`, `max77705_pr_set`, and `max77705_port_type_set` through
`max77705_ops` (`max77705_usbc.c:421-553,3762-3769`). The custom contract
keeps `typec_register_port()` and the natural-attach reporting calls
`typec_set_*`/partner register/unregister, but assigns
`typec_cap.ops = NULL`. The pinned Type-C class then makes the data-role and
power-role attributes read-only and hides `port_type`; it does not suppress
driver-originated attach reporting.

The complete IF-callback consumer audit adds one deliberate exception to the
removal rule. Across the exact 491-module union:

| IF-callback export | Exact stock consumer | P3.15/custom disposition |
|---|---|---|
| `register_usb` | `dwc3-msm.ko` | retained; P3.15 contains DWC3 |
| `register_muic` | `pdic_max77705.ko` | retained with `muic_d.ops = NULL` |
| `register_usbpd` | `pdic_max77705.ko` | retained |
| `usbpd_set_host_on` | `dwc3-msm.ko` | retained |
| `usbpd_wait_entermode` | `lvstest.ko` | nulled; `lvstest.ko` is absent from P3.15 |
| `usb_set_vbus_current` | `pdic_max77705.ko` | call may occur, but the fixed linked DWC3 supplies no USB ops callback |
| `usbpd_sbu_test_read`, `usbpd_cc_control_command`, `muic_check_usb_killer`, `muic_set_bc12` | none | nulled/unavailable |

`usbpd_set_host_on` is not a Type-C role-forcing writer. Its pinned body only
updates `device_add`, `detach_done_wait`, and `host_turn_on_event`, plus one
waitqueue wake (`max77705_usbc.c:3621-3639`). DWC3 calls it after host
start/stop (`dwc3-msm-core.c:6596-6604`), so deleting it would introduce a
second behavioral change. The custom `usbpd_ops` table must therefore retain
only that state/wakeup callback and explicitly null the SBU, CC-control, and
enter-mode fields. The fixed `dwc3-msm.ko` still imports `register_usb` but
defines neither `ops_usb` nor `restart_usb_host_mode`; its zero-allocated
`usb_d.ops` remains null. Consequently the PDIC-side
`usb_set_vbus_current(..., USB_CURRENT_CLEAR)` call has no effective callback
endpoint in this fixed closure, rather than being an untracked VBUS writer.

The rejected custom PDIC contract would remove the five original
firmware/debug/misc surfaces, the Max77705 MUIC attribute group, the Type-C
role-mutation operations, the external `sec_pd` mutation function pointers,
and unused IF-callback operations. It presents only read-only
`PDIC_SYSFS_PROP_CHIP_NAME` through `pdic_core_register_chip()`, while normal
MUIC, CC, PD, notifier, initial-detect, natural-attach reporting, the
state-only `usbpd_set_host_on`, and the separately tagged read-only MUX
observer remain in scope. Keeping `pdic_core_register_chip()` is intentional
because the manager's alternate-mode callback still uses the registered chip
object.

The v1 custom-66 receipt remains historical rejection evidence. Completing
its conditional initial-detect and runtime write matrix would be required only
to revive that broader design. It is not a gate for the selected diagnostic.

### Selected direct-polling custom-65 contract

The exact MFD source demonstrates that the `max77705@66` OF client normally
matches an I2C driver with `compatible="maxim,max77705"` and creates a dummy
USBC/MUIC client at `(0x4a >> 1) = 0x25`. The I2C core matches OF clients
before ID-table fallback and exports `devm_i2c_new_dummy_device()`. With stock
MFD and PDIC absent, one custom module can own that client directly and create
only the `0x25` dummy. The implemented probe additionally rejects any parent
whose seven-bit address is not exactly `0x66` before taking its one-shot claim.
The hash-pinned stock log reports raw `pmic_id:15, pmic_rev:2`; the pinned
revision table maps exactly `(0x15, 0x02 & 0x07)` to logical PASS5. Those are
the implemented identity values, not an inference from the later logical
`device found: rev:5 ver:0` message.

The pinned command ABI is complete enough for a bounded polling transaction:

```text
UIC_INT              0x02
APCmdResI            BIT(7)
AP_DATAOUT0..END     0x21..0x41
AP_DATAIN0           0x51
CONTROL1_R/W         0x05 / 0x06
full COM_USB byte    0x09
```

The selected source contract permits exactly this sequence:

1. validate PMIC identity on the parent client;
2. read and consume the full otherwise-unowned UIC latch once, retaining its
   raw byte;
3. issue one `CONTROL1_R`, poll `APCmdResI` under a compile-time bound, and
   require a matching `0x05` response plus one value byte;
4. if and only if pre is not `0x09`, issue one `CONTROL1_W(0x09)`, require a
   matching `0x06` response, and never retry an ambiguous write;
5. issue immediate post1 `CONTROL1_R` under the same validation;
6. hold an exact 30-second retention/correlation interval while the already
   armed gadget path and host sidecar remain active, without another MUX write;
7. issue terminal post2 `CONTROL1_R` under the same validation; and
8. publish only cached fields through one read-only 0444 result parameter.

The PMIC compatibility check follows the stock MFD rule: compare ID `0x15`
and only `PMICREV[2:0] == 0x02`, while retaining the complete raw revision byte
so `PMICREV[7:3]` remains evidence. The terminal encoder finishes every cached
byte before `smp_store_release()` publishes readiness; the getter performs the
paired `smp_load_acquire()` and returns `-EAGAIN` until publication. This is a
source requirement, not only a runtime convention: module-parameter sysfs is
created before `do_init_module()`, so a reader can otherwise overlap the
blocking probe and observe an initial or torn value.

`-EAGAIN` is therefore a readiness observation, not a self-sufficient terminal
classification. The retained record must cross it with loader state and exact
pre/post binding witnesses: exact-parent presence and owner, matching-unbound
and wrong-address-compatible parent counts, diagnostic-bound parent count, and
exact-adapter/foreign `0x25` client counts. A loader still inside
`finit_module()` is bounded continuation; zero matches, wrong-address matches,
and another driver owning the exact parent are distinct no-proof results; an
exact unbound parent or a complete diagnostic-parent/sole-dummy binding paired
with post-return `-EAGAIN` is a synchronous probe or publication
contradiction. Force-synchronous registration does not prove entry into this
driver's `probe()`: supplier, pinctrl, DMA, or driver-sysfs setup can fail in
driver core first. Therefore an exact parent that remains unbound after
synchronous return is classified as pre-probe/probe-reachability failure, not
as a kernel-semantics violation. A post-return claim-busy `EAGAIN` is not an
observable no-match branch at all: the first successful claim path caches even
dummy-client failure and returns zero before registration completes.

The v10 arming gate consequently separates two proof directions. Each of the
six observable `EAGAIN` rows must have at least one unique retained-vector
preimage that decodes to that row, while claim-busy is a negative invariant
whose decoder preimage must be empty and whose encoder acceptance is a hard
error. The local row-admission rule accepts a separate row only when it is
source-reachable or a required negative invariant, changes safety, causal
interpretation, or next action, and is distinguishable in retained evidence.
This is a Max77705 design discipline, not a new common Process-v2 gate.

It requests no IRQ, creates no workqueue or MFD child, registers no Type-C,
MUIC, IF-manager, notifier, power-supply, misc, debug, proc, or writable sysfs
surface, and contains no firmware, reset, BC/DCD, CC/PD, VBUS, sink-capability,
audio, alternate-mode/VDM/Dex, AFC, or QC path. Reading UIC_INT consumes the
whole read-to-clear byte, not only `APCmdResI`; the accepted discarded latch
set includes `SYSMsgI`, `VBUSDetI`, `VbADCI`, `DCDTmoI`, `CHGTypI`, and
`UIDADCI`. The source must retain every returned UIC byte, and this effect is
safe from Linux-consumer theft only under the enforced condition that no other
Max77705 driver is bound or loaded.

The v10 helper registers and tests this source shape and requires the exact
linked-build receipt. Its current receipt is
`custom-surface-authority-20260812-15.json`. Source, precompile validation,
A/B linked module, import/relocation closure, and fixed-Image modversion/CFI
proof are satisfied. Boot staging, runtime binding, timeout/result fixtures,
host-sidecar positive control, and independent review remain open. Carrier
geometry, actual C request-v3 publication, and real Process-v2 adapter
round-trip are now closed separately below.

The publisher fixture host-compiles and executes the transformed full P3.15
checkpoint client rather than a Python reimplementation. It emits 15 requests
and 1,500 bytes of host-only fixture output, not retained or device footprint,
whose SHA-256 is
`1200128d11c57bda9fdfa879fb3e592a1d368e0fc15a6bed255957678a136b2d`;
those bytes equal the Carrier request model exactly. The real evidence adapter
then round-trips nine terminal-bucket preimages, six observable `EAGAIN`
preimages, and five MUX-class preimages through JSON persistence, rejects an
unknown overlay, and proves the claim-busy decoder preimage empty. These tests
do not invent target sysfs names, target binding state, or package wiring.

The linked artifact first qualified under v6 supersedes the earlier H0-only v5
linked artifact; v10 reuses those exact module bytes and tightens only the host
result contract. Review found two source-contract mismatches before packaging:
v5 compared the entire
raw PMIC revision byte rather than the stock driver's low-three-bit logical
revision, and its getter could overlap result encoding because module-parameter
sysfs exists before module init completes. The correction preserves the raw
revision as evidence, uses the stock compatibility mask, publishes only a
terminal cache through release/acquire ordering, and forces synchronous probe
policy explicitly. The corrected A/B rebuild introduced no new undefined
import or linked call relocation; no device action or boot package occurred.

### Broad MFD effects retained only by the stock comparison

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
RGB, or flash cell is compiled by the pinned target fragment. The stock-67
comparison loads the parent but not the charger or fuel-gauge driver, so it
must prove those children remain unbound. The selected custom-65 diagnostic
creates no MFD cells at all.
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

The source-derived active DT composition predicted:

- three enabled QUPv3 wrapper devices;
- three enabled GPI DMA devices; and
- nine enabled GENI I2C controllers.

The exact-target D0 has now independently confirmed all 15 live devices and
made the temporary merged file unnecessary as runtime-name authority. The
private result is 16,542 bytes with SHA-256
`5adbb80d5178b709097abc2f9bcc0d597fafeab72f904057d9f44dbca18ccdcf`;
the 72,904-byte raw TSV is SHA-256
`4bfac8c987587e5b7138b5f78bf66d94567c039a49cb6c0f4f872543497d5a2a`.
The committed collector is `b28f0df99e`. Re-executing its actual parser over
the raw bytes reproduced the stored inventory byte-for-structure and verified
the raw size/hash. The exact live names are:

| class | target | exact non-target names |
|---|---|---|
| QUPv3 | `9c0000.qcom,qupv3_0_geni_se` | `8c0000.qcom,qupv3_2_geni_se`, `ac0000.qcom,qupv3_1_geni_se` |
| GPI | `900000.qcom,gpi-dma` | `800000.qcom,gpi-dma`, `a00000.qcom,gpi-dma` |
| GENI I2C | `994000.i2c` | `884000.i2c`, `888000.i2c`, `88c000.i2c`, `988000.i2c`, `990000.i2c`, `a84000.i2c`, `a90000.i2c`, `a94000.i2c` |

Every one of the 15 exposed `driver_override`, read exactly `(null)`, and was
stock-bound to the source-expected driver: `qupv3_geni_se`, `gpi_dma`, or
`i2c_geni`. All three substrate modules and all three excluded stock
MFD/PDIC/SPU modules were loaded. These are stock-state observations, not a
candidate precondition. The custom runtime must still prove that none of the
three substrate drivers is loaded before it writes the twelve sentinels.

The target chain is:

```text
9c0000 QUPv3 wrapper
  -> 900000 GPI DMA
  -> 994000 GENI I2C
  -> max77705@66
```

The exact stock adapter was `i2c-57`. It contained `57-0066/max77705`,
`57-0057/pca9481`, and stock-MFD-created dummy clients at `0x25`, `0x36`,
`0x62`, and `0x69`. It did not expose a `57-0042` client. The earlier
`fsa4480@42` statement came from generic Waipio source and is not retained as
exact FYG8 runtime authority. The four observed dummy clients independently
corroborate the source-derived stock-MFD client-creation model, but remain
stock-only geometry. The future custom geometry must distinguish the
DT-created `0x66` parent from those dummies: it may create only its registered
`0x25` client and must reject any foreign pre-existing owner or client rather
than copying the stock list.

The adapter number is not stable candidate authority. The exact GENI driver
calls `i2c_add_adapter()` (`drivers/i2c/busses/i2c-msm-geni.c:2166`). The I2C
core first accepts an `i2c` DT alias when one exists and otherwise allocates
the first available dynamic ID before naming the device `i2c-N`
(`common/drivers/i2c/i2c-core-base.c:1517-1554`). Thus `i2c-57`, `57-0066`,
and `57-0057` are scoped to the stock D0 registration context. The successor
must resolve the unique adapter whose real path descends from
`/sys/bus/platform/devices/994000.i2c/`, then require exactly one `*-0066`
client below that adapter. Its static qualification must reject a literal
`i2c-57` or `57-0066` dependency and any ambiguous adapter or client count.

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

The override proposal is not D0 and remains unauthorized. H0 may implement
and validate the target-only runtime without device contact. A standalone
connected write of these overrides on stock Android would be D1 and requires
fresh exact D1 authority and terminal-health handling, but it is not planned.
The D0 proved that all fifteen controls were already bound. The sysfs store
only replaces `pdev->driver_override` under the device lock
(`drivers/base/driver.c:34-103`, `drivers/base/platform.c:1044-1055`); it does
not unbind or reprobe an existing device. Such a D1 could prove only that the
file accepts and reads back bytes, not that a future driver registration is
suppressed. Producing the latter result on stock would first require an
out-of-scope unbind and would defeat the proposed tier boundary. If the same
transient writes execute inside the planned boot-only successor, they are part
of the enclosing F1 and must not be split out or pretested as a lower-tier D1
action. The completed bounded exact-target D0 read:

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

### Proof allocation for the narrowing boundary

| property | required authority |
|---|---|
| exact target-only override path construction, write/readback, rollback-by-reboot state machine, and terminal buckets | H0 execution of the transformed runtime and transaction fixtures |
| an override written while a platform driver is absent suppresses later matching and leaves only the unblocked target bound | pinned arm64 QEMU with multiple backed platform devices, real sysfs `driver_override`, late module registration, and clear-plus-reprobe positive controls |
| actual QUPv3/GPI/GENI binding, I2C transfer, Max77705 response, CONTROL1 retention, and host correlation | the enclosing boot-only F1 only |

The QEMU control is a required H0 gate, not an S22+ emulator. It must first
prove that every synthetic control device binds without an override, unload
the driver, write and read back blockers before the second driver
registration, then prove that only the unblocked target binds. Clearing the
blockers and using the normal bus reprobe path must bind the two controls as a
positive counterfactual. Direct driver `bind`/`unbind` sysfs shortcuts are not
accepted as the proof phase, and this result grants no device authority.

#### Current QEMU status — raw-replay schema independently qualified

The control, builder, and mutation fixtures are implemented. The pinned inputs
are Debian arm64 kernel `6.12.94`, QEMU `10.2.1`, and the signed modular
`virtio_mmio.ko`. QEMU supplies three backed `virtio-mmio` platform devices;
the control discovers all three in an initial positive pass, unloads the
module, blocks two devices, and performs the late-registration proof described
above.

Two H0 executions reached the same guest terminal transition: target
`a003a00.virtio_mmio` bound, controls `a003c00.virtio_mmio` and
`a003e00.virtio_mmio` remained blocked, clear-plus-reprobe bound both controls,
and final unload removed all three bindings. Neither execution produced a
qualified host receipt. The first observer terminated QEMU as soon as it saw
the PASS prefix and truncated the record before its newline. The bounded
repair waited for a complete record, but the second observer then rejected
the complete PL011 `CRLF` line with an LF-only anchored parser.

The earlier classification treated those as the same material failure because
they shared a terminal-framing invariant. That was too coarse under the
binding S22+ Rule 7, which identifies a material failure by the failed
invariant, input/producer contract, and causal mechanism together. Run 1 was
premature host termination on an incomplete record. Run 2 was rejection of a
complete CRLF record by the transport codec. They are distinct novel failure
signatures, so the CRLF failure retained one scoped repair and one corrected
execution. This conclusion comes from the binding target contract, not the
retired Fast-Loop text; the historical `H0 unlimited` clause is non-operative.

Runs 1 and 2 retained only their initramfs/rootfs artifacts. They did not
preserve console bytes, so neither can be replayed from durable evidence. The
observer repair therefore adopts the minimum applicable boundary already
identified by
`A90_HOST_OBSERVATION_PARSER_RECURRENCE_ANALYSIS_H0_2026-07-31.md` without
attempting that report's broader cross-target migration:

```text
exclusive byte-preserving raw capture plus chunk receipt
-> QEMU PL011 LF/CRLF codec
-> exact terminal frame parser
-> three-device semantic classifier
-> atomic PASS/FAIL decision
```

The two lost failure shapes are not represented as recovered evidence. They
are registered explicitly as synthetic representatives in
`tests/fixtures/s22plus_max77705_driver_override_qemu/replay-corpus-v1.json`:
an incomplete terminal record must remain incomplete and reject, while a
complete CRLF terminal record must decode to the exact three-device PASS. The
manifest separately references, but does not copy, the private run-03 raw and
capture hashes as the captured success member. A focused test hard-codes the
two expected classifications rather than trusting manifest labels alone.

This corpus covers only the three-device QEMU observer. It does not claim to
exercise the future 15-device candidate runtime schema. That materialized
runtime observer must add its own negative corpus before qualification; the
QEMU grammar will not be expanded speculatively to imitate a schema that does
not exist yet.

The raw file is created exclusively before decoding, every received chunk is
written and synced before use, and a separate capture receipt binds byte
length, SHA-256, monotonic chunk boundaries, and source. The codec accepts LF
and CRLF while rejecting bare CR, NUL, invalid UTF-8, incomplete terminal
records, duplicate terminal records, and malformed semantic fields. A replay
entry point requires the raw bytes and their capture receipt and invokes the
same codec, parser, and classifier as the live path. `qemu-console.log` is only
a convenience copy; the `.raw` file and capture receipt are the authority.

The first independent review did not issue `PASS_GO`. It found that the first
validator checked raw geometry but not exact receipt keys, fixed source/clock,
chunk source order, or finite nondecreasing timestamps; replay recorded rather
than required the expected manifest hash; malformed FAIL prefixes were accepted
without the guest's exact `stage=%s detail=%d` grammar; and tail collection
reopened the raw path with append mode after closing the exclusive descriptor.
The scoped repair now validates the complete receipt schema and authority hash,
parses canonical positive signed-int FAIL detail, and acquires one exclusive raw
descriptor before build/QEMU startup and keeps that same descriptor through
tail drain. No QEMU rerun is needed for these parser/schema repairs: the stricter
replay accepts the already captured run-03 raw only when bound to the documented
manifest SHA. The first re-review then found one remaining TOCTOU: replay hashed
the manifest path and reopened it for parsing. The final repair reads one
`manifest_bytes` object exactly once and performs both the expected-SHA check
and strict JSON decoding on that object; a switching-path fixture proves that a
second byte object cannot be substituted.

The final independent re-review attacked all four findings and returned:

```text
PASS_GO — S22PLUS_FYG8_MAX77705_DRIVER_OVERRIDE_QEMU_RAW_CAPTURE_REPLAY_SCHEMA_V1
```

The reviewed S22+ changed closure is exactly:

- `1024b095e8828710b29c949390fcfa25c977fee4`;
- `2867a6df8c7718623b8e9476e98b34dda1216490`;
- `17ae7a56fcc65fa170a05f11482e3166a40d7c33`; and
- `28408eecb911a7d47af13a3092546c21b97d8866`.

The review independently reproduced the manifest substitution attack, exact
schema mutations, malformed FAIL variants, and exclusive-FD ownership checks,
then replayed the actual run-03 raw to the same PASS. The qualified closure
binds guest control C SHA-256
`18441154b6893465039b8773539ddc6ddeb5413299bab16659ebf2abc6979c21`,
observer/replay SHA-256
`990cd4e793ebf2c71b7a37fd08a4826427822e5ff0eef45dd6750c9f7778e86b`,
synthetic corpus SHA-256
`c453f6533dcf522ac3ec1937d69b02ab5e615b225a5e4a2be8bb575ed3dd0af3`,
and focused test-source SHA-256
`4ff41fd612da85510e2ee864e2605750b77b91ea9f5823b2e87a49f8143a9838`.

The single corrected execution then passed with:

- exact pinned QEMU/kernel/config/module/source identities;
- run-03 host observer/replay script SHA-256
  `26ddd8842be0f683f071b546e8d2d42c40cd3b3c77192b00495cfb962a4e5cd8`;
- post-review strict validator/replay script SHA-256
  `990cd4e793ebf2c71b7a37fd08a4826427822e5ff0eef45dd6750c9f7778e86b`;
- target `a003a00.virtio_mmio`, blocked controls
  `a003c00.virtio_mmio` and `a003e00.virtio_mmio`, and active count 3;
- one complete CRLF terminal record;
- 1,463 raw bytes in 20 contiguous receive chunks, SHA-256
  `904093a5216f8bfd5408ac6e500e4809fb763124bb8fc9948bc8af5c788156f3`;
- capture-receipt SHA-256
  `d92fafd1caaa1f528c3bf52548a34a9e5c56bb4efe67f862777c6c77fc71ef7b`;
- live result SHA-256
  `3a9258add9574d2bb8e9bcd57341237809da2373972f109bc340dd1e656c020e`;
  and strict expected-manifest replay-result SHA-256
  `ba6f7132c760690b6322c92b2336158cf4951c7be9a57e49a17ba04e2dc5c413`;
  and
- an independent no-QEMU replay of those same bytes and receipt to the same
  `PASS_MAX77705_DRIVER_OVERRIDE_QEMU_HOST_ONLY` proof.

Status is now `DRIVER_OVERRIDE_QEMU_RAW_CAPTURE_REPLAY_SCHEMA_V1_QUALIFIED`.
The execution, exact replay, failure corpus, and independent review close the
generic pre-registration platform `driver_override` suppression property and
its three-device QEMU evidence schema. They do not validate the future
15-device runtime corpus, S22+ sysfs path construction, QUPv3/GPI/GENI binding,
Max77705 I2C or MUX behavior, candidate packaging, or any device authority. No
Android device command, D0/D1/F1 action, payload, or partition operation
occurred.

## GPI use must be observed rather than assumed

`geni_i2c_prepare()` reads `GENI_IF_FIFO_DISABLE_RO` on first use:

- nonzero selects `GSI_ONLY` and GSI DMA;
- zero selects `FIFO_SE_DMA` and configures the GENI FIFO path.

GSI mode requests TX and RX DMA channels from the GPI driver. FIFO mode does
not require those channels for the transfer. The dependency closure may still
load and target-bind GPI, but the result contract must record the selected I2C
mode. It must not claim that a successful Max77705 transfer proves a GPI data
path unless the hardware-selected mode was GSI.

## Direct-polling CONTROL1 pre/post1/post2 observer

### Why ordinary logs and cached state are insufficient

The normal MUIC path writes `CONTROL1` but does not read it before or after the
write. `write_vps_regs()` derives its previous switch from software state and
assumes `COM_OPEN` when there is no prior software cable. It is not hardware
readback. This is why the selected diagnostic performs its own validated
pre/post1/post2 command sequence rather than retaining normal MUIC detection.

The generic response handler reads `CONTROL1_R` data but discards ordinary
values unless the command is an update-sequence operation. A log line saying
that `COM_USB` was selected proves only source-path reach. A successful queue
call proves only that the request was enqueued.

### Readback and negative-result ceiling

The pinned Linux source proves the command and response ABI, but it does not
prove that `CONTROL1_R` senses the physical analog switch contacts. The value
may instead be firmware command state or a shadow of the latest accepted
write. Nor does the source prove that a cold `CONTROL1_W(0x09)` engages the
physical path without a preceding successful BC1.2/attach classification.
Public primary material located for related Maxim parts is not authority for
this exact IC, so it is not used to close either gap.

`COM_USB=0x09` also leaves `NoBCComp=0`, meaning BC1.2 comparison remains
enabled. Immediate post1 therefore proves only the opcode-visible state at one
instant. Terminal post2, after the exact 30-second correlation interval,
distinguishes observed late reversion from retention at two sampled times; it
still does not turn register readback into a physical contact measurement.

Consequently, host attach/enumeration is the only independent physical-path
witness in this design. Every host-silent row is non-refuting for the physical
MUX hypothesis, even when pre, post1, and post2 are all `0x09`. Such a row can
refute absence of opcode-visible `COM_USB` state, but not absence of physical
continuity or an autonomous/classification-dependent switch transition.

### Rejected queue-based observer

The PDIC probe initializes its workqueues and IRQ handlers before
`max77705_muic_probe()`. The parent USBC interrupt source remains masked until
the end of child probe.

The former full-PDIC custom-66 design proposed:

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

### Why queue tag propagation was rejected

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

That scheme requires tag propagation across every queue copy and coexists with
all ordinary PDIC commands. The direct diagnostic removes the queue entirely:
it owns the only Linux USBC/MUIC client, writes one command at a time, polls
the response bit, validates the returned opcode, and proceeds only after the
current command is terminal.

The preferred userspace boundary is one read-only cached-result interface,
for example a custom 0444 module-parameter getter. The getter must return only
the terminal cached state and must never initiate I2C. Probe publication and
the getter must use an explicit synchronization rule. Raw kmsg text alone is
not a sufficient retained authority because an observer parser defect would
again destroy the only evidence.

The exact carrier representation is now fixed as envelope v2. It preserves:

- parent identity and exact parent/MUIC bind witnesses;
- pre command issued, response-bit poll count, returned opcode, and byte;
- whether the optional write was attempted, its single-call return bucket,
  response-bit poll count, and returned opcode;
- immediate post1 command issued, response-bit poll count, returned opcode,
  and byte;
- exact retention interval and terminal post2 command, response-bit poll
  count, returned opcode, and byte;
- the raw initial UIC byte plus every poll byte whose read consumed non-AP
  latch bits;
- first failure stage, timeout, response mismatch, and ambiguous-write flags;
- proof that no stock MFD/PDIC/SPU module was opened or loaded; and
- host-side attach/enumeration correlation.

Lossless PackBits remains mandatory for a MUX-causal row. If the raw poll
vectors cannot fit losslessly, the row becomes the explicit
`result_payload_unrepresentable` no-proof terminal. Its 44-byte bounded
summary contains SHA-256 of the four concatenated vectors, per-command byte
OR, per-command first byte (`poll0`), and per-command nonzero-read count. The
remaining 32 bytes stay zero. This summary improves diagnosis but never
restores MUX causality or reconstructs the consumed read-to-clear sequence.

The summary carries four source-derived one-way checks. A retained response
witness requires `APCmdResI` in that command slot's OR; a timed-out command's
active slot forbids it; `APCmdResI` without a response witness remains possible
when the response-data read fails after the wait succeeds; and OR is zero if
and only if the nonzero count is zero. These are slot-local rules, not a global
BIT(7) assertion.

### Result matrix

| Device result | Host sidecar | Permitted interpretation |
|---|---|---|
| pre `0x3f`, post1/post2 `0x09` | exact enumeration | strong causal support that the one bounded MUX command enabled a physical path during the interval |
| pre `0x3f`, post1/post2 `0x09` | silent | opcode-visible state persisted at both samples; physical continuity and the MUX hypothesis remain unresolved |
| pre `0x09`, post1/post2 `0x09` | exact attach or enumeration | the MUX was opcode-visible as USB before the diagnostic; no MUX write occurred, so attach is not attributed to a transition |
| pre `0x09`, post1/post2 `0x09` | silent | absence of opcode-visible `COM_USB` is refuted, but physical continuity and the MUX hypothesis are not |
| pre other than `0x3f`/`0x09`, post1/post2 `0x09` | exact attach or enumeration | inherited state was classified and the only MUX write is temporally associated with an independent physical witness |
| pre other than `0x3f`/`0x09`, post1/post2 `0x09` | silent | opcode-visible transition and bounded retention proved; physical actuation remains unproved and the MUX hypothesis stays open |
| post1 `0x09`, post2 non-`0x09` | any | late opcode-visible reversion observed; no maintained-state or physical-MUX claim |
| exact pre, write skipped, post1 or post2 differs from pre | any | opcode-visible state changed autonomously or the source/runtime attribution is incomplete; no MUX conclusion |
| any pre, attempted write, post1 non-`0x09` | silent | immediate command/response/control-state failure boundary; no physical-MUX conclusion |
| any pre, attempted write, post1 non-`0x09` | exact attach or enumeration | device/host attribution contradiction; preserve both facts but make no MUX-causal claim |
| missing, duplicate, wrong-order, malformed, timeout, response-opcode mismatch, or unclassified write return | any | `NO_PROOF_OBSERVER`; no MUX conclusion |
| exact attach without completed device evidence | attach | preserve host fact, but do not invent the missing device-side transition |

When post1 is a validated `CONTROL1_R=0x09`, the decoder also crosses post2
`CONTROL1` with `poll0[post2]`. That first post2 UIC read contains the latch
accumulated since post1's final UIC read through the first post2 poll. The
source-pinned detection-bit mask is `0x7b`; its narrower
`DCDTmoI|CHGTypI` subset is `0x0a`.

| Post2 `CONTROL1` | Post2 `poll0 & 0x7b` | Permitted retention reading |
|---|---:|---|
| `0x09` | zero | quiet retention interval; weak opcode-visible maintenance evidence |
| `0x09` | nonzero | a detection latch occurred during the interval and opcode-visible `COM_USB` survived to post2 |
| non-`0x09` | nonzero | late opcode-visible reversion is correlated with a retained detection-latch event |
| non-`0x09` | zero | late opcode-visible reversion lacks a retained detection-event witness |

This second matrix proves only event presence and temporal correlation.
`CHGTypI` or `DCDTmoI` does not prove that the physical switch moved, and it
does not prove that the event caused either retention or reversion.

The `pre=0x09` rows are explicit because they are a high-value distinction and
must not fall through an else branch, but they are no longer labeled a
physical-MUX refutation. Once a write is attempted, a missing post1 or post2
command/response remains `NO_PROOF_OBSERVER`; an ambiguous write is never
retried.

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

The one custom diagnostic module was therefore built twice from the exact
FYG8 source/config/toolchain closure. The completed linked audit proves:

- byte-identical A/B module output;
- exact module name and vermagic;
- preserved exported symbol names and CRC requirements;
- CFI-compatible indirect-call types;
- no unexpected undefined symbol or dependency drift;
- linked source and final `.ko` hashes;
- correct `modinfo` dependency list;
- no exported symbol and no `alias`, `firmware`, or `softdep` metadata.

Both linked outputs are byte-identical at 293,400 bytes with SHA-256
`4f4f485a35cdb12206b814390b56674ca6a6d691c9a1d7a29c97030053231849`.
They are AArch64 relocatable ELFs with build ID
`ffdf1cece67ed6d3c4940167e0669f7ef140e15e`, exact FYG8 vermagic, 15
expected undefined imports, 16 exact modversion records including
`module_layout`, CFI jump-table relocations for both callbacks, and zero
exports. Linked call-relocation counts agree with the bounded source effect
model: three CONTROL1 transactions plus identity/latch polling require six
byte reads, one block read, two byte writes, two block writes, one dummy-client
creation, one 30-second `msleep`, and no firmware/reset/IRQ/power/notifier
call.

The first automated linked build exposed that source identity plus a linked
audit did not itself prove the declared precompile validator wiring. The
final builder therefore calls `validate_diag_source_text()` before source-tree
copy, `modules_prepare`, or module compilation and receipts both its complete
validation result and validator-function SHA-256
`0914d607dac146b4e1aec41df36a104cfaa93c3c09568171f4fe75ec9cd08c3d`.
The v10 custom-surface authority rejects a missing, changed, late, or
semantically different linked-build receipt. This was an H0 qualification
repair; neither build contacted the target or created a boot package.
The build receipt records full helper hash
`0a663733feb27ba9fb1710bfd463e0534905a7cefc9f76aec4ff1c831908bd6e`
at precompile time. The current helper hash differs because it subsequently
bound the final build receipt; the source-validator function itself remains
exactly bound by the function hash above, avoiding a circular whole-file hash
claim.

The following are not established by the module build and remain package or
runtime gates:

- exact generic-ramdisk staging under one unique selected filename;
- direct loader selection of that file while neither stock MFD nor PDIC is
  opened; and
- absence of any attempted load, alias autoload, or fallback to the stock
  vendor-ramdisk MFD/PDIC files.

The private H0 build history remains explicit. `-01` stopped before compiler
execution because the filesystem did not support the requested reflink;
`-02` stopped in host `modules_prepare` because the pinned sysroot needed
explicit LLD/compiler-rt linkage; `-03` linked cleanly but exposed the missing
precompile-validator wiring described above; `-04` closed that wiring but a
final source review found that compatible matching did not itself enforce the
exact parent address; and `-05` is the final passing build with the pre-claim
`0x66` address check. None created a boot archive or contacted a device, and
no superseded output is promoted as the selected module.

The fixed build has `CONFIG_MODULES=y`, `CONFIG_MODVERSIONS=y`, and
`CONFIG_MODULE_SIG` unset. Kernel signature enforcement therefore does not
block an exact custom-module experiment. This does not relax the harder ABI,
CFI, trimmed-export, reproducibility, or package-binding requirements above.
The primary authority for that statement is the hash-pinned, fixed
P3.10-derived `.config`, not an option's absence from
`waipio-gki_defconfig`. P3.15's successful live use of its 61 reused stock
vendor modules under the same fixed-Image line is empirical corroboration of
module loading, not a substitute for the exact configuration or a custom
module loadability proof.

### Host-capacity preflight

The initial 4,246,401,024-byte free-space observation was insufficient for an
ordinary full `super` extraction or an unqualified full-kernel build. The
subsequent exact S22+ cleanup removed 68 superseded or invalidated private
payloads accounting for 5,033,287,680 allocated bytes only after reversible
quarantine and focused regression. After the final bounded Gate 0 output was
retained and its diagnostic duplicate removed, `df -B1` reported
51,230,306,304 bytes available.

Before any extraction, module build, full-kernel build, or candidate package
starts, the successor must derive its peak simultaneous working set, add an
explicit safety margin, and prove that much space is available on the target
filesystem. A short write, ENOSPC, unexpected size, missing file, or hash
mismatch must block publication before an artifact can enter a manifest or
binding. Gate 0 demonstrated the preferred bounded shape: it streamed and
hashed the large input while retaining only the 57,610,240-byte partition
extent. That closes this extraction's capacity proof; it does not pre-authorize
a later module build or package, whose peak working set must be derived anew.

If the repository cannot produce isolated exact modules under that closure,
the build may need to invoke the full kernel build infrastructure. Even then,
the candidate must keep the fixed Image unchanged unless a separately reviewed
Image change is explicitly selected. A successful source compile alone is not
a loadability qualification.

Boot is the only permitted partition payload. The stock modules physically
remain under stock `vendor_boot` `/lib/modules`, so “replace the stock files”
is not a valid boot-only construction. The custom diagnostic must instead be
added to the generic boot ramdisk under a collision-free path such as
`/lib/modules/s22plus_max77705_mux_diag.ko`.

The P3.15 runtime currently constructs `/lib/modules/` plus the plan filename.
A successor must bind that loader input to the diagnostic path, prove the
effective-rootfs composition contains its bytes exactly once, and prove the
stock vendor MFD/PDIC/SPU paths are never opened. The inherited
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
  -> prove one unbound max77705@66 parent and no competing Max77705 driver
  -> complete and prove the inherited gadget path is active
  -> prove the exact-target host USB sidecar is armed
  -> load s22plus_max77705_mux_diag.ko
  -> its probe performs pre/optional-write/post1, blocks for exactly 30 seconds,
     and performs post2
  -> prove only the parent and one 0x25 dummy client are owned and read the
     cached terminal state
  -> correlate with the already bounded host USB sidecar
```

The stock module order remains the inherited 61 entries followed by six
dependency-ordered additions. The selected diagnostic branch has four
additions and no `spu_verify.ko`, MFD, or PDIC. The diagnostic itself has an
empty `modinfo depends` field and its complete undefined-import/modversion
surface is linked-qualified. P3.16 proves the 64-entry early load order plus one
late-only staged payload, exact stage positions, override/bind checks,
gadget/sidecar readiness, dedicated load, 30-second dwell, and result capture.
It preserves `ucsi_glink.ko` as an A/B baseline and reproduces P3.04's stale-
position-table incident as a qualification regression.

## H0 gate disposition

The gates are listed together for continuity. P3.16 closes every host-side gate;
actual device behavior remains deliberately outside H0:

0. **Host capacity, carrier, and normal-order authority — closed for this unit**
   - the bounded extractor authenticated the complete ZIP/sparse/raw/extent
     chain and recovered the exact 356-line second-stage authority;
   - the exact 37-name first-stage / 30-name `vendor_dlkm` partition, every
     selected stock module byte, and the dependency-safe stock 67-entry native
     order are bound by private receipts;
   - the complete 491-name stock-module union proves that only stock PDIC
     consumes the removable MFD updater exports; the full-PDIC custom-66 shape
     is rejected and the direct custom-65 source, linked ABI, runtime, and
     packaging are qualified;
   - vendor_boot first-stage, recovery, and vendor_dlkm second-stage orders are
     kept distinct; and
   - the general per-operation peak-space-plus-margin and short-write/hash
     fail-closed rule remains active for later build and package work.

1. **Diagnostic source and linked effect contract — closed for H0 source/ELF**
   - the exact direct I2C parent match and only one managed dummy client at
     `0x25` are implemented;
   - `validate_diag_source_text()` is exercised before the build, and the v10
     contract now rejects a missing or changed linked-build receipt;
   - source and linked relocations prove exactly three read commands and at
     most one conditional, non-retried `CONTROL1_W(0x09)`;
   - PMIC identity, the full initial UIC byte and every poll byte, UIC/AP
     register constants, bounded poll count, response-opcode checks,
     first-failure stage, the exact 30-second dwell, and cached 0444 result are
     source-bound; and
   - linked imports, exports, metadata, and calls reject every firmware/reset,
     IRQ/mask, MFD-child, MUIC/CC/PD, VBUS, alternate/AFC/QC,
     notifier/power, workqueue, exported ABI, and writable user-control
     surface.

2. **Exact module artifact — linked ABI and staging/package closed**
   - reuse the three exact stock substrate modules from the pinned vendor
     ramdisk and recheck their already confirmed identities;
   - the one diagnostic module is reproducibly built twice and linked-qualified;
   - the generic boot ramdisk stages it under one unique selected path while
     proving stock MFD, PDIC, and SPU copies are never opened;
   - linked imports/relocations/metadata, module name, vermagic, modversions,
     CFI callbacks, and exact A/B byte identity are proven;
   - dependency, stage, and package closures are recomputed and receipted.

3. **Runtime and telemetry — H0 materialization and qualification closed**
   - target-only override machinery and readback;
   - exact target adapter, parent, diagnostic, and sole `0x25` client witnesses;
   - no competing Max77705 driver, IRQ owner, or command consumer;
   - exactly one diagnostic insertion and no unload/reinsert path, because the
     in-module atomic claim suppresses reprobe only for that loaded instance;
   - selected FIFO/GSI mode;
   - gadget-path and host-sidecar readiness before late diagnostic load;
   - the inherited 20-second bind gate closes before late load; the generic
     loop contains exactly 64 early modules and must not contain the staged
     diagnostic payload;
   - one dedicated `finit_module` call owns a lifetime of at least 31 seconds,
     so the exact 30-second dwell cannot be nested in the bind-gate deadline;
   - pre-write direct fence, bounded per-command deadlines, immediate post1,
     exact 30-second retention/correlation dwell, terminal post2, response
     validation, and explicit no-retry handling for an ambiguous write;
   - time-budget proof that the bounded blocking probe and all setup/cleanup
     remain inside the candidate endpoint and guard lifetimes;
   - cached diagnostic terminal state;
   - nine separate terminal buckets for late-load failure, registered/no
     matching parent, wrong-address identity rejection, parent ownership
     conflict, cached early transaction failure, post-return `-EAGAIN`,
     result-read timeout, synchronous probe/publication contradiction, and
     unrepresentable lossless payload;
   - observer failure is never decoded alone: site, normalized error class,
     loader state, and every site-authoritative binding witness survive the
     retained representation; all 49 site/error rows have unique retained
     preimages and claim-busy has an empty decoder preimage;
   - one envelope-v2 128-byte value fills the fixed Carrier-v2 two-slot payload exactly;
     an oversized lossless poll vector becomes explicit no-proof rather than a
     truncated MUX result. The overflow form retains four poll counts, total
     raw length, SHA-256, per-command OR, poll0, nonzero count, and the fixed
     transaction/result fields, but retains no raw sequence and therefore
     cannot reconstruct the consumed UIC history;
   - post2 `CONTROL1` and post2 poll0 cross into four explicit retention rows,
     with event-presence and physical/causal interpretation ceilings retained;
   - the exact allocation-free PID1 parser accepts only the module getter's
     canonical ordered grammar, computes the same SHA-256/OR/poll0/nonzero
     summary as the Python authority, and rejects malformed or semantically
     impossible strings before any runtime classification;
   - the actual transformed C publisher emits the same 100-byte request-v3
     bytes as the Carrier model for all nine terminal and five MUX details,
     rejects out-of-family details, and leaves the inherited request-v2
     publisher byte-identical;
   - same-session exact-target stock/Download positive control before any
     candidate-side host-silence interpretation;
   - host-sidecar correlation;
   - fail-closed preservation of the interpretation ceiling: no host-silent
     readback tuple may refute physical MUX continuity;
   - carrier encoder/decoder/generation-position tests pass through the real
     Process-v2 adapter for all nine terminal buckets, all 49 observer rows,
     all five MUX result classes, and the claim-busy negative
     invariant. These are H0-closed schema and publisher proofs only; physical
     reproduction is neither required nor sufficient for the arming
     precondition;
   - target-specific override/bind runtime materialization consumes the exact
     D0 inventory, and the package/qualification paths call these validators
     directly before producing the ready bundle.

4. **Historical and safety regression**
   - S7A2 must remain a prior negative recipe result, not disappear from the
     result contract;
   - the 86-module/debug-partition path must be mechanically rejected;
   - no charger, battery, forced-host, source-VBUS, EUD, UART, generic raw-I2C
     interface, or debug path may enter the candidate closure;
   - the direct diagnostic may use only its compiled exact I2C operations; it
     must not expose them as a user-controlled raw-I2C surface;
   - the full-PDIC custom-66 design must remain rejected unless a later unit
     reopens and completes its much broader write matrix; and
   - a stock selection must instead bind the exact stock updater call,
     first-pass inputs, retry state, and terminal result to its separately
     reviewed risk disposition. It may not borrow the custom nonreachability
     claim.

Gates 1 through 4 above describe the selected custom-65 path and are now closed
for H0. A stock-67
selection instead requires a reviewed finding that
the stock-equivalent updater/control-plane risk is admissible for this exact
context; it does not inherit an approval merely because stock Android has run
the same probe.

## Required D0 gate — closed read-only

The exact D0 completed at `2026-08-11T17:36:26Z` and captured:

- exact platform device names for the three QUPv3 wrappers, three GPI devices,
  and nine enabled GENI I2C devices;
- each `driver`, `driver_override`, modalias, and current binding state;
- the target `994000.i2c` topology and existing Max77705 client path;
- current loaded state of the three substrate modules and the three excluded
  stock MFD/PDIC/SPU modules; and
- exact stock health and USB inventory.

The initial and final host snapshots were identical, contained exactly one
Android `04e8:6860` endpoint and no Download endpoint, and exact FYG8 rooted
boot health plus boot/supporting-partition identities passed. The snapshot
shell wrote nothing, performed no bind/unbind or module/service action, did
not reboot, and did not trigger Max77705 control. The ADB inventory contained
one target, and A90 command count was zero.

This closes name, file-presence, current-value, stock-owner, and live-topology
uncertainty. It does not authorize the later twelve `driver_override` writes.
Nor does the stock-bound observation waive the candidate's pre-effect rule:
the candidate must begin with the substrate modules absent, apply and read
back all twelve exact sentinels, then bind only the three target devices.

## Independent review boundary — closed for the named H0 capability

One proportional independent review was required because the successor changes
execution-critical module artifacts, introduces transient platform override
writes, and introduces one bounded direct-I2C CONTROL1 effect.

The completed review covered:

- exact diagnostic source and linked A/B outputs;
- proof that no stock MFD/PDIC/SPU module is opened and no broad control-plane
  surface survives in the diagnostic;
- platform override scope and rollback-by-reboot behavior;
- exact two-read/optional-one-write I2C inventory, polling deadline,
  response-opcode checks, read-to-clear ownership, and no-retry proof;
- direct-parent/dummy-client bind and command-order proof;
- telemetry carrier and Process-v2 adapter round trip;
- module/stage capacity and position-table regression;
- 86-module and forbidden-writer rejection; and
- unchanged boot-only transfer, rollback, and final-health machinery.

The final pass is
`PASS_P316_PROCESS_V2_CANONICAL_ARTIFACT_READY_HOST_ONLY`. It qualifies the
named capability and hashes only. It does not
authorize a run or revive P3.15.

## Stop conditions

The successor is not admissible if any of the following remains true:

- host capacity does not cover a source-derived peak extraction/build/package
  working set plus margin, or any output reports ENOSPC, a short write,
  unexpected size, or hash drift;
- stock MFD is selected without an explicit reviewed disposition of its
  stock-equivalent updater and retry hazard;
- the direct diagnostic source, exact A/B module, or modversion/CFI closure
  fails its registered contract;
- any selected stock module cannot be rematerialized from the pinned vendor
  ramdisk with the exact inventory identity;
- target-only platform narrowing cannot be proven before driver registration;
- the diagnostic gains any unregistered IRQ, child, power, firmware, reset,
  notifier, protocol, workqueue, writable-control, EUD, UART, or raw-user-I2C
  effect;
- the source or linked module permits a second/ambiguous CONTROL1 write retry;
- validated polling responses cannot be retained without relying solely on raw
  log parsing;
- the package cannot distinguish pre `0x09`, pre non-`0x09`, optional write,
  post, response mismatch, timeout, and observer failure;
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
- the combined 67 expected names were cross-checked against both normal-load
  authorities: 37 are first-stage-only in this comparison, 30 are
  `vendor_dlkm`-inventory-only, the intersection and uncovered sets are empty,
  and all 30 second-stage rows match expected size/SHA-256 with
  `reference_status=byte-identical`;
- the 140-entry first-stage and 446-entry recovery lists were counted and kept
  distinct; all 61 P3.15 modules occur in recovery order, while 36 occur in
  first-stage order;
- the bounded Gate 0 extractor authenticated the complete firmware ZIP,
  streamed `super.img.lz4`, validated the full sparse and logical raw-super
  identities, and retained only the exact `vendor_dlkm` extent;
- F2FS inode 144 yielded the exact 5,843-byte, 356-line second-stage
  `modules.load` with the already tracked SHA-256;
- the 67-order audit proved 37/30 stage partitioning, zero missing dependency
  closure, and zero forward dependency edges in the proposed native sequence;
- the same audit recorded why Android line order is not a direct-loader recipe:
  it has 126 selected dependency inversions, while first-stage and recovery
  also carry the same five duplicate names;
- the extraction preflight required 1,131,352,064 bytes including margin,
  observed 51,231,506,432 bytes available, and atomically published only after
  all identities passed;
- the source ranges in the locator map were read directly rather than inferred
  from symbol names or a parallel upstream tree;
- the exact MFD-cell conditionals were evaluated against the target fragment:
  only USBC, charger, and fuel-gauge cells compile, and all three child drivers
  are module-only;
- the hash-pinned fixed P3.10-derived `.config`, rather than defconfig absence,
  proves kernel module signatures are disabled while modversions, CFI, Full
  LTO, and trimmed-export constraints remain; the successful P3.15 stock-module
  run was retained only as empirical corroboration;
- the retained binary log markers were found in the hash-pinned file, while
  the absent opcode payload/read value was kept explicitly unresolved;
- the P3.15 USB sidecar was verified nonempty and untruncated and its private
  udev stream was confirmed to contain exact-target stock and Download-mode
  transitions before candidate silence; this was not confused with the
  zero-byte ACM observer;
- the exact 491-module linked-symbol union was also evaluated for every named
  IF-manager export: P3.15 contains `if_cb_manager` and DWC3, omits
  `lvstest`, and the fixed linked DWC3 defines no USB callback ops;
- the Max77705 MUIC writable group, Type-C mutation ops, null common-MUIC ops,
  state-only host callback, and all relevant registration/call sites were
  checked against the pinned source and linked symbols;
- the full-stack audit rejects the former custom-66 design because it retains
  IRQ/MFD-child, MUIC/CC/PD, alternate/AFC/QC, notifier, and user-control
  surfaces that are unnecessary for the MUX discriminator;
- the direct diagnostic source validator accepts only the exact parent bind,
  one `0x25` dummy client, one full-UIC-latch read, three CONTROL1 reads, one
  exact 30-second dwell, and at most one conditional non-retried CONTROL1
  write of full byte `0x09`;
- the validator proves post1 is unconditional after the optional-write block
  and post2 occurs only after the retention dwell, rejects synthesis of either
  post value, and rejects any I2C call outside the registered call multiset;
- the final builder ran that validator before any compile step, reconstructed
  the exact 166,037-member P3.10 source overlay, reproduced the fixed
  `.config`/`vmlinux.symvers`, and built byte-identical A/B modules;
- the linked audit proved exact AArch64 ELF, vermagic, 15-import/16-modversion
  closure, CFI jump-table callback relocations, registered call counts, zero
  exports, and no broad linked-effect family;
- `python3 -m unittest
  tests.test_s22plus_fyg8_max77705_custom_surface_contract` passed 30/30,
  including the exact 491-module consumer scan and negative custom-source
  and linked-receipt fixtures;
- `python3 -m unittest tests.test_s22plus_fyg8_max77705_telemetry` passed
  21/21, including 49-row observer-site/error surjectivity, nine terminal and five MUX retained
  preimages, claim-busy exclusion, the 44-byte overflow summary and tamper
  rejection, fixed-result validation for overflow and result-absent envelopes,
  all four post2-retention rows, and the real Process-v2 adapter round trip;
- `python3 -m unittest
  tests.test_s22plus_fyg8_max77705_runtime_parser` passed 1/1 by compiling and
  executing the allocation-free C parser over four valid strings and thirteen
  mutations, matching Python summaries and producing a pinned-clang AArch64
  freestanding object;
- `python3 -m unittest tests.test_s22plus_fyg8_max77705_checkpoint` passed 1/1
  by compiling and executing the transformed full C checkpoint client and
  comparing all 15 request-v3 byte strings with the Carrier model;
- `python3 -m unittest
  tests.test_s22plus_fyg8_max77705_mux_diag_build` passed 12/12, including
  precompile-validator ordering, fixed-KMI, parser, toolchain-link, and real
  linked-module audit fixtures;
- `python3 -m unittest tests.test_s22plus_fyg8_vendor_dlkm_order_gate` passed
  9/9, including the ZIP/tar/process/sparse-parser seam and multicall basename
  regression;
- `python3 -m unittest tests.test_s22plus_fyg8_max77705_order_authority`
  passed 4/4;
- `python3 -m unittest
  tests.test_s22plus_fyg8_max77705_driver_override_qemu_control` passed 21/21,
  including incomplete-marker rejection, exact LF/CRLF equivalence, bare-CR,
  NUL and invalid-UTF-8 rejection, immutable-write refusal, capture-manifest
  authority-mutation rejection, exact FAIL grammar, exact-byte replay, single
  exclusive-FD tail capture, single-object manifest hash/parse binding, and the
  named two-failure corpus;
- the single Rule-7-corrected pinned arm64 QEMU execution produced the exact
  three-device target/block/reprobe/unload PASS and committed its raw capture
  before semantic decoding; the no-QEMU replay independently returned the
  same proof from the recorded raw and capture hashes;
- final independent review reproduced the four schema/ownership attack
  classes and returned
  `PASS_GO — S22PLUS_FYG8_MAX77705_DRIVER_OVERRIDE_QEMU_RAW_CAPTURE_REPLAY_SCHEMA_V1`
  for exact closure `1024b095e8` + `2867a6df8c` + `17ae7a56fc` +
  `28408eecb9`;
- `python3 -m unittest tests.test_device_action_process_v2_docs` passed 21/21;
  and
- tracked and new-report whitespace checks passed with a terminating newline.

The transient merged-DT count is deliberately not promoted to a durable
qualification result. Its required regeneration and receipt are an explicit
successor gate above.

## P3.16 implementation and offline-ready closure

P3.16 implements the selected custom-65 shape without changing the fixed
P3.10 Image or rebuilding the kernel. The early plan contains exactly 64 stock
modules: the inherited 61 plus `msm-geni-se.ko`, `gpi.ko`, and
`i2c-msm-geni.ko`. The 293,400-byte diagnostic exists once in the generic boot
ramdisk, is forbidden from the early loop, and is opened by one dedicated late
loader only after gadget readiness, sidecar arming, twelve sentinel readbacks,
and the exact target-only binding precondition.

The host fixtures execute the materialized seams rather than Python stand-ins:

- dynamic adapter/client discovery below `994000.i2c`, including exact `0066`
  and pre/post `0025` geometry, wrong-address, duplicate, malformed, and driver
  ownership cases;
- pre/post binding construction, not only the directory scanner;
- late helper pipe-drain, reap, abort, unexpected-`wait4`, deadline, synchronous
  `finit_module`, and result-read lifecycles;
- the source-real priority `helper failure > loader deadline > result-read
  failure`; and
- the rule that result bytes may be sampled while loading but may be parsed,
  classified, or published only after the helper proves successful synchronous
  `finit_module` return.

Observer failures no longer collapse into an invented terminal. Byte 47 binds
seven observer sites to seven normalized error classes. The decoder exposes
only site-authoritative binding fields: preflight has no topology authority,
late-loader and post-topology retain only the proven pre/loader subset, and
result-policy retains the full binding witness. Module-path `openat` failure is
an observer error, while `late_finit_module_failure` is reserved for an actual
negative child result. Missing result, read failure, and deadline are distinct;
unmeasured zero-initialized post fields decode as unknown rather than absence.
The native envelope fixture executes 64 rows, comprising 49 observer rows,
nine terminal rows, five MUX rows, and one oversized-evidence row. The real
Process-v2 adapter round-trips the same authority and rejects mixed or
non-authoritative combinations.

The frozen canonical artifacts are:

| Artifact | SHA-256 |
|---|---|
| overlay intent | `7ed7530597dee0064fd76ba698aca5230e7efe079b099e9c1799b902814040b5` |
| prepackaging closure | `4068d8aefd49adb38ed12465508aefada5025a7a99efda5b19c27ca5b6c0cbf0` |
| reproducible userspace result | `a9bcfe693861d6a277a4b75ce462a94b5d02c644e9baa7eb769c8e3807e5c2bf` |
| candidate A artifact result | `567987e49cac251d44a0f0c255eb0659b3c5057ca4707cd2343342b913432f2f` |
| final qualification | `25dc4066b4e49bed0b46e100753accd515b98021783aa8e4e0918d1df6cd11dc` |
| independent static closure | `0842f1efb5a51bc05117e499a45ac65592504b46eaa6c3750537f49a9de568b5` |
| Process-v2 run manifest | `803d8c106e538302bc64c89294678e0efd9a56de96a6d8bd93e57a7e9d8f1c00` |
| canonical ready manifest | `a9fb48065d717d47b0877d96f08b7d05974ac3a6a8f7b7dea4b17ba4cab4c533` |

Candidate A and B are byte-identical: boot SHA-256 is
`7c6ee851196b7d604aff7a4ce81eba271adc52c5408de10a568b924e8c6f41c9`
and AP SHA-256 is
`59893227c4deccc107d2fc4469a882e44212e076a0c5c8e4072031b853a6c6f0`.
An independent clean-directory regeneration reproduced the intent,
prepackaging, qualification, static, boot, and AP bytes exactly. Process-v2
promotion returned its offline PASS, the private ready bundle is byte-identical
to the promoted evidence/candidate files, and a non-creating ready rehearsal
returned the same manifest hash. Final changed-closure review returned
`PASS_GO — S22PLUS_FYG8_P316_CUSTOM65_PROCESS_V2_OFFLINE_READY_CAPABILITY_V1`:
all 33 current
`SOURCE_KEYS` matched, the candidate and rollback each contained only
`boot.img.lz4`, the exact S22 profile and 1,200-second guard derivation matched,
and no A90 reference or action was present.

The final frozen-source regression ran 232 current tests: 137 Max77705,
P3.16, and documentation tests plus 95 common Process-v2 runner, evidence, and
live-observer tests. All passed. Two historical immutable-closure checks remain
expected invalidations rather than current regressions: P3.13 rejects its old
overlay intent at setup, and P3.14 rejects its old execution-overlay receipt,
because the shared `device_action_f1_live_v2.py` SOURCE_KEY changed. Their
historical intents were not rewritten to manufacture a pass.

This closure also records why the enlarged host gate was necessary. Before
source freeze, focused review found and forced repairs for a post-reap pipe
drain race, a topology fixture that had not executed the live seam, observer
site/error collapse, phase-marker leakage into terminal encoding, false binding
authority for unmeasured fields, immediate-caller input gaps, result-read and
module-open collapse, a false result-read timing invariant, and one
unexpected-`wait4` exit that failed to reap the child. Each was repaired and
executed host-side before packaging, so none consumed an attended flash.

The ready manifest says `ready-for-f1-approval`; that phrase is an artifact
state, not live authority. Creation and rehearsal both preserve
`device_contact=false`, `live_authorized=false`, and `f1_authorized=false`.
Actual GENI transfer, Max77705 command/retention behavior, physical MUX
continuity, and host attach remain unknown until one separately authorized,
attended boot-only F1. Fresh exact-target D0 preparation, a clean retained
baseline, current rollback/recovery proof, immutable live binding, and one
fresh exact approval remain mandatory.

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
   boot; valid PC-VBUS first-pass state is protective, but the named
   updateward read-failure-defaulting class and guard-free reset/retry passes
   keep the active write branch structurally reachable. Stock use is
   unadjudicated, not automatically rejected or approved.
6. PDIC load is broad Max77705 control-plane bring-up, not a passive MUX read.
7. The P3.15 base and all six stock additions are recoverable from pinned
   local firmware; Android's separate 356-line vendor_dlkm second-stage order
   and the dependency-safe 67-entry native order are now recovered and bound.
8. An exact 491-module union audit proves PDIC is the sole consumer of the
   three removable MFD updater exports, but the complete linked PDIC source
   also retains IRQ/MFD-child, MUIC/CC/PD, alternate-mode, AFC/QC, notifier,
   and user-control effects. The former full-PDIC custom-66 shape is therefore
   rejected as disproportionate rather than implemented.
9. The fixed Image can instead support a custom-65 shape: P3.15's 61 modules,
   three exact GENI/GPI/I2C substrate modules, and one direct-polling
   diagnostic bound to `max77705@66`. Its registered effect set is three
   validated reads spanning an exact 30-second retention interval plus at most
   one conditional, non-retried write of full `COM_USB=0x09`, with no stock
   MFD/PDIC/SPU load. The diagnostic source and exact P3.10-ABI A/B linked
   module are now qualified at H0.
10. CONTROL1 readback is not proven to sense physical switch contacts. A
    host-silent tuple cannot refute physical MUX continuity even when all three
    values are `0x09`; only host attach/enumeration is an independent physical
    path witness in this design.
11. The source match, command protocol, precompile validation, reproducible
    linked module, imports, modversions, CFI callbacks, bounded call surface,
    retained envelope, actual C request-v3 publisher, exact runtime topology
    and lifecycle seams, and real Process-v2 decoder path are proven. The
    exact-target D0 geometry and generic QEMU suppression/raw-replay schema are
    qualified. Sidecar positive control, deterministic packaging, independent
    static closure, Process-v2 promotion, canonical ready manifest, rehearsal,
    and changed-closure review also pass. Actual device-side binding, I2C,
    MUX, and host behavior remain live-only unknowns.

The resulting H0 state is:

```text
MUX_CAUSALITY_UNPROVEN
BASE_MODULE_BYTES_AND_SECOND_STAGE_ORDER_RECOVERED
STOCK_67_UNADJUDICATED
FULL_PDIC_CUSTOM_66_REJECTED_AS_DISPROPORTIONATE
CUSTOM_65_SOURCE_LINKED_AB_ABI_AND_D0_SYSFS_GEOMETRY_QUALIFIED
CUSTOM_65_P316_RUNTIME_TOPOLOGY_LIFECYCLE_AND_OBSERVER_QUALIFIED
CUSTOM_65_EFFECT_SET_BOOT_ONLY_PACKAGED_AND_PROCESS_V2_READY
DRIVER_OVERRIDE_QEMU_RAW_CAPTURE_REPLAY_SCHEMA_V1_QUALIFIED
LIVE_UNAUTHORIZED_DEVICE_BEHAVIOR_UNMEASURED
```
