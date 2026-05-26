# V1032 PM Runtime-Domain Guard Live Plan

- date: `2026-05-26`
- type: bounded live proof
- input: `docs/reports/NATIVE_INIT_V1031_HELPER_V175_DEPLOY_2026-05-26.md`
- helper: `/cache/bin/a90_android_execns_probe`
- helper version: `a90_android_execns_probe v175`

## Objective

Run the V1027 PM full-contract order with helper `v175` and
`--require-android-selinux-exec-match`.

The purpose is not Wi-Fi bring-up. The purpose is to prove that native PM actor
execution is fail-closed when the requested Android SELinux exec context does
not appear in `/proc/self/attr/exec` before `execv`.

## Gate

The proof permits only the existing PM full-contract surface:

```text
property shim
  -> pm_proxy_helper
  -> pm-service
  -> pm-proxy
  -> mdm_helper
  -> PM fd predicate
  -> service-manager/CNSS matrix only if lower guards pass
```

Each Android actor child must log:

- requested target context
- `setexeccon`/`attr/exec` write result
- observed `/proc/self/attr/exec`
- expected Android context
- match result

If the match result is false, the child exits before target `execv`.

## Guardrails

- no Wi-Fi HAL start
- no `wificond`
- no `IWifi.start`
- no `qcwlanstate` write
- no scan/connect/link-up
- no credentials
- no DHCP, route, or external ping
- no controller eSoC notify or BOOT_DONE
- no boot image write
- no partition write
- no firmware mutation
- no GPIO/sysfs/debugfs write

## Commands

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_runtime_domain_guard_live_v1032.py
python3 scripts/revalidation/native_wifi_pm_runtime_domain_guard_live_v1032.py plan
python3 scripts/revalidation/native_wifi_pm_runtime_domain_guard_live_v1032.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

## Success Criteria

- Remote helper sha and usage match helper `v175`.
- `--require-android-selinux-exec-match` is active in the helper command.
- If native `attr/exec` remains `kernel`, PM actor children fail closed before
  target `execv`.
- No forbidden Wi-Fi, network, eSoC notify, boot, partition, firmware, GPIO, or
  sysfs/debugfs action occurs.
- Postflight `bootstatus` and `selftest` remain healthy.

## Next

If the guard blocks cleanly, V1033 should classify why native current-boot
SELinux exec labeling remains outside the requested Android PM domains before
any further PM full-contract retry.
