# S22+ FYG8 P3.19 — USB recovery-control correction and raw-first successor

Status: `P319_STOCK_RECOVERY_CONTROL_RESULT_IMPLEMENTED_REVIEW_PENDING`.
The predecessor correction remains separately review-pending under topic 35;
the fresh successor interpretation is topic 36.

**NO STANDING DEVICE OR LIVE AUTHORITY.** The image, source, binary, and
external-corpus predecessor was host-only. Its independent operator recovery
entry and later D0 listing lacked raw-first evidence and remain retrospectively
`HEALTH_PENDING / NO_PROOF_OBSERVER` and
`HOST_OBSERVER_FAILURE / NO_PROOF_OBSERVER`.

A separate fresh attended request was later consumed by one physical stock-
recovery entry, bounded D0 observation, one physical `Reboot system now`
return, final health, and a post-return read-only Max77705 inventory. Those
actions are closed; they create no reusable approval, recovery authority, or
continuation.

The predecessor correction contacted no device and performed no replay. It
preserves the
predecessor at commit `d38dd963a0f6`, 26,765 bytes, SHA-256
`e59df701d4c6653001a1a3b3c1a1ac4d4e5815a87a125aad1f3c97bb26c69d10`.
The private retrospective marker
`workspace/private/outputs/s22plus_fyg8_p319/stock-recovery-control-retrospective-20260824-01.json`
is 2,358 bytes, SHA-256
`07b34c8326a9091ed15836e748e8f38ac6ce85ccbe0faac74661c39ed04dd6dc`,
mode `0400`, link count one. It explicitly is neither raw evidence nor a device
result. Neither the correction nor the successor creates a candidate, package,
ready/run/approval manifest, standing connected authority, recovery authority,
or replay authority, and neither changes a candidate byte. The predecessor's
network access was read-only public web fetches; no repository content, private
identifier, or device datum was transmitted.

## Why this unit exists

The operator was asked two questions in sequence: whether any S22+ USB analysis
surface remains, and whether external custom-kernel or Linux-porting projects
carry transferable information. This report records both answers with the
evidence each rests on, and separates what was proved from what was only
located.

It has three parts:

- **Part A** cross-checks the parallel FYD9-to-FYG8 USB delta closure and adds
  one binary result that closure did not carry.
- **Part B** reads both recovery images — stock and TWRP — and separates the
  valid static control facts from an unretained operator observation.
- **Part C** is the external corpus, with per-source provenance.

Part A is a confirmation. Part B and Part C are new. The original Part B live
closure claim is withdrawn by this correction.

## Part A — Independent cross-check of the FYD9-to-FYG8 USB delta

The unit cross-checked here is now committed as `794762bdf4`
("s22plus: audit FYG8 USB source delta") with its report
`S22PLUS_FYG8_P319_FYD9_FYG8_USB_DELTA_CLOSURE_H0_2026-08-23.md`.

### What was derived independently

Before the parallel closure report was read, the operator derived the following
directly from the pinned archives:

| Fact | Value |
|---|---|
| FYG8 OSRC package shape | delta over `S906NKSU7FYD9`, not a full tree |
| FYG8 delta archive | 1,421,025 B, SHA-256 `23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a` |
| Raw archive members | 52 = 30 directory + 22 regular file |
| Regular files touching USB | exactly 2, both `drivers/usb/notify/` |
| Delta applied to the P290 tree? | yes — both USB files byte-identical to the materialized tree |
| `g0q_kor_singlex_w00_r12.dts` | identical across delta, P290 tree, and the IRQ audit input, SHA-256 `aff997ab764b7be8ff66d57b0633fa11c881a108f8fabea186cf5a4216844822` |

The FYD9 base was reopened from
`inputs/s22plus_kernel_source/SM-S906N_15_base_osrc/Kernel.tar.gz` and the two
notify files extracted for the diff. The derived FYG8 semantics were:

- `reserve_state_check()` gains a post-wait branch setting `first_restrict`,
  `set_notify_disable(..., NOTIFY_BLOCK_TYPE_HOST)`, and `skip_possible_usb`;
- `usb_sl_store()` gains value validation and relaxes the `first_restrict`
  release condition;
- `DISABLE_LOCKSCREEN_USB_RESTRICTION` is a `bool` with no Kconfig default and
  appears in neither `waipio_sec_defconfig` nor `waipio-gki_defconfig`, so the
  restriction branch is not disabled by the audited configuration;
