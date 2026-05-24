# Native Init V714 Helper v121 Deploy and ICNSS Edge Live Proof

- date: `2026-05-24 KST`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v121_deploy_preflight.py`
- live wrapper: `scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py`
- deploy evidence: `tmp/wifi/v714-execns-helper-v121-deploy-live-serial1850-20260524-100803/`
- live evidence: `tmp/wifi/v714-provider-first-icnss-edge-v121-orchestrated-live-20260524-101503/`
- status: `pass`

## Scope

This cycle completed the helper v121 deployment and ran the bounded V712
provider-first ICNSS edge proof.

Allowed actions:

- serial helper deployment to `/cache/bin/a90_android_execns_probe`;
- V641 clean-DSP reboot prep;
- V401 SELinuxfs mount surface;
- V490 Android SELinux policy-load proof;
- bounded provider-first companion/provider/CNSS retry proof;
- runner-owned cleanup and reboot.

Forbidden actions were preserved:

- no Wi-Fi HAL or `wificond` start;
- no supplicant or hostapd start;
- no scan/connect/link-up;
- no credential use;
- no DHCP, route change, or external ping;
- no boot image or partition write.

## Deploy Result

Helper v121 deployed successfully over serial using the safe `1850` chunk size.
NCM was not used because the host-side NCM address was not configured for the
expected `192.168.7.1/24` path.

```text
decision: execns-helper-v121-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Live Result

The live proof reached the intended lower surface:

- service-notifier `180`: `1`
- service-notifier `74`: `1`
- provider registration query: `vendor.qcom.PeripheralManager` seen
- initial CNSS suppressed: yes
- post-provider CNSS retry: started
- Binder transaction failure: `0`
- ICNSS edge capture: present in the nested V712 arm manifest

The Wi-Fi progression markers still did not move:

| marker | count |
| --- | ---: |
| `qmi_server_connected` | `0` |
| `wlfw_start` | `0` |
| `wlfw_service_request` | `0` |
| `wlan_pd` | `0` |
| `bdf_regdb` | `0` |
| `bdf_bdwlan` | `0` |
| `wlan_fw_ready` | `0` |
| `wlan0` | `0` |

## Tooling Fix

The live nested arm manifest correctly reported:

```text
decision: v712-provider-first-icnss-edge-captured-gap-persists
icnss_edge_captured: True
```

The top-level orchestrator summary had recalculated the older
`v712-provider-first-cnss-gap-persists` label and rewrote the nested manifest
path string to a non-existent `arm-v712-v121...` path. The orchestrator was
patched to preserve the nested arm decision/path and include a compact ICNSS
edge summary in future top-level reports.

## Interpretation

V714 removes the earlier Binder/provider ambiguity from the primary path. The
remaining blocker is below CNSS userspace retry and before WLFW/BDF/`wlan0`.
The next step is a host-only classifier over the ICNSS edge surface before any
HAL, scan/connect, DHCP, or external ping attempt.

## Validation

Executed:

```bash
python3 scripts/revalidation/wifi_execns_helper_v121_deploy_preflight.py \
  --transfer-method serial \
  --serial-chunk-size 1850 \
  --approval-phrase '<V712 deploy approval>' \
  --apply --assume-yes run

python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py \
  --apply --assume-yes run

python3 -m py_compile scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py
python3 scripts/revalidation/native_wifi_provider_first_icnss_edge_orchestrator_v712.py \
  --out-dir tmp/wifi/v714-v712-orchestrator-plan-check \
  plan
git diff --check
```
