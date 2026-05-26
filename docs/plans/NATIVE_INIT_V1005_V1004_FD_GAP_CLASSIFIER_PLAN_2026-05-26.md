# V1005 V1004 fd Gap Classifier Plan

## Goal

Classify why V1004 did not start the service-window-scoped
`/dev/subsys_esoc0` trigger: the fd gate did not observe `mdm_helper` holding
`/dev/esoc-0`.

V1005 is host-only. It compares:

- V1000 Android service-window dmesg/process/GPIO evidence;
- V911 native `mdm_helper` runtime-contract fd evidence;
- V1004 full Android service-window fd-gate evidence.

## Scope

1. Parse Android V1000 dmesg for service-window actor timing, `/dev/subsys_esoc0`
   get, `wlfw_start`, WLAN-PD, and ICNSS QMI.
2. Confirm Android V1000 process evidence includes `mdm_helper` holding
   `/dev/esoc-0`.
3. Confirm V911 proved native `mdm_helper` can hold `/dev/esoc-0` and wait in
   `ESOC_WAIT_FOR_REQ`.
4. Confirm V1004 started the full service-window actor set but the fd gate
   counted `0`.
5. Select the next route: Android dmesg refresh, helper fd-poll support, or
   evidence repair.

## Guardrails

V1005 must remain host-only:

- no device command;
- no Android boot or ADB command;
- no actor start;
- no `/dev/esoc-0` or `/dev/subsys_esoc0` open;
- no eSoC ioctl;
- no Wi-Fi scan/connect/link-up;
- no credential use;
- no DHCP/routes/external ping;
- no boot image, partition, firmware, GPIO, sysfs, or debugfs mutation.

## Success Criteria

V1005 passes if it produces one of these classified routes:

- `v1005-select-service-window-mdm-helper-fd-poll-support`;
- `v1005-select-android-dmesg-refresh-before-native-retry`.

A pass is not Wi-Fi success. It only selects the next minimal gate toward the
native Wi-Fi bring-up path.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_v1004_fd_gap_classifier_v1005.py
python3 scripts/revalidation/native_wifi_v1004_fd_gap_classifier_v1005.py
git diff --check
```