- `EXTERNAL_NOTIFY_POSSIBLE_USB` reaches
  `usb_typec_manager_notifier.c` and maps to `MANAGER_NOTIFY_PDIC_DELAY_DONE`,
  which is one of the inputs `manager_set_alternate_mode()` requires before it
  calls `set_enable_alternate_mode(ALTERNATE_MODE_READY | ALTERNATE_MODE_START)`.

All of these agree with the parallel closure report.

### The member-count difference is not a defect

The closure report states 51 overlay members, 29 of them directories. The raw
archive has 52 members and 30 directories. The difference is the archive's
`Kernel/` wrapper: the FYD9 base archive roots at `kernel_platform/`, with no
`Kernel/` prefix, so normalizing the overlay onto the base drops exactly that
one member. 52 − 1 = 51, and 30 − 1 = 29. The census is consistent; no
correction is required.

### New: the DWC3 client veto is absent from the shipped module

The closure report argues from source that the CLIENT veto inside
`mode_store()` is not compiled, because it sits under a plain
`#ifdef CONFIG_USB_NOTIFIER` while the option is `=m`, which defines only the
`_MODULE` form. That reasoning is correct, and it is now confirmed against the
shipped binary rather than left at source level.

Module read: `outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-32/module-bytes/dwc3-msm.ko`,
308,624 B, SHA-256
`8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1`.

| Probe | Result |
|---|---|
| `is_blocked` in undefined symbols | **absent** |
| `get_otg_notify` in undefined symbols | **absent** |
| `"blocked peripheral mode"` / `"blocked host mode"` strings | **absent** |
| `"%s: mode_request:%s"` string (positive control) | **present** |

The positive control matters: `mode_store()` itself is compiled in, and only
the guarded veto is missing. The module does import
`enable_usb_notify`, `vbus_session_notify`, `usb_reset_notify`, and
`store_usblog_notify` from the notify layer, so the absence of `is_blocked` is
a real per-call-site result, not a consequence of the notify layer being
unlinked.

**Consequence.** A write of `peripheral` to `a600000.ssusb/mode` cannot be
vetoed by the notify layer's disable state on this build. The operator's
earlier concern that the `mode` lever could fail silently with `-EINVAL`
through this path is withdrawn. The lockscreen-restriction delta therefore
remains a HOST-delivery and alternate-mode-readiness matter and is not promoted
to an explanation of gadget silence.

## Part B — Both recovery images, read

Both recovery images were unpacked host-side with the repository's own
`workspace/public/src/third_party/mkbootimg/unpack_bootimg.py`. That unpacking
flashed nothing and contacted no device. The stock image was already extracted
at `workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/recovery.img`;
the TWRP image is the single member of the pinned
`workspace/private/inputs/s22plus_twrp/g0q/twrp-3.7.0_12-1_afaneh92-g0q.tar`.

### The decisive difference is the kernel

| | Stock `recovery.img` | TWRP `recovery.img` |
|---|---|---|
| Size | 104,857,600 B, SHA-256 `93fac06ca79bf4b3…` | 55,435,280 B, dated 2022-12-12 |
| Header version | 2 | 2 |
| Kernel payload | raw Image, 41,490,944 B | gzip, inflates to 41,488,896 B |
| Kernel SHA-256 | `027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d` | `6beb83aa231749d503e101e0…` |
| Kernel banner | `5.10.226-android12-9-30958166-abS906NKSS7FYG8`, built 2025-08-01 | `5.10.81-afaneh92-g0418bf01a3e2 (afaneh@afaneh-linux)` |
| Same Image as stock FYG8 `boot.img`? | **yes, byte-identical** | no |

The stock recovery kernel is the *same bytes* as the kernel in
the stock FYG8 `boot.img`: `027d4ab6...`. It is **not** the current P3.19
candidate's fixed 41,490,944-byte Image, which is
`71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8`.
TWRP runs a third, independently built `5.10.81` kernel from December 2022.

**Consequence.** Stock recovery is a control for the shipped FYG8 stock-kernel
and recovery-userspace path, not an exact-Image control for the P3.19 candidate.
TWRP is further removed: any USB result under it would concern its different
kernel and could not be carried across to the candidate. This remains a
measured reason, independent of the contract question, not to install TWRP for
the P3.19 USB question.

