# V1042 PM SELinux Domain Proof v177 Plan

- date: `2026-05-26`
- type: current-boot SELinux policy/domain refresh
- selected after: V1041 current-boot runtime-domain guard block
- helper: `/cache/bin/a90_android_execns_probe`
- helper version: `a90_android_execns_probe v177`
- helper sha256: `d71c7c87a7759eb8e2eb0058c2057e0e9348a4c6f572f48d6d9b2962053a4795`

## Objective

Refresh the current-boot SELinux precondition and prove the required PM domains
with deployed helper `v177` before another PM full-contract live retry.

V1041 showed that helper `v177` was deployed, but all PM actor exec attrs still
observed `kernel`. V1036 previously proved the PM domains can work when V490
policy-load evidence is fresh. V1042 re-establishes that precondition for the
current boot.

## Sequence

1. Mount or verify `selinuxfs` with the bounded V401 toybox executor.
2. Run V490 policy-load proof with helper `v177` and no init reexec/daemon/Wi-Fi
   start.
3. Run PM `selinux-domain-proof` for:
   - `u:r:per_proxy_helper:s0`
   - `u:r:vendor_per_mgr:s0`
   - `u:r:vendor_per_proxy:s0`
   - `u:r:vendor_mdm_helper:s0`
   - control `u:r:vendor_wcnss_service:s0`

## Hard Guardrails

- no actor start
- no daemon start
- no Wi-Fi HAL start
- no scan/connect/link-up
- no credentials
- no DHCP, route, or external ping
- no init re-exec
- no boot image write
- no partition write
- no firmware mutation
- no GPIO/sysfs/debugfs write

## Commands

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

## Success Criteria

- V401 selinuxfs mount passes.
- V490 writes compiled Android policy to `/sys/fs/selinux/load` without init
  reexec, daemon start, or Wi-Fi bring-up.
- All required PM domains survive static post-exec proof with helper `v177`.
- No actor, daemon, Wi-Fi, network, boot, partition, firmware, GPIO, sysfs, or
  debugfs action occurs.

## Next

If V1042 passes, rerun the V1041 PM full-contract live proof immediately while
current-boot policy state is fresh.
