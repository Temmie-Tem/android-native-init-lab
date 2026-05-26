# V1055 PM Full-Contract with Modem Holder v180 Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| current-boot selinuxfs | `tmp/wifi/v1055-v401-selinuxfs-mount/manifest.json` | `toybox-selinuxfs-mount-live-executor-run-pass` |
| policy load | `tmp/wifi/v1055-v490-policy-load-v180/manifest.json` | `v490-selinux-policy-load-proof-pass` |
| PM domain proof | `tmp/wifi/v1055-v1042-pm-selinux-domain-proof-v180/manifest.json` | `v1042-pm-selinux-domain-handoff-present` |
| live gate | `tmp/wifi/v1055-pm-full-contract-with-modem-holder-live/manifest.json` | `v1055-modem-pre-holder-not-confirmed-clean` |

V1055 shows that V1053's plain fallback did not form a holder. The first
nonblocking open still returns `errno=14`, the plain retry starts, but the child
never reports success or a second errno before the bounded parent window ends.
This classifies the fallback as a blocking first-opener/PIL path, not a usage or
private-root path issue.

## Findings

- Helper/live guard:
  - helper: `a90_android_execns_probe v180`
  - matrix: `pm_full_contract_with_modem_holder_matrix=1`
  - cleanup reboot executed: `1`
- Private node:
  - `private_node.subsys_modem.exists=1`
  - `private_node.subsys_modem.path=/tmp/a90-v231-640/root/dev/subsys_modem`
  - major/minor: `236:0`
- Modem pre-holder:
  - `modem_pre_holder_child_chroot=1`
  - `modem_pre_holder_path=/dev/subsys_modem`
  - `modem_pre_holder_nonblock_opened=0`
  - `modem_pre_holder_nonblock_errno=14`
  - `modem_pre_holder_plain_retry=1`
  - `modem_pre_holder_open_reported=0`
  - `modem_pre_holder_result_reported=0`
  - `modem_pre_holder_confirmed=0`
- PM fd contract:
  - `pm_proxy_helper_subsys_modem_fd_count=0`
  - `per_mgr_subsys_modem_fd_count=0`
  - `pm_full_contract_seen=0`
- Actor/postflight:
  - `pm_full_contract_poll_count=100`
  - `all_postflight_safe=0`
  - `result=reboot-required`
  - post-reboot `bootstatus` and `selftest` passed.

## Interpretation

The pre-holder is now in the correct namespace and reaches the correct device
node. The nonblocking open produces `EFAULT`, and the plain open does not return
within the bounded gate. That matches the earlier PM/PIL blocker model: in
native init, this path is acting as the first opener and enters the lower PIL
bring-up path instead of becoming a cheap fd holder.

The next useful step is not another retry of the same holder. V1056 should
classify the Android first-opener/PIL prerequisite: which Android actor already
holds or initializes `subsys_modem` before `pm_proxy_helper`, and whether native
can reproduce that precondition without service-manager/HAL/scan/connect.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_full_contract_with_modem_holder_live_v1055.py
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v1055-v401-selinuxfs-mount \
  --approval-phrase "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v1055-v490-policy-load-v180 \
  --helper-sha256 f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641 \
  --approval-phrase "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/native_wifi_pm_selinux_domain_proof_v177_v1042.py \
  --out-dir tmp/wifi/v1055-v1042-pm-selinux-domain-proof-v180 \
  --v490-manifest tmp/wifi/v1055-v490-policy-load-v180/manifest.json \
  --helper-sha256 f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641 \
  --approval-phrase "approve v1042 PM SELinux domain proof v177 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/native_wifi_pm_full_contract_with_modem_holder_live_v1055.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-pm-full-contract-with-modem-holder \
  --allow-cleanup-reboot \
  --assume-yes run
python3 scripts/revalidation/a90ctl.py --hide-on-busy bootstatus
python3 scripts/revalidation/a90ctl.py --hide-on-busy selftest
```

## Guardrails

No `ks`, MHI pipe transfer, Wi-Fi HAL, `wificond`, scan/connect, credentials,
DHCP/routes, external ping, controller eSoC notify, BOOT_DONE spoofing, boot
image write, partition write, firmware mutation, GPIO write, sysfs write, or
debugfs write occurred. `/dev/subsys_esoc0` was not opened because WLFW
precondition was not observed.

## Next

V1056 should be host-only or read-only live classification of Android's lower
`subsys_modem` first-opener/PIL precondition, not another service-manager/HAL
retry.
