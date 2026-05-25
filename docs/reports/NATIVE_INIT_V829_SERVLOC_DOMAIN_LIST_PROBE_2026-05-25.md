# Native Init V829 Service-Locator Domain-List Probe Report

## Result

- decision: `v829-servloc-domain-list-response-success`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py`
- evidence: `tmp/wifi/v829-servloc-domain-list-probe-retry-20260525-113735/`

## What Ran

```bash
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v126_deploy_preflight.py \
  scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py

bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v829-execns-helper-v126-build/a90_android_execns_probe

python3 scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py \
  --out-dir tmp/wifi/v829-servloc-domain-list-probe-plan-check \
  plan

python3 scripts/revalidation/wifi_execns_helper_v126_deploy_preflight.py \
  --out-dir tmp/wifi/v829-execns-helper-v126-deploy-plan-check \
  plan

python3 scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py \
  --out-dir tmp/wifi/v829-servloc-domain-list-probe-preflight \
  --transfer-method auto \
  preflight

python3 scripts/revalidation/native_wifi_servloc_domain_list_probe_v829.py \
  --out-dir tmp/wifi/v829-servloc-domain-list-probe-retry-20260525-113735 \
  --transfer-method auto \
  run
```

## Evidence Summary

| Signal | Result |
| --- | --- |
| helper marker | `a90_android_execns_probe v126` |
| helper sha256 | `106d408acf6d48c6a38350756cd921e8ffb8fcc518708855036fd858e79236e2` |
| request bytes | `24` |
| service-locator endpoint | service `64/257`, node `1`, port `16475` |
| QMI response | success, result `0`, error `0` |
| total domains | `1` |
| parsed domain | `msm/modem/wlan_pd` |
| parsed domain instance | `180` |
| WLAN-like domains | `1` |
| cleanup reboot | executed |
| post-cleanup native health | v724 `status` pass, selftest `fail=0` |

## Interpretation

V829 proves that native init can query the service-locator QMI service for the
`wlan/fw` process-domain list below service-manager and Wi-Fi HAL. The returned
entry is `msm/modem/wlan_pd` with instance `180`.

This closes the previous uncertainty between a visible service-locator endpoint
and the kernel ICNSS continuation path. The next blocker is no longer domain
list discovery. The next narrow gate is service-notifier listener registration
for `msm/modem/wlan_pd` instance `180`, then observing whether the state
indication advances toward WLFW service `69/1`.

## Safety

- One bounded service-locator QMI payload was sent.
- No service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up,
  credential use, DHCP, route change, or external ping executed.
- No `esoc0` open, qcwlanstate write, bind/unbind, driver override, or module
  load/unload executed.
- No boot image write, partition write, bootloader handoff, or custom kernel
  flash executed.
- Cleanup reboot restored healthy stock v724 native init.
- No Wi-Fi secret material was written to tracked output.

## Notes

An earlier live attempt was interrupted after menu busy output appeared during
helper deploy checks. The canonical run above used a fresh evidence directory
and completed successfully. The remote helper was already current by the
canonical run, so that run records `helper_deploy_executed=false` while still
verifying helper v126 sha and usage before the live probe.

## Next

V830 should derive and implement a bounded service-notifier
`REGISTER_LISTENER` proof for `msm/modem/wlan_pd` instance `180`. It should
remain below service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
external ping, boot image writes, partition writes, and custom kernel flashing.
