# Native Init V1150 Magisk Vendor Overlay Repair Report

Date: `2026-05-27`

## Result

- Decision: `v1150-magisk-vendor-overlay-repair-dryrun-ready`
- Pass: `true`
- Updated scaffold: `scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py`
- Updated handoff runner: `scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py`
- Rebuilt V1147 manifest: `tmp/wifi/v1147-android-mdm-helper-strace-module/manifest.json`
- Retry dry-run manifest: `tmp/wifi/v1149-retry-dryrun/manifest.json`

## V1149 First Live Result

The first V1149 live run reached Android twice, installed the Magisk module,
ran the post-fs-data/service scripts, and rolled back to native v724 cleanly.

It did not capture the `mdm_helper` wrapper:

```text
post-fs-data.sh ran as u:r:magisk:s0
service.sh ran
/data/local/tmp/a90-wifi/ existed
mdm_helper.wrapper.log absent
mdm_helper.strace.txt absent
mdm_helper pid absent at collection time
native v724 rollback pass
```

The immediate runner failure was a host-side pull destination bug:

```text
adb pull .../a90-wifi-v1149.tar.gz .../android-trace/a90-wifi-v1149.tar.gz
adb: cannot create file/directory .../android-trace/...: No such file or directory
```

## Repair

Two fixes were added before retry:

1. V1147 now stages the same wrapper at both:

```text
module/system/vendor/bin/mdm_helper
module/vendor/bin/mdm_helper
```

2. V1149 now creates the host `android-trace/` directory before `adb pull` and
   adds an `android-overlay-proof` step that records `/vendor/bin/mdm_helper`,
   `/system/vendor/bin/mdm_helper`, and matching mount lines.

The reason for the extra `vendor/bin` path is that Android services execute the
absolute `/vendor/bin/mdm_helper` path, and a `/system/vendor` overlay can be
insufficient when `/system/vendor` is only a symlink view of `/vendor`.

## Retry Dry-run

Executed:

```bash
python3 scripts/revalidation/native_wifi_android_mdm_helper_strace_module_v1147.py \
  --strace-binary external_tools/userland/bin/strace-aarch64-static-7.0
python3 scripts/revalidation/android_mdm_helper_strace_handoff_v1149.py \
  --out-dir tmp/wifi/v1149-retry-dryrun \
  --native-image stage3/boot_linux_v724.img \
  --native-expect-version 'A90 Linux init 0.9.68 (v724)' \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  dry-run
```

Result:

```text
decision: v1149-handoff-dryrun-ready
pass: True
```

The retry ZIP contains both wrapper paths and remains install-ready.

## Safety

- Native rollback after the failed first live run: `pass`
- Wi-Fi credentials: not used
- Scan/connect/DHCP/routes/external ping: not executed
- Native `/dev/subsys_esoc0` retry: not executed
- Native eSoC ioctl: not executed
- Direct `/vendor` partition mutation: not executed

## Next

Rerun V1149 live with the repaired module. The expected discriminator is
whether `android-overlay-proof` shows the wrapper is mounted over
`/vendor/bin/mdm_helper` and whether `mdm_helper.wrapper.log` plus
`mdm_helper.strace.txt` are produced during the second Android boot.
