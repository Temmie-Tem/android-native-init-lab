# S22+ Native-Init M13 No-Module Configfs Live Gate Preflight - 2026-07-07

## Verdict

M13 live-gate preflight passed. No live flash was run.

Codex added the SHA-pinned `AGENTS.md` M13 boot-only/Odin exception and the
guarded helper
`workspace/public/src/scripts/revalidation/s22plus_m13_nomodule_configfs_live_gate.py`.
The helper verifies the exact M13 candidate, rollback APs, manifest safety,
`AGENTS.md` authorization text, Android/Magisk baseline stability, and current
boot hash before any live flash.

M13 deliberately has no reboot beacon and no ACM-triggered download command.
If the candidate parks or exposes ACM, rollback requires operator manual
download-mode entry followed by the helper's rollback-only mode.

## Candidate

```text
AP.tar.md5             5e959f0dd7c55d8e6a9363cde0c0fcc72876639bdc46ccdc826186cfc43134fa
boot.img               21808217d6cf698217e25cf35caf3a271a7f55451cad85ba576d54a40010441b
M13 /init              6b2d229217d83c7f36032c37291bebbebe7c8c5782d006fedcc538649d99f5d3
source                 4e3a88336c6a6e0b1ed6e25f572ed0ec26c2e8d177942598a6e32aa1b2a762e8
base Magisk boot       2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel                 bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

Rollback APs verified by the helper:

```text
Magisk boot-only rollback AP  d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot-only fallback AP   1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Helper Gates

Offline-check command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m13_nomodule_configfs_live_gate.py --offline-check
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
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m13_nomodule_configfs_live_gate.py
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
module_insertions=false
module_binary_injection=false
module_list_files_injected_into_boot_ramdisk=0
module_files_injected_into_boot_ramdisk=0
configfs_runtime_gadget=ss_acm.0 only
udc_binding=a600000.dwc3 only; never dummy_udc.0
usb_role_force=attempt /sys/class/usb_role/*/role=device
block_device_writes=false
tar_members=["boot.img.lz4"]
```

Runtime no-module/no-reboot gates verified:

```text
required_string=module_insertions=absent
required_string=module_list_payload=absent
required_string=no_reboot_beacon=1
required_string=acm_cmd_status=1
required_string=S22_NATIVE_INIT_USB_ACM_M13 ACK status park
arm64 __NR_reboot=142 load absent from manifest objdump
arm64 __NR_finit_module=273 load absent from manifest objdump
/lib/modules string absent from stripped /init
.ko string absent from stripped /init
modules.load/modules.dep strings absent from stripped /init
```

Private run logs:

```text
workspace/private/runs/s22plus_m13_nomodule_configfs_live_gate_20260707T141716Z/s22plus_m13_nomodule_configfs_live_gate.txt
workspace/private/runs/s22plus_m13_nomodule_configfs_live_gate_20260707T141722Z/s22plus_m13_nomodule_configfs_live_gate.txt
```

## Live Contract

The next supervised live command is:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m13_nomodule_configfs_live_gate.py --live --ack S22PLUS-M13-NOMODULE-CONFIGFS-LIVE-GATE
```

Rollback-only command after the operator manually enters download mode:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m13_nomodule_configfs_live_gate.py --rollback-from-download --ack S22PLUS-M13-ROLLBACK-FROM-DOWNLOAD
```

Expected branch logic:

```text
ACM appears:
  target signal reached. Enter download mode manually, then run rollback-only.

No ACM, device visibly parks:
  module insertion likely introduced the M12 loop. Enter download mode manually,
  then run rollback-only before adding any module work back.

Bootloop / Odin endpoint appears:
  if Odin endpoint is already present, helper can rollback immediately; otherwise
  enter download mode manually and run rollback-only. Next shrink removes
  configfs/role-force and keeps only marker + park.

ADB returns:
  unexpected Android return. Helper attempts host-commanded rollback through
  download mode.
```

No live flash was executed in this preflight unit.
