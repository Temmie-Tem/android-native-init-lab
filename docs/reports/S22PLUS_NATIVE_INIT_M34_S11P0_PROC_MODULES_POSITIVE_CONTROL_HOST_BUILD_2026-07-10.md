# S22+ M34 S11P0 Proc-Modules Positive Control Host Build

Date: 2026-07-10 KST  
Scope: host-only source/build unit; no flash, no reboot, no partition write

## Purpose

S10C0 live proved that direct `cmd-db.ko` `finit_module` reaches the accepted
path under native-init. The remaining ambiguity is whether later
`/proc/modules` checks are observing the right thing. S11P0 is the next bounded
split: it keeps the S10C0/S9 module recipe, keeps the direct `cmd-db.ko` rc
gate, and adds a watchdog-module positive control for native-init's
`/proc/modules` read path.

The S11P0 one-bit live predicate is:

```text
direct cmd-db.ko finit accepted AND
(/proc/modules contains qcom_wdt_core OR /proc/modules contains gh_virt_wdt)
```

A HIT means the `/proc/modules` read path can see a known survival-path module
after the same module load loop. A MISS means the positive-control read failed
or the loader did not reach the expected state; it does not authorize guessing
downstream USB/configfs causes.

## Source Changes

Touched files:

```text
workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c
workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py
tests/test_s22plus_m34_runtime_gadget_split_build.py
```

Key runtime strings:

```text
stage=S11P0
stage_number=21
version=0.12
module_load_probe=finit_cmd_db_accepted_and_watchdog_proc_visible
s11_proc_modules_positive_control=1
proc_modules=1
direct_finit_rc=1
probe_module=cmd-db.ko
probe_proc_name=cmd_db
positive_control=watchdog_proc_visible
positive_control_proc_names=qcom_wdt_core,gh_virt_wdt
positive_control_modules=qcom_wdt_core.ko,gh_virt_wdt.ko
phase=s11_proc_modules_positive_control_probe
predicate=cmd_db_finit_accepted_and_watchdog_proc_visible
true_action=reboot_download
false_action=park
```

S11P0 does not create configfs gadgets, bind UDC, force USB roles, write TypeC
roles, write power rails, mount persistent partitions, hand off to Android, or
load Magisk modules. It only runs as direct PID1, mounts minimal proc/sys/dev/run
state, loads the pinned module list, reads `/proc/modules`, and conditionally
requests `reboot(download)`.

## Host Build

Command:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py \
  --stages S11P0 \
  --force
```

Output:

```text
out_dir=workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_14
```

Hashes:

```text
AP.tar.md5               dacb20dc0466487e6ad30f7ad5ebcb053a9593966922464eba4b3ed60e5f3b45
AP.tar                   4931a4f64735215fda79a8bacbc6787f275cdcbd32b353581d2a573db3121c28
boot.img                 3ac8b8a5dde2ef6c3f7170c258a4dc6f3a3f9a4bb4575b5af5cf3380952d7881
boot.img.lz4             0dd2d3788263229355a1e267f056047890e4e29ca3563a56b502b981e9917c02
/init                    efd8141e8c552b4e30f0052186b801d36420476d155e7c489c0a8644718dd5f6
module list              c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26
base Magisk boot         2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
no-change repack boot    2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
template source          70f4326294da2f27c7736f5119c7c9ad32f10e02e066fd2f2530ca91a8e4078b
```

The AP tar contains exactly one member:

```text
boot.img.lz4
```

## Validation

Passed:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py \
  tests/test_s22plus_m34_runtime_gadget_split_build.py

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests/test_s22plus_m34_runtime_gadget_split_build.py

Ran 5 tests in 0.020s
OK
```

Manifest safety fields:

```text
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
stage_s11p0_module_load_probe=finit_cmd_db_accepted_and_watchdog_proc_visible
```

## Live Status

No S11P0 live gate was run. No Odin flash, reboot, partition write, native-init
candidate execution, or rollback was performed in this unit.

Before any live S11P0 run, add a fresh narrow `AGENTS.md` exception or equivalent
checked live gate that pins the hashes above, requires boot-only AP scope, and
retains the current rollback rules.
