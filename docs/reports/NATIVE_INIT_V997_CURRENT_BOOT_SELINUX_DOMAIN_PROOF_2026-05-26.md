# V997 Current-Boot SELinux Domain Proof

- generated: `2026-05-26`
- scope: current-boot SELinux refresh and domain proof
- V401 evidence: `tmp/wifi/v997-v401-selinuxfs-mount/manifest.json`
- V490 evidence: `tmp/wifi/v997-v490-policy-load/manifest.json`
- V997 evidence: `tmp/wifi/v997-current-boot-selinux-domain-proof/manifest.json`
- decision: `v491-post-load-domain-handoff-present`
- pass: `True`
- helper: `a90_android_execns_probe v169`

## Summary

V997 refreshed the current boot SELinux path and proved that the service-window
critical domains can survive post-exec after current-boot policy load.

All five target domains matched:

| Context | Result |
| --- | --- |
| `u:r:servicemanager:s0` | PASS |
| `u:r:hwservicemanager:s0` | PASS |
| `u:r:vndservicemanager:s0` | PASS |
| `u:r:wificond:s0` | PASS |
| `u:r:hal_wifi_default:s0` | PASS |

## Execution

```bash
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v997-v401-selinuxfs-mount \
  --approval-phrase "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes run

python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v997-v490-policy-load \
  --helper-sha256 c47f0659178186d45cf5199fdad4d198f0c69b6998f2127ff420f9e0f0204a74 \
  --approval-phrase "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes run

python3 scripts/revalidation/native_wifi_current_boot_selinux_domain_proof_v997.py \
  --out-dir tmp/wifi/v997-current-boot-selinux-domain-proof \
  --helper-sha256 c47f0659178186d45cf5199fdad4d198f0c69b6998f2127ff420f9e0f0204a74 \
  --v490-manifest tmp/wifi/v997-v490-policy-load/manifest.json \
  --approval-phrase "approve v997 current-boot SELinux domain proof only; no policy load, no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes run
```

## Result

```text
decision: v491-post-load-domain-handoff-present
pass: True
matching_cases: 5/5
```

## Guardrails

- no service-manager start
- no Wi-Fi HAL start
- no `wificond` start
- no daemon start
- no scan/connect/link-up
- no credential use
- no DHCP/route/external ping
- no boot image or partition write

## Next

V998 should retry the bounded Android service-window using helper `v169` while
the current-boot SELinux policy-load remains active.
