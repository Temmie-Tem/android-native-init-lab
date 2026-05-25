# V941 mdm_helper Queue-Timing Support Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| source/build verifier | `tmp/wifi/v941-mdm-helper-queue-timing-support/manifest.json` | `v941-mdm-helper-queue-timing-support-pass` |

V941 adds helper `v156` queue-timing diagnostics to the existing
`mdm_helper` runtime-contract mode. It is source/build-only: no device command,
actor start, eSoC ioctl, Wi-Fi HAL, scan/connect, DHCP/route mutation, or
external ping occurred.

## Implementation

- Updated helper marker:
  `a90_android_execns_probe v156`
- Modified source:
  `stage3/linux_init/helpers/a90_android_execns_probe.c`
- Added verifier:
  `scripts/revalidation/native_wifi_mdm_helper_queue_timing_support_v941.py`
- Build artifact:
  `tmp/wifi/v941-execns-helper-v156-build/a90_android_execns_probe`
- Build sha256:
  `ff5a87694bbb9c557aaaaacf61e1ceb0af9dffb3984d9f6887a2f93c8bceceb8`

## Added Diagnostics

The existing `wifi-companion-mdm-helper-runtime-contract-capture` mode now emits
`mdm_helper_queue_timing.*` keys at these phases:

- `before_property_shim`
- `after_per_mgr_settle`
- `after_mdm_helper_spawn`
- `window`
- `final`
- `after_cleanup`

Each phase records:

- monotonic timestamp;
- `per_mgr` and `mdm_helper` pid/alive/state/exit/signal/reap flags;
- `per_mgr` fd matches for `/dev/subsys_modem`, `/dev/subsys_esoc0`, and
  `/dev/esoc-0`;
- `mdm_helper` fd matches for `/dev/esoc-0`, `/dev/subsys_esoc0`, and the MHI
  pipe;
- process scans for `pm-service`, `pm-proxy`, `pm_proxy_helper`, `ks`, and MHI
  pipe cmdline users.

## Guardrails

The verifier confirms the runtime-contract hard guards remain present:

- `service_manager_start_executed=0`
- `cnss_start_executed=0`
- `wifi_hal_start_executed=0`
- `scan_connect_linkup=0`
- `credentials=0`
- `dhcp_routing=0`
- `external_ping=0`
- `subsys_esoc0_controller_open_attempted=0`
- `notify_attempted=0`
- `boot_done_attempted=0`

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm_helper_queue_timing_support_v941.py
python3 scripts/revalidation/native_wifi_mdm_helper_queue_timing_support_v941.py
```

Verifier checks passed:

- `execns_version_v156`
- `queue_timing_snapshot_function`
- `queue_timing_child_state`
- `queue_timing_fd_counts`
- `runtime_phase_markers`
- `no_new_trigger_or_wifi_bringup`
- static ARM64 helper build
- helper marker and `mdm_helper_queue_timing` strings in the artifact

## Next

V942 should deploy helper `v156` only, with no daemon start and no Wi-Fi
bring-up. After deployment, a separate bounded live capture can rerun the
runtime-contract mode and classify the fresh `mdm_helper_queue_timing.*`
evidence before any `/dev/subsys_esoc0`, eSoC notification, Wi-Fi HAL, or
scan/connect retry.
