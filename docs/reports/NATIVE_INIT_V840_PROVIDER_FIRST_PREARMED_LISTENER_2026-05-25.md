# Native Init V840 Provider-first Prearmed Listener Report

## Result

- decision: `v840-provider-first-prearmed-no-indication`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_provider_first_prearmed_listener_v840.py`
- evidence: `tmp/wifi/v840-provider-first-prearmed-listener-live/`

## Scope

V840 ran the bounded provider-first lower stack and prearmed WLAN-PD listener.
It did not start Wi-Fi HAL, wificond, supplicant, or hostapd; it did not scan,
connect, use credentials, run DHCP, change routes, ping externally, open
`esoc0`, write subsystem state, load/unload `wlan.ko`, write boot images, write
partitions, or flash a custom kernel.

## Executed Actions

- Helper v130 deploy preflight; remote helper was current, so no helper deploy
  mutation was needed.
- V641 clean-DSP arm-only reboot.
- Current V401 SELinuxfs mount and V490 policy-load prep.
- Firmware mounts and `subsys_modem` holder lower window.
- V700 provider-first service-manager/vndservicemanager/PeripheralManager
  start-only sequence.
- One fresh bounded `cnss-daemon` retry after provider registration.
- Listener-only `REGISTER_LISTENER msm/modem/wlan_pd` probe.
- Runner-owned reboot cleanup.

## Key Signals

| Signal | Value |
| --- | --- |
| provider decision | `v700-provider-first-cnss-gap-persists` |
| listener endpoint | `service=66 instance=46081 node=0 port=2` |
| listener response | `success`, state `0x7fffffff` / `uninit` |
| listener indication | absent |
| listener begin → service `74` | `1557.218 ms` |
| register send → service `74` | `1309.218 ms` before service `74` |
| listener close after service `74` | `13704.782 ms` |
| held service `74` + `5s` | `true` |
| service-notifier `180/74` | present |
| WLFW/BDF/firmware-ready/`wlan0` | absent |
| cleanup health | v724 version seen, selftest healthy |

## Interpretation

Provider-first CNSS retry does not supply the missing native WLAN-PD state-up
trigger. V838 already ruled out lower-only listener timing; V840 now rules out
the combined provider-first CNSS retry plus prearmed listener timing window.

The remaining blocker is still below Wi-Fi HAL and link bring-up:

```text
mss ONLINE + QRTR/sysmon + service-notifier 180/74
  + provider-first service-manager/PeripheralManager + CNSS retry
  + prearmed WLAN-PD listener
  -> WLAN-PD remains UNINIT
  -> WLFW/service69/BDF/wlan0 absent
```

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_provider_first_prearmed_listener_v840.py
python3 scripts/revalidation/native_wifi_provider_first_prearmed_listener_v840.py \
  --out-dir tmp/wifi/v840-plan-check \
  plan
python3 scripts/revalidation/native_wifi_provider_first_prearmed_listener_v840.py \
  --out-dir tmp/wifi/v840-preflight-check \
  preflight
python3 scripts/revalidation/native_wifi_provider_first_prearmed_listener_v840.py \
  --out-dir tmp/wifi/v840-provider-first-prearmed-listener-live \
  --allow-arm-clean-dsp \
  --allow-reboot \
  --allow-cleanup-umount \
  --allow-system-mount \
  --allow-selinuxfs-mount \
  --allow-policy-load \
  --allow-firmware-mounts \
  --allow-subsys-modem-holder \
  --allow-known-asoc-warning \
  --allow-provider-first-service-manager-start-only \
  --allow-provider-first-cnss-retry \
  --allow-service-notifier-prearm \
  --allow-cleanup-reboot \
  --assume-yes \
  run
python3 scripts/revalidation/a90ctl.py status
```

Result:

```text
decision: v840-provider-first-prearmed-no-indication
pass: True
service_manager_start_executed: True
wifi_hal_start_executed: False
scan_connect_executed: False
external_ping_executed: False
```

## Next Gate

V841 should classify the missing lower native WLAN-PD state-up trigger. The
useful deltas are:

- Android reaches WLAN-PD `UP` and WLFW after the same listener model.
- Native now has service `74/180`, provider-first service-manager and
  PeripheralManager, and CNSS retry, but still no indication.
- `sysmon_esoc0` remains a key missing native signal in the parsed timeline.

