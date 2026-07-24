# S22+ FYG8 P2.40 E2 focused readiness audit

Date: 2026-07-23 KST
Tier: H0
Status: `PASS_P240_E2_FOCUSED_READINESS_H0`
Live authority: none

## Post-Analysis Erratum (2026-07-25)

The UDC gate designed below is retired. Requiring one and only one non-dot
entry in `/sys/class/udc` conflicts with the already observed FYG8 stock
topology, where `dummy_udc.0` and `a600000.dwc3` coexist, and with the exact
candidate's `CONFIG_USB_DUMMY_HCD=y`. The correct invariant is exact
membership and identity of `a600000.dwc3`, independent of unrelated UDC
entries. See P2.58 for the full reconstruction. The source/DT/module closure
in this report remains historical evidence; the singleton predicate does not.

## Verdict

E2 is ready for one bounded host implementation unit. The exact FYG8 module
closure, a dependency-valid order that preserves the proven E1B foundation,
the platform-bind predicates, the automatic DWC3-child path, the UDC creation
path, and the compact checkpoint capacity are closed host-side.

The remaining functional unknown is intentionally live-only: whether the 59
exact stock modules bind the platform stack and publish `a600000.dwc3` under
bare PID 1. Further host-only source or web research cannot answer that
board-runtime question. The E2 candidate must answer it with retained
first-failure evidence.

This audit did not edit runtime code, build a kernel, package a candidate,
contact a device, create a Process v2 binding, or authorize F1. P2.39 is closed
healthy and its approval is consumed.

## Proven Baseline

P2.39 proved the profile-2 E1B path live:

- local procfs, sysfs, tmpfs, device-node, and child-lifecycle stages passed;
- the exact five-module watchdog sequence loaded with `finit_module() == 0`;
- all five runtime names were visible in `/proc/modules`;
- retained stage `0x35` preceded terminal success `0x3f`; and
- exact rollback and final Android/root/supporting-partition health passed.

This removes PID 1 execution, module ABI, effective vendor ramdisk, and the
checkpoint carrier from the E2 unknown set. It does not prove platform probe,
driver bind, a DWC3 child, or a UDC.

The earlier O3/O3F no-enumeration runs are not negative E2 evidence. They had
no retained internal phase and combined module loading, bind, configfs, role
forcing, UDC binding, and ACM in one candidate.

## Exact Module Closure

The existing O3 planner derives 59 modules from the exact FYG8
`modules.dep`, `modules.softdep`, stock order, blocklist, and functional roots.
Its canonical identity remains:

```text
module_count = 59
constraint_count = 210
canonical_plan_tsv_sha256 =
  a34ebbad3b5d770f133e37a450cc3007e4a84ab831788484680e88aad6b3d534
```

Blindly executing the proven E1B five-module sequence before that plan would
violate one metadata edge: `qcom_hwspinlock.ko -> smem.ko`. Prepending
`qcom_hwspinlock.ko`, then retaining the exact E1B five-module order, and then
appending the unused canonical O3 entries gives a valid E2 order:

```text
00 qcom_hwspinlock.ko
01 smem.ko
02 minidump.ko
03 qcom-scm.ko
04 qcom_wdt_core.ko
05 gh_virt_wdt.ko
06 cmd-db.ko
07 debug-regulator.ko
08 icc-debug.ko
09 iommu-logger.ko
10 phy-generic.ko
11 proxy-consumer.ko
12 gdsc-regulator.ko
13 clk-qcom.ko
14 clk-dummy.ko
15 gcc-waipio.ko
16 qcom_iommu_util.ko
17 qnoc-qos.ko
18 sec_class.ko
19 abc.ko
20 sec_debug.ko
21 secure_buffer.ko
22 qcom_ipc_logging.ko
23 qcom-pdc.ko
24 pinctrl-msm.ko
25 pinctrl-waipio.ko
26 qcom_rpmh.ko
27 clk-rpmh.ko
28 rpmh-regulator.ko
29 icc-bcm-voter.ko
30 qrtr.ko
31 socinfo.ko
32 icc-rpmh.ko
33 qnoc-waipio.ko
34 arm_smmu.ko
35 qmi_helpers.ko
36 eud.ko
37 phy-msm-ssusb-qmp.ko
38 repeater.ko
39 redriver.ko
40 usb_notify_layer.ko
41 qcom_glink.ko
42 qcom_glink_smem.ko
43 qcom_smd.ko
44 rproc_qcom_common.ko
45 pdr_interface.ko
46 pmic_glink.ko
47 switch_class.ko
48 common_muic.ko
49 vbus_notifier.ko
50 if_cb_manager.ko
51 pdic_notifier_module.ko
52 usb_typec_manager.ko
53 usb_f_ss_mon_gadget.ko
54 phy-msm-snps-hs.ko
55 phy-msm-snps-eusb2.ko
56 qc_usb_audio.ko
57 dwc3-msm.ko
58 ucsi_glink.ko
```