### The stock recovery QCOM role/UDC prerequisite fragment is six lines

`init.recovery.qcom.rc` in the stock ramdisk contains this role/UDC fragment:

```
on init
    setprop sys.usb.controller a600000.dwc3
    setprop sys.usb.configfs 1

on property:ro.boot.usbcontroller=*
    wait  /sys/bus/platform/devices/${ro.boot.usb.dwc3_msm:-a600000.ssusb}/mode
    write /sys/bus/platform/devices/${ro.boot.usb.dwc3_msm:-a600000.ssusb}/mode peripheral
    wait  /sys/class/udc/${ro.boot.usbcontroller} 1
```

`ro.boot.usbcontroller` is supplied by the recovery kernel command line, which
also carries `androidboot.selinux=permissive`.

These six lines are not the whole gadget recipe. The common recovery `init.rc`
later creates the configfs gadget, links `ffs.adb`, selects product `0xD001`,
and binds the UDC. The fragment above is the same role lever the 2026-07-09 S3
unit omitted. Its userspace control flow has **no explicit wait** for a PDIC
notification, VBUS notifier, or Type-C manager call before the role write; this
static reading does not exclude asynchronous kernel Type-C events.

### Module authority, confirmed at the source image

The `modules.load.recovery` inside the stock recovery ramdisk is byte-identical
to the copy already held under `vendor_ramdisk_metadata` — both
`616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10`. The
446-line list cited earlier in this campaign is therefore the real recovery
list, not a build artifact.

- The list is 446 lines but **441 unique names**, and every unique name ships
  as a `.ko` file in the ramdisk — nothing in the list is missing. The five
  names that occur twice are `cpu_hotplug`, `gh_virt_wdt`, `qcom_tsens`,
  `qcom_wdt_core`, and `thermal_pause`, all thermal or watchdog, none USB.
  This matches the P2.86 audit of 2026-07-29, which recorded the same list
  digest and the same five duplicates.
- All eight role-chain modules are present as real files: `dwc3-msm.ko`,
  `usb_f_ss_acm.ko`, `mfd_max77705.ko`, `pdic_max77705.ko`,
  `usb_typec_manager.ko`, `ucsi_glink.ko`, `pmic_glink.ko`, `eud.ko`.
- The loader is stock first-stage init: `system/bin/init` (7,014,920 B) carries
  the strings `modules.load.recovery`, `modules.load`, and
  `system/core/init/first_stage_init.cpp`. No rc file performs `insmod`.

### What TWRP does differently

TWRP ships `init.recovery.usb.rc`, which builds the gadget explicitly —
configfs `g1`, `idVendor 0x18D1`, `ffs.adb` / `ffs.fastboot` / `ffs.mtp`,
functionfs mounts, and `write /config/usb_gadget/g1/UDC ${sys.usb.controller}`.

**It never writes `ssusb/mode`.** The token `ssusb` does not occur in any TWRP
rc or shell file. TWRP therefore omits the exact role lever this campaign
proved necessary in the S3 unit, and must be relying either on `5.10.81`
behaviour or on natural attach. That makes it weaker evidence than stock
recovery, not stronger.

TWRP's module list is also a different generation: 440 lines,
`99d53b684fea37ba5185…`, 438 `.ko` files. Against the stock 446 it drops 15
names and adds 9. The USB-relevant differences are that stock carries
`redriver.ko` and `nb7vpq904m.ko` where TWRP carries
`ssusb-redriver-nb7vpq904m.ko` — the redriver module was renamed between the
two firmware generations — and that TWRP adds USB-Ethernet drivers
(`asix.ko`, `ax88179_178a.ko`).

### Predecessor operator-reported observation; formal control was open

While the predecessor report was being written, the operator independently
placed the device in stock recovery and reported it as stock. That boot-mode
transition is D1 even though no repository runner dispatched it. The host USB
stack was then read passively. No immutable host snapshot, D1 intent/result, or
final Android-health receipt was preserved, so the transition is retained only
as an operator-reported `HEALTH_PENDING / NO_PROOF_OBSERVER` event.

The predecessor report records the following host fields. They are supportive
observations, not machine-authoritative evidence:

