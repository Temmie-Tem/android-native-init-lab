# V1043 PM Full-Contract After V1042 Plan

- date: `2026-05-26`
- type: bounded live PM full-contract proof
- selected after: V1042 current-boot PM domain proof
- runner: `scripts/revalidation/native_wifi_pm_full_contract_v177_live_v1041.py`
- evidence dir: `tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live`

## Objective

Rerun the helper `v177` PM full-contract gate immediately after V1042 proves the
current-boot SELinux policy/domain precondition.

This separates two cases:

1. PM actors still fail SELinux exec-domain guard; or
2. PM actors enter the expected domains and the remaining blocker is lower,
   around `/dev/subsys_modem` fd formation.

## Gate

Allowed live order:

```text
property shim
  -> pm_proxy_helper
  -> pm-service
  -> pm-proxy
  -> mdm_helper
  -> PM fd predicate
  -> service-manager/CNSS only if lower guards pass
```

## Hard Guardrails

- no Wi-Fi HAL start
- no `wificond`
- no `IWifi.start`
- no `qcwlanstate` write
- no scan/connect/link-up
- no credentials
- no DHCP, route, or external ping
- no live eSoC ioctl, notify, or BOOT_DONE
- no `/dev/subsys_esoc0` open unless all lower gates pass
- no boot image write
- no partition write
- no firmware mutation
- no GPIO/sysfs/debugfs write

## Command

```bash
python3 scripts/revalidation/native_wifi_pm_full_contract_v177_live_v1041.py \
  --out-dir tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

## Success Criteria

- Runtime-domain guard matches all required PM actors.
- If `/dev/subsys_modem` fd contract remains absent, V1039 focused fd/wchan
  snapshots are captured.
- Forbidden Wi-Fi actions remain false.
- Cleanup reboot restores `bootstatus` and `selftest` if an actor remains in an
  unsafe state.
