# Native Init V1133 Lower Holder Route Classifier Report

Date: `2026-05-27`

## Result

- Decision: `v1133-outer-global-holder-post-policy-cnss-composite-selected`
- Pass: `true`
- Evidence: `tmp/wifi/v1133-lower-holder-route-classifier/manifest.json`
- Summary: `tmp/wifi/v1133-lower-holder-route-classifier/summary.md`
- Classifier:
  `scripts/revalidation/native_wifi_lower_holder_route_classifier_v1133.py`

## Summary

V1133 reclassifies the lower route after V1132.

The current route should not be:

1. the stale V1071 `pm-service exit 255` / broad BPF branch;
2. another helper-private `/dev/subsys_modem` pre-holder retry;
3. another `O_NONBLOCK` variation.

The selected route is:

```text
outer global firmware + subsys_modem holder
  -> mss ONLINE / QRTR RX
  -> current post-policy provider-positive CNSS PM observer
  -> observe whether mdm3/WLFW/service69/wlan0 advance
```

## Evidence

| Item | Result |
| --- | --- |
| V731 outer holder | `v731-firmware-mounted-modem-holder-qrtr-rx-pass` |
| V1113 recent outer holder | `mss_after_holder=ONLINE`, `qrtr_rx=1` |
| V1128 post-policy CNSS PM | provider visible, PM client/server register/connect return `0x0` |
| V1131 helper-private pre-holder | attempted but open-pending; holder not confirmed |
| V1132 nonblock semantics | subsystem open ignores nonblocking flags and enters synchronous powerup |

Important state split:

```text
V1113 outer holder:
  holder_opened=true
  mss_after_holder=ONLINE
  qrtr_rx=1

V1128 post-policy CNSS PM:
  provider_seen=true
  cnss_pm_register_ok=true
  cnss_pm_connect_ok=true
  pm_server_register_ok=true
  pm_server_connect_ok=true

V1131 private pre-holder:
  holder_attempted_but_open_pending=true
  holder_confirmed=false
  mss_after=OFFLINING
  mdm3_after=OFFLINING
```

## Interpretation

The missing combination is now explicit:

- V731/V1113 prove the outer holder can advance the lower modem prerequisite.
- V1128 proves the current post-policy PM/provider/CNSS path can reach
  successful register/connect.
- V1131/V1132 prove moving that holder inside the helper as a synthetic
  private pre-holder does not work.

Therefore V1134 should combine the working outer holder window with the working
post-policy CNSS PM observer. It should not use the helper-private modem
pre-holder flag.

## Safety

V1133 did not perform:

```text
device_commands_executed=false
device_mutations=false
tracefs_write_executed=false
pm_actor_executed=false
cnss_daemon_start_executed=false
wifi_hal_start_executed=false
scan_connect_executed=false
credential_use_executed=false
dhcp_route_executed=false
external_ping_executed=false
partition_write_executed=false
flash_executed=false
```

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_lower_holder_route_classifier_v1133.py
python3 scripts/revalidation/native_wifi_lower_holder_route_classifier_v1133.py
```

Result:

```text
decision: v1133-outer-global-holder-post-policy-cnss-composite-selected
pass: True
```

## Next

V1134 should be a bounded live runner that:

1. refreshes current-boot V401/V490 preconditions before actor start;
2. mounts global firmware read-only and opens the outer `subsys_modem` holder;
3. waits for QRTR RX / `mss=ONLINE`;
4. runs the V1128/V1131 post-policy provider-positive CNSS PM observer using
   helper `v213`;
5. disables helper-private modem pre-holder;
6. records CNSS PM returns, PM server side effects, `mss`, `mdm3`, QRTR service
   `69/74/180`, WLFW/BDF/MHI, and `wlan0`;
7. performs cleanup reboot and post-reboot health checks.

Still forbid `/dev/subsys_esoc0`, Wi-Fi HAL, scan/connect, credentials,
DHCP/route changes, external ping, partition writes, boot image writes, and
flash.