| Field | Value |
|---|---|
| idVendor:idProduct | `18d1:d001` |
| manufacturer / product | `samsung` / `SM-S906N` |
| bcdUSB / speed | `2.10` / `480` (High Speed) |
| Configurations / interfaces | 1 / 1 |
| Interface class/subclass/protocol | `ff/42/01` — the ADB interface signature |
| Endpoints | 2 |
| Kernel driver | `usbfs` (no in-kernel claim, as expected for ADB) |

Serial and usbfs path are deliberately not recorded.

The reported fields are consistent with the static recipe read from the image:

- `init.recovery.qcom.rc` sets `sys.usb.controller a600000.dwc3`,
  `sys.usb.configfs 1`, writes `mode peripheral`, and waits on
  `/sys/class/udc/a600000.dwc3`;
- `system/etc/init/hw/init.rc:168-172` then, for `sys.usb.config=adb` with
  `sys.usb.configfs=1`, writes `idProduct 0xD001`, links exactly one
  `ffs.adb` function into `configs/b.1`, and writes
  `UDC ${sys.usb.controller}`.

One function, one interface, `0xD001` — which is what the host reports.

The operator also reported a photograph of the ordinary AOSP recovery menu,
headed:

```
Android Recovery
samsung/g0qksx/g0q
12/SP1A.210812.016/S906NKSS7FYG8
user/release-keys
```

`user/release-keys` and that build id are consistent with unmodified stock
recovery for this firmware, and the statically unpacked ramdisk carries the
same `ro.build.display.id`. The photograph was not retained as a referenced
private artifact, however, so it does not machine-bind the running bytes to the
image analysed here.

The reported screen is consistent with the authorization limitation: the menu
is the standard one and carries no "Allow USB debugging" prompt. A second
reported screen shows Samsung's banner —
`Reboot Recovery Cause is [init:1]`, `Reason is []`, `Supported API: 3`,
`MANUAL MODE v1.0.0`, `No command specified.` — consistent with a manual
key-combination entry and no pending OTA command.

Two incidental facts follow. `Apply update from ADB` would move
`sys.usb.config` to `sideload`, which `init.rc:161-166` shows uses the same
`0xD001` product id and the same single `ffs.adb` function, so it changes device
state without changing the gadget and still offers no shell; it was not used.
If the reported stock screen is exact, the TWRP installed on 2026-07-06 is no
longer the running recovery. That is not byte-level recovery-partition proof,
and the repository records no unit that restored it — an evidence-chain gap
between 2026-07-07 and now.

With the operator's explicit approval a bounded D0 listing was then run. Target
ambiguity was removed first, host-side: the only other Samsung endpoint on this
host is the A90, whose interfaces are `02/02/01`, `0a/00/00`, `02/0d/00`,
`0a/00/01` — CDC ACM plus NCM, with **no** `ff/42/01` ADB interface, so the ADB
server cannot attach to it. The S22+ is the sole ADB target.

The predecessor report says `adb devices -l` returned exactly one device in
state **`unauthorized`**. Its stdout and stderr were not preserved raw-first,
and no structured result was written. The D0 is therefore
`HOST_OBSERVER_FAILURE / NO_PROOF_OBSERVER`, is not reusable, and cannot be
replayed by this correction.

If exact, `unauthorized` is consistent with the host and device reaching the
ADB `CNXN`/`AUTH` exchange over the bulk endpoints and stopping at key
verification. Because the transcript is absent, the bidirectional bulk path is
not formally proved by this unit.

The static recovery image explains the reported unauthorized state:
`prop.default` and `default.prop` both set `ro.adb.secure=1`, the ramdisk
carries no `adb_keys`, and `system/etc/init/hw/init.rc:81` starts
`adbd --root_seclabel=u:r:su:s0 --device_banner=recovery`. With `ro.adb.secure`
on and no key in the ramdisk, adbd must use `/data/misc/adb/adb_keys`; the
operator reported that this hardware-wrapped `/data` was unavailable in
recovery. The predecessor therefore obtained no `/proc/modules`,
`ssusb/mode`, or loaded-module evidence. No further device command was sent.

**The predecessor did not formally close the Part B control.** Static evidence
proves the stock FYG8 recovery Image, its 446-line module authority, the QCOM
role/UDC fragment, and the generic configfs gadget recipe. The unretained
observation is consistent with that path producing a High-Speed gadget, but it
cannot prove the live result, the exact running bytes, or the current P3.19
candidate.

