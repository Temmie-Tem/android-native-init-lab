# Native Init V911 mdm_helper eSoC FD Stall Classifier Plan

## Goal

Run helper `v149` in the bounded runtime-contract capture path and classify the
new fdinfo/proc evidence at the V908 boundary.

## Gate

V911 reuses the V908 runner with helper `v149` and requires:

- remote helper SHA/marker parity for `v149`;
- bounded selinuxfs mount/cleanup;
- private property root and `per_mgr_light` ordering;
- no `pm_proxy_helper`;
- no controller `/dev/subsys_esoc0` open;
- no service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, or external ping.

## Success Criteria

- `mdm_helper` is observable.
- `/dev/esoc-0` fd is present.
- fdinfo for that fd is captured.
- `wchan`, `syscall`, `stack`, `status`, `sched`, and task snapshots are
  captured.
- `ks`/MHI remain classified if they still do not appear.
- postflight cleanup is healthy.

## Validation

Run:

```bash
python3 scripts/revalidation/native_wifi_mdm_helper_runtime_contract_capture_v908.py \
  --out-dir tmp/wifi/v911-mdm-helper-esoc-fd-stall-live \
  --local-helper tmp/wifi/v909-execns-helper-v149-build/a90_android_execns_probe \
  --helper-sha256 b615aa127e130e8b285642b34992102fa6d0c15702479bc1265dd4c5f06dff49 \
  --helper-marker "a90_android_execns_probe v149" \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-runtime-contract-capture \
  --allow-cleanup-reboot \
  --assume-yes \
  run
python3 scripts/revalidation/native_wifi_mdm_helper_esoc_fd_stall_classifier_v911.py
```

## Next

If `mdm_helper` blocks in `ESOC_WAIT_FOR_REQ`, the next gate should evaluate a
guarded powerup trigger while `mdm_helper` owns the request path. That gate must
remain bounded and must not start Wi-Fi HAL or scan/connect.
