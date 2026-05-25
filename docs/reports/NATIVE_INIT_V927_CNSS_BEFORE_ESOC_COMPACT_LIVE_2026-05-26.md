# Native Init V927 CNSS-before-eSoC Compact Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| V927 plan mode | `tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-plan/manifest.json` | `v927-mdm-helper-cnss-before-esoc-plan-ready` |
| V927 live gate | `tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-live/manifest.json` | `v927-wlfw-precondition-missing-no-open` |

V927 confirmed the V923 blocker with helper `v153` and compact CNSS output:
`mdm_helper`, `cnss_diag`, and `cnss-daemon -n -l` start cleanly in the repaired
runtime namespace, but `cnss-daemon` still does not emit the WLFW precondition.
The `/dev/subsys_esoc0` child-open gate therefore remains closed.

## Key Findings

| Marker | Value |
| --- | --- |
| helper marker | `a90_android_execns_probe v153` |
| remote helper hash | matched expected helper `v153` hash |
| CNSS surface mode | `compact` |
| linkerconfig mode | `copy-real` |
| VNDK APEX alias mode | `v30-to-system-ext-v30` |
| Android SELinux context mode | `service-defaults` |
| private property root | present |
| `mdm_helper` start attempted | `true` |
| `/dev/esoc-0` fd seen in `mdm_helper` | `true` |
| `cnss_diag` started | `true` |
| `cnss-daemon` started | `true` |
| WLFW precondition observed | `false` |
| `/dev/subsys_esoc0` open attempted | `false` |
| transcript truncation | `false` |
| postflight actor cleanup | safe; no cleanup reboot required |

## Interpretation

The V925 runtime namespace repair is active: real linkerconfig, VNDK APEX alias,
Android SELinux-context defaults, and the private property root are all visible
to the helper. Compact output also worked; the final result was not lost to
stdout truncation.

The remaining blocker is not the V923 transcript limit. It is the lower CNSS /
WLFW precondition gap: `cnss-daemon` runs, but it does not reach a `wlfw_start`
precondition before the eSoC trigger gate times out. Because the precondition is
absent, V927 correctly avoids opening `/dev/subsys_esoc0`.

## Guardrails

- No service-manager start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP, route change, or external ping.
- No controller eSoC notify or BOOT_DONE spoofing.
- No module load/unload, boot image write, partition write, firmware mutation,
  GPIO write, sysfs write, debugfs write, or Wi-Fi link-up.

## Device Health

Post-run serial checks confirmed:

- `bootstatus`: `BOOT OK`, `selftest: pass=11 warn=1 fail=0`
- `selftest`: `pass=11 warn=1 fail=0`
- `netservice`: flag disabled, `ncm0=present`, `tcpctl=stopped`
- cleanup reboot: not required

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_cnss_before_esoc_compact_live_v927.py
python3 scripts/revalidation/native_wifi_mdm_helper_cnss_before_esoc_compact_live_v927.py \
  --out-dir tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-plan \
  plan
python3 scripts/revalidation/native_wifi_mdm_helper_cnss_before_esoc_compact_live_v927.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-before-subsys-trigger-capture \
  --allow-cleanup-reboot \
  --assume-yes \
  run
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py selftest
python3 scripts/revalidation/a90ctl.py netservice status
```

## Next

V928 should be host-only first: classify why `cnss-daemon -n -l` still lacks the
WLFW precondition even with the repaired runtime namespace. The useful inputs
are V927 compact contract keys, V924 CNSS precondition analysis, Android
positive `wlfw_start` timing from V914, and the current helper transcript. Do
not repeat full-output CNSS live runs.
