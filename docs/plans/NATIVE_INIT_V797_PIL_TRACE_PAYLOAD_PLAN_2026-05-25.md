# Native Init V797 PIL Trace Payload Plan

## Goal

Capture `msm_pil_event:pil_notif` payload fields during the already-tested
lower-window transition so the native PIL sequence can be compared against
Android before another trigger retry.

## Scope

- Temporarily mount tracefs if it is not already mounted.
- Enable only `msm_pil_event:pil_notif`.
- Run the proven lower-window transition:
  firmware mounts -> `subsys_modem` holder -> lower companion start-only ->
  bounded `a90_wlanbootctl boot-observe`.
- Capture trace payload lines and parse `event_name`, `code`, and firmware name.
- Disable trace controls, unmount tracefs if V797 mounted it, and reboot-clean.

## Hard Gates

- No service-manager start.
- No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping.
- No raw `esoc0`, bind/unbind, driver override, module load/unload, boot image
  write, partition write, or custom kernel flash.
- No broad ftrace function filter, graph tracer, or trace marker use.
- No Wi-Fi secret material in tracked output.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pil_trace_payload_v797.py
python3 scripts/revalidation/native_wifi_pil_trace_payload_v797.py --out-dir tmp/wifi/v797-static-plan-check plan
python3 scripts/revalidation/native_wifi_pil_trace_payload_v797.py --out-dir tmp/wifi/v797-preflight-check --v490-manifest tmp/wifi/v797-v490-current-run/manifest.json preflight
python3 scripts/revalidation/native_wifi_pil_trace_payload_v797.py run \
  --v490-manifest tmp/wifi/v797-v490-current-run/manifest.json \
  --allow-tracefs-mount \
  --allow-trace-control-write \
  --allow-lower-window-boot-wlan \
  --assume-yes
git diff --check
```

## Expected Routing

- If payload capture fails, repair tracefs/event-control handling before any
  trigger retry.
- If payload capture contains only modem notifications while mdm3/service `69`
  stay absent, classify the missing mdm3/WLAN-PD notification sequence next.
- Do not proceed to scan/connect or credentials until service `69`, BDF,
  wiphy/`wlan0`, or a sharper Wi-Fi firmware-ready edge appears.
