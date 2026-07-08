# S22+ Native-Init M23 DTS-Exact QMP Host Build - 2026-07-08

## Verdict

PASS: host-only M23 candidate built and statically validated. No flash, reboot,
partition write, sysfs write, or device action was performed.

M23 implements the current no-EUD pivot: derive a narrow QMP/DWC3 USB module
closure from the stock vendor DTB instead of loading Android's full first-stage
module set.

## Public Source

- Builder:
  `workspace/public/src/scripts/revalidation/build_s22plus_inplace_m23_dts_exact_qmp_park.py`
- Runtime template:
  `workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c`
- Generated runtime source is private build output:
  `workspace/private/outputs/s22plus_native_init/inplace_m23_dts_exact_qmp_v0_1/build/s22plus_init_usb_acm_m23_dts_exact_qmp.c`

## Private Artifact

- Output:
  `workspace/private/outputs/s22plus_native_init/inplace_m23_dts_exact_qmp_v0_1`
- Odin AP:
  `workspace/private/outputs/s22plus_native_init/inplace_m23_dts_exact_qmp_v0_1/odin4/AP.tar.md5`
- AP member set: `boot.img.lz4` only.
- Boot ramdisk changes:
  - replaced `/init`, mode `750`
  - added `/s22plus_m23_dts_exact_qmp.modules`, mode `640`
  - injected zero module binaries into boot ramdisk

## Artifact Hashes

| Artifact | SHA256 |
| --- | --- |
| `AP.tar.md5` | `558eddb4b78b68c86d65f171072145c63210e9b33b5d0b56f2a3e4a00f0ba2d8` |
| `boot.img` | `277bf33c0f7cc62fe2b635b83c22b052d35a4e97dfb2e1cadaf60fdcb961184e` |
| `/init` | `745131e23a657905542697cc1c0573a87e484df2e9a06810344d8d4d0be6f357` |
| module list | `a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349` |
| generated source | `75610dbd2148017708300aaf5c37b169d12a6a87ec30ed5d96e753708654c9c0` |
| base Magisk boot | `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e` |
| kernel | `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff` |
| vendor DTB | `2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e` |

## DTS Derivation

The builder parses all four stock vendor DTB blobs and requires them to derive
the same closure. Target nodes:

- `/soc/ssusb@a600000`
- `/soc/ssusb@a600000/dwc3@a600000`
- `/soc/hsphy@88e3000`
- `/soc/ssphy@88e8000`

Seed modules:

- `arm_smmu.ko`
- `clk-rpmh.ko`
- `dwc3-msm.ko`
- `gcc-waipio.ko`
- `gdsc-regulator.ko`
- `phy-generic.ko`
- `phy-msm-snps-eusb2.ko`
- `phy-msm-snps-hs.ko`
- `phy-msm-ssusb-qmp.ko`
- `pinctrl-waipio.ko`
- `qnoc-waipio.ko`
- `rpmh-regulator.ko`
- `usb_f_ss_acm.ko`

The final transitive closure is 43 modules in stock `modules.load.recovery`
order. Blocked dependency edges are intentionally not loaded:

- `abc.ko`
- `minidump.ko`
- `sec_debug.ko`

EUD handling: the DTB extcon reference to `/soc/qcom,msm-eud@88e0000` is
detected but excluded. This candidate does not load, open, or enable EUD because
Phase-B proved the retail EUD attach path is TrustZone-gated (`rc:-22`).

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
iommu-logger.ko
pinctrl-waipio.ko
qnoc-waipio.ko
phy-generic.ko
pinctrl-msm.ko
proxy-consumer.ko
qcom_iommu_util.ko
qcom_rpmh.ko
qcom-scm.ko
qnoc-qos.ko
sec_class.ko
secure_buffer.ko
smem.ko
socinfo.ko
arm_smmu.ko
phy-msm-ssusb-qmp.ko
phy-msm-snps-hs.ko
phy-msm-snps-eusb2.ko
dwc3-msm.ko
usb_f_ss_mon_gadget.ko
usb_f_ss_acm.ko
repeater.ko
redriver.ko
usb_notify_layer.ko
switch_class.ko
common_muic.ko
vbus_notifier.ko
usb_typec_manager.ko
if_cb_manager.ko
pdic_notifier_module.ko
qc_usb_audio.ko
```

## Runtime Shape

Generated `/init` preserves the M18 freestanding raw-syscall park shape, but
with M23 identifiers and the 43-module DTS-exact list:

```text
S22_NATIVE_INIT_USB_ACM_M23_DTS_QMP
/s22plus_m23_dts_exact_qmp.modules
module_group=dts_exact_qmp
module_count=43
S22_NATIVE_INIT_USB_ACM_M23_DTS_QMP READY
S22_NATIVE_INIT_USB_ACM_M23_DTS_QMP ACK status park
```

The binary contains no `download`, `M18_FULL`, or `full_firststage` runtime
strings. It has no interpreter and no arm64 `__NR_reboot=142` path.

## Validation

Commands run:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m23_dts_exact_qmp_park.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_inplace_m23_dts_exact_qmp_park.py --force

aarch64-linux-gnu-gcc -fsyntax-only -nostdlib -static -ffreestanding \
  -fno-builtin -fno-stack-protector -Os -Wall -Wextra -Werror \
  workspace/private/outputs/s22plus_native_init/inplace_m23_dts_exact_qmp_v0_1/build/s22plus_init_usb_acm_m23_dts_exact_qmp.c

tar -tf \
  workspace/private/outputs/s22plus_native_init/inplace_m23_dts_exact_qmp_v0_1/odin4/AP.tar.md5

wc -l \
  workspace/private/outputs/s22plus_native_init/inplace_m23_dts_exact_qmp_v0_1/build/s22plus_m23_dts_exact_qmp.modules
```

Results:

- builder completed successfully
- Python bytecode compile passed
- freestanding AArch64 syntax check passed
- `magiskboot` no-change unpack/repack of the base boot was byte-identical
- patched boot preserved the base kernel hash
- AP tar contains exactly `boot.img.lz4`
- module list has exactly 43 lines
- manifest records `live_flash_authorized=false`

## Next

No live flash is authorized by this report. The next live-capable unit, only
after explicit operator approval, is a fresh SHA-pinned `AGENTS.md` exception
and guarded dry-run/live helper for this exact M23 AP.

Expected live signal:

- ACM enumerates: M23 closed the missing substrate enough to reach the control
  channel.
- bootloop/no ACM: stop treating EUD/retained logs as useful for this class and
  move to UART or another real-time console path.