Two bounded interpretations remain:

- **If the reported High-Speed enumeration is exact,** D+/D- was routed through
  a USB-capable path without Android. Missing raw evidence prevents promoting
  that implication to a formal `CONTROL1=COM_USB` result.
- **Part A needs no live promotion.** The shipped `dwc3-msm.ko` binary already
  proves the CLIENT veto is absent. The operator observation is merely
  consistent with that static result.

### Raw-first successor control on 2026-08-24

A fresh attended successor now separates the predecessor's missing evidence
from a new run rather than retroactively upgrading it. The operator directly
requested the stock-recovery control, physically entered stock recovery once,
and later selected exactly `Reboot system now`. The host sent no reboot,
payload, partition, Odin, candidate, or recovery-service command. It retained
the pre-entry normal-Android inventory before the transition, every subsequent
host stream before parsing, two operator photos, an ADB protocol trace, and the
final normal-Android health reads.

The authority result is private
`workspace/private/runs/s22plus-fyg8-stock-recovery-observation/stock-recovery-observation-20260823T154609Z-0a61a74a/result-v2.json`,
7,542 bytes at SHA-256 `a41cfe6043a0f904098c9273e4e23d8476b153a22aa17452676e9186833eabcc`,
mode `0400`, link count 1. It supersedes the preserved 6,627-byte
`70c88e9c...` V1 terminal only to add complete command accounting; observation,
classification, and health are unchanged. The terminal is `CLOSED` with
`PROVED_STOCK_RECOVERY_USB_ENUMERATION_AUTH_BLOCKED_RETURN_HEALTHY`.

The visual evidence manifest is 1,397 bytes at SHA-256 `63e11611...`, mode
`0400`, link count 1. Its two original JPEGs are retained privately at
103,354 bytes/`b3af608f...` and 83,486 bytes/`8eea8a16...`. They show:

- `Android Recovery`, `samsung/g0qksx/g0q`,
  `12/SP1A.210812.016/S906NKSS7FYG8`, and `user/release-keys`, with
  `Reboot system now` selected; and
- `Reboot Recovery Cause is [init:1]`, empty `Reason`, `Supported API: 3`,
  `MANUAL MODE v1.0.0`, and `No command specified.`

Those photographs support the operator-visible stock FYG8 recovery identity
and manual entry. They do not hash the executing Image or read back the
recovery partition.

The same serial hash moved from normal Android at `usb:2-1.3` to recovery at
`usb:3-1.3`. Raw descriptor and sysfs evidence proves `18d1:d001`, manufacturer
`samsung`, product `SM-S906N`, USB 2.10 High-Speed at 480 Mb/s, configuration
`adb`, one `ff/42/01` interface, and 512-byte bulk OUT and IN endpoints. Udev
tagged the device as MTP/media-player/gphoto, which explains the desktop file
browser entry, but the descriptor contains no MTP interface.

The private ADB trace evidence is 2,526 bytes at SHA-256 `2e2c2c4d...`, mode
`0400`, link count 1. A bounded host-server restart captured the exact packet
order:

```
HOST CNXN 234
DEVICE AUTH_TOKEN 20
HOST AUTH_SIGNATURE 256
DEVICE AUTH_TOKEN 20
HOST AUTH_RSAPUBLICKEY 723
```

No device `CNXN` followed. The server was restored and the same target remained
`unauthorized`. This proves bidirectional bulk transport and localizes the stop
at recovery ADB key authorization: the first signature was not accepted, and
the public key could not be confirmed. The raw trace retains private token and
serial bytes; tracked text records neither. Recovery received zero shell, file,
or service commands.

The V2 terminal accounts for 73 global ADB inventories, two bounded
`wait-for-device` observations, three host ADB-server controls, six host USB
observer commands, one direct host-sysfs snapshot, three targeted normal-
Android shell reads, one normal-Android host-transport query, and zero targeted
recovery service commands, device writes, host reboots, partition/candidate
transfers, A90 commands, or S20+ commands. The large inventory count comes from
the two bounded 45- and 180-second transition windows; it is observation, not
effect replay.

Return health is exact: FYG8 Android is boot-complete, boot animation is
stopped, verified-boot state is `orange`, root is available, Download count is
zero, and the partition identities match the bound profile: boot
`2e541703...`, vendor_boot `096e433e...`, DTBO `97a4864f...`, recovery
`93fac06c...`.

