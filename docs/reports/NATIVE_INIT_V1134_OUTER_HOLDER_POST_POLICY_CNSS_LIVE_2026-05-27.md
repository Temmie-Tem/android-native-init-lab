# Native Init V1134 Outer Holder Post-policy CNSS Live Report

Date: `2026-05-27`

## Result

- Decision: `v1134-cnss-pm-connect-no-wlfw-delta`
- Pass: `true`
- Evidence: `tmp/wifi/v1134-outer-holder-post-policy-cnss-live-run/manifest.json`
- Device after cleanup: `A90 Linux init 0.9.68 (v724)`, selftest `fail=0`

## Summary

V1134 executed the V1133-selected composite live gate:

```text
global firmware mounts
  -> outer /dev/subsys_modem holder
  -> mss ONLINE / QRTR RX wait
  -> post-policy provider-positive CNSS PM observer
```

The run reproduced the important upper path: `cnss-daemon` reached Peripheral
Manager and both PM client operations returned success:

```text
register_ret=['0x0']
connect_ret=['0x0']
```

However, this still did not advance the lower WLAN chain. QRTR services
`69`, `74`, and `180` were absent after the observer window, and there was no
WLFW/BDF/MHI/QCA6390/wlan0 marker.

## Key Evidence

```text
firmware_mounts_executed=True
global_modem_holder_opened=True
helper_private_holder_requested=False
cnss_daemon_start_executed=True
wifi_hal_start_executed=False
wifi_bringup_executed=False
external_ping_executed=False
```

Lower state:

```text
mss_before=OFFLINING
mss_after_holder=ONLINE
mss_after_observer=ONLINE
mdm3_before=OFFLINING
mdm3_after_holder=OFFLINING
mdm3_after_observer=OFFLINING
```

Marker summary:

```text
qrtr_rx=2
qrtr_tx=0
sysmon_qmi=0
service_notifier=0
wlan_pd=0
mhi=0
qca6390=0
wlfw=0
bdf=0
wlan0=0
kernel_warning=3
```

The first kernel warning remains the known eSoC reference-count mismatch:

```text
subsys-restart: subsystem_put(): subsystem_put: esoc0 count:0
esoc0: subsystem_put: Reference count mismatch
```

## Interpretation

V1134 closes the question of whether combining:

- global modem firmware visibility;
- an outer `/dev/subsys_modem` holder;
- V490 post-policy runtime;
- provider-positive CNSS PM register/connect;

is sufficient to publish WLFW/service `69`.

It is not sufficient. The next blocker is below Peripheral Manager client
success: `mdm3`/eSoC or WLAN firmware publication still does not advance from
`OFFLINING` to the WLFW/service69 path.

## Guardrail Result

The run did not execute Wi-Fi HAL start, scan/connect/link-up, credentials,
DHCP/route changes, external ping, partition writes, boot image writes, or
flash.

Cleanup reboot completed and native health returned:

```text
A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
```

## Next

V1135 should classify the remaining lower blocker under the now-proven upper
PM path:

1. compare V1134 post-PM success against Android mdm3/eSoC/WLFW publication;
2. focus on why `mdm3` remains `OFFLINING` despite successful PM register/connect;
3. separate safe eSoC reference-count warning analysis from actual WLFW
   publication requirements;
4. keep Wi-Fi HAL, scan/connect, credentials, DHCP/route, and external ping
   blocked until service `69` or equivalent WLFW readiness appears.

## Validation

Executed current-boot preconditions:

```bash
python3 scripts/revalidation/a90ctl.py --timeout 30 mountsystem ro
python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v1134-v490-policy-load-v213-r2 \
  --helper-sha256 d1c354b2b089ede50cc53d452666d119e9151b1e97b7bb1344dbd0431bd69356 \
  --approval-phrase "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
```

V490 result:

```text
decision: v490-selinux-policy-load-proof-pass
pass: True
```

Executed V1134 live:

```bash
python3 scripts/revalidation/native_wifi_outer_holder_post_policy_cnss_live_v1134.py \
  --out-dir tmp/wifi/v1134-outer-holder-post-policy-cnss-live-run \
  --allow-tracefs-mount \
  --allow-tracefs-write \
  --allow-vendor-mount \
  --allow-selinuxfs-mount \
  --allow-pm-service-trigger-observer \
  --allow-cnss-daemon-start \
  --assume-yes run
```

Result:

```text
decision: v1134-cnss-pm-connect-no-wlfw-delta
pass: True
```
