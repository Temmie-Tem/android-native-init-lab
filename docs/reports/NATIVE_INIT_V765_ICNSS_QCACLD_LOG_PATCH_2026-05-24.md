# Native Init V765 ICNSS/QCACLD Log Patch Report

- date: `2026-05-24 KST`
- status: `pass`
- decision: `v765-icnss-qcacld-log-patch-ready`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py`
- evidence: `tmp/wifi/v765-icnss-qcacld-log-patch/`

## Summary

V765 generated a review-only unified diff with `A90V765` log markers for the
ICNSS/QCACLD path. It did not mutate source, build a kernel, write a boot image,
or run any device command.

Result:

```text
decision: v765-icnss-qcacld-log-patch-ready
patch_edits: 19
source_mutation_executed: False
kernel_build_executed: False
boot_image_write_executed: False
device_commands_executed: False
```

## Patch Coverage

| area | coverage |
| --- | --- |
| ICNSS QMI lookup | `icnss_register_fw_service()` |
| WLFW service arrival | `wlfw_new_server()` |
| ICNSS server event | `icnss_driver_event_server_arrive()` |
| ICNSS FW ready | `icnss_driver_event_fw_ready_ind()` |
| ICNSS driver registration | `icnss_driver_event_register_driver()`, `__icnss_register_driver()` |
| ICNSS probe handoff | `icnss_call_driver_probe()` |
| PLD-SNOC | `pld_snoc_register_driver()`, `pld_snoc_probe()` |
| HDD static loader | `wlan_boot_cb()`, `hdd_driver_load()` |
| HDD register/startup | `wlan_hdd_register_driver()`, `hdd_wlan_startup()` |

The generator anchors logs after local declarations or before existing runtime
statements to avoid the earlier compile-risk pattern of inserting logs before C
declarations.

## Validation

Commands:

```text
python3 -m py_compile scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py
python3 scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py plan
python3 scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py run
```

Manifest checks:

```text
v760-source-targets: pass
v763-architecture-rebase: pass
v764-mdm-helper-retry: pass
patch-edits: pass, applied=19 missing=0
patch-scope: pass, source_mutation=False
```

## Evidence Files

- `tmp/wifi/v765-icnss-qcacld-log-patch/manifest.json`
- `tmp/wifi/v765-icnss-qcacld-log-patch/summary.md`
- `tmp/wifi/v765-icnss-qcacld-log-patch/a90-v765-icnss-qcacld-log.patch`

## Next Gate

V766 should review and apply the generated patch to a disposable source build
tree, then run the kernel build/package checks. Boot image write, flash, live
handoff, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping
remain separate gates.

V766 follow-up fixed the generated unified-diff formatting so the patch is
actually `patch -p1` applicable, then verified clean apply and defconfig in a
disposable tree.
