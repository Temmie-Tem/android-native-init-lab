# S22+ M31B Watchdog-Managed Park Host Build (2026-07-09)

## Verdict

HOST-ONLY BUILD PASS. No flash, reboot, Odin action, partition write, or device
write was run for this unit.

M31B is the first PMIC/PON watchdog-ceiling discriminator after the M30/M21A
RDX photo was corrected to `PMIC abnormal reset`. The candidate does not request
Download mode. It loads only the stock watchdog dependency closure and then
parks, so a future live gate can answer whether the early native PID1 reset is
caused by starving a pre-armed watchdog.

Live flashing is not authorized by this report.

## Candidate

Source:

`workspace/public/src/native-init/s22plus_init_m31b_wdt_managed_park.c`

Builder:

`workspace/public/src/scripts/revalidation/build_s22plus_m31b_wdt_managed_park.py`

Private output:

`workspace/private/outputs/s22plus_native_init/m31b_wdt_managed_park_v0_1`

Runtime shape:

```text
freestanding AArch64 PID1
minimal /proc /sys /dev /run setup
create /dev/kmsg only for bounded marker/result logging
read /s22plus_m31b_wdt_managed.modules
finit_module() only the stock watchdog dependency closure
park forever with 10 second nanosleep cadence
no reboot syscall
no Download beacon
no USB/configfs/ACM
no Android/Magisk handoff
no persistent partition mount or block write
```

## Watchdog Closure

The closure is derived from the extracted FYG8 vendor ramdisk `modules.dep` and
checked against a fixed expected list:

```text
smem.ko
minidump.ko
qcom-scm.ko
qcom_wdt_core.ko
gh_virt_wdt.ko
```

The generated ramdisk module-list payload is:

```text
smem.ko
minidump.ko
qcom-scm.ko
qcom_wdt_core.ko
gh_virt_wdt.ko
```

The builder rejects forbidden drift into unrelated or previously suspect paths:
`qcom_soc_wdt.ko`, `sec_qc_qcom_wdt_core.ko`, `phy-msm-ssusb-qmp.ko`,
`dwc3-msm.ko`, `usb_f_ss_acm.ko`, and `eud.ko`.

## Hashes

```text
source              32d85b4aeb64e5e1615b175b93fde166795598bfa0614934a9dcfb1bb165230d
base_boot           2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
nochange_repack     2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
original_magisk_init 383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468
kernel              bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
m31b_init           b01e52d3762e3cbdcba3501b00bb1dc9f9084899550ea23b92df43884bed23d0
m31b_wdt_modules    80da959311e4a0f6bedb40da3c6f74c7fd5918017e40e0787b3e17c153cfe937
boot_img            206fbb40df69a496f7fbe67e32cf862049d9258ef518db6949e1b5db2f4afdc4
boot_img_lz4        f249236d9ce234f34c598515fac6a98cf301c769474f183a475927f14fa0e280
AP.tar.md5          06d1c149c7c09a284062826f21ac848220e99d552d6b91762abbfb80f3679527
```

AP member list:

```text
boot.img.lz4
```

## Static Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m31b_wdt_managed_park.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m31b_wdt_managed_park.py \
  --force

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_s22plus_m31b_wdt_managed_park_build
```

Results:

- `py_compile`: pass.
- Builder: pass.
- Unit tests: 4 tests pass.
- Magiskboot no-change repack is byte-identical to the rooted Magisk base boot.
- Patched boot remains boot-partition sized.
- Patched boot preserves the Magisk-patched kernel SHA256
  `bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`.
- AP tar has exactly one member, `boot.img.lz4`.
- Final `/init` is AArch64, static, no PT_INTERP.
- Final `/init` loads arm64 `__NR_finit_module` (273).
- Final `/init` does not load arm64 `__NR_reboot` (142).
- Required strings are present:
  `S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK`, `version=0.1`,
  `observation=watchdog-managed-park`, `no_reboot_request=1`,
  `no_download_beacon=1`, `module_count=5`,
  `/s22plus_m31b_wdt_managed.modules`, `phase=modules_load_done`, and
  `phase=park_enter`.
- Forbidden strings are absent: `reboot_request=download`, `ttyGS0`,
  `ss_acm.0`, `/config`, `usb_gadget`, dynamic loader, and libc.

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
module_list_path=/s22plus_m31b_wdt_managed.modules
configfs_runtime_gadget=false
usb_role_force=false
acm=false
```

## Future Live Interpretation

A future M31B live gate is meaningful only under a fresh SHA-pinned boot-only
`AGENTS.md` exception and a fail-closed helper.

PASS:

- Candidate boots and does not show PMIC/RDX abnormal reset past the selected
  observation window, initially 60-120 seconds.
- No host-observed fast loop.
- No automatic Download claim is made; this is a park candidate.
- Operator manually enters Download mode only for rollback after the observation
  window, and the helper records that as recovery, not proof of self-Download.
- Rollback restores the pinned Magisk boot baseline.

FAIL / NO-PROOF:

- PMIC/RDX abnormal reset appears before the observation window completes.
- Repeated bootloop or kernel panic appears.
- Host endpoint appears in a way inconsistent with the park-only design.
- Rollback cannot restore the Magisk baseline.

## Next

Do not flash M31B from this report alone. The next unit, if live testing is
selected, must add a fresh M31B-only `AGENTS.md` exception and a guarded helper
that verifies these exact hashes, refuses non-boot payloads, uses no auto-reboot,
observes the dwell, and treats manual Download only as rollback recovery.
