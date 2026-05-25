# V900 mdm_helper/ks Contract Live Plan

## Goal

Run the first bounded native live proof for the Android-derived
`mdm_helper`/`ks` image/link contract.

V900 is not a Wi-Fi bring-up step. It only checks whether starting
`/vendor/bin/mdm_helper` before opening `/dev/subsys_esoc0` can produce
`/vendor/bin/ks`, the MHI pipe command line, GPIO 142 readiness, or later
WLFW/BDF/`wlan0` evidence.

## Inputs

- V896 Android positive-control contract:
  `docs/reports/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_2026-05-26.md`
- V897 native contract classifier:
  `docs/reports/NATIVE_INIT_V897_MDM_HELPER_KS_CONTRACT_DESIGN_2026-05-26.md`
- V898 helper mode:
  `docs/reports/NATIVE_INIT_V898_MDM_HELPER_KS_CONTRACT_HELPER_BUILD_2026-05-26.md`
- V899 helper deploy:
  `docs/reports/NATIVE_INIT_V899_HELPER_V144_DEPLOY_2026-05-26.md`
- live runner:
  `scripts/revalidation/native_wifi_mdm_helper_ks_contract_live_v900.py`

## Method

1. Verify native health with `bootstatus` and `selftest`.
2. Mount system/vendor read-only through the existing guarded helper path.
3. Verify remote helper sha, marker, and mode before execution.
4. Run helper mode
   `wifi-companion-mdm-helper-ks-image-contract-preflight`.
5. Permit only this ordered live contract:
   - start `/vendor/bin/mdm_helper`;
   - wait until `mdm_helper` is observable;
   - open `/dev/subsys_esoc0` only after that gate opens;
   - observe `/vendor/bin/ks` and
     `/dev/mhi_0305_01.01.00_pipe_10`.
6. If any actor or trigger cannot be proven stopped, perform cleanup reboot and
   verify native health.

## Hard Gates

- No service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, or Wi-Fi link-up.
- No controller-side `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, explicit
  `PWR_ON`, `ESOC_WAIT_FOR_REQ`, `ESOC_NOTIFY`, or `ESOC_BOOT_DONE`.
- No module load/unload, boot image write, partition write, firmware mutation,
  GPIO/sysfs/debugfs write, or Wi-Fi configuration.

## Success Criteria

- The runner emits a private evidence bundle and manifest.
- Remote helper sha/marker/mode match the expected artifact.
- The helper proves the `mdm_helper` before `/dev/subsys_esoc0` ordering.
- The result is classified as one of:
  - `ks-mhi-observed`;
  - `mdm-helper-window-no-ks`;
  - `mdm-helper-not-observable`;
  - `reboot-required` with cleanup reboot health restored.
- Native postflight or cleanup reboot ends with `selftest fail=0`.

## Expected Branches

- If `ks` or MHI appears, inspect `mdm3`, GPIO 142, WLFW/BDF, and `wlan0`
  before any HAL or scan work.
- If `/dev/subsys_esoc0` blocks again, capture the exact wait location before
  another equivalent retry.
- If `mdm_helper` exits before observation, classify its missing runtime input.
