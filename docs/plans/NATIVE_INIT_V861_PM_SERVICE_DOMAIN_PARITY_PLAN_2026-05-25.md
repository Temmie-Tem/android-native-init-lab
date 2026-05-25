# Native Init V861 pm-service Domain Parity Plan

## Objective

V860 removed the current `pm-service`/`pm-proxy` property denials, but
`pm-service` still did not hold `/dev/subsys_esoc0` or `/dev/subsys_modem`.
V861 tests whether the missing Android `vendor_per_mgr` SELinux launch context
is the blocker.

## Inputs

| Input | Evidence |
|---|---|
| V853 Android actor reference | `tmp/wifi/v853-android-esoc-actor-handoff/manifest.json` |
| V855 native node parity | `tmp/wifi/v855-esoc-node-parity-preflight/manifest.json` |
| V860 property-clean replay | `tmp/wifi/v860-pm-service-property-superset-replay-live/manifest.json` |
| helper v133 build | `tmp/wifi/v861-execns-helper-v133-build/a90_android_execns_probe` |

## Scope

1. Add Android default SELinux exec context mapping for:
   - `/vendor/bin/pm-service` → `u:r:vendor_per_mgr:s0`
   - `/vendor/bin/pm-proxy` → `u:r:vendor_per_mgr:s0`
2. Build and deploy helper v133.
3. Rerun only the bounded `pm-service`/`pm-proxy` start-only path under V855
   node parity and V860 private property root.
4. Classify:
   - whether exec target context is accepted,
   - whether runtime `attr/current` transitions,
   - whether subsystem fd holds appear.

## Hard Gates

- No `mdm_helper` or `ks` start.
- No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping.
- No raw eSoC ioctl, GPIO/sysfs/debugfs/subsystem writes, module load/unload,
  boot image write, or partition write.

## Commands

```bash
mkdir -p tmp/wifi/v861-execns-helper-v133-build
bash scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v861-execns-helper-v133-build/a90_android_execns_probe

python3 scripts/revalidation/native_wifi_pm_service_domain_parity_v861.py \
  --out-dir tmp/wifi/v861-pm-service-domain-parity-plan-r2 \
  plan

python3 scripts/revalidation/native_wifi_pm_service_domain_parity_v861.py \
  --out-dir tmp/wifi/v861-pm-service-domain-parity-live-r2 \
  --transfer-method serial \
  --allow-helper-deploy \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-node-materialization \
  --allow-node-cleanup \
  --allow-pm-service-start-only \
  --assume-yes \
  run
```

## Success Criteria

- Helper v133 deploys or verifies as current.
- `pm-service` and `pm-proxy` exec target contexts are accepted.
- Property denials remain zero.
- The replay records runtime `attr/current`, child exit status, fd counts, and
  subsystem fd hold state.

## Failure Criteria

- V860 property denials regress.
- Helper v133 hash or marker mismatch.
- Created Android-equivalent nodes fail cleanup.
- Any hard-gated Wi-Fi bring-up, external networking, eSoC write, or partition
  write appears in evidence.
