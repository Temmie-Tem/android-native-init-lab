# Native Init V723 QRTR/Service-Locator Rearm Live Report

- date: `2026-05-24 KST`
- runner: `scripts/revalidation/native_wifi_qrtr_servloc_rearm_v723.py`
- final evidence: `tmp/wifi/v723-qrtr-servloc-rearm-live-final-20260524-120916/`
- latest pointer: `tmp/wifi/latest-v723-qrtr-servloc-rearm.txt`
- decision: `v723-late-servloc-rearm-no-wlanpd`
- status: `pass`

## Scope Result

V723 executed a bounded lower-only live proof:

- `device_commands_executed=True`
- `cnss_daemon_start_executed=False`
- `service_manager_start_executed=False`
- `wifi_hal_start_executed=False`
- `scan_connect_linkup_executed=False`
- `dhcp_or_external_ping_executed=False`
- `credentials_used=False`

Allowed live actions were limited to `mountsystem ro`, selinuxfs surface
mounting, and helper v121 lower companion start:

```text
qrtr-ns -> pd-mapper -> rmt_storage -> tftp_server
```

No Wi-Fi credential, scan/connect, DHCP, route change, external ping,
`qcwlanstate`, CNSS daemon, service-manager, or Wi-Fi HAL path was used.

## Input Evidence

| source | evidence |
| --- | --- |
| Current read-only baseline | `tmp/wifi/v723-current-cnss2-readonly-20260524-115736/v706-readonly/manifest.json` |
| Manual SELinuxFS prep | `tmp/wifi/v723-v401-selinuxfs-current-20260524-120401/manifest.json` |
| Manual lower-only trial | `tmp/wifi/v723-manual-late-qrtr-rearm-selinux-20260524-120417/` |
| Final V723 runner | `tmp/wifi/v723-qrtr-servloc-rearm-live-final-20260524-120916/manifest.json` |

## Key Result

The current boot already had the kernel-side failure:

```text
servloc: init_service_locator: wait for locator service timed out
servloc: pd_locator_work: Unable to connect to service locator!, rc = -62
```

V723 then started only the lower companion set. The helper contract passed:

| item | value |
| --- | --- |
| helper | `a90_android_execns_probe v121` |
| mode | `wifi-companion-android-order-post-sysmon-observer-start-only` |
| order | `qrtr_ns,pd_mapper,rmt_storage,tftp_server` |
| child_started | `4` |
| all_observable | `1` |
| all_postflight_safe | `1` |
| result | `companion-window-pass` |

The dmesg delta showed service-locator reconnected:

| marker | delta |
| --- | ---: |
| `service_locator_connected` | `1` |
| `service_notifier_180` | `0` |
| `service_notifier_74` | `0` |
| `pd_notifier` | `0` |
| `qca6390` | `0` |
| `wlfw` | `0` |
| `bdf` | `0` |
| `fw_ready` | `0` |
| `wlan0` | `0` |
| `kernel_warning` | `0` |

## Interpretation

V723 narrows the blocker:

```text
Late lower QRTR companion startup can reconnect service-locator,
but it does not recover WLAN-PD service 180/74 after the boot-time
service-locator timeout has already occurred.
```

That means the next useful unit is not another late `cnss-daemon`, HAL, or
connect retry. The next gate must move the lower companion startup earlier in
the native boot sequence, before the kernel `servloc` timeout and before CNSS2
has permanently missed its SERVREG listener window.

This refines V721: `qrtr-ns` can be observable in a later service-positive
window, but that is not equivalent to kernel CNSS2 having received the required
SERVREG/WLAN-PD indication.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_qrtr_servloc_rearm_v723.py

python3 scripts/revalidation/native_wifi_qrtr_servloc_rearm_v723.py \
  --out-dir tmp/wifi/v723-plan-check plan

python3 scripts/revalidation/native_wifi_qrtr_servloc_rearm_v723.py \
  --out-dir tmp/wifi/v723-preflight-check-after-fix preflight

python3 scripts/revalidation/native_wifi_qrtr_servloc_rearm_v723.py \
  --out-dir tmp/wifi/v723-qrtr-servloc-rearm-live-final-20260524-120916 \
  --approval-phrase "approve v723 QRTR/service-locator late rearm proof only; no CNSS daemon, no service-manager, no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping" \
  --apply --assume-yes run
```

Result:

```text
decision: v723-late-servloc-rearm-no-wlanpd
pass: True
reason: service-locator reconnected but service180/74 stayed absent
cnss_daemon_start_executed: False
wifi_hal_start_executed: False
dhcp_or_external_ping_executed: False
```

## Next Gate

V724 should be a disabled-by-default, one-shot, boot-time lower companion proof:

1. reuse v641 firmware-backed native baseline;
2. require an explicit `/cache` arm flag;
3. after `/cache` and `/mnt/system/system` are ready, start only
   `qrtr-ns`, `pd-mapper`, `rmt_storage`, and `tftp_server`;
4. run before the kernel `servloc` timeout;
5. log marker deltas for `service_locator_connected`, service `180/74`,
   WLAN-PD, CNSS2 callback, WLFW/BDF/fw-ready, and `wlan0`;
6. keep CNSS daemon, service-manager, Wi-Fi HAL, scan/connect, credentials,
   DHCP, routes, and external ping blocked.
