# V1341 Android-order Pre-CNSS Provider Policy-ready Live

- Date: 2026-06-01
- Scope: native-init Wi-Fi bring-up blocker analysis
- Device baseline: `A90 Linux init 0.9.68 (v724)`
- Helper: `a90_android_execns_probe v279`
- Mode: `wifi-companion-android-order-pre-cnss-provider-observe-only`

## Decision

`v1341-provider-positive-no-lower-transition` — PASS.

V1341 repaired the V1339/V1340 provider-runtime gap by refreshing the current
boot V490 SELinux policy load and adding vndservice readiness/provider queries
to the Android-order pre-CNSS provider sequence.

The PM provider side is now positive:

| Item | Value |
| --- | --- |
| V490 policy load | `v490-selinux-policy-load-proof-pass` |
| vndservice readiness query | `query-exit-zero` |
| provider after `pm-service` | `1` |
| provider after `pm-proxy` | `1` |
| `pm-service` runtime domain | `u:r:vendor_per_mgr:s0` |
| `pm-proxy` runtime domain | `u:r:vendor_per_proxy:s0` |

## Build and Deploy

| Step | Result | Evidence |
| --- | --- | --- |
| helper v279 build | PASS | `stage3/linux_init/helpers/a90_android_execns_probe_v279` |
| helper v279 deploy | PASS | `tmp/wifi/v1341-execns-helper-v279-deploy/manifest.json` |
| V490 policy load | PASS | `tmp/wifi/v1341-v490-policy-load/manifest.json` |
| V1341 bounded live | PASS | `tmp/wifi/v1341-android-pre-cnss-provider-policy-ready-live/manifest.json` |

Helper v279:

- sha256: `2ec7c9584e0adb09755e1066ee01a986e3b7fd719c11b8a96aaf5c500d9dd15a`
- static aarch64: no dynamic section
- added query phases:
  - `android_pre_cnss_provider_vndservicemanager_ready`
  - `android_pre_cnss_provider_after_per_mgr`
  - `android_pre_cnss_provider_after_per_proxy`

## Live Contract

V1341 ran this bounded order:

```text
servicemanager
hwservicemanager
vndservicemanager
vndservice_ready_query
pm_proxy_helper
qrtr_ns
rmt_storage
tftp_server
pd_mapper
per_mgr
vndservice_query
per_proxy
vndservice_query
mdm_helper
cnss_diag
cnss_daemon
```

Observed helper result:

| Field | Value |
| --- | --- |
| `result` | `start-only-runtime-gap` |
| `reason` | `child-exited-before-observe-window` |
| `all_observable` | `1` |
| `all_postflight_safe` | `1` |
| `per_mgr_subsys_esoc0_window` | `0` |
| `mdm_helper_esoc0_window` | `0` |
| `ks_window` | `0` |
| `mhi_cmdline_window` | `0` |

## Interpretation

V1341 closes the V1339 provider startup regression:

```text
V490 policy load
  -> PM children enter vendor_per_mgr/vendor_per_proxy
  -> vendor.qcom.PeripheralManager appears in vndservice query
  -> Android-order provider side is positive
```

The remaining blocker moved forward and is now narrower:

```text
provider-positive pre-CNSS stack
  -> no provider-triggered /dev/subsys_esoc0 fd in window
  -> no mdm_helper /dev/esoc-0 hold
  -> no ks
  -> no MHI pipe
  -> no WLFW service 69
  -> no wlan0
```

This means the next useful work is not another SELinux/provider registration
repair. The provider registration side is working again. The next blocker is
the PM request/actionability path that should cause `pm-service` to open
`/dev/subsys_esoc0` or otherwise trigger the lower SDX50M/eSoC path.

## Guardrails Verified

- V490 policy load was the only global mutation.
- V490 did not reexec init, start daemons, or bring up Wi-Fi.
- No manual `/dev/subsys_esoc0` open.
- No eSoC ioctl, notify, or BOOT_DONE spoof.
- No PMIC/GPIO write.
- No Wi-Fi HAL or `wificond`.
- No scan/connect, credentials, DHCP/routes, or external ping.
- No flash, boot image write, or partition write.
- Cleanup reboot was not required.

## Validation

Executed:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh stage3/linux_init/helpers/a90_android_execns_probe_v279
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v279_deploy_preflight_v1341.py \
  scripts/revalidation/native_wifi_android_pre_cnss_provider_policy_ready_live_v1341.py
python3 scripts/revalidation/wifi_execns_helper_v279_deploy_preflight_v1341.py \
  --approval-phrase "approve v1341 deploy execns helper v279 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/native_wifi_android_pre_cnss_provider_policy_ready_live_v1341.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-policy-load \
  --allow-android-pre-cnss-provider-observe-only \
  --allow-cleanup-reboot \
  --assume-yes run
```

Result:

```text
decision: v1341-provider-positive-no-lower-transition
pass: True
```

## Next

V1342 should preserve the V1341 provider-positive setup and classify the PM
request/actionability gap before attempting Wi-Fi HAL or scan/connect:

1. keep current-boot V490 policy load as a hard precondition;
2. keep explicit vndservice provider-positive query;
3. observe `pm-service` Binder transaction/request handling after provider
   positive state;
4. classify why the request does not transition to `/dev/subsys_esoc0`,
   `mdm_helper` `/dev/esoc-0`, `ks`, MHI, WLFW, or `wlan0`;
5. keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
   manual eSoC open, PMIC/GPIO writes, flash, and boot image writes blocked.