The reordered TSV identity is:

```text
fc8169da1036ae8ba76e81ffe6afb17d063d114735a427e858afeeaa82a2218e
```

Host recomputation found 59 unique modules, all 210 constraints satisfied,
zero selected blocklisted modules, no `modules.options` file, and no orphan
options. The exact compressed vendor ramdisk is:

```text
sha256 = 41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193
decompressed_newc_bytes = 63974144
newc_entries_without_trailer = 452
selected_modules_present = 59/59
```

None of the 59 exact ELF payloads contains a `request_firmware*` symbol string.
E2 therefore has no identified firmware-file prerequisite. The implementation
checker must still emit and independently verify every selected module's size
and SHA256 from this vendor ramdisk; this audit does not replace that manifest.

`sec_log_buf.ko` is absent and remains forbidden while the retained carrier is
active.

## Provider And Probe Chain

The source-matched Samsung archive has SHA256
`86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf`.
Its probe paths establish the reason for the first five bind gates:

1. `qcom_hwspinlock_probe()` registers the hardware-spinlock bank.
2. `qcom_smem_probe()` calls `of_hwspin_lock_get_id()` and can return
   `-EPROBE_DEFER`; the source also declares
   `MODULE_SOFTDEP("pre: qcom_hwspinlock")`.
3. `cmd_db_dev_probe()` maps and validates the command database magic.
4. `rpmh_rsc_probe()` calls `cmd_db_ready()` and defers until command DB and
   its power-domain prerequisites are ready.
5. `gcc_waipio_probe()` maps and registers the clock controller and propagates
   `qcom_cc_*` failures.

`dwc3_msm_probe()` then depends on the planned GDSC, clock, reset, PHY,
redriver, interconnect, and role-switch providers. Module registration alone
cannot prove any of those probes succeeded, so E2 keeps all bind predicates
separate from `/proc/modules` evidence.

## Automatic DWC3 Child And UDC

The exact FYG8 `dwc3-msm.ko` is 308624 bytes with SHA256
`8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1`.
Its relocation-bearing disassembly proves that the successful probe path calls:

```text
0x6fd0 queue_delayed_work_on
0x6fe0 enable_usb_notify
0x7008 probe_typec_manager_gadget_ops
```

The source-matched control flow is:

```text
dwc3_msm_probe
  -> queue sm_work at delay 0
  -> DRD_STATE_UNDEFINED
  -> dwc3_msm_core_init
  -> of_platform_populate(parent)
  -> built-in dwc3_probe(child)
  -> dwc3_core_init_mode(dr_mode=otg)
  -> dwc3_drd_init(usb-role-switch)
  -> default peripheral dwc3_set_mode work
  -> dwc3_gadget_init
  -> usb_add_gadget
  -> /sys/class/udc/a600000.dwc3
```

The exact DTBO contains 11 `usb-role-switch`/`dr_mode` property sets and no
`role-switch-default-mode` string. The preserved DT audit fixes the child to
`dr_mode = "otg"`. The exact P2.39 kernel configuration enables built-in DWC3,
dual role, USB role switch, gadget, configfs, and ACM support.

Therefore an explicit `mode=peripheral` write is not a prerequisite for E2's
DWC3-child and UDC observations. Child role setup already schedules peripheral
initialization. This is not a live-bind proof: asynchronous gadget
initialization can still fail, and that failure is why the exact UDC gate is
required after the child-bind gate.

Configfs creation, role forcing, gadget UDC binding, `ttyGS0`, and host bytes
belong to E3, not E2.

## E2 Runtime Contract

The implementation should extend the existing runtime and planner rather than
fork the old O3 candidate:

1. execute the eight proven local E1 stages;
2. load the 59-module E2 order above from `/lib/modules`;
3. for each module require exact `openat`, `finit_module() == 0`, and `close`
   success;
4. after each load, stream `/proc/modules` to EOF and require the exact loaded
   prefix with no missing, duplicate, or foreign runtime name;
5. reject `-EEXIST` rather than treating it as success;
6. after all 59 modules are visible, observe the eight exact bind/UDC gates;
7. publish terminal E2 success only after all eight gates pass; and
8. enter the existing quiet park under bounded host observation.

The runtime must stop at the first failed module or gate. A module-stage
failure records the exact module stage, item index, and bounded errno. A gate
failure records the exact expected gate and errno. This identifies the first
failed module or bind boundary; it does not claim syscall-trace granularity
inside one module operation.

## Bind Gate Semantics

