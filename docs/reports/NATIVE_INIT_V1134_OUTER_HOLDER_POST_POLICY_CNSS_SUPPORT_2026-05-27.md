# Native Init V1134 Outer Holder Post-policy CNSS Support Report

Date: `2026-05-27`

## Result

- Decision: `v1134-outer-holder-post-policy-cnss-plan-ready`
- Pass: `true`
- Plan evidence:
  `tmp/wifi/v1134-outer-holder-post-policy-cnss-live/manifest.json`
- Runner:
  `scripts/revalidation/native_wifi_outer_holder_post_policy_cnss_live_v1134.py`
- Plan:
  `docs/plans/NATIVE_INIT_V1134_OUTER_HOLDER_POST_POLICY_CNSS_PLAN_2026-05-27.md`

## Summary

V1134 support adds the runner for the V1133-selected composite live gate.

It combines:

- V1113 outer global firmware mount + `/dev/subsys_modem` holder window;
- V1121/V1131 no-pre-CNSS-`per_proxy` PM observer order;
- helper `a90_android_execns_probe v213`;
- no helper-private modem pre-holder flags.

The runner plan mode passed and confirmed that no device mutation, PM actor,
CNSS daemon, reboot, Wi-Fi HAL, scan/connect, credential use, DHCP/route change,
or external ping occurred.

## Contract

Required child flag:

```text
--pm-observer-start-cnss-before-per-proxy
```

Forbidden child flags:

```text
--allow-pm-observer-modem-pre-holder
--pm-observer-modem-pre-holder
```

The live runner decides separately whether:

- outer holder and QRTR RX are reproduced;
- CNSS PM register/connect return values are reproduced under the holder;
- `mdm3`, QRTR service `69/74/180`, WLFW/BDF/MHI, or `wlan0` advance;
- PM server still opens `/dev/subsys_modem` despite the outer holder.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_outer_holder_post_policy_cnss_live_v1134.py
python3 scripts/revalidation/native_wifi_outer_holder_post_policy_cnss_live_v1134.py plan
```

Result:

```text
decision: v1134-outer-holder-post-policy-cnss-plan-ready
pass: True
firmware_mounts_executed: False
global_modem_holder_opened: False
helper_private_holder_requested: False
cnss_daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next

Run the current-boot preconditions and then V1134 live:

1. V401 selinuxfs runtime surface;
2. V490 native SELinux policy-load proof for helper `v213`;
3. V1134 live with tracefs/vendor/selinuxfs/PM/CNSS allow flags.

Still forbid `/dev/subsys_esoc0`, eSoC control ioctl, Wi-Fi HAL, scan/connect,
credential use, DHCP/route changes, external ping, partition writes, boot image
writes, and flash.
