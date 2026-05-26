# V1032 PM Runtime-Domain Guard Live

- date: `2026-05-26`
- scope: bounded live proof
- helper: `a90_android_execns_probe v175`
- decision: `v1032-pm-runtime-domain-guard-blocked-clean`
- pass: `True`
- evidence: `tmp/wifi/v1032-pm-runtime-domain-guard-live/manifest.json`

## Summary

V1032 ran the PM full-contract order with
`--require-android-selinux-exec-match`. The guard blocked PM actor target
execution before `execv` because `/proc/self/attr/exec` still read `kernel`
after the requested Android SELinux exec contexts were written.

This is the expected safe result: native did not continue into unsafe PM actor
execution under the wrong runtime domain.

## Result

| Item | Value |
| --- | --- |
| decision | `v1032-pm-runtime-domain-guard-blocked-clean` |
| guard blocked | `True` |
| blocked children | `mdm_helper`, `per_mgr_light`, `pm_proxy`, `pm_proxy_helper` |
| target execv allowed by guard | `False` |
| `/dev/subsys_esoc0` open attempted | `False` |
| Wi-Fi HAL start | `False` |
| scan/connect | `False` |
| credential use | `False` |
| DHCP/route | `False` |
| external ping | `False` |
| Wi-Fi bring-up | `False` |
| cleanup reboot | `False` |

## Findings

- `pm_proxy_helper` requested `u:r:per_proxy_helper:s0`, but observed
  `attr/exec=kernel`.
- `pm-service`/`per_mgr_light` requested `u:r:vendor_per_mgr:s0`, but observed
  `attr/exec=kernel`.
- `pm-proxy` requested `u:r:vendor_per_mgr:s0`, but observed
  `attr/exec=kernel`.
- `mdm_helper` requested `u:r:vendor_mdm_helper:s0`, but observed
  `attr/exec=kernel`.
- The helper stopped each guarded child before target `execv`.

## Interpretation

V1030/V1031 guard support is working on-device. The current blocker is no
longer missing observability; it is a real runtime-domain gap in the native
SELinux execution environment. The next useful unit is a host-only classifier
over current-boot SELinuxfs/policy state, helper source, Android V1024 actor
domains, and V1032 guard evidence.

Do not retry PM full-contract actor execution until the native SELinux exec
labeling gap is explained or repaired.

## Guardrails

- no Wi-Fi HAL start
- no `wificond`
- no `IWifi.start` or `qcwlanstate` write
- no scan/connect/link-up
- no credentials
- no DHCP, route, or external ping
- no controller eSoC notify or BOOT_DONE
- no boot image write
- no partition write
- no firmware mutation
- no GPIO/sysfs/debugfs write

## Validation

Commands:

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
python3 scripts/revalidation/a90ctl.py --timeout 5 bootstatus
python3 scripts/revalidation/a90ctl.py --timeout 5 selftest
```

Postflight:

```text
boot: BOOT OK shell
selftest: pass=11 warn=1 fail=0
```

## Next

V1033 should classify the current native SELinux exec-labeling gap. Focus areas:

1. whether `attr/exec` write succeeds but is not observable because the native
   context is outside Android policy transition rules;
2. whether current-boot SELinux policy loading lacks the PM domain transitions
   needed for these vendor binaries;
3. whether helper execution must happen from a different domain, namespace, or
   entrypoint before PM actors can safely run.
