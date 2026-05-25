# Native Init V908 mdm_helper Runtime Contract Capture Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| r1 setup check | `tmp/wifi/v908-mdm-helper-runtime-contract-capture-live/manifest.json` | `v908-step-failed` |
| r2 runtime-contract capture | `tmp/wifi/v908-mdm-helper-runtime-contract-capture-live-r2/manifest.json` | `v908-mdm-helper-esoc-fd-observed` |

V908 proved that the V906/V907 runtime-contract repair changes the native
surface materially: with selinuxfs mounted and the private property layout
bound, `per_mgr_light` plus `mdm_helper` reaches `/dev/esoc-0`.

## r1 Failure

The first run failed before actor start:

```text
helper_status=setup-error
setup_error=stat host selinux status: No such file or directory
```

Read-only probing showed `selinuxfs` is supported by the kernel but not mounted
by default in native init. The V908 runner was updated to perform a bounded
selinuxfs mount before helper execution and cleanup unmount after postflight.

## r2 Capture

| Field | Value |
| --- | --- |
| decision | `v908-mdm-helper-esoc-fd-observed` |
| selinuxfs_mount_executed | `True` |
| selinuxfs_umount_executed | `True` |
| property_root | `/mnt/sdext/a90/private-property-v317/v535/dev/__properties__` |
| mdm_helper_observable | `1` |
| fd_esoc0_count.window | `0` |
| fd_esoc0_count.final | `1` |
| fd_subsys_esoc0_count.final | `0` |
| fd_mhi_pipe_count.final | `0` |
| ks_count.final | `0` |
| mhi_pipe_cmdline_count.final | `0` |
| all_postflight_safe | `1` |

The observed fd target was:

```text
/tmp/a90-v231-699/root/dev/esoc-0
```

This is the private namespace mirror of `/dev/esoc-0`, not a controller
`/dev/subsys_esoc0` open.

## Postflight

- post actor surface: empty
- Wi-Fi link surface: empty
- `subsys9/state`: `OFFLINING`
- GPIO142 `mdm status` IRQ count: `0`
- no `ks`, MHI pipe, WLFW, BDF, `wlan0`, DHCP, route, or external ping
- post `bootstatus` and `selftest` remained healthy

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

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_runtime_contract_capture_v908.py
python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_capture_v908.py plan
python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_capture_v908.py \
  --out-dir tmp/wifi/v908-mdm-helper-runtime-contract-capture-live-r2 \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-runtime-contract-capture \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

## Interpretation

The blocker moved forward:

```text
before V908: mdm_helper observable, no /dev/esoc-0
after V908:  mdm_helper observable, /dev/esoc-0 fd observed, no ks/MHI
```

The next missing transition is inside or immediately after the `/dev/esoc-0`
interaction. `mdm_helper` now reaches the eSoC userland device, but it does not
produce `/vendor/bin/ks`, the MHI pipe, GPIO142 IRQ, mdm3 ONLINE, WLFW service
69, BDF, or `wlan0`.

## Next

V909 should classify the `/dev/esoc-0` interaction boundary without opening
`/dev/subsys_esoc0`: capture `mdm_helper` wchan/syscall/fdinfo/stack while the
`/dev/esoc-0` fd is present, then compare that stalled point with the Android
reference where `ks` and MHI appear.
