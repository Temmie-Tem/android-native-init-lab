# S22+ Native-Init M17 Power-QMP Host Build - 2026-07-08

## Verdict

PASS: host-only M17 candidate built and statically validated. No flash or
write to the device was performed.

The operator reported another bootloop observation while the project was on
the M15/M16 PHY split path. A read-only host check after that report found the
phone back on the rooted Android/Magisk baseline: `boot_completed=1`,
`bootanim=stopped`, orange verified boot, Magisk root available, and pstore
file count `0`. Treat the device as recovered, but do not repeat the naked-QMP
line of testing.

## Why M17

M15 showed that the two PHY-side modules loop. M16 was a host-only build that
would test `phy-msm-ssusb-qmp.ko` naked, but the later operator steer corrected
the method: a Qualcomm QMP PHY should not be probed before its power/clock
substrate is present.

M17 therefore starts from the stable M13 no-module park floor and adds only the
power/clock substrate dependency closure plus `phy-msm-ssusb-qmp.ko`. It still
withholds:

- the other PHYs: `phy-generic.ko`, `phy-msm-snps-hs.ko`,
  `phy-msm-snps-eusb2.ko`
- `dwc3-msm.ko` and USB function drivers
- role/PD/glink stack modules
- watchdog modules

This keeps the next live discriminator to park-vs-loop for powered QMP only.

## Artifact

- Output: `workspace/private/outputs/s22plus_native_init/inplace_m17_power_qmp_v0_1/odin4/AP.tar.md5`
- AP.tar.md5 SHA256: `78b2641788a1517f39bdbd50dc425dbaeab0683aa662bcd8bfe9c925a8a50274`
- boot.img SHA256: `090811c8f50aab753ef7f085c3cf5bd73e9d6d43e2ad629e95d2cfe48a0ecac2`
- M17 `/init` SHA256: `34389fc52cd74aa50b2ab2980075183bcde519ffc5d7f9dfb787e1e5b3e2bfe4`
- M17 module list SHA256: `1e00da43ae2b22c56855a28967201733b66b65ec4e91086faa67a4d9b3177fb8`
- Source SHA256: `561099a8401ea6b5d5642614b6f6a73e225b239556de07c11cf2d99e1d0a6d2f`
- Base Magisk boot SHA256: `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`
- Kernel SHA256: `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`

AP tar members:

```text
boot.img.lz4
```

## Runtime Shape

M17 preserves the M13/M16 freestanding raw-syscall PID1 shape:

- minimal `/proc`, `/sys`, `/dev`, `/config` setup
- emits `S22_NATIVE_INIT_USB_ACM_M17`
- reads `/s22plus_m17_power_qmp.modules`
- `finit_module` for the listed modules from stock vendor_boot `/lib/modules`
- attempts role force to `device`
- attempts `ss_acm.0` gadget bind only to `a600000.dwc3`
- parks forever; no reboot beacon

Required strings were present:

```text
S22_NATIVE_INIT_USB_ACM_M17
module_group=power_qmp
module_count=21
S22_NATIVE_INIT_USB_ACM_M17 READY
S22_NATIVE_INIT_USB_ACM_M17 ACK status park
```

## Module List

```text
clk-rpmh.ko
gcc-waipio.ko
icc-rpmh.ko
qcom_ipc_logging.ko
rpmh-regulator.ko
clk-dummy.ko
clk-qcom.ko
cmd-db.ko
debug-regulator.ko
gdsc-regulator.ko
icc-bcm-voter.ko
icc-debug.ko
minidump.ko
qti-fixed-regulator.ko
proxy-consumer.ko
qcom_rpmh.ko
qcom-scm.ko
sec_debug.ko
smem.ko
socinfo.ko
phy-msm-ssusb-qmp.ko
```

Dependency closure count is `21`. `blocked_from_closure=[]` and
`blocked_watchdogs_present_in_closure=[]`.

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m17_power_qmp_park.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m17_power_qmp_park.py --force
```

Additional checks:

- `/init` is static ARM aarch64, stripped, no interpreter.
- `magiskboot` no-change unpack/repack of the base boot was byte-identical.
- patched boot preserved the base kernel hash.
- AP tar contains exactly `boot.img.lz4`.
- module binaries injected into boot ramdisk: `0`
- module-list files injected into boot ramdisk: `1`
- no arm64 `__NR_reboot=142` in the intended `mov x8` syscall path.
- arm64 `__NR_finit_module=273` is present by design.
- forbidden strings absent from `/init`: `ld-linux`, `libc.so`, `/vendor_dlkm`,
  `modules.load.recovery`, `download`.

## Next

No live flash is authorized by this report. Next live use needs a fresh
SHA-pinned S22+ boot-only `AGENTS.md` exception plus a guarded helper/dry-run
for exactly this AP/boot hash. If live-tested, the expected proof is:

- parks or ACM appears: powered QMP no longer causes the loop; proceed to the
  next add-back rung
- bootloops: QMP still faults even with substrate; stop blind subset work and
  wait for UART-quality evidence
