# V1027 PM Full-Contract Live Plan

- date: `2026-05-26`
- type: bounded live classifier
- helper: `a90_android_execns_probe v174`
- prior deploy: `docs/reports/NATIVE_INIT_V1026_HELPER_V174_DEPLOY_2026-05-26.md`

## Objective

Run the V1025 Android PM full-contract order on native init and determine
whether the Android-good fd predicate can be reproduced before any Wi-Fi
scan/connect work.

## Gate

Order:

```text
property-shim
  -> pm_proxy_helper
    -> pm-service
      -> pm-proxy
        -> mdm_helper
          -> PM full-contract fd gate
            -> /dev/esoc-0 fd gate
              -> service-manager trio
                -> cnss_diag
                  -> cnss-daemon
```

Required PM full-contract predicate:

```text
pm_proxy_helper -> /dev/subsys_modem
pm-service      -> /dev/subsys_modem
mdm_helper      -> /dev/esoc-0
```

## Guardrails

- no Wi-Fi HAL start
- no `wificond`
- no `IWifi.start`
- no `qcwlanstate`
- no scan/connect/link-up
- no credentials
- no DHCP/routes/external ping
- no eSoC controller ioctl
- no notify or BOOT_DONE
- no GPIO/sysfs/debugfs write
- cleanup reboot allowed if any actor is not proven stopped

## Commands

```bash
python3 scripts/revalidation/native_wifi_pm_full_contract_live_v1027.py plan
python3 scripts/revalidation/native_wifi_pm_full_contract_live_v1027.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

## Success Criteria

The classifier passes if it records one of these bounded outcomes:

- PM full-contract observed, WLFW still missing
- PM full-contract observed, WLFW precondition appears
- PM full-contract missing with actor/fd evidence

Only the second outcome can move toward WLAN/BDF/`wlan0` immediately. Missing
PM full-contract evidence must be classified before any subsystem retry.
