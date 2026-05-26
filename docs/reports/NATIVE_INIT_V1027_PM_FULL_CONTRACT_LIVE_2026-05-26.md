# V1027 PM Full-Contract Live

- date: `2026-05-26`
- scope: bounded live classifier
- helper: `a90_android_execns_probe v174`
- decision: `v1027-pm-full-contract-missing-no-open`
- pass: `True`
- evidence: `tmp/wifi/v1027-pm-full-contract-live/manifest.json`

## Summary

V1027 started the Android PM full-contract order under native init. The gate did
not reach service-manager or CNSS because the PM fd predicate never became true.

Observed:

| Field | Value |
| --- | --- |
| `pm_proxy_helper_start_executed` | `True` |
| `pm_proxy_start_executed` | `True` |
| `mdm_helper_start_executed` | `True` |
| `mdm_helper_esoc0_fd_seen` | `1` |
| `pm_proxy_helper_subsys_modem_fd_count` | `0` |
| `per_mgr_subsys_modem_fd_count` | `0` |
| `pm_full_contract_seen` | `False` |
| `service_manager_start_executed` | `False` |
| `cnss_diag_start_executed` | `False` |
| `cnss_daemon_start_executed` | `False` |
| `subsys_esoc0_open_attempted` | `False` |
| `wifi_hal_start_executed` | `False` |
| `wifi_bringup_executed` | `False` |

The helper recorded `reboot-required` because `pm_proxy_helper` was not proven
stopped. Cleanup reboot completed and current native health is back to
`BOOT OK`, selftest `fail=0`.

## Interpretation

The next blocker is earlier than the post-provider subsystem retry. Native
`pm_proxy_helper` starts, but it does not reach an observable
`/dev/subsys_modem` fd. The dmesg tail shows `pm_proxy_helper` entered the modem
subsystem path and triggered modem PIL loading, while the PM full-contract fd
predicate stayed false.

This differs from the Android-good V1024 evidence where `pm_proxy_helper` and
`pm-service` both held `/dev/subsys_modem`.

## Guardrails

- no Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP/route, or external ping
- no `/dev/subsys_esoc0` child open
- no controller eSoC ioctl, notify, or BOOT_DONE
- no boot image or partition write
- cleanup reboot was used only because an actor was not proven stopped

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_full_contract_live_v1027.py
python3 scripts/revalidation/native_wifi_pm_full_contract_live_v1027.py plan
python3 scripts/revalidation/native_wifi_pm_full_contract_live_v1027.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
git diff --check
```

Post-run current health check:

```text
boot: BOOT OK shell
selftest: pass=11 warn=1 fail=0
```

## Next

V1028 should be a host-only classifier for the `pm_proxy_helper` modem get
blocker. Compare V1027 with Android V1024/V1022 evidence and decide whether the
missing input is service context, property/service state, modem firmware path,
or a lower modem subsystem precondition.
