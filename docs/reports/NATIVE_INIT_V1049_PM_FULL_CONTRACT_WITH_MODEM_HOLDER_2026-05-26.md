# V1049 PM Full-Contract with Modem Holder Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| current-boot selinuxfs | `tmp/wifi/v1049-v401-selinuxfs-mount/manifest.json` | `toybox-selinuxfs-mount-live-executor-run-pass` |
| policy load | `tmp/wifi/v1049-v490-policy-load-v178/manifest.json` | `v490-selinux-policy-load-proof-pass` |
| PM domain proof | `tmp/wifi/v1049-v1042-pm-selinux-domain-proof-v178/manifest.json` | `v1042-pm-selinux-domain-handoff-present` |
| live gate | `tmp/wifi/v1049-pm-full-contract-with-modem-holder-live/manifest.json` | `v1049-modem-pre-holder-not-confirmed-clean` |

V1049 disproves the first implementation of the modem pre-holder hypothesis.
The new matrix order executed and runtime PM domains matched, but the pre-holder
child did not open `/dev/subsys_modem`.

## Findings

- Current-boot SELinux preconditions were valid:
  - V401 selinuxfs mount: pass
  - V490 policy load: pass
  - PM domain proof: pass
- V1049 helper/live guard:
  - helper: `a90_android_execns_probe v178`
  - matrix: `pm_full_contract_with_modem_holder_matrix=1`
  - runtime-domain guard blocked: `0`
  - runtime-domain match count: `4`
- Modem pre-holder result:
  - `modem_pre_holder_start_attempted=1`
  - `modem_pre_holder_pid=611`
  - `modem_pre_holder_opened=0`
  - `modem_pre_holder_errno=2`
  - `modem_pre_holder_confirmed=0`
- PM fd result:
  - `pm_proxy_helper_subsys_modem_fd_count=0`
  - `per_mgr_subsys_modem_fd_count=0`
  - `pm_full_contract_seen=0`
- Contradictory surface worth noting:
  - helper context captured `private_node.subsys_modem.exists=1`
  - path was `/tmp/a90-v231-685/root/dev/subsys_modem`
  - pre-holder still returned `ENOENT`, which points to the holder opening the
    wrong namespace/path timing rather than the node being absent from the
    prepared private root.
- Cleanup reboot executed and post-reboot health passed:
  - `boot: BOOT OK shell 4.1s`
  - `selftest: pass=11 warn=1 fail=0`

## Interpretation

The V1047 concept was directionally useful but the implementation opened the
wrong path or opened before entering the namespace where `/dev/subsys_modem` is
visible. The evidence does not show a new SELinux blocker: all four PM actor
exec domains matched after V490 policy load.

The next fix should move the modem pre-holder open to the same private-root path
used by the actor context, or explicitly open the prepared path
`<temp_root>/dev/subsys_modem` before actor start and then hold that fd. Do not
retry V1049 unchanged.

## Guardrails

No `ks`, MHI pipe transfer, Wi-Fi HAL, `wificond`, scan/connect, credentials,
DHCP/routes, external ping, controller eSoC notify, BOOT_DONE spoofing, boot
image write, partition write, firmware mutation, GPIO write, sysfs write, or
debugfs write occurred. `/dev/subsys_esoc0` was not opened because WLFW
precondition was not observed.

## Validation

Commands:

```bash
python3 scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py \
  --out-dir tmp/wifi/v1049-v401-selinuxfs-mount \
  --approval-phrase "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/native_selinux_policy_load_proof_v490.py \
  --out-dir tmp/wifi/v1049-v490-policy-load-v178 \
  --helper-sha256 7df75c618f58d599ece1a6017f66040aff57badb8955a70e07de2a77a3561c75 \
  --approval-phrase "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/native_wifi_pm_selinux_domain_proof_v177_v1042.py \
  --out-dir tmp/wifi/v1049-v1042-pm-selinux-domain-proof-v178 \
  --v490-manifest tmp/wifi/v1049-v490-policy-load-v178/manifest.json \
  --helper-sha256 7df75c618f58d599ece1a6017f66040aff57badb8955a70e07de2a77a3561c75 \
  --approval-phrase "approve v1042 PM SELinux domain proof v177 only; no daemon start and no Wi-Fi bring-up" \
  --apply --assume-yes run
python3 scripts/revalidation/native_wifi_pm_full_contract_with_modem_holder_live_v1049.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-pm-full-contract-with-modem-holder \
  --allow-cleanup-reboot \
  --assume-yes run
```

Result:

```text
decision: v1049-modem-pre-holder-not-confirmed-clean
pass: True
modem_pre_holder_opened: False
modem_pre_holder_errno: 2
pm_full_contract_seen: False
cleanup_reboot_executed: True
```

## Next

V1050 should be source/build-only: repair the modem pre-holder open path so it
uses the prepared private root `/dev/subsys_modem` path, then rebuild helper
`v179`. Do not rerun the current V1049 helper unchanged.
