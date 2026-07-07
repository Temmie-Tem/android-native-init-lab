# S22+ M18 Capture Postmortem (2026-07-08)

## Verdict

PASS, host-only postmortem.

The S22+ ramoops-DTBO + M18 live run recovered cleanly, but it did not capture a
M18 marker. The retained evidence does not localize the failure inside M18.

Do not repeat the same M18 live. Preferred next instrument remains UART or an
equivalent real-time kernel console. If a no-UART fallback is pursued, design it
host-only first as either a checkpoint/download discriminator or a genuinely
dependency-closed USB-tail candidate, then require a fresh SHA-pinned gate.

## Inputs

- Live run directory:
  `workspace/private/runs/s22plus_ramoops_dtbo_m18_capture_20260707T164400Z`
- Live log:
  `s22plus_ramoops_dtbo_m18_capture_live_gate.txt`
- Retained log:
  `android_pstore/post_m18_boot_rollback_last_kmsg.bin`
- M18 source:
  `workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c`
- M18 manifest:
  `workspace/private/outputs/s22plus_native_init/inplace_m18_full_firststage_usb_v0_1/manifest.json`

Raw private logs and retained binaries are intentionally not committed.

## Findings

### Live Flow

`s22plus_m18_capture_postmortem.py` found every required live/recovery flag:

- patched DTBO flash passed;
- Android/root returned with patched DTBO;
- M18 boot flash passed;
- 41 M18 observe iterations saw no ACM;
- M18 returned through Odin/download-mode;
- Magisk boot rollback passed;
- pstore files were empty;
- `/proc/last_kmsg` read returned 2097136 bytes;
- M18 marker search returned 0;
- stock DTBO rollback passed;
- final Android returned.

### Retained Channel

The retained `last_kmsg` scan found:

- `S22_NATIVE_INIT_USB_ACM_M18_FULL`: 0
- `S22M18FULL0001`: 0
- `module_group=full_firststage_usb`: 0
- `full_firststage_usb`: 0
- `bootloader_mode = 1`: 4
- `reboot_reason = 0x9`: 10
- `Failed to get KlogOffset`: 9
- `SamsungLogFlush KlogOffset:0x0`: 9

This looks like ABL/download retention, not the M18 native-init printk stream.

### M18 Source Ordering

M18 executes in this order:

1. `setup_minimal_fs();`
2. `emit(k_marker);`
3. `load_full_firststage_usb_modules();`
4. `force_usb_roles_device();`
5. `(void)create_acm_gadget();`
6. `serial_probe_loop();`

The first M18 emission is `S22_NATIVE_INIT_USB_ACM_M18_FULL phase=mounts`,
written through `/dev/kmsg`. The version marker is also `/dev/kmsg` only. So
missing retained markers do not prove M18 died before the marker; the retained
channel may simply not preserve this stream.

### Dependency Closure Caveat

The M18 manifest proves the USB tail was not dependency-closed under
`modules.dep`: 8 USB-tail modules still have 29 non-reset missing dependency
edges.

The missing non-reset dependency groups are:

- `dwc3-msm.ko`: `usb_f_ss_mon_gadget.ko`, `qc_usb_audio.ko`, `redriver.ko`,
  `common_muic.ko`, `switch_class.ko`, `usb_notify_layer.ko`
- `i2c-msm-geni.ko`: `gpi.ko`
- `mfd_max77705.ko`: `usb_notify_layer.ko`
- `pdic_max77705.ko`: `usb_f_ss_mon_gadget.ko`, `qc_usb_audio.ko`,
  `redriver.ko`, `spu_verify.ko`, `common_muic.ko`, `switch_class.ko`,
  `usb_notify_layer.ko`
- `pdic_notifier_module.ko`: `switch_class.ko`, `usb_notify_layer.ko`
- `phy-msm-snps-eusb2.ko`: `repeater.ko`, `usb_f_ss_mon_gadget.ko`,
  `common_muic.ko`, `switch_class.ko`, `usb_notify_layer.ko`
- `phy-msm-snps-hs.ko`: `usb_f_ss_mon_gadget.ko`, `common_muic.ko`,
  `switch_class.ko`, `usb_notify_layer.ko`
- `usb_typec_manager.ko`: `common_muic.ko`, `switch_class.ko`,
  `usb_notify_layer.ko`

This corrects the interpretation: the run does not prove that a fully
dependency-closed Android first-stage USB environment fails. It proves that this
specific M18 shape still loops and that retained evidence cannot say where.

## Next

No same-M18 retry. The useful next step is one of:

- UART/kernel-console capture, preferred;
- host-only design of a checkpoint/download discriminator;
- host-only design of a dependency-closed USB-tail candidate.

Any further live candidate needs a fresh SHA-pinned exception, dry-run gate, and
attended rollback plan.

## Validation

Commands:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/s22plus_m18_capture_postmortem.py

python3 workspace/public/src/scripts/revalidation/s22plus_m18_capture_postmortem.py \
  --output workspace/private/runs/s22plus_ramoops_dtbo_m18_capture_20260707T164400Z/m18_capture_postmortem.json
```

Result: `result=pass`, `device_action=false`.
