# S20+ G986N native USB substrate H0/D0 report

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`)

Status: **PASS - NATIVE USB FAST TRACK IS PLAUSIBLE; NO LIVE CANDIDATE OR AUTHORITY**

## Scope

This unit asks whether the exact S20+ can obtain an early, bounded native USB
witness more directly than the S22+ USB work, while reusing only architectural
lessons—not artifacts, identities, approvals, or authority—from A90 and S22+.

The host review used the exact Samsung-published source and exact stock boot.
One connected D0 observation then read only public Android properties and
unprivileged sysfs/configfs visibility from the exact healthy S20+. It issued
no `su`, write, reboot, USB-mode change, payload, Odin, or partition command.
No command was addressed to A90, S22+, or another target.

## Exact host inputs

- Samsung target source ZIP SHA-256:
  `f21189586ed4739b4810a81346cee0fdd6b82aa8fd7854b6ca337e7cac13d31e`
- Nested `Kernel.tar.gz` SHA-256:
  `4ed0aa2f390d9d847eee313693fe8b9b726f4decefc40b3ba8fde1b64272ae6d`
- Exact stock boot SHA-256:
  `29fde3a189b906ea20ed0e14fcd7a448e005597b82e3adceea64196284bd31ab`
- Embedded final stock configuration text SHA-256:
  `5e4e4a986f7aae396dc3ebb03818a4c0b9bea5f6948c5e17eb6abaf8d988f760`

The stock boot header names `a600000.dwc3` as
`androidboot.usbcontroller`. The source DTS has Qualcomm `ssusb@a600000` /
`dwc3@a600000` in dual-role, SuperSpeed mode. The exact y2q Korean overlay
also contains Samsung's MAX77705 Type-C/PD notifier path.

## Kernel and source closure

The exact final stock configuration has the relevant substrate built into the
kernel rather than dependent on a separate module-loading ladder:

- `CONFIG_USB_DWC3=y`
- `CONFIG_USB_DWC3_MSM=y`
- `CONFIG_USB_DWC3_DUAL_ROLE=y`
- `CONFIG_USB_GADGET=y`
- `CONFIG_USB_LIBCOMPOSITE=y`
- `CONFIG_USB_CONFIGFS=y`
- `CONFIG_USB_CONFIGFS_ACM=y`
- `CONFIG_USB_F_ACM=y`
- `CONFIG_CCIC_MAX77705=y`
- `CONFIG_MFD_MAX77705=y`
- `CONFIG_TYPEC=y`
- `CONFIG_EXTCON=y`
- `CONFIG_USB_NOTIFIER=y`
- `CONFIG_USB_NOTIFY_LAYER=y`
- `CONFIG_USB_TYPEC_MANAGER_NOTIFIER=y`

The source-derived automatic attach path is not an A90-simple DWC3-only path:

`MAX77705/Type-C -> usb_typec_manager -> usb_notifier_qcom -> dwc3-msm`

`usb_notifier_qcom` forwards an attached UFP/VBUS event and
`dwc3-msm` schedules the peripheral-role transition. The same driver also
exports a bounded `mode=peripheral` control, but that is only a candidate
mechanism; this report does not authorize writing it.

## Connected D0 observation

The selected endpoint exactly matched `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`, was boot-complete with stopped boot animation, ran SELinux
`Enforcing`, and returned shell UID 2000.

The bounded reads established:

- `sys.usb.controller=a600000.dwc3`;
- `sys.usb.config`, `sys.usb.state`, and `persist.sys.usb.config` agreed on
  `mtp,conn_gadget,adb`;
- the sole visible UDC name was `a600000.dwc3`;
- the parent controller was bound to `msm-dwc3` and the child to `dwc3`;
- configfs was supported and mounted at `/config`; and
- the live stock ADB connection itself proved physical attachment through
  that controller.

The unprivileged shell could not enumerate the gadget tree or UDC state/mode
attributes. Under enforcing SELinux this is recorded as **unprivileged
non-observability**, not as proof that those nodes are physically absent.

Canonical private result:
`workspace/private/runs/s20plus-g986n-usb-substrate-d0/usb-d0-20260815T183554Z/result.json`,
SHA-256
`41204b1c91aaacb5bc0c0dbc45198d428cb1948a78eec3690f0037b6c5bae660`.
Its canonical command count is two global inventories and two exact-S20+
reads; all device-effect and other-target counts are zero.

## Cross-target interpretation

| Target | Useful lesson | Target-specific difference |
|---|---|---|
| A90 | A small configfs gadget with one `acm.usb0` function and UDC `a600000.dwc3` is a good witness shape. | Its runner, target identity, init environment, and authority do not transfer. |
| S22+ | Samsung Type-C/PD notification, role transition, PHY/runtime-PM, and electrical attachment must be treated as one chain. | Its exact module closure and device evidence do not transfer. |
| S20+ | It has the same DWC3 controller name and a Samsung notifier chain, while all currently needed pieces are built in. | It still needs its own ordering, ownership, cleanup, and physical-enumeration proof. |

Therefore S20+ is **not** a direct A90 clone, but its first USB proof should be
materially smaller than the S22+ module-driven investigation.

## Selected N3-U0 candidate shape

The smallest next host-only design/build unit is a temporary boot-overlay ACM
witness, not a replacement `/init` and not a persistent promotion:

1. start from the exact known-good resident Magisk boot;
2. preserve its kernel, DTBs, command line, Magisk `/init`, backups, and all
   existing ramdisk entries;
3. add exactly one `overlay.d/*.rc` and one static AArch64 witness binary;
4. use only the fixed `a600000.ssusb` / `a600000.dwc3` controller family;
5. create one owned configfs gadget with one `acm.usb0` function;
6. read the owned ACM function's exact one-digit `port_num`, reject values
   outside `0..3`, and emit one versioned finite banner only through the
   resulting owned `/dev/ttyGS<n>`;
7. if the automatic notifier path is insufficient, permit only a separately
   reviewed bounded `mode=peripheral` transition;
8. unbind and remove only its owned gadget before stock Android USB takes over;
9. observe exact healthy rooted Android and then restore the exact resident
   boot using the existing boot-only recovery boundary.

Before any live candidate, H0 must close the exact init ordering and race with
stock gadget `g1`, deterministic ramdisk delta, fixed cleanup behavior, host
USB observation grammar, and boot-only rollback binding. The first unit does
not add NCM, storage, networking, a DTB change, a kernel module, a PID1
replacement, or resident promotion.

## Authority

This report records H0/D0 feasibility only. It builds no candidate and grants
no D1, R1, F1, `su`, USB-mode, reboot, Odin, or partition authority. Any live
N3-U0 boot requires its own exact builder/artifact closure, hostile tests,
independent review, fresh target binding, and attended boot-only approval.

The subsequent host-only implementation/build is recorded separately in
`S20PLUS_G986N_N3U0_ACM_HOST_BUILD_H0_2026-08-16.md`; it does not retroactively
create live authority here.