The ordered predicates remain:

| Index | Gate | Exact path |
|---:|---|---|
| 0 | hwspinlock | `/sys/bus/platform/drivers/qcom_hwspinlock/soc:hwlock` |
| 1 | smem | `/sys/bus/platform/drivers/qcom-smem/soc:qcom,smem` |
| 2 | cmd-db | `/sys/bus/platform/drivers/cmd-db/80860000.aop_cmd_db_region` |
| 3 | rpmh | `/sys/bus/platform/drivers/rpmh/af20000.rsc` |
| 4 | gcc-waipio | `/sys/bus/platform/drivers/gcc-waipio/100000.clock-controller` |
| 5 | ssusb | `/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb` |
| 6 | dwc3-core | `/sys/bus/platform/drivers/dwc3/a600000.dwc3` |
| 7 | udc | `/sys/class/udc/a600000.dwc3` |

For gates 0-6, plain `access()` is insufficient. Require `lstat()` to report a
symlink, bounded `readlink()` success, and the exact expected device basename
in the resolved target. For gate 7, enumerate `/sys/class/udc` and require one
and only one non-dot entry named `a600000.dwc3`.

Use one 20-second global `CLOCK_MONOTONIC` deadline for the complete gate
phase, polling every 100 ms. Publish each newly complete contiguous gate once.
Do not restore O3's eight independent 10-second waits. A read error, a previous
gate disappearing, timeout, cursor change, or ambiguous UDC publishes the next
allowed failure if possible and then parks; it never proceeds to E3 writes.

## Checkpoint Capacity

Keep the proven 45-byte shared-header plus two 10-byte A/B slots unchanged.
Add profile number 3 with this unique-stage sequence:

```text
local stages:  0x10 0x11 0x12 0x13 0x14 0x20 0x21 0x22
module stages: 0x40..0x7a  (59; item = stage - 0x40)
gate stages:   0x7b..0x82  (8;  item = stage - 0x7b)
terminal:      0x8f
```

This is 76 post-ENTRY generations, 76 unique stage values, maximum generation
76, and maximum stage `0x8f`. Both fit in the existing `u8` fields. Under the
current generic failure-detail domain, exhaustive source validation covers:

```text
75 nonterminal stages * 4096 progress/failure variants + 1 terminal
= 307201 reachable slot variants
```

The old pre-carrier O3/O3F stage labels and any historical `0x7f` terminal are
not contracts for profile 3 and must not be reused.

## Implementation Gates

The next H0 unit is limited to:

- extend the planner with the pinned E2 order and identity;
- extend the checkpoint model, kernel patch, client, and decoder with profile
  3 and the 76-stage sequence;
- implement the 59-module exact-prefix loader and eight read-only predicates;
- extend the independent effective-rootfs/module-byte audit;
- cross-compile and inspect the static AArch64 runtime;
- exhaust all 307201 reachable profile-3 slot variants; and
- run focused regressions for E1A and E1B identity preservation; and
- obtain one independent review of the changed execution-critical closure.

The prior USB-role static audit also has one private-input reproducibility gap
to close in P2.41. Its tracked result binds an 11-overlay manifest, but the
current expanded private source directory retains only the r12 decompile. The
exact DTBO remains present and hash-pinned, and direct string inspection still
finds 11 `usb-role-switch`/`dr_mode` sets and no
`role-switch-default-mode`. Regenerate the 11 exact decompiles from that DTBO,
or teach the verifier to parse the pinned DTBO directly; do not substitute the
different source-archive DTS bytes.

Use no Full-LTO candidate build until those host contracts pass. This unit
creates no AP, connected D0, approval token, or live authority.

## Validation

- dependency/order recomputation: 59 unique modules, 210 constraints, zero
  violations;
- exact vendor-ramdisk newc scan: all 59 modules present and zero
  `request_firmware*` string hits;
- profile-3 arithmetic: 76 unique stages, generation 76, terminal `0x8f`, and
  307201 reachable variants;
- existing planner and compact-carrier suites: 30 tests passed; and
- USB-role static-RE rerun: blocked before content validation because only
  1/11 private decompiled DTS inputs remains. This is an H0 input-restoration
  gap, not a live USB result or a contradiction of the tracked audit.

## Limits And Decision

This audit proves that E2 has a complete and bounded implementation contract.
It does not prove direct-PID1 platform bind, DWC3 child creation, UDC creation,
USB enumeration, ACM bytes, NCM, a shell, Debian, or a supervisor.

Proceed to P2.41 E2 host implementation. Stop if the generated order differs,
the effective vendor-rootfs bytes cannot be independently pinned, profile 3
cannot preserve E1A/E1B decoding, or E2 requires any sysfs/configfs write.
