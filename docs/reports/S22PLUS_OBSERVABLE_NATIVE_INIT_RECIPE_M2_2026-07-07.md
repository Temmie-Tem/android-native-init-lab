# S22+ Observable Native-Init Recipe M2 - 2026-07-07

## Scope

Host-only derivation of the first observable-native-init recipe from the M1
Magisk boot-time capture. No adb, device mutation, reboot, Odin transfer,
partition write, or Magisk hook was used in this unit.

Terminology note: "module" in this report means Linux kernel `.ko` module. It
does not mean a Magisk app module. The prior M1 unit also did not install a
Magisk module; it temporarily installed two hook scripts and removed them.

## Inputs

Private M1 capture source:

```text
workspace/private/runs/s22plus_magisk_boot_time_capture_m1_20260706T173432Z/device_capture/s22plus_boot_capture_m1/post_fs_data_19700108T054017Z.txt
```

The input is private because it contains raw boot logs and device state.

## Recipe Builder

Added:

```text
workspace/public/src/scripts/revalidation/s22plus_observable_init_recipe.py
```

Validation:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_observable_init_recipe.py

python3 workspace/public/src/scripts/revalidation/s22plus_observable_init_recipe.py
```

Private output:

```text
workspace/private/outputs/s22plus_observable_init_recipe/s22plus_magisk_boot_time_capture_m1_20260706T173432Z/observable_init_recipe.json
```

## Source Counts

The builder deduplicated the duplicated vendor module metadata from M1:

```text
modules_load_unique_count=356
modules_dep_count=356
proc_modules_count=482
```

Interpretation:

- `modules.load` / `modules.dep` cover 356 shipped vendor modules.
- live `/proc/modules` has 482 entries because built-ins/permanent/generated
  and non-`.ko` module names also appear there.
- M2 uses `modules.load` order as the candidate insertion order and
  `modules.dep` as dependency closure input.

## USB-First Candidate

Combined USB-first dependency closure:

```text
module_count=26
missing_from_modules_load=[]
missing_from_live_proc_modules=[]
```

Candidate order:

```text
01 phy-msm-ssusb-qmp.ko
02 phy-msm-snps-eusb2.ko
03 dwc3-msm.ko
04 usb_f_diag.ko
05 usb_f_qdss.ko
06 usb_f_gsi.ko
07 usb_f_conn_gadget.ko
08 usb_f_ss_mon_gadget.ko
09 usb_f_ss_acm.ko
10 repeater.ko
11 redriver.ko
12 usb_notify_layer.ko
13 usb_notifier_qcom.ko
14 ipa_fmwk.ko
15 usb_bam.ko
16 sps_drv.ko
17 switch_class.ko
18 common_muic.ko
19 vbus_notifier.ko
20 usb_typec_manager.ko
21 if_cb_manager.ko
22 pdic_notifier_module.ko
23 mfd_max77705.ko
24 pdic_max77705.ko
25 spu_verify.ko
26 qc_usb_audio.ko
```

This is the first native-init observability candidate set. It is intentionally
smaller than the whole 356-module vendor list, and it should be attempted before
display or distro work.

## Configfs Functions

M1 observed these functions in Android configfs:

```text
ffs.adb
ncm.0
rndis.rndis
```

No matching `ncm.ko` or `ffs.adb.ko` appears in `modules.load`. Treat these as
configfs/functionfs objects exposed after the USB module substrate is present,
not as separate `.ko` files to insert.

## Display Probe Set

Display/GPU dependency closure:

```text
module_count=28
missing_from_modules_load=[]
missing_from_live_proc_modules=[]
```

Candidate order:

```text
01 lcd.ko
02 gpucc-waipio.ko
03 mdt_loader.ko
04 smcinvoke_mod.ko
05 msm_performance.ko
06 msm_ext_display.ko
07 panel_event_notifier.ko
08 msm_kgsl.ko
09 hdcp.ko
10 qseecom-mod.ko
11 dwc3-msm.ko
12 usb_f_ss_mon_gadget.ko
13 redriver.ko
14 usb_notify_layer.ko
15 gh_irq_lend.ko
16 gh_mem_notifier.ko
17 switch_class.ko
18 dev_ril_bridge.ko
19 sec_panel_notifier.ko
20 common_muic.ko
21 sec_input_notifier.ko
22 vbus_notifier.ko
23 usb_typec_manager.ko
24 if_cb_manager.ko
25 pdic_notifier_module.ko
26 qc_usb_audio.ko
27 msm_drm.ko
28 msm-mmrm.ko
```

Display should remain a second rung. M1 already showed DRM exists by Magisk
`post-fs-data`, but USB or pstore must be the proof channel before display work
is trusted.

## Native-Init Direction

Next boot-candidate design should be:

1. direct native `/init` starts with pstore/kmsg marker setup;
2. mount minimal pseudo filesystems needed for module insertion and configfs;
3. insert the 26-module USB-first list in the M2 order, with bounded per-module
   result logging;
4. create a minimal configfs gadget or reuse the Android-shape recipe for an
   observation channel:
   - primary: ADB/FunctionFS only if `adbd` can be staged safely;
   - simpler first proof: NCM or ACM if host can observe link/device creation;
5. stop before display/distro work until the USB/pstore observation channel is
   live-proven.

## Result

PASS: M2 produced a bounded host-only USB-first module recipe from real rooted
Android evidence. The next unit can design/build an observable native-init
candidate, but any live boot flash still requires a fresh SHA-pinned S22+
boot-only `AGENTS.md` exception.
