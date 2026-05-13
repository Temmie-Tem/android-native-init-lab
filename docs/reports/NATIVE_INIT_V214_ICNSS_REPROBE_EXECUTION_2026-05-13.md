# Native Init v214 ICNSS Reprobe Execution Report

## Summary

- status: SAFETY STOP
- runtime device build: `A90 Linux init 0.9.59 (v159)`
- plan: `docs/plans/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_PLAN_2026-05-13.md`
- collector: `scripts/revalidation/native_firmware_request_probe.py`
- helper: `/cache/bin/a90_icnssctl`
- evidence: `tmp/wifi/v214-icnss-reprobe`
- final decision: `icnss-rebind-failed`

v214 executed the planned opt-in ICNSS reprobe. The safe firmware path and
vendor mount portions worked, but `icnss` bind failed after unbind with kernel
error `-17` (`EEXIST`) and `write icnss control: No such device`. The device was
then rebooted back to native init, and ICNSS returned to the bound state.

This result blocks further Wi-Fi bring-up until ICNSS lifecycle handling is
understood. Do not proceed to scan/connect or daemon/HAL bring-up from this
state.

## Implementation Notes

- Reused v213 collector with `--apply-path --reprobe`.
- Built `stage3/linux_init/helpers/a90_icnssctl` as a static ARM64 binary.
- Deployed helper through TWRP ADB because host-side NCM IPv4 setup required
  interactive sudo and was not available to the agent.
- Patched the collector after the first v214 attempt to use the live
  `/sys/class/block/sda29/dev` major/minor instead of the v212 observed static
  `259:22`. On this boot, `sda29` was `259:32`.
- Patched the collector's post-reprobe ICNSS bound helper so future reports do
  not treat pre-reprobe `DRIVER=icnss` as post-reprobe bound evidence.

## Static Validation

```sh
scripts/revalidation/build_icnssctl_helper.sh

python3 -m py_compile scripts/revalidation/native_firmware_request_probe.py

python3 - <<'PY'
import sys
sys.path.insert(0, 'scripts/revalidation')
import native_firmware_request_probe as p
p.validate_no_active_wifi_commands()
p.validate_command_guard()
print('v214 dynamic/rebind guard PASS')
PY

git diff --check
```

Results:

- `a90_icnssctl` static build: PASS
- Python compile: PASS
- command guard: PASS
- `git diff --check`: PASS

Hashes:

```text
652b66cb9079b0e9dd194c871bee7aca8dde16577a53f1837be71bd25babf0d5  stage3/linux_init/helpers/a90_icnssctl
af78f9d308359555a050b913e886cc2333b6f177e1fd5837bebc3d8e71c95730  scripts/revalidation/native_firmware_request_probe.py
f0a92f9dcf703111005c470175ded13d0f85b1d893ea0b0e19812e8aa09b7e90  docs/plans/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_PLAN_2026-05-13.md
```

## Helper Deployment

TWRP ADB deployment:

```sh
adb shell 'mkdir -p /cache/bin && chmod 755 /cache/bin'
adb push stage3/linux_init/helpers/a90_icnssctl /cache/bin/a90_icnssctl
adb shell 'chmod 755 /cache/bin/a90_icnssctl && sync && sha256sum /cache/bin/a90_icnssctl'
```

Native verification after reboot:

```text
mode=0755 uid=0 gid=0 size=663568
652b66cb9079b0e9dd194c871bee7aca8dde16577a53f1837be71bd25babf0d5  /cache/bin/a90_icnssctl
DRIVER=icnss
OF_NAME=qcom,icnss
OF_FULLNAME=/soc/qcom,icnss@18800000
```

## Reprobe Result

Command:

```sh
python3 scripts/revalidation/native_firmware_request_probe.py \
  --native-bridge \
  --apply-path \
  --reprobe \
  --i-understand-icnss-reprobe \
  --v209-manifest tmp/wifi/v209-vendor-ro-mount-probe/manifest.json \
  --v210-manifest tmp/wifi/v210-vendor-asset-classifier/manifest.json \
  --v211-manifest tmp/wifi/v211-firmware-path-policy/manifest.json \
  --v212-manifest tmp/wifi/v212-firmware-path-rollback/manifest.json \
  --out-dir tmp/wifi/v214-icnss-reprobe
```

Result:

```text
FAIL out_dir=tmp/wifi/v214-icnss-reprobe decision=icnss-rebind-failed reason=ICNSS bind/rebind evidence did not return to bound state
```

Key facts:

- `sda29`: `259:32`
- ext4 support: present
- temporary vendor mount: PASS
- request path visibility under `/mnt/vendor/firmware`: PASS
- `firmware_class.path` applied: `/mnt/vendor/firmware`
- `icnss unbind`: PASS
- `icnss bind`: FAIL
- bind stderr: `write icnss control: No such device`
- dmesg: `icnss: Driver is already initialized`
- dmesg: `icnss: probe of 18800000.qcom,icnss failed with error -17`
- request evidence: none
- `firmware_class.path` rollback: PASS
- `/mnt/vendor` cleanup: PASS
- `/tmp/a90-v213-*` mount cleanup: PASS

Evidence hashes:

```text
4e71bef89f30c3e5633aa99bc8a39882a2374c39135f154751d22b72c00e094f  tmp/wifi/v214-icnss-reprobe/manifest.json
c9bc79cff9ecb97e838fe422c307a5b2deb604fa49d2aca68c36292bbca50df1  tmp/wifi/v214-icnss-reprobe/summary.md
4956e7c5f64ca8be6f8ca416a325f6d634113b111b3b0379f6cc4c70d32320c2  tmp/v214-after-rebind-retry-dmesg.txt
```

## Recovery

After the failed bind, a single manual bind retry produced the same `-17`
failure. The device was rebooted to restore ICNSS state.

Post-reboot recovery check:

```text
DRIVER=icnss
/sys/bus/platform/drivers/icnss contains 18800000.qcom,icnss
firmware_class.path = /vendor/firmware_mnt/image
a90_icnssctl SHA256 = 652b66cb9079b0e9dd194c871bee7aca8dde16577a53f1837be71bd25babf0d5
```

Recovery evidence hash:

```text
4e466f4d647587a54fae9ea4f774f8b28110c7b8e7e46cff466791f58fa1fc78  tmp/wifi/v214-post-reboot-recovery.txt
```

## Decision

v214 proves that generic sysfs unbind/bind is not a safe ICNSS reprobe method on
this kernel. The bind path returns `-ENODEV` to userspace while the kernel logs
`-EEXIST` / already initialized, leaving the driver sysfs link absent until
reboot.

The next step should be v215 focused on ICNSS/CNSS lifecycle research, not Wi-Fi
bring-up. Candidate directions:

1. inspect Android/TWRP dmesg and init service ordering around ICNSS/CNSS;
2. look for ICNSS recovery/sysfs debug controls under the ICNSS node;
3. inspect vendor init rc for CNSS service hooks and subsystem restart policy;
4. search kernel source references for Samsung SM8150/ICNSS `Driver is already
   initialized` behavior;
5. avoid further unbind/bind until a driver-specific recovery method is known.
