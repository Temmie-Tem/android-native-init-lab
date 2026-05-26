# V1024 Fast FD Contract Classifier Plan

- date: `2026-05-26`
- type: source improvement + bounded Android handoff + host-only classifier
- selected after: V1023 Android PM/eSoC timing handoff

## Objective

Close the remaining Android-good PM/eSoC contract gap without another blind
native `/dev/subsys_esoc0` retry.

V1023 proved late ADB can capture the full WLFW/FW-ready/`wlan0` dmesg chain,
but the original V1022 sampler scanned process fds too late to reliably catch
the short early `vendor.per_proxy_helper` window.

## Changes

Improve `native_wifi_android_pm_esoc_timing_v1022.py` so the sample loop dumps
target process fds first:

- `pidof`-based fast path for `pm_proxy_helper`, `pm-service`, `pm-proxy`,
  `mdm_helper`, CNSS, `wificond`, and Wi-Fi HAL actors
- `/proc/*/comm` focused fallback before the broader `ps`/`cmdline` scan
- process-block fd classification to avoid false positives across adjacent
  process fd blocks

Then run the existing Android handoff with a V1024 evidence directory and
classify the combined result host-only.

## Hard Gates

- no native `/dev/subsys_esoc0` retry
- no `/dev/esoc-*` ioctl
- no eSoC notify, image response, or BOOT_DONE
- no GPIO/sysfs/debugfs write
- no Wi-Fi command, scan/connect/link-up, credential use, DHCP/route, or external ping
- Android boot write must be followed by native v724 readback and native `BOOT OK`

## Validation

Static:

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py \
  scripts/revalidation/native_wifi_v1024_fast_fd_contract_classifier.py
python3 scripts/revalidation/native_wifi_android_pm_esoc_timing_v1022.py --out-dir tmp/wifi/v1024-v1022-fast-fd-plan plan
python3 scripts/revalidation/native_wifi_v1024_fast_fd_contract_classifier.py plan
git diff --check
```

Live evidence:

```bash
RUN_DIR="tmp/wifi/v1024-fast-fd-android-timing-handoff-live-$(date +%Y%m%d-%H%M%S)"
echo "$RUN_DIR" > tmp/wifi/latest-v1024-fast-fd-android-timing-handoff.txt
python3 scripts/revalidation/android_pm_esoc_timing_handoff_v1023.py \
  --out-dir "$RUN_DIR" \
  --allow-android-boot-flash \
  --assume-yes \
  --i-understand-native-rollback \
  run
python3 scripts/revalidation/native_wifi_v1024_fast_fd_contract_classifier.py run
```

## Success Criteria

- Early sample captures at least one Android PM/eSoC fd contract snapshot.
- Late sample captures WLFW/FW-ready/`wlan0` continuation.
- Classifier compares this against V1020 native missing PM proxy contract.
- Native rollback is verified after live handoff.

