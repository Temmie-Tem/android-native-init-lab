# S22+ Native-Init M5 USB-ACM Host Build - 2026-07-07

## Scope

Host-only build of the next S22+ native-init milestone after M4T2/M4T3:
bring up a USB ACM control channel from custom PID1. No live flash was run, no
device partition was written, and no `AGENTS.md` live exception was added for
this M5 candidate.

M5 is intentionally a larger step than the M4 micro-probes. M4T2 proved the
kernel can execute a custom static `/init` as PID1, and M4T3 proved a raw
custom-PID1 reboot-to-download path. M5 now aims for the force multiplier:
native `/init` mounts the minimal virtual filesystems, inserts the measured
USB-first vendor module chain, creates a configfs `ss_acm.0` gadget, and parks
while probing `/dev/ttyGS0`.

## Inputs

Source:

```text
workspace/public/src/native-init/s22plus_init_usb_acm_m5.c
```

Builder:

```text
workspace/public/src/scripts/revalidation/build_s22plus_inplace_m5_usb_acm.py
```

Private module bundle:

```text
workspace/private/inputs/s22plus_module_bundles/FYG8_usb_first_m2
```

Base boot image:

```text
workspace/private/outputs/s22plus_magisk_root_boot_only/boot.img
```

The M5 builder starts from the known-booting Magisk boot image and uses
`magiskboot unpack/repack`; it does not use `mkbootimg` from scratch. The
no-change MagiskBoot repack gate was byte-identical to the base boot.

## Native Init Behavior

M5 performs only runtime/ramdisk operations:

```text
mount /proc
mount /sys
mount /dev as devtmpfs, falling back to tmpfs
mount /run tmpfs
mount /config configfs
create /dev/kmsg, /dev/console, /dev/null, /dev/zero
emit S22_NATIVE_INIT_USB_ACM_M5 marker to kmsg
finit_module the 26 FYG8 USB-first modules from /lib/modules/s22plus-m5
create /config/usb_gadget/g1/functions/ss_acm.0
bind the gadget to the first non-dummy UDC found under /sys/class/udc
poll /sys/class/tty/ttyGS0/dev and /dev/ttyGS0
retry UDC binding every 6 seconds until the gadget is bound
write "S22_NATIVE_INIT_USB_ACM_M5 READY" to ttyGS0 when it opens
park forever with heartbeat kmsg lines
```

It does not start Android or Magisk, does not mount persistent partitions, does
not write block devices, does not touch watchdog, and does not auto-reboot.

## USB Module Chain

The ramdisk injects the M2 USB-first bundle under:

```text
/lib/modules/s22plus-m5
```

Module count:

```text
26
```

Total module bytes:

```text
2854024
```

Order:

```text
phy-msm-ssusb-qmp.ko
phy-msm-snps-eusb2.ko
dwc3-msm.ko
usb_f_diag.ko
usb_f_qdss.ko
usb_f_gsi.ko
usb_f_conn_gadget.ko
usb_f_ss_mon_gadget.ko
usb_f_ss_acm.ko
repeater.ko
redriver.ko
usb_notify_layer.ko
usb_notifier_qcom.ko
ipa_fmwk.ko
usb_bam.ko
sps_drv.ko
switch_class.ko
common_muic.ko
vbus_notifier.ko
usb_typec_manager.ko
if_cb_manager.ko
pdic_notifier_module.ko
mfd_max77705.ko
pdic_max77705.ko
spu_verify.ko
qc_usb_audio.ko
```

This targets `ss_acm.0`, matching the observed rooted-Android configfs function
name and the shipped `usb_f_ss_acm.ko` module.

## Built Artifact

Private output directory:

```text
workspace/private/outputs/s22plus_native_init/inplace_m5_usb_acm_v0_2
```

Boot-only Odin package:

```text
workspace/private/outputs/s22plus_native_init/inplace_m5_usb_acm_v0_2/odin4/AP.tar.md5
```

Package member list:

