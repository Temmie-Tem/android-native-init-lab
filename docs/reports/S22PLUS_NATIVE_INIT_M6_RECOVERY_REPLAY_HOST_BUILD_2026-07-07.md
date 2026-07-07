# S22+ Native-Init M6 Recovery-Replay Host Build - 2026-07-07

## Verdict

PASS: host-only M6 USB-ACM recovery-module-replay candidate built and statically
validated.

No live flash was run. Live flash is not authorized, and the current M5B
incident was still recovery-pending at the time of this host build. This
package must not be flashed until the phone is recovered to the rooted Magisk
Android baseline and a fresh SHA-pinned `AGENTS.md` boot-only exception is
added for the exact M6 hashes below.

## Why M6

M5 used a 26-module symbol-level USB closure and did not enumerate. The
host-side root-cause analysis found that the closure omitted probe-time platform
dependencies for the real USB controller/PHY/role stack. M6 changes the method:

- keep the freestanding raw-syscall PID1 runtime;
- do not duplicate the 441 vendor `.ko` files into the boot ramdisk;
- rely on the stock `vendor_boot` ramdisk's runtime `/lib/modules`;
- replay `/lib/modules/modules.load.recovery` in vendor order;
- bind only the real UDC, `a600000.dwc3`, never `dummy_udc.0`;
- if needed, attempt `/sys/class/usb_role/*/role = device`;
- create the same bounded `ss_acm.0` command channel and park.

## Added

```text
workspace/public/src/native-init/s22plus_init_usb_acm_m6_recovery_replay.c
workspace/public/src/scripts/revalidation/build_s22plus_inplace_m6_recovery_replay.py
workspace/public/src/scripts/revalidation/s22plus_m6_recovery_replay_live_gate.py
```

Generated private package:

```text
workspace/private/outputs/s22plus_native_init/inplace_m6_recovery_replay_v0_1/odin4/AP.tar.md5
```

## Candidate Hashes

```text
AP.tar.md5             a12bd8f067375cb14ab9043da5bae37d1f93f82c1d70bccd8fa9cef2f616bee9
boot.img               7fe85c5973b930d777a670ac5997b0f26a51fa5b97705f5e467b0cecf501ffd2
M6 /init               7aecdf7a2c936b0785d20f5124667a8d682e9eb9678e77d20893889312860295
source                 ebefc50fdb88947892db0e79900529bdb3351ef2132934757e391a2395410552
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
vendor_ramdisk00       41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193
```

The Odin AP contains exactly one member:

```text
boot.img.lz4
```

## Vendor Ramdisk Gate

The builder verifies the stock FYG8 `vendor_boot` ramdisk before producing the
candidate:

```text
vendor .ko count                 441
modules.load count               140
modules.load.recovery count      446
modules.load.recovery bytes      7239
M6 runtime recovery-list buffer   32768
M6 runtime module-name buffer     128
modules.load.recovery max name    30
modules.load.recovery duplicates  5
modules.dep count                441
vendor .ko total bytes           63764320
module files injected into boot  0
```

The rebuilt manifest also gates that every `modules.load.recovery` entry is a
single `.ko` token with no inline whitespace and that the longest basename
fits the M6 runtime parser buffer (`30 < 128`).

Required recovery-order modules were present. Selected positions:

```text
clk-rpmh.ko             8
rpmh-regulator.ko       15
gdsc-regulator.ko       33
phy-generic.ko          59
msm-geni-se.ko          132
pmic_glink.ko           198
altmode-glink.ko        201
eud.ko                  210
phy-msm-ssusb-qmp.ko    259
phy-msm-snps-hs.ko      260
phy-msm-snps-eusb2.ko   261
dwc3-msm.ko             262
usb_f_ss_acm.ko         273
ucsi_glink.ko           274
i2c-msm-geni.ko         285
usb_typec_manager.ko    379
mfd_max77705.ko         401
pdic_max77705.ko        405
```

The expected softdep line was present:

```text
softdep dwc3_msm pre: phy-generic phy-msm-snps-hs phy-msm-snps-eusb2 phy-msm-ssusb-qmp eud post: ucsi_glink
```

## Build Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m6_recovery_replay.py \
  workspace/public/src/scripts/revalidation/s22plus_m6_recovery_replay_live_gate.py

aarch64-linux-gnu-gcc -nostdlib -static -ffreestanding -fno-builtin \
  -fno-stack-protector -Os -Wall -Wextra -Werror -Wl,-e,_start \
  -o /tmp/s22plus_init_usb_acm_m6_recovery_replay_test \
  workspace/public/src/native-init/s22plus_init_usb_acm_m6_recovery_replay.c

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m6_recovery_replay.py --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m6_recovery_replay_live_gate.py \
  --offline-check
```

Static result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
Type: EXEC
Machine: AArch64
No INTERP/program interpreter
```

The builder required these strings in the final M6 `/init`:

```text
S22_NATIVE_INIT_USB_ACM_M6
/lib/modules/modules.load.recovery
/lib/modules/modules.softdep
module_source=stock_vendor_boot_ramdisk
module_injection=none
a600000.dwc3
role_force=device
ss_acm.0
ttyGS0
S22M6ACM0001
S22_NATIVE_INIT_USB_ACM_M6 READY
S22_NATIVE_INIT_USB_ACM_M6 ACK download
```

Forbidden string gate rejected glibc/dynamic-loader markers, `/vendor_dlkm`, and
the old `s22plus-m5` module path.

MagiskBoot gates:

```text
no-change repack byte-identical  true
patched boot size                100663296
ramdisk before                   1492480
ramdisk after                    1303408
kernel hash unchanged            true
```

Odin invalid-device parse gate:

```text
Check file : .../inplace_m6_recovery_replay_v0_1/odin4/AP.tar.md5
/dev/bus/usb/999/999
No such file or directory
usb device Fail
```

This proves Odin parsed the single-member AP before failing at the intentionally
invalid USB path.

## Guarded Helper

The M6 live helper was added but **not armed**. Current execution used only
`--offline-check`, which verifies the M6 AP, manifest, and pinned rollback APs
without checking AGENTS authorization, without checking Android, and without any
device action:

```text
offline-check ok: M6 candidate and rollback APs verified; no device action
device_action=0
agents_exception_checked=0
android_checked=0
```

Follow-up helper validation also proved the armed paths remain locked while the
M6 `AGENTS.md` exception is absent. Default dry-run, `--live`, and
`--rollback-from-download` each stopped before any device action with:

```text
AGENTS.md missing M6 live authorization markers
rc=1
```

The helper now allocates a unique private run directory if multiple invocations
land in the same UTC second, preventing a host-side `FileExistsError` from
masking the intended AGENTS authorization failure.

After adding the parser-bound manifest gates, the package was rebuilt with the
same AP/boot/init hashes and revalidated:

```text
m6_manifest_parser_gate_audit=pass
offline-check ok
--live without M6 AGENTS exception -> rc=1 before device action
```

Default dry-run, live, and rollback-from-download modes still require the future
SHA-pinned `AGENTS.md` exception. Dry-run/live also require a recovered rooted
Android baseline and current boot hash verification.

## Safety State

M6 is host-build-ready only.

Live preconditions:

1. recover the current M5B incident to the rooted Magisk Android baseline;
2. verify `sys.boot_completed=1`, Magisk root, and boot hash
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
3. add a fresh SHA-pinned `AGENTS.md` S22+ boot-only exception for this exact
   M6 AP and boot hash;
4. add/run a guarded live helper with attended ack and pinned Magisk rollback.

Until those are true, do not flash M6.
