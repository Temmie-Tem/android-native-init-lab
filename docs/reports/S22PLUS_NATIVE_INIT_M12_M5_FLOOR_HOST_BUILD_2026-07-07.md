# S22+ Native-Init M12 M5-Floor Host Build - 2026-07-07

## Verdict

M12 host-only build passed. No live flash was run.

M12 is the next bounded candidate after the M11 live boot loop. It keeps the
M11 freestanding PID1, minimal filesystem setup, configfs `ss_acm.0` gadget,
USB role-force, `a600000.dwc3`-only bind policy, and no-reboot park loop. The
only intentional behavioral reduction is the module list: M12 loads the 24
modules common to M5 v0.4 and M11, in M5 order, from stock vendor_boot
`/lib/modules`. It withholds the 24 M11-only substrate modules and the two
M5-only modules until the floor behavior is live-known.

## Artifacts

```text
source                 workspace/public/src/native-init/s22plus_init_usb_acm_m12_m5_floor.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m12_m5_floor.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m12_m5_floor_v0_1
AP.tar.md5             deece127aa5c85dbf4937459fc528f2cfcd9926fb3556f26ffc9b10fbfe932cb
boot.img               f211e46c7153df31c458a907f4ac56fe4a3d160d8ded2a13a8e0e31af6f5106c
M12 /init              50ae525230680c495d3c40fc671cb88118e8bd473cef92873266142549a28002
M12 module list        c2e44f6f934542f8f7889ef09245294ee342c5ae03a0f6db9988b58b943ddc16
source                 5b43593a24b3b03a667f5515b8a558e40121b4da091efb56adf383ea50240392
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
vendor ramdisk         41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193
```

AP tar contents:

```text
boot.img.lz4
```

## M12 Runtime

Safety flags from the manifest:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
runtime=freestanding-raw-syscall
auto_reboot=false
reboot_syscall=false
host_commanded_reboot_download=false
observation_model=park-vs-loop plus host ACM enumeration; no reboot beacon
construction=magiskboot unpack/repack; replace ramdisk /init only
module_binary_injection=false
module_list_path=/s22plus_m12_m5_floor.modules
module_list_files_injected_into_boot_ramdisk=1
module_files_injected_into_boot_ramdisk=0
configfs_runtime_gadget=ss_acm.0 only
udc_binding=a600000.dwc3 only; never dummy_udc.0
usb_role_force=attempt /sys/class/usb_role/*/role=device
block_device_writes=false
```

Required strings present in the stripped `/init`:

```text
S22_NATIVE_INIT_USB_ACM_M12
version=0.1
runtime=freestanding
raw_syscalls=1
/s22plus_m12_m5_floor.modules
module_list=boot_ramdisk_m5_floor
watchdog_blocklist=1
no_reboot_beacon=1
acm_cmd_status=1
module_source=stock_vendor_boot_ramdisk
module_injection=list_only
a600000.dwc3
role_force=device
ss_acm.0
ttyGS0
S22M12ACM0001
S22_NATIVE_INIT_USB_ACM_M12 READY
S22_NATIVE_INIT_USB_ACM_M12 ACK status park
```

Forbidden runtime properties verified:

```text
program interpreter absent
download string absent from stripped /init
arm64 __NR_reboot=142 load absent from objdump
modules.load.recovery string absent from stripped /init
/vendor_dlkm string absent from stripped /init
s22plus-m5 string absent from stripped /init
```

## Module Floor

M12 module list:

```text
subset_count=24
subset_bytes=391
order_source=M5 v0.4 order filtered to modules common with M11
M11-only reference count=24
M5-only withheld modules=usb_notifier_qcom.ko, qc_usb_audio.ko
```

Injected text list:

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
```

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m12_m5_floor.py
aarch64-linux-gnu-gcc -fsyntax-only -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -Os -Wall -Wextra -Werror workspace/public/src/native-init/s22plus_init_usb_acm_m12_m5_floor.c
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m12_m5_floor.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m12_m5_floor_v0_1/odin4/AP.tar.md5
strings -a workspace/private/outputs/s22plus_native_init/inplace_m12_m5_floor_v0_1/build/s22plus_init_usb_acm_m12
aarch64-linux-gnu-objdump -d workspace/private/outputs/s22plus_native_init/inplace_m12_m5_floor_v0_1/build/s22plus_init_usb_acm_m12
```

Build gates confirmed:

```text
no-change MagiskBoot repack byte-identical to base boot
patched kernel hash preserved
ramdisk replaced entry init mode 750
added module-list entry s22plus_m12_m5_floor.modules mode 640
AP tar member list exactly ["boot.img.lz4"]
vendor .ko count 441
modules.load.recovery count 446
modules.dep count 441
dwc3_msm softdep line present
no module binaries injected into boot ramdisk
```

## Live Status

No live flash is authorized by this host-build unit.

Next bounded unit, if selected, is M12 live-gate preflight only: add a fresh
SHA-pinned `AGENTS.md` boot-only exception and a guarded helper that verifies
the exact M12 hashes above plus the pinned Magisk/stock rollback APs. The live
result should be interpreted as:

```text
M12 parks/no ACM:
  M11-only substrate caused the M11 loop; add M11-only modules back in small groups.

M12 loops:
  the M11 loader/runtime path or vendor_boot source path lost the M5 floor; inspect
  retained logging and shrink again before adding modules.

M12 parks + ACM:
  USB control channel is reached; move to ACM command handling and recovery.
```
