# v230 Android Exec Namespace Probe Report

## Summary

- status: `LIVE INVENTORY PASS / RUNTIME GAP NARROWED`
- live status: `android-exec-namespace-runtime-gap`
- implementation: `scripts/revalidation/wifi_android_exec_namespace_probe.py`
- evidence: `tmp/wifi/v230-android-exec-namespace-probe/`
- latest device build used for Wi-Fi evidence remains: `A90 Linux init 0.9.59 (v159)`

v230 adds a host-side inventory/probe tool for the Android execution namespace
gap found in v229. The tool is intentionally read-only by default and does not
execute `cnss-daemon`, does not start Wi-Fi, and does not perform global bind
mounts.

## Implemented Behavior

- `plan`: validates v221/v222/v226/v227/v228/v229 prior evidence and emits
  `android-exec-plan-ready`.
- `inventory`/`preflight`: first checks bridge availability, then runs a fresh
  v229 preflight and read-only device inventory.
- `probe`: requires `--allow-temp-namespace --assume-yes`, but v230 still refuses
  global mounts because no private device namespace helper is shipped yet.
- output handling uses `EvidenceStore` private/no-follow evidence writers.

## Host Validation

```text
python3 -m py_compile scripts/revalidation/wifi_android_exec_namespace_probe.py
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py plan
```

Result:

```text
decision=android-exec-plan-ready pass=True
reason=host-side plan and prior evidence are ready; no live inventory performed
```

## Live Inventory

Command:

```text
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py \
  --out-dir tmp/wifi/v230-android-exec-namespace-inventory-20260515-033554 \
  inventory
```

Result:

```text
decision=android-exec-namespace-runtime-gap pass=True
reason=read-only inventory still has blockers: linkerconfig-need-unproven
```

Key findings:

- fresh v229 gate still returns `start-only-runtime-gap`.
- `/mnt/system/system/vendor` is a symlink to `/vendor`.
- namespace policy should materialize `/system/vendor` as a symlink to `/vendor`.
- vendor source is `needs-remount`: `sda29` is visible, but vendor is not live
  mounted into Android runtime paths.
- `/system/bin/linker64`, `/system/lib64/libc.so`, and APEX runtime evidence are
  visible enough for the next step.
- blocker remains: `linkerconfig-need-unproven`.

Post-inventory smoke:

- `a90ctl.py --json version`: PASS, `A90 Linux init 0.9.59 (v159)`.
- `a90ctl.py netservice status`: PASS, NCM absent and tcpctl stopped.
- `a90ctl.py selftest verbose`: PASS, `pass=11 warn=1 fail=0`.

## Next Step

Next:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py \
  --out-dir tmp/wifi/v230-android-exec-namespace-probe-live \
  probe \
  --allow-temp-namespace \
  --assume-yes
```

The expected result remains a safe stop until v231 adds a private namespace
helper or v230 learns how to prove `/linkerconfig` absence is acceptable.

For a fresh re-run:

```bash
python3 scripts/revalidation/wifi_android_exec_namespace_probe.py \
  --out-dir tmp/wifi/v230-android-exec-namespace-inventory-rerun \
  inventory
```
