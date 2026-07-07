# S22+ Native-Init M11 Park USB Live Gate Preflight - 2026-07-07

## Verdict

M11 live-gate preflight passed. No live flash was run.

Codex added the SHA-pinned `AGENTS.md` M11 boot-only/Odin exception and the
guarded helper
`workspace/public/src/scripts/revalidation/s22plus_m11_park_usb_live_gate.py`.
The helper verifies the exact M11 candidate, rollback APs, manifest safety,
`AGENTS.md` authorization text, Android/Magisk baseline stability, and current
boot hash before any live flash.

M11 deliberately has no reboot beacon and no ACM-triggered download command.
If the candidate parks or exposes ACM, rollback requires operator manual
download-mode entry followed by the helper's rollback-only mode.

## Candidate

```text
AP.tar.md5             8b4a4fa6db3bc0b2bf5e4fd1fccf4b671fd2fbd7fbbcc08542c3be816a3f5d43
boot.img               32f2667c31f05d967529031630e5b004cf5238120ffc6ec7089dcc40a3352a3f
M11 /init              234ded5b6172a3470825a1c616e6537c3de4b2274d8c26525386f8e85d5e8d7e
M11 module list        c254be05c91199c4f69380f0488de13c7b2cde987594bc1c5d0a6657a0e8eb58
source                 ff92af817cd4564b6fd811484540e8a217ff19bbe445839981ce7818498561f6
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
vendor_ramdisk00       41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193
```

Rollback APs verified by the helper:

```text
Magisk boot-only rollback AP  d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot-only fallback AP   1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Helper Gates

Offline-check command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m11_park_usb_live_gate.py --offline-check
```

Result:

```text
offline-check ok
device_action=0
agents_exception_checked=0
android_checked=0
```

Default dry-run command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m11_park_usb_live_gate.py
```

Result:

```text
dry-run ok
agents_exception_missing=[]
android_stability_result=ok samples=4
current_boot_hash matches 2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
host Odin endpoint absent during dry-run snapshot
```

Manifest safety verified:

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
module_binary_injection=false
module_list_path=/s22plus_m11_park_usb.modules
module_list_files_injected_into_boot_ramdisk=1
module_files_injected_into_boot_ramdisk=0
configfs_runtime_gadget=ss_acm.0 only
udc_binding=a600000.dwc3 only; never dummy_udc.0
usb_role_force=attempt /sys/class/usb_role/*/role=device
block_device_writes=false
tar_members=["boot.img.lz4"]
```

M11 subset gates verified:

```text
subset_count=48
dependency_closure_count=53
subset_bytes=738
blocked_from_closure=abc.ko, icc-debug.ko, minidump.ko, qc_usb_audio.ko, sec_debug.ko
critical_modules_present=dwc3-msm.ko, usb_f_ss_acm.ko, usb_typec_manager.ko, if_cb_manager.ko, pdic_notifier_module.ko, vbus_notifier.ko, mfd_max77705.ko, pdic_max77705.ko
explicit_blocklist_absent_from_final_subset=true
```

Runtime no-reboot gates verified:

```text
required_string=no_reboot_beacon=1
required_string=acm_cmd_status=1
required_string=S22_NATIVE_INIT_USB_ACM_M11 ACK status park
arm64 __NR_reboot=142 load absent from manifest objdump
```

Private run logs:

```text
workspace/private/runs/s22plus_m11_park_usb_live_gate_20260707T132910Z/s22plus_m11_park_usb_live_gate.txt
workspace/private/runs/s22plus_m11_park_usb_live_gate_20260707T132958Z/s22plus_m11_park_usb_live_gate.txt
```

## Live Contract

The next supervised live command is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m11_park_usb_live_gate.py --live --ack S22PLUS-M11-PARK-USB-LIVE-GATE
```

Rollback-only command after the operator manually enters download mode:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m11_park_usb_live_gate.py --rollback-from-download --ack S22PLUS-M11-ROLLBACK-FROM-DOWNLOAD
```

Expected branch logic:

```text
ACM appears:
  target signal reached. Enter download mode manually, then run rollback-only.

No ACM, device visibly parks:
  reset source likely avoided, USB enum still missing. Enter download mode manually, then run rollback-only.

Bootloop / Odin endpoint appears:
  if Odin endpoint is already present, helper can rollback immediately; otherwise enter download mode manually and run rollback-only.

ADB returns:
  unexpected Android return. Helper attempts host-commanded rollback through download mode.
```

No live flash was executed in this preflight unit.
