# V998 Android Service-Window Post-SELinux

- generated: `2026-05-26`
- scope: bounded Android service-window retry after V997 current-boot SELinux proof
- decision: `v970-android-service-window-no-wlfw`
- pass: `True`
- evidence: `tmp/wifi/v998-android-service-window-live-v169-post-selinux/manifest.json`
- transcript: `tmp/wifi/v998-android-service-window-live-v169-post-selinux/native/mdm-helper-cnss-before-esoc.txt`
- helper: `a90_android_execns_probe v169`

## Summary

V998 is a material improvement over V993.

V993 blocker:

```text
wificond stayed kernel after exec and crashed in addService
```

V998 result after V997 current-boot SELinux proof:

```text
capture.exec.attr/current.value=u:r:wificond:s0\x00
child_started=14
all_observable_at_timeout=1
all_postflight_safe=1
result=service-window-no-wlfw
reason=all-actors-observed-but-wlfw-precondition-missing
```

So the SELinux/service-manager registration blocker is no longer the active
frontier for this path. The next blocker is lower: WLFW precondition remains
missing.

## Key Findings

| Item | Result |
| --- | --- |
| service-manager trio started | PASS |
| Wi-Fi HAL legacy/ext actors started | PASS |
| `wificond` started and observed | PASS |
| `wificond` post-exec context | `u:r:wificond:s0` |
| `mdm_helper` started | PASS |
| `cnss-daemon` started | PASS |
| all 14 actors observed | PASS |
| all postflight cleanup safe | PASS |
| WLFW precondition | MISSING |
| `wlan0` | absent |
| scan/connect/credentials/DHCP/external ping | not executed |

## Guardrails

- no `qcwlanstate`
- no `IWifi.start`
- no `/dev/subsys_esoc0` open
- no eSoC ioctl
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no cleanup reboot required

## Validation

```bash
python3 scripts/revalidation/native_wifi_android_service_window_live_v970.py \
  --out-dir tmp/wifi/v998-android-service-window-live-v169-post-selinux \
  --local-helper tmp/wifi/v995-execns-helper-v169-build/a90_android_execns_probe \
  --helper-sha256 c47f0659178186d45cf5199fdad4d198f0c69b6998f2127ff420f9e0f0204a74 \
  --helper-marker "a90_android_execns_probe v169" \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-android-wifi-service-window \
  --allow-cleanup-reboot \
  --assume-yes run
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py exposure
```

Result:

```text
decision: v970-android-service-window-no-wlfw
pass: True
boot: BOOT OK shell 4.6s
selftest: pass=11 warn=1 fail=0
exposure: ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Next

The next gate should not repeat SELinux repair. It should target the remaining
WLFW precondition gap.

The likely next unit is a bounded classifier that compares V998 against the
older eSoC/CNSS gates and decides whether to re-enable the guarded
`cnss-daemon wlfw_start` / `/dev/subsys_esoc0` trigger path now that
service-window SELinux context is fixed.
