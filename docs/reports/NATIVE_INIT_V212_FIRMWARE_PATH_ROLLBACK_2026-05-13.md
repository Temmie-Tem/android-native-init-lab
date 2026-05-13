# v212 Firmware Path Apply / Rollback Probe Report

## Summary

- status: `PASS`
- runtime: `A90 Linux init 0.9.59 (v159)`
- collector: `scripts/revalidation/native_firmware_path_apply_probe.py`
- evidence: `tmp/wifi/v212-firmware-path-rollback`
- dry-run decision: `apply-required`
- apply decision: `path-rollback-pass`
- reason: `firmware_class.path` apply, readback, request resolution, rollback,
  and cleanup passed

v212 proves the guarded temporary firmware path model. The dry-run does not
write `firmware_class.path`; the explicit `--apply` run writes
`/mnt/vendor/firmware`, verifies readback, then restores the original
`/vendor/firmware_mnt/image`.

## Implemented

- `scripts/revalidation/native_firmware_path_apply_probe.py`
  - requires v209/v210/v211 expected decisions by default
  - mounts `sda29` at `/mnt/vendor` with ext4 `ro,noload`
  - confirms likely request paths under `/mnt/vendor/firmware`
  - defaults to dry-run and returns `apply-required`
  - only generates sysfs write commands when `--apply` is explicitly present
  - uses `/cache/bin/a90_fwpathctl` for fixed-target sysfs writes because
    `/cache/bin/toybox` has no `sh` applet on the current device
  - rejects plain `echo`, shell redirection, bind mounts, Wi-Fi bring-up,
    daemon starts, module mutation, firmware copy, and persistent path
    mutations
- `stage3/linux_init/helpers/a90_fwpathctl.c`
  - fixed target: `/sys/module/firmware_class/parameters/path`
  - commands: `read`, `write <absolute-path>`
  - validates path characters and writes without shell or redirection
- `scripts/revalidation/build_fwpathctl_helper.sh`
  - builds the static ARM64 helper used for the apply phase

## Validation

Static checks:

```text
python3 -m py_compile \
  scripts/revalidation/native_firmware_path_apply_probe.py \
  scripts/revalidation/native_firmware_path_policy_probe.py \
  scripts/revalidation/a90harness/evidence.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_firmware_path_apply_probe
native_firmware_path_apply_probe.validate_apply_commands()
print('v212 command guard PASS')
PY

git diff --check
```

Helper build and deploy:

```text
scripts/revalidation/build_fwpathctl_helper.sh
python3 scripts/revalidation/tcpctl_host.py \
  --device-ip 'fe80::7051:8cff:fede:ff88%enx3a86942e0878' \
  --device-binary /cache/bin/a90_fwpathctl \
  install \
  --local-binary stage3/linux_init/helpers/a90_fwpathctl \
  --transfer-timeout 120 \
  --verbose
```

Helper artifact:

```text
8d08de43edd921099a6c2e627222e06488913d93f56fc0db01b5c7902df5e3cc  stage3/linux_init/helpers/a90_fwpathctl
```

Dry-run live collector:

```text
python3 scripts/revalidation/a90ctl.py --json version
rm -rf tmp/wifi/v212-firmware-path-rollback
python3 scripts/revalidation/native_firmware_path_apply_probe.py \
  --native-bridge \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --out-dir tmp/wifi/v212-firmware-path-rollback
```

Dry-run result:

```text
PASS out_dir=tmp/wifi/v212-firmware-path-rollback decision=apply-required reason=dry-run mount and request resolution passed; rerun with --apply to test sysfs write rollback
```

Artifact hashes:

```text
64d4ebc3d7a0d913c09dc0393adc2484f0cd66097d9d16e8172cfc7c8d6cf6d5  tmp/wifi/v212-firmware-path-rollback/manifest.json
23190130f3ad30b04be0c4b48d6bf0a42a77d96ebbcb789fb3ddf23ec1a52e09  tmp/wifi/v212-firmware-path-rollback/summary.md
```

Apply live collector:

```text
rm -rf tmp/wifi/v212-firmware-path-rollback
python3 scripts/revalidation/native_firmware_path_apply_probe.py \
  --native-bridge \
  --apply \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --out-dir tmp/wifi/v212-firmware-path-rollback
```

Apply result:

```text
PASS out_dir=tmp/wifi/v212-firmware-path-rollback decision=path-rollback-pass reason=firmware_class.path apply, readback, request resolution, rollback, and cleanup passed
```

Apply artifact hashes:

```text
f1fea94259a979f0d9dee7c2ba548d77bb7fde1ab6b550c492f550276d7f2ba8  tmp/wifi/v212-firmware-path-rollback/manifest.json
9320206dc5734a312cd93e09872cee9dbfb1707cdf09e20ef2b78f50a1150acb  tmp/wifi/v212-firmware-path-rollback/summary.md
```

## Dry-Run Evidence

- v209 decision: `vendor-assets-visible`
- v210 decision: `firmware-path-policy-needed`
- v211 decision: `sysfs-path-update-needed`
- `sda29` major/minor: `259:22`
- ext4 available: `true`
- mount command:

  ```text
  run /cache/bin/toybox mount -t ext4 -o ro,noload /tmp/a90-v212-*/sda29 /mnt/vendor
  ```

- mounted line: `ext4 ro,relatime,norecovery,i_version`
- cleanup rc: `0`
- leftover `/mnt/vendor` mount: `false`
- leftover `/tmp/a90-v212-*` mount: `false`
- original `firmware_class.path`: `/vendor/firmware_mnt/image`
- post-run `firmware_class.path`: `/vendor/firmware_mnt/image`

Likely request paths visible:

- `/mnt/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini`
- `/mnt/vendor/firmware/wlan/qca_cld/bdwlan.bin`
- `/mnt/vendor/firmware/wlan/qca_cld/regdb.bin`
- `/mnt/vendor/firmware/wlanmdsp.mbn`

Uncertain bare request paths not visible:

- `/mnt/vendor/firmware/WCNSS_qcom_cfg.ini`
- `/mnt/vendor/firmware/bdwlan.bin`
- `/mnt/vendor/firmware/regdb.bin`

## Apply Phase Status

Executed and passed.

Observed apply decision:

```text
path-rollback-pass
```

Post-apply acceptance:

- `firmware_class.path` readback equals `/mnt/vendor/firmware` after apply
- likely request paths remain visible
- rollback readback equals original `/vendor/firmware_mnt/image`
- final `firmware_class.path` equals `/vendor/firmware_mnt/image`
- no `/mnt/vendor` mount remains
- no `/tmp/a90-v212-*` mount remains
- no active Wi-Fi bring-up occurred

## Current Conclusion

The v212 guarded firmware path rollback test is complete. Native Wi-Fi work can
now proceed to the next non-connect stage: firmware request evidence or a
controlled ICNSS/CNSS preflight, still without scan/connect.
