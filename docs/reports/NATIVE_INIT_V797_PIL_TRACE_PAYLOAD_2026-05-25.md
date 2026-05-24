# Native Init V797 PIL Trace Payload Report

## Result

- decision: `v797-pil-notif-payload-captured`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_pil_trace_payload_v797.py`
- evidence: `tmp/wifi/v797-pil-trace-payload/`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pil_trace_payload_v797.py
python3 scripts/revalidation/native_wifi_pil_trace_payload_v797.py --out-dir tmp/wifi/v797-static-plan-check plan
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v797-v401-current-run \
  --approval-phrase 'approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run
python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v797-v490-current-run \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --helper-sha256 d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6 \
  --approval-phrase 'approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up' \
  --apply --assume-yes run
python3 scripts/revalidation/native_wifi_pil_trace_payload_v797.py \
  --out-dir tmp/wifi/v797-preflight-check \
  --v490-manifest tmp/wifi/v797-v490-current-run/manifest.json \
  preflight
python3 scripts/revalidation/native_wifi_pil_trace_payload_v797.py run \
  --v490-manifest tmp/wifi/v797-v490-current-run/manifest.json \
  --allow-tracefs-mount \
  --allow-trace-control-write \
  --allow-lower-window-boot-wlan \
  --assume-yes
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| captured `pil_notif` events | `8` |
| event names | `before_send_notif`, `after_send_notif` |
| codes | `2`, `3`, `6`, `7` |
| firmware field | `fw=modem` for all captured events |
| `mss` | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` | `OFFLINING -> OFFLINING -> OFFLINING` |
| service `69` / `wlan0` / wiphy | `0 / false / false` |
| lower companion order | `qrtr_ns,rmt_storage,tftp_server,pd_mapper` |
| tracefs cleanup | unmounted/disabled after run |
| reboot cleanup | v724 `version` seen and `selftest`/status healthy |

Captured payload sample:

```text
pil_notif: event_name=before_send_notif code=2 fw=modem
pil_notif: event_name=after_send_notif code=2 fw=modem
pil_notif: event_name=before_send_notif code=6 fw=modem
pil_notif: event_name=after_send_notif code=6 fw=modem
pil_notif: event_name=before_send_notif code=3 fw=modem
pil_notif: event_name=before_send_notif code=7 fw=modem
pil_notif: event_name=after_send_notif code=7 fw=modem
pil_notif: event_name=after_send_notif code=3 fw=modem
```

## Classification

V797 converts the V782 count-only observation into payload evidence. The native
lower transition produces modem PIL notifications only, with code sequence
`2, 6, 3, 7` paired by `before_send_notif` / `after_send_notif`.

The important negative result remains unchanged:

```text
modem PIL notifications captured
  -> mss ONLINE
  -> mdm3 still OFFLINING
  -> no service 69 / WLFW / BDF / wiphy / wlan0
```

This makes the next classifier concrete: compare native V797 PIL payload
sequence with Android reference dmesg/trace evidence and identify whether
Android has additional mdm3/WLAN-PD-related PIL notifications, different codes,
or later WLAN firmware events that native never reaches.

## Safety

- Tracefs was enabled only for `msm_pil_event:pil_notif` and disabled after
  capture.
- No service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes,
  external ping, raw `esoc0`, bind/unbind, module load/unload, boot image write,
  partition write, or custom kernel flash.
- Cleanup reboot restored v724 health.

## Next

V798 should be host-only first:

1. map PIL notification codes `2/3/6/7` to the kernel source enum if available;
2. compare V797 native payload with Android reference logs around modem/mdm3;
3. decide whether the missing edge is a specific mdm3/WLAN-PD PIL event, a
   post-PIL userspace publication gap, or a kernel-only transition that needs a
   different stock tracepoint.
