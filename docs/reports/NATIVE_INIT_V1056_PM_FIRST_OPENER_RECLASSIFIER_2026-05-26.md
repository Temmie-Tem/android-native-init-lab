# V1056 PM First-Opener Reclassifier

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| plan | `docs/plans/NATIVE_INIT_V1056_PM_FIRST_OPENER_RECLASSIFIER_PLAN_2026-05-26.md` | host-only |
| classifier | `tmp/wifi/v1056-pm-first-opener-reclassifier/manifest.json` | `v1056-android-count-zero-first-open-parity-gap-classified` |

V1056 reclassifies the V1047/V1055 path. The missing piece is not a synthetic
pre-holder before `pm_proxy_helper`.

## Findings

| Finding | Value |
| --- | --- |
| Android `vendor.per_proxy_helper` start | `5.822268s` |
| Android modem first-open marker | `__subsystem_get(): modem count:0` at `5.832819s` |
| Android `vendor.per_mgr` start | `6.961623s` |
| Android later modem marker | `__subsystem_get(): modem count:1` at `7.707305s` |
| Native V1043 actual `pm_proxy_helper` first-open | blocked in `pil_boot/subsys_powerup/flush_work` |
| Native V1055 synthetic pre-holder node | `/tmp/a90-v231-640/root/dev/subsys_modem` exists |
| Native V1055 nonblocking open | `errno=14` |
| Native V1055 plain fallback | did not return before the bounded window |

## Interpretation

Android starts `vendor.per_proxy_helper` before `vendor.per_mgr`. It enters the
modem subsystem path with `modem count:0`, then later Android observes
`modem count:1`. Therefore `pm-service` is not the pre-holder that makes
`pm_proxy_helper` cheap in Android.

Native V1043 already tried the Android-order actor path with PM SELinux domains
matched; it still blocked before forming the PM fd contract. V1055 then proved
that adding a synthetic pre-holder before `pm_proxy_helper` only creates another
count-zero first-opener, and that first-opener blocks too.

So the current blocker is lower than PM actor ordering:

```text
Android count-zero first open succeeds
Native count-zero first open blocks
```

The next unit should classify the runtime prerequisites for that count-zero
first open, not rerun the same pre-holder gate.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_first_opener_reclassifier_v1056.py
python3 scripts/revalidation/native_wifi_pm_first_opener_reclassifier_v1056.py run
```

Result:

```text
decision: v1056-android-count-zero-first-open-parity-gap-classified
pass: True
next_step: v1057-readonly-first-open-runtime-prereq-classifier
```

## Guardrails

Host-only. No device command, bridge command, Android boot, ADB command,
`/dev/subsys_modem` open, `/dev/subsys_esoc0` open, `/dev/esoc-0` open, eSoC
ioctl, actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
ping, boot image write, partition write, firmware mutation, GPIO write, sysfs
write, or debugfs write occurred.

## Next

V1057 should be a read-only first-open runtime prerequisite classifier:

1. verify `firmware_class.path`;
2. verify global and private firmware mounts;
3. verify `modem.b00`/`modem.mdt` visibility at the PIL path;
4. classify whether native has already changed lower modem state before the PM
   first-open window.

Do not rerun the same modem pre-holder live gate.
