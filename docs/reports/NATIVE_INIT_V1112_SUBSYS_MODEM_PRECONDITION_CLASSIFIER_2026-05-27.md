# V1112 Subsys Modem Precondition Classifier Report

Date: `2026-05-27`

## Result

- Decision: `v1112-select-global-firmware-holder-before-cnss-pm-connect`
- Pass: `true`
- Evidence: `tmp/wifi/v1112-subsys-modem-precondition-classifier/manifest.json`
- Collector: `scripts/revalidation/native_wifi_subsys_modem_precondition_classifier_v1112.py`

## Summary

V1112 reconciles the V1111 `/dev/subsys_modem` blocker with earlier global
firmware and modem-holder evidence.

V1111 proved that after fixing the pre-CNSS `per_proxy` ordering, `cnss-daemon`
can complete the PM register/connect path, and that successful CNSS PM connect
makes a `pm-service` Binder owner thread call:

```text
openat("/dev/subsys_modem") -> __subsystem_get
```

The blocked open occurs with no pre-existing PM actor `/dev/subsys_modem` fd.

V1112 live read-only surface shows the current global firmware prerequisite is
not present in the base native namespace:

```text
firmware_class.path=/vendor/firmware_mnt/image
/vendor/firmware_mnt/image exists=false
/vendor/firmware_mnt/image/modem.b00 readable=false
/mnt/vendor mounted=true
/vendor/firmware_mnt mounted globally=false
modem state=OFFLINING
esoc0 state=OFFLINING
subsys_modem dev=236:0
```

V1061 proves the complementary half: when global firmware mounts and a global
`/dev/subsys_modem` holder are present, the modem holder opens and `mss` reaches
`ONLINE`, but that path lacked the later CNSS-triggered `pm-service` open.

## Interpretation

The next useful gate is not another plain `pm-service`/CNSS retry and not Wi-Fi
HAL. The evidence now points to combining two separately proven prerequisites:

1. V1061 global firmware mount + bounded modem holder to satisfy
   `firmware_class.path` and avoid first-opener/PIL ambiguity.
2. V1108/V1111 PM ordering where `cnss-daemon` reaches successful PM connect and
   triggers `pm-service` to open `/dev/subsys_modem`.

This should answer whether the V1111 block is only a missing first-opener
precondition or whether `pm-service` still blocks even after the modem holder is
already established.

## Safety

- `device_mutations=false`
- `subsys_modem_open_attempted=false`
- `subsys_esoc0_open_attempted=false`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `flash_executed=false`
- `reboot_executed=false`

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_subsys_modem_precondition_classifier_v1112.py
python3 scripts/revalidation/native_wifi_subsys_modem_precondition_classifier_v1112.py plan
python3 scripts/revalidation/native_wifi_subsys_modem_precondition_classifier_v1112.py run
```

Live run result:

```text
decision: v1112-select-global-firmware-holder-before-cnss-pm-connect
pass: True
```

## Next

V1113 should be source/build-only first:

- add a PM-service observer order that installs global firmware mounts and a
  bounded `/dev/subsys_modem` holder before service-manager/PM/CNSS PM-connect
  probing;
- keep `/dev/subsys_esoc0`, eSoC ioctl/control, Wi-Fi HAL, `wificond`,
  scan/connect, credentials, DHCP/routes, and external ping forbidden;
- capture whether the later `pm-service` `/dev/subsys_modem` open returns or
  remains blocked once the holder prerequisite is already true.
