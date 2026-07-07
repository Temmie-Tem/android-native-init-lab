# S22+ Native-Init M13 No-Module Configfs Park Host Build - 2026-07-07

## Verdict

M13 host-only build passed. No live flash was run.

M13 is the first shrink below the M12 live boot loop. It keeps the M12
freestanding PID1, minimal filesystem setup, configfs `ss_acm.0` gadget
attempt, USB role-force attempt, `a600000.dwc3`-only bind policy, and
no-reboot park loop. The intentional reduction is that M13 removes all runtime
module insertion and does not inject a boot-ramdisk module-list payload.

This candidate separates the next live branch:

```text
M13 parks/no ACM:
  M12 loop was likely introduced by runtime module insertion or module-source
  access. Reintroduce module work in smaller groups only after the floor is
  stable.

M13 still loops:
  the loop is below module insertion. Next shrink removes configfs/role-force
  and keeps only freestanding PID1 + marker + bounded park.

M13 parks + ACM:
  configfs/role-force path can expose control without module insertion; move to
  command handling and recovery planning.
```

## Artifacts

```text
source                 workspace/public/src/native-init/s22plus_init_usb_acm_m13_nomodule_configfs_park.c
builder                workspace/public/src/scripts/revalidation/build_s22plus_inplace_m13_nomodule_configfs_park.py
output                 workspace/private/outputs/s22plus_native_init/inplace_m13_nomodule_configfs_park_v0_1
AP.tar.md5             5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa
boot.img               21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b
M13 /init              6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3
source                 4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

AP tar contents:

```text
boot.img.lz4
```

## M13 Runtime

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
construction=magiskboot unpack/repack; replace ramdisk /init only
module_insertions=false
module_binary_injection=false
module_list_files_injected_into_boot_ramdisk=0
module_files_injected_into_boot_ramdisk=0
configfs_runtime_gadget=ss_acm.0 only
udc_binding=a600000.dwc3 only; never dummy_udc.0
usb_role_force=attempt /sys/class/usb_role/*/role=device
block_device_writes=false
```

Required strings present in the stripped `/init`:

```text
S22_NATIVE_INIT_USB_ACM_M13
version=0.1
runtime=freestanding
raw_syscalls=1
module_insertions=absent
module_list_payload=absent
configfs_runtime_gadget=ss_acm.0
no_reboot_beacon=1
acm_cmd_status=1
a600000.dwc3
role_force=device
ss_acm.0
ttyGS0
S22M13ACM0001
S22_NATIVE_INIT_USB_ACM_M13 READY
S22_NATIVE_INIT_USB_ACM_M13 ACK status park
```

Forbidden runtime properties verified:

```text
program interpreter absent
download string absent from stripped /init
arm64 __NR_reboot=142 load absent from objdump
arm64 __NR_finit_module=273 load absent from objdump
/lib/modules string absent from stripped /init
.ko string absent from stripped /init
modules.load/modules.dep strings absent from stripped /init
M11/M12 module-list payload strings absent from stripped /init
```

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_inplace_m13_nomodule_configfs_park.py
aarch64-linux-gnu-gcc -fsyntax-only -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -Os -Wall -Wextra -Werror workspace/public/src/native-init/s22plus_init_usb_acm_m13_nomodule_configfs_park.c
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_inplace_m13_nomodule_configfs_park.py --force
tar -tf workspace/private/outputs/s22plus_native_init/inplace_m13_nomodule_configfs_park_v0_1/odin4/AP.tar.md5
strings -a workspace/private/outputs/s22plus_native_init/inplace_m13_nomodule_configfs_park_v0_1/build/s22plus_init_usb_acm_m13
aarch64-linux-gnu-objdump -d workspace/private/outputs/s22plus_native_init/inplace_m13_nomodule_configfs_park_v0_1/build/s22plus_init_usb_acm_m13
```

Build gates confirmed:

```text
no-change MagiskBoot repack byte-identical to base boot
patched kernel hash preserved
ramdisk replaced entry init mode 750
no module-list entry added
no module binaries injected into boot ramdisk
AP tar member list exactly ["boot.img.lz4"]
```

## Live Status

No live flash is authorized by this host-build unit.

Next bounded unit, if selected, is M13 live-gate preflight only: add a fresh
SHA-pinned `AGENTS.md` boot-only exception and a guarded helper that verifies
the exact M13 hashes above plus the pinned Magisk/stock rollback APs. Because
M13 deliberately has no reboot beacon, the live gate must remain attended and
must assume manual download-mode rollback if the device parks or loops with no
Android transport.
