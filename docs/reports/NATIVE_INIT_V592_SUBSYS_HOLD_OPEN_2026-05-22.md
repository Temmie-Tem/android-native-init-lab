# V592 Native Subsystem Hold-Open Report

- Date: 2026-05-22
- Helper: `a90_android_execns_probe v100`
- Evidence:
  - `tmp/wifi/v592-execns-helper-v100-deploy-preflight`
  - `tmp/wifi/v592-subsys-hold-open-proof`

## Result

- Deploy: `execns-helper-v100-deploy-pass`
- Live proof: `v592-subsys-hold-open-cleanup-review`
- Helper result: `subsys-hold-reboot-required`
- Wi-Fi bring-up: not executed
- Daemon/HAL start: not executed

## Observations

- `mountsystem ro` was required after native restore because `/mnt/system/system` was absent.
- Helper v100 created temporary subsystem char nodes:
  - `subsys_modem`: `236:0`
  - `subsys_esoc0`: `236:9`
- Opening the subsystem cdev path did not produce QRTR/QMI/WLFW readiness.
- The hold window showed:
  - `mss_state=OFFLINING`
  - `mdm3_state=OFFLINING`
  - `rpmsg_count=0`
  - `rpmsg_ipcrtr_present=0`
- The child exceeded the bounded cleanup window and was temporarily observed as an `a90_android_execns_probe` D-state process.
- A later read-only V593 pass showed the helper residual had cleared, so the D-state was a long firmware request wait rather than a permanent stuck process.

## Interpretation

`subsys_modem` open is not a safe next retry primitive by itself. It enters the modem PIL firmware load path, but native global firmware visibility is not ready. qcwlanstate/HAL retries remain blocked until the firmware request path is corrected.

## Next Gate

- Use V593 OFFLINING classifier output as the new blocker source.
- Compare Android firmware path and native global firmware mounts before any further cdev/HAL retry.
