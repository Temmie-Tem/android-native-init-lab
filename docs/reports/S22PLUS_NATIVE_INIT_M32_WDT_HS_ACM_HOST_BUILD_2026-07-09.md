# S22+ M32 Watchdog-Managed HS ACM Host Build (2026-07-09)

## Verdict

HOST-ONLY BUILD PASS. No flash, reboot, Odin action, partition write, or device
write was run for this unit.

M32 is the first observable-transport candidate after M31B proved that loading
the stock watchdog closure can survive the prior 30 second PMIC/PON ceiling. It
keeps the M31B watchdog-managed base, adds the dependency-complete HS-only USB
ACM closure from the M28/M25 substrate, excludes the suspect QMP/EUD paths, and
parks without a Download beacon.

Live flashing is not authorized by this report.

## Candidate

Builder:

`workspace/public/src/scripts/revalidation/build_s22plus_m32_wdt_hs_acm.py`

Generated source:

`workspace/private/outputs/s22plus_native_init/m32_wdt_hs_acm_v0_1/build/s22plus_init_usb_acm_m32_wdt_hs.c`

Private output:

`workspace/private/outputs/s22plus_native_init/m32_wdt_hs_acm_v0_1`

Runtime shape:

```text
freestanding AArch64 PID1
minimal runtime setup inherited from the M18 USB/ACM template
read /s22plus_m32_wdt_hs_acm.modules
finit_module() dependency-complete watchdog + HS USB/ACM module closure
force USB role=device
create runtime configfs ss_acm.0 gadget
open ttyGS0 command loop
park without reboot request
no Download beacon
no Android/Magisk handoff
no persistent partition mount or block write
```

## Module Closure

The closure is derived from the extracted FYG8 vendor ramdisk `modules.dep` and
checked against a fixed expected list. The generated module-list payload has 45
entries and SHA256
`2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c`.

```text
smem.ko
minidump.ko
sec_debug.ko
qcom_ipc_logging.ko
cmd-db.ko
qcom_rpmh.ko
clk-rpmh.ko
debug-regulator.ko
proxy-consumer.ko
gdsc-regulator.ko
clk-qcom.ko
clk-dummy.ko
gcc-waipio.ko
icc-bcm-voter.ko
icc-debug.ko
socinfo.ko
icc-rpmh.ko
rpmh-regulator.ko
qcom-scm.ko
qcom_wdt_core.ko
gh_virt_wdt.ko
iommu-logger.ko
qnoc-qos.ko
qnoc-waipio.ko
phy-generic.ko
qcom_iommu_util.ko
sec_class.ko
secure_buffer.ko
arm_smmu.ko
abc.ko
usb_notify_layer.ko
switch_class.ko
common_muic.ko
vbus_notifier.ko
pdic_notifier_module.ko
usb_typec_manager.ko
usb_f_ss_mon_gadget.ko
phy-msm-snps-hs.ko
repeater.ko
phy-msm-snps-eusb2.ko
redriver.ko
if_cb_manager.ko
qc_usb_audio.ko
dwc3-msm.ko
usb_f_ss_acm.ko
```

Hard exclusions:

```text
eud.ko
phy-msm-ssusb-qmp.ko
sec_debug_region.ko
ucsi_glink.ko
```

## Hashes

```text
base_boot            2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
nochange_repack      2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
generated_source     ad1b94c144faa3ba3dd232110a07a7680ce5aa7c796061158e0cd75c3edd37b2
m32_init             0595a0e932fa0ca7240192e2438d134ca8e4338a48e68a17edb8d9b023dc8f77
m32_modules          2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c
kernel               bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
boot_img             8001809f9f0d7b2d6615bdec97843680a0c20721d679dde74a76bbe6d95bb9ca
boot_img_lz4         8bf41568e59880ecccb2c9d638208406b134a11a2e2045fef0897beec3dd99b4
AP.tar.md5           b2dee88862cbbfa8e9da799978c10134a07f41e4d144c23b2db1d0b8e00adbd4
```

AP member list:

```text
boot.img.lz4
```

## Static Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m32_wdt_hs_acm.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m32_wdt_hs_acm.py \
  --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m32_wdt_hs_acm_build

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m31b_wdt_managed_park_build \
  tests.test_s22plus_m28_dep_complete_download_build
```

Results:

- `py_compile`: pass.
- Builder: pass.
- M32 unit tests: 5 tests pass.
- Adjacent M31B/M28 regression tests: 10 tests pass.
- MagiskBoot no-change repack is byte-identical to the rooted Magisk base boot.
- Patched boot remains boot-partition sized.
- Patched boot preserves the Magisk-patched kernel SHA256
  `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`.
- AP tar has exactly one member, `boot.img.lz4`.
- Final `/init` is AArch64, static, no PT_INTERP.
- Final `/init` loads arm64 `__NR_finit_module` (273).
- Final `/init` does not load arm64 `__NR_reboot` (142).
- Required strings are present:
  `S22_NATIVE_INIT_USB_ACM_M32_WDT_HS`, `version=0.1`,
  `module_list=dep_complete_wdt_hs_acm`, `watchdog_managed=1`,
  `wdt_closure=1`, `dep_complete=1`, `hs_only=1`, `qmp_excluded=1`,
  `dtbo_high_speed_cap=not_included`, `module_count=45`,
  `no_reboot_beacon=1`, `acm_cmd_status=1`, `a600000.dwc3`,
  `role_force=device`, `ss_acm.0`, `ttyGS0`, and `0x0200`.
- Forbidden strings are absent from `/init`: dynamic loader, libc,
  `/vendor_dlkm`, `download`, `LINUX_REBOOT`, `watchdog_blocklist=1`,
  `phy-msm-ssusb-qmp.ko`, and `super-speed`.

## Manifest Safety State

The manifest records:

```text
boot_only=true
host_only_build=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
base_is_known_booting_magisk_boot=true
construction=magiskboot unpack/repack; replace ramdisk /init and add one text module list
runtime=freestanding-raw-syscall
mkbootimg_from_scratch=false
no_android_or_magisk_handoff=true
auto_reboot=false
intended_reboot_syscall=false
reboot_request=null
persistent_partition_mount=false
block_device_writes=false
module_binary_injection=false
module_list_path=/s22plus_m32_wdt_hs_acm.modules
configfs_runtime_gadget=ss_acm.0 only
usb_role_force=true
acm=true
watchdog_managed=true
qmp_module_excluded=true
dtbo_high_speed_cap_included=false
```

## Future Live Interpretation

A future M32 live gate is meaningful only under a fresh SHA-pinned boot-only
`AGENTS.md` exception and a fail-closed helper.

PASS:

- Candidate survives the observation window without PMIC/RDX reset.
- Host sees an ACM/ttyGS0 endpoint from the runtime configfs gadget.
- No self-Download claim is made; this is a parked transport candidate.
- Rollback restores the pinned Magisk boot baseline.

FAIL / NO-PROOF:

- PMIC/RDX abnormal reset appears before or during the observation window.
- No ACM endpoint appears before the bounded observation timeout.
- Host sees only Odin/Download/RDX instead of the intended ACM transport.
- Rollback cannot restore the Magisk baseline.

## Next

Do not flash M32 from this report alone. The next unit, if live testing is
selected, must add a fresh M32-only `AGENTS.md` exception and a guarded helper
that verifies these exact hashes, refuses non-boot payloads, uses no auto-reboot,
observes survival plus ACM enumeration, and treats manual Download only as
rollback recovery.
