# S22+ M34 S10C0 Direct-Finit Loader Audit Host Build

Date: 2026-07-09 20:28 KST / 2026-07-09 11:28 UTC

## Verdict

Host-only build complete. No flash, reboot, ADB write, Odin transfer, or device
action was performed.

S10C0 is the next bounded native-init candidate after the consumed S10B0 live
MISS. S10B0 proved that the first `/proc/modules` prefix predicate did not hit,
but it could not distinguish `cmd-db.ko` failing to load from `/proc/modules`
being an unreliable observation channel during direct PID1 native-init. S10C0
keeps the same 89-module S9/S10A/S10B recipe and changes only the first boundary
observation: it records the direct `finit_module` result for `cmd-db.ko`.

## Candidate

Output directory:

```text
workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_13/
```

Built stage:

```text
S10C0
stage_number=20
module_load_probe=finit_cmd_db_accepted
probe_module=cmd-db.ko
probe_proc_name=cmd_db
module_count=89
```

Hashes:

```text
AP.tar.md5  9221cfa3ea3ce0776860a5041981e23a84d0be9b833203401dab771897266c6f
AP.tar      d34140e26b04436cf01e9429ec65b3a07192004b637b7931090cac3301e67c29
boot.img    8d77e1434cd47fe47f4723c948e4ff6db759cbe4bf75dd21e9e0c265d928c6df
boot.img.lz4 43a375b942ad9d619b71b04dc98aac8422a6ddc0ae6ea2cff78ed77a771e809b
/init       cd80d5923c94f8a423821bc6dee4547f22763e177fbcc637d1bcb101c4b8c39b
modules     c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26
template    e7c8e62487701d6af31b5e7bc060a12091a5f55737aec67c4b45be484f67666b
base boot   2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel      bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

The Odin AP contains exactly one member:

```text
boot.img.lz4
```

## Runtime Contract

S10C0 emits `version=0.11` and records the loader audit fields below:

```text
phase=s10c_module_loader_audit_probe
predicate=cmd_db_finit_accepted
present=<0|1>
modules_open_rc=<rc>
modules_read_rc=<rc>
attempted=<count>
expected=89
ok=<count>
eexist=<count>
fail=<count>
first_fail_index=<index>
first_fail_rc=<rc>
first_fail_name=<module|none>
cmd_db_seen=<0|1>
cmd_db_rc=<rc>
true_action=reboot_download
false_action=park
```

Predicate HIT means `cmd-db.ko` was attempted and its `finit_module` rc was `0`
or `-EEXIST`; the candidate then requests `reboot(download)`. Predicate MISS
parks and requires manual Download-mode rollback.

This intentionally removes the `/proc/modules` dependency from the first S10
boundary. The build-time required-string audit confirms S10C0 does not require
`/proc/modules`.

## Safety Envelope

S10C0 remains boot-only and direct PID1. It does not enable configfs, bind UDC,
force USB role/typec, mount persistent partitions, write block devices, start
Android, or hand off to Magisk.

The candidate still carries the same 89-module S9/S10A/S10B load recipe,
including the already-known risk modules from that closure, so live execution
requires a fresh SHA-pinned `AGENTS.md` boot-only exception and explicit
operator approval. There is no active live authorization for S10C0.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py --stages S10C0 --force
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/build_s22plus_m34_runtime_gadget_split.py workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests/test_s22plus_m34_runtime_gadget_split_build.py tests/test_s22plus_m34_s10b0_module_load_prefix_live_gate.py
```

Result:

```text
build: ok
py_compile: ok
unittest: Ran 11 tests, OK, skipped=2
```

## Next

Author a fail-closed S10C0 live helper that pins the exact hashes above, performs
offline checks and default dry-run against the current rooted Android baseline,
then add a fresh `AGENTS.md` exception before any live flash. Do not advance to
S10B1+ or downstream USB/configfs work until S10C0 separates direct
`finit_module` acceptance from `/proc/modules` observation failure.