```text
boot.img.lz4
```

Hashes:

```text
AP.tar.md5                  0085679f89e50625a76ccb02dabc6275a5f324acb798d9d98138de21d01c2769
AP.tar                      cd00a82836be3e156d174858d54a632516ec1139cdee58111e0da9a59c51c32c
boot.img                    1cef2fdee227efc4ae48063cb79e27cfd0c36e7dd8d4dd23eb1825cd577b019f
boot.img.lz4                882131883b485d764de3ab5fd2306aa4ccec37270eea94705d7ccd934dbcef25
base Magisk boot            2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
no-change repack boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
M5 /init                    63b61ed65be23e325421cc7f5443fb339f59c204de2a0ee142af5f4cbb3374e4
source                      4fbfd678409ff92b17b2414f228eacd31cad31f04455d41da744311c51eb7554
module bundle manifest      1c22c93496e03a7df6dd74959511797b6d033b74361d3d3733d7be8269a5fa05
original Magisk /init       383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468
ramdisk before              e4654429abca10df94e5145a05853f14620b9e1cd1c7642959981f49c8454aae
ramdisk after               3783befdd409c5209e9a9fd693f0ccbebec7944265788a020619035442b23b03
```

Sizes:

```text
AP.tar.md5                  100669481
boot.img                    100663296
boot.img.lz4                100663699
M5 /init                    663456
module bundle total         2854024
ramdisk before              1492480
ramdisk after               4814884
```

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m5_usb_acm.py
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror -o /tmp/s22plus_init_usb_acm_m5_test workspace/public/src/native-init/s22plus_init_usb_acm_m5.c
python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m5_usb_acm.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m5_usb_acm_v0_2/odin4/AP.tar.md5
```

Results:

```text
py_compile: pass
standalone cross-compile: pass
builder: pass
tar members: boot.img.lz4 only
MagiskBoot no-change repack: byte-identical
base boot size: 100663296
patched boot size: 100663296
ramdisk cpio test before rc: 1
ramdisk cpio test after rc: 1
first inserted module extraction hash: match
patched boot kernel hash: unchanged
Odin invalid-device parse gate: reached package check, then failed only at /dev/bus/usb/999/999
```

Required strings found in the built `/init`:

```text
S22_NATIVE_INIT_USB_ACM_M5
version=0.2
usb_first_modules=26
gadget=ss_acm.0
tty=/dev/ttyGS0
no_android_handoff=1
no_auto_reboot=1
udc_bind_retry=1
finit_rc
ss_acm.0
ttyGS0
```

The built `/init` is an AArch64 static executable and has no dynamic loader
interpreter segment in the recorded `readelf` program headers.

## Safety State

This is not live-authorized. Before any M5 flash, add a fresh SHA-pinned S22+
boot-only `AGENTS.md` exception and a guarded live helper/dry-run for exactly:

```text
AP.tar.md5  0085679f89e50625a76ccb02dabc6275a5f324acb798d9d98138de21d01c2769
boot.img    1cef2fdee227efc4ae48063cb79e27cfd0c36e7dd8d4dd23eb1825cd577b019f
```

M5 has no auto-reboot path. A live test must be attended with pinned Magisk
boot rollback staged. If the ACM channel enumerates and becomes usable, it may
become the recovery/control channel for the session. If it does not enumerate,
rollback requires manual download-mode entry before flashing the pinned Magisk
boot-only AP.

## Interpretation

M5 is ready as a host-built candidate, not as a live result. It packages the
right next experiment: stop spending one flash per syscall, and attempt to earn
the A90-style USB serial control channel directly from native PID1.

The main remaining technical risk is that this M5 `/init` is a static C/glibc
binary with more startup/runtime surface than the raw M4T2/M4T3 assembly probes.
That is acceptable for the control-channel candidate, but live evidence must be
interpreted accordingly: a failure may be in glibc startup, virtual filesystem
mounting, module insertion, configfs setup, UDC binding, or ACM tty creation.
