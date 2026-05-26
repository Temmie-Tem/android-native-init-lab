# V1042 PM SELinux Domain Proof v177

- date: `2026-05-26`
- scope: current-boot SELinux policy/domain refresh
- decision: `v1042-pm-selinux-domain-handoff-present`
- pass: `True`
- evidence:
  - V401: `tmp/wifi/v1042-v401-selinuxfs-mount/manifest.json`
  - V490: `tmp/wifi/v1042-v490-policy-load-v177/manifest.json`
  - V1042: `tmp/wifi/v1042-pm-selinux-domain-proof-v177/manifest.json`

## Summary

V1042 restored the current-boot SELinux precondition after V1041 showed PM
actor exec attrs still stuck at `kernel`.

The sequence passed:

1. V401 mounted `selinuxfs`.
2. V490 compiled Android split policy and wrote it to `/sys/fs/selinux/load`
   using helper `v177`.
3. V1042 proved all required PM domains survive static post-exec proof.

## Result

| Item | Value |
| --- | --- |
| V401 selinuxfs mount | pass |
| V490 policy load | pass |
| policy load executed | `True` |
| init reexec | `False` |
| daemon start | `False` |
| Wi-Fi bring-up | `False` |
| required PM domain matches | `4/4` |
| control WCNSS domain match | pass |

## PM Domain Cases

| Context | Result |
| --- | --- |
| `u:r:per_proxy_helper:s0` | pass |
| `u:r:vendor_per_mgr:s0` | pass |
| `u:r:vendor_per_proxy:s0` | pass |
| `u:r:vendor_mdm_helper:s0` | pass |
| `u:r:vendor_wcnss_service:s0` | pass |

## Guardrails

- No PM actor start.
- No daemon start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP, route, or external ping.
- No init reexec.
- No boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write.

## Validation

Commands:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_selinux_domain_proof_v177_v1042.py
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v1042-v401-selinuxfs-mount \
  --approval-phrase "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v1042-v490-policy-load-v177 \
  --helper-sha256 d71c7c87a7759eb8e2eb0058c2057e0e9348a4c6f572f48d6d9b2962053a4795 \
  --approval-phrase "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
python3 scripts/revalidation/native_wifi_pm_selinux_domain_proof_v177_v1042.py \
  --v490-manifest tmp/wifi/v1042-v490-policy-load-v177/manifest.json \
  --approval-phrase "approve v1042 PM SELinux domain proof v177 only; no daemon start and no Wi-Fi bring-up" \
  --apply \
  --assume-yes \
  run
```

## Next

Run the PM full-contract proof immediately while the policy-load state is fresh.
That follow-up is V1043.