A second existing raw-first D0 consumed the report's cheaper normal-Android
question. Its result is private
`workspace/private/runs/s22plus-fyg8-max77705-sysfs-d0/d0-20260823T160942Z-1787501382211543634/result.json`,
16,825 bytes at SHA-256 `6bac2ea6...`, mode `0400`, link count 1. The 72,904-byte
raw snapshot at `1854e227...` proves `/proc/modules` contains all six named
runtime rows: `msm_geni_se`, `gpi`, `i2c_msm_geni`, `spu_verify`,
`mfd_max77705`, and `pdic_max77705`. The stock `994000.i2c` path is bound to
`i2c_geni`, and `57-0066` is compatible `maxim,max77705` and bound to driver
`max77705`. This is normal-stock-Android evidence, not recovery or candidate
module-load evidence.

### What this does and does not establish

Established, host-only:

- stock recovery and stock FYG8 `boot.img` contain the same `027d4ab6...`
  Image, which differs from the current candidate's `71f573eb...` Image;
- its QCOM userspace role fragment directly writes `mode peripheral` and waits
  for the UDC without an explicit Type-C-event dependency;
- common recovery `init.rc` separately constructs and binds the ADB gadget;
- the 446-line list is authentic and its USB members all ship as files.
- the fresh stock-recovery successor formally enumerated the exact target at
  High-Speed with the expected single ADB interface and bulk IN/OUT endpoints;
- the packet transcript proves `CNXN`/`AUTH` bidirectional transport and an
  authorization stop after signature rejection and public-key presentation;
- the same target returned to exact healthy FYG8 Android with no Download
  endpoint and unchanged bound partition identities; and
- normal stock Android actually loads `spu_verify`, `mfd_max77705`, and
  `pdic_max77705`, and binds the Max77705 parent at `57-0066`.

Not established:

- **exact running recovery Image bytes or `CONTROL1` state.** The photos bind
  an operator-visible FYG8 stock identity, not a partition readback or a
  candidate-exact Image;
- **which subset of the 446 rows is required or successfully loaded.** The
  ramdisk schedules the full list, but no live `/proc/modules` evidence was
  available inside recovery. The post-return normal-Android list cannot be
  substituted for it;
- **anything requiring a shell in recovery.** ADB is `unauthorized` and cannot
  be authorized while `/data` is unavailable, so the loaded-module list was not
  read.
- **whether the Max77705/PDIC tree is required.** The recovery list schedules
  it while userspace separately forces the role by sysfs write, so static
  reading cannot separate the two. It shows only that userspace has no explicit
  Type-C-event wait before setting the role.
- **whether either campaign plan suffices.** Membership of the 446-row stock
  list does not prove closure for the current exact 73-row candidate or for the
  separate preferred 65-module diagnostic alternative.

The earlier framing of TWRP as an existence proof is withdrawn and replaced by
the above.

## Part C — External corpus

All entries below were located by public web search on 2026-08-23 and are
recorded with the claim each supports and the confidence in it. None was
downloaded into the repository.

