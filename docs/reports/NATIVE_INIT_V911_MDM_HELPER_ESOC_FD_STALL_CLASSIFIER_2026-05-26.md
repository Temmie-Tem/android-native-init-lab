# Native Init V911 mdm_helper eSoC FD Stall Classifier Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| v149 live capture | `tmp/wifi/v911-mdm-helper-esoc-fd-stall-live/manifest.json` | `v908-mdm-helper-esoc-fd-observed` |
| host-only classifier | `tmp/wifi/v911-mdm-helper-esoc-fd-stall-classifier/manifest.json` | `v911-mdm-helper-wait-for-req-observed` |

V911 classified the V908/V909 boundary. `mdm_helper` now reaches `/dev/esoc-0`
and its worker thread blocks in the eSoC request wait ioctl.

## Key Evidence

| Field | Value |
| --- | --- |
| `fd_esoc0_count.window` | `1` |
| `fd_esoc0_count.final` | `1` |
| `fd_subsys_esoc0_count.final` | `0` |
| `fd_mhi_pipe_count.final` | `0` |
| `ks_count.final` | `0` |
| `mhi_pipe_cmdline_count.final` | `0` |
| `/dev/esoc-0` fd flags | `0404000` |
| `/dev/esoc-0` fd mnt_id | `29` |
| main thread wchan | `SyS_nanosleep` |
| worker thread wchan | `esoc_dev_ioctl` |
| worker syscall | `29 0x3 0x8004cc02 ...` |
| decoded ioctl | `ESOC_WAIT_FOR_REQ` |
| all_postflight_safe | `1` |

The ioctl decodes as `_IOR(0xcc, 2, u32)`, matching the local eSoC
`ESOC_WAIT_FOR_REQ` contract documented earlier.

## Interpretation

The blocker moved again:

```text
before V908: mdm_helper observable, no /dev/esoc-0
V908:        mdm_helper observable, /dev/esoc-0 fd observed, no ks/MHI
V911:        mdm_helper worker blocked in ESOC_WAIT_FOR_REQ, no ks/MHI
```

This means the native runtime contract is now close enough for `mdm_helper` to
enter the expected request-engine wait path. The missing piece is a bounded
powerup/request event while `mdm_helper` owns `/dev/esoc-0`.

## Guardrails

- `pm_proxy_helper_start_executed=0`
- `service_manager_start_executed=0`
- `cnss_start_executed=0`
- `wifi_hal_start_executed=0`
- `scan_connect_linkup=0`
- `credentials=0`
- `dhcp_routing=0`
- `external_ping=0`
- `subsys_esoc0_controller_open_attempted=0`
- `reg_req_eng_attempted=0`
- `notify_attempted=0`
- `boot_done_attempted=0`

Postflight remained healthy: actor surface empty, Wi-Fi link surface empty,
`bootstatus` OK, and `selftest fail=0`.

## Validation

Executed:

```bash
python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_capture_v908.py \
  --out-dir tmp/wifi/v911-mdm-helper-esoc-fd-stall-live \
  --local-helper tmp/wifi/v909-execns-helper-v149-build/a90_android_execns_probe \
  --helper-sha256 b615aa127e130e8b285642b34992102fa6d0c15702479bc1265dd4c5f06dff49 \
  --helper-marker "a90_android_execns_probe v149" \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-runtime-contract-capture \
  --allow-cleanup-reboot \
  --assume-yes \
  run
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_esoc_fd_stall_classifier_v911.py
python3 scripts/revalidation/native_wifi_mdm_helper_esoc_fd_stall_classifier_v911.py
```

## Next

V912 should plan a guarded powerup trigger while `mdm_helper` owns the REQ path.
The likely candidate is a bounded `/dev/subsys_esoc0` trigger with explicit
cleanup/reboot handling, but it must be planned carefully because previous
subsystem-open gates could enter D-state.