| Source | Claim it supports | Confidence |
|---|---|---|
| [aaronsb/sm-x800-linux](https://github.com/aaronsb/sm-x800-linux) — Galaxy Tab S8+ (SM-X800, SM8450), mainline 6.13-rc3 | An independent mainline port on the same SoC and the same vendor bootloader reports **USB host (xhci) working and USB gadget not**, attributing the gap to Type-C / `pmic_glink` not being described. It also documents that Samsung's ABL merges its own DTB overlay fragments onto the selected DTB, corrupting a mainline device tree, and works around it by wrapping kernel, DTB, and ramdisk inside `uniLoader` disguised as a kernel image. | High — stated in the project's own README |
| [Galaxy S22 mainline DT series, v9](https://patchew.org/linux/20250912202603.7312-1-ghatto404@gmail.com/) | `sm8450-samsung-r0q.dts` (Galaxy S22, SM-S901E) was **merged** by Bjorn Andersson on 2025-09-12 as commit `11cf389c103f69d1170fbd70acbcc282cf03b748`. USB is USB 2.0 only; UFS, buttons and other blocks are deliberately deferred. | High — merge recorded on the patch tracker |
| [sm8450-hdk pmic_glink node](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20230130-topic-sm8450-upstream-pmic-glink-v1-5-0b0acfad301e@linaro.org/) | Mainline SM8450 obtains USB role switching from `pmic_glink` with `usb-role-switch` on the DWC3 node, not from a Maxim MUIC. | High |
| [sm8450-mainline](https://github.com/sm8450-mainline/) and [fdt](https://github.com/sm8450-mainline/fdt) | Active SM8450 mainline organisation (Linux fork, pmaports, U-Boot, UEFI, downstream DTB archive). Device focus is Xiaomi and Nothing, **not Samsung**, so direct S22 benefit is limited. | High |
| [mfdl/android_kernel_samsung_sm8450](https://github.com/mfdl/android_kernel_samsung_sm8450), [Vikinsson207/android_kernel_samsung_sm8450](https://github.com/Vikinsson207/android_kernel_samsung_sm8450) (S906E, `S906EXXS2AVDD`), [samsung-sm8450-kernel/kernel_msm](https://github.com/samsung-sm8450-kernel/kernel_msm) | Public mirrors of S22-series kernel source, usable to cross-diff other regions and firmware revisions — for example whether the Part A lockscreen hook exists outside `S906N`/FYG8. | High for existence; contents unverified |
| [afaneh92/android_device_samsung_r0q](https://github.com/afaneh92/android_device_samsung_r0q) | TWRP build device tree from the same maintainer as the locally held `g0q` build; the source-side counterpart to the Part B artifact. | High for existence; contents unverified |
| [ianmacd/d2s — `drivers/muic/max77705-muic.c`](https://github.com/ianmacd/d2s/blob/master/drivers/muic/max77705-muic.c) | Public earlier-generation copy of the same Samsung MAX77705 MUIC driver family, for cross-reading `CONTROL1` / `COM` semantics. | High for existence |
| [mfd: MAX77705 PMIC driver, v16](https://patchew.org/linux/20250117-starqltechn._5Fintegration._5Fupstream-v16-0-11afa877276c@gmail.com/20250117-starqltechn._5Fintegration._5Fupstream-v16-5-11afa877276c@gmail.com/) | Upstream MAX77705 MFD work (Sankouski, `starqltechn`). **Caveat:** search evidence indicates the MUIC/extcon portion may not be upstream, so this may not answer a `CONTROL1` reset-default question. | Medium — upstream MUIC coverage unconfirmed |

### The convergence worth noting

Two independent lines point at the same place. Mainline SM8450 produces the USB
role from `pmic_glink`/UCSI, and the only comparable Samsung SM8450 mainline
port names the absence of exactly that as why its gadget does not work. The
campaign's own selected producer design excluded `ucsi_glink.ko` on the grounds
that UCSI is not operational, while both `pmic_glink.ko` (line 198) and
`ucsi_glink.ko` (line 274) appear in the stock recovery list. That exclusion is
worth revisiting on evidence rather than treating as settled.

This is a direction, not a result. No claim is made here that UCSI is
operational on this target.

## Is a TWRP install warranted?

The question was raised on the basis of future experiment convenience rather
than the USB question. Assessed on its own terms the answer is **no, not now**,
for four reasons that are independent of the contract prohibition.

1. **It contributes nothing candidate-exact to the USB question.** TWRP runs
   `5.10.81`; stock recovery supplies the much closer FYG8 stock-kernel and
   recovery-userspace control surface, although it too is not byte-identical to
   the current candidate Image.
2. **It would destroy the stock control surface characterised here.** Stock
   recovery is a minimal, non-Android FYG8 userspace reachable by key
   combination with **zero** partition writes. Installing TWRP overwrites it,
   and restoring it is a second forbidden-partition write.
3. **Most of what TWRP is for is already forbidden.** Its distinguishing
   capability is partition-level read and write; `AGENTS.md` clause 2 permits
   only `boot` as a payload and the F1 process is boot-only by design.
4. **The previous episode was not cleanly tracked.** The 2026-07-06 install is
   recorded and the device is now stock, with no unit recording the restoration.
   That accounting gap should be closed before a similar event is repeated.

### The one real gap it would close

The current F1 evidence model closes on *Odin write success plus boot health*.
Nothing reads the partition back, because Odin is write-only. The same
deficiency is why this unit could not determine what occupied `recovery`
without booting it and looking at the screen.

If byte-level readback is judged a defect in the evidence model rather than an
accepted limit, then a reader — TWRP or otherwise — becomes the only remedy and
would justify a reviewed binding-contract change. That is a contract-owner
judgement. It is not on the current P3.19 critical path and this report does not
request it.

### The cheaper route has now been consumed

The question left open by Part B — which modules actually load, and whether the
Max77705 MFD/PDIC pair loads at all — did not need recovery. The fresh bounded
normal-Android D0 above proves `spu_verify`, `mfd_max77705`, and
`pdic_max77705` are loaded on the stock FYG8 boot. That set is not the 446-name
recovery set and does not prove the recovery or candidate load path.

## Ranked next units

Part B removed the item that previously ranked first: both recovery ramdisks
have now been read. What remains is narrower.

1. **Close the current-plan dependency question host-side.** Compute whether
   the exact currently requalified 73-row plan closes the dependencies needed
   for `a600000.ssusb/mode` and the UDC. The separate preferred 65-module
   diagnostic shape in `GOAL.md` is an alternative design and must not be
   substituted silently for the 73-row candidate. A 65-module comparison, if
   desired, is a separately labelled branch.
2. **Reconcile the fresh stock-Android module result with the two candidate
   shapes.** The current stock boot loads the MFD/PDIC/SPU trio, but that does
   not decide whether the exact 73-row plan reaches the same bind/probe path or
   whether the separate 65-module alternative is complete.
3. **Read the `sm-x800-linux` gadget failure analysis and `uniLoader` approach**
   — the only comparable independent port on this SoC and bootloader.
4. **Re-examine `pmic_glink`/UCSI as a role producer** against the Part C
   convergence.
5. **Cross-diff the public S22-series kernel mirrors** for the Part A hook.

Items 3 and 5 require network fetches and should be scoped as their own
host-only units with their own receipts.

## Boundaries

### Successor stock-recovery observation

The first 2026-08-23 operator recovery entry remains unreceipted and no-proof.
The separate 2026-08-24 successor does not rewrite it: it has a fresh direct
operator request, raw-first acquisition, immutable terminal result, exact
packet trace, operator photographs, and final Android-health evidence.

Booting the device to stock recovery writes no partition and sends no payload,
but it is a reboot and a boot-mode transition. `DEVICE_ACTION_RISK_TIERS.md`
places it at **D1**, not D0: D0 explicitly forbids reboot and boot-mode change,
while D1 names "an attended reboot, request/exit Download mode" as its example.
D1 requires one fresh explicit operator request per bounded action. The
successor consumed exactly the current attended request, and it creates no
standing authority for another entry.

For any later repeat, one operational hazard remains: the Samsung stock
recovery menu places "Wipe data/factory reset" adjacent to the other entries,
and this target's `/data` is TEE-wrapped and carries campaign state. The
successor used the already highlighted `Reboot system now` item without moving
the selection. A future unit must again predeclare that exact path and stop if
the highlight or menu differs.

### Installing TWRP

Flashing TWRP to `recovery` is `X` under `AGENTS.md` clause 2, which permits
`boot` as the only partition payload and names `recovery` first among the
forbidden targets; `DEVICE_ACTION_RISK_TIERS.md` repeats that no policy tier
authorizes it. The 2026-07-06 install was possible because commit `078f4a6572`
added a narrow 26-line S22+ recovery/vbmeta exception to `AGENTS.md`; that
exception is no longer present in the current file. Re-enabling it would be a
binding-contract change requiring independent review, and is the contract
owner's decision, not this unit's. Part B records separately that a TWRP
install would not supply the control this campaign needs, because its kernel is
not the candidate's.

### Scope

This successor changes no candidate byte and does not alter the remaining P3.19
integration blocker. As of `eb4fd9908d` that blocker is `FRESH_BASELINE_MISSING`
alone; `REQUALIFICATION_REQUIRED` was cleared by that commit and is no longer
outstanding. The consumed D1/D0 actions are closed and grant no new D0, D1, F1,
recovery, replay, causal-result, candidate-success, device, or live authority.
Topic 35 still covers only the predecessor correction and remains independently
review-pending. The fresh successor interpretation opens separate topic 36.
Part A remains review-pending; Part C is host evidence; neither is `PASS_GO`.
