# V1043 PM Full-Contract After V1042

- date: `2026-05-26`
- scope: bounded live PM full-contract proof after fresh V1042 policy/domain proof
- decision: `v1041-pm-full-contract-missing-no-open`
- pass: `True`
- evidence: `tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live/manifest.json`

## Summary

V1043 reran the PM full-contract proof immediately after V1042. This time the
runtime-domain guard matched all four PM actors, proving the V1041 guard block
was a stale current-boot SELinux precondition rather than a helper `v177`
context-mapping failure.

The remaining blocker is lower: the PM fd contract still did not form.
`pm_proxy_helper` and `pm-service` never held `/dev/subsys_modem`, while
`mdm_helper` did acquire `/dev/esoc-0`. Service-manager/CNSS and
`/dev/subsys_esoc0` stayed blocked.

## Result

| Item | Value |
| --- | --- |
| runtime-domain guard blocked | `False` |
| runtime-domain guard matched | `4` |
| `pm_proxy_helper` domain | `u:r:per_proxy_helper:s0` |
| `pm-service` domain | `u:r:vendor_per_mgr:s0` |
| `pm-proxy` domain | `u:r:vendor_per_proxy:s0` |
| `mdm_helper` domain | `u:r:vendor_mdm_helper:s0` |
| `pm_proxy_helper` `/dev/subsys_modem` fd count | `0` |
| `pm-service` `/dev/subsys_modem` fd count | `0` |
| `mdm_helper` `/dev/esoc-0` fd seen | `True` |
| PM fd poll count | `54` |
| gap snapshot captured | `True` |
| service-manager/CNSS start | `False` |
| `/dev/subsys_esoc0` open attempted | `False` |
| Wi-Fi HAL / scan / connect | `False` |
| cleanup reboot | `True` |

## Focused Gap Evidence

The new V1039 snapshot support worked:

- `pm_proxy_helper` fd links: only stdin/stdout/stderr, no `/dev/subsys_modem`.
- `pm_proxy_helper` state: `D (disk sleep)`.
- `pm_proxy_helper` wchan: `flush_work`.
- `pm_proxy_helper` stack includes `pil_boot` and `subsys_powerup`.
- `pm-service` fd links: pipes only, no `/dev/subsys_modem`.
- `pm-service` wchan: `SyS_nanosleep`.

This matches the earlier modem-get/PIL-loading blocker: `pm_proxy_helper` is
stuck inside modem subsystem powerup before it can expose the expected fd
contract.

## Guardrails

- No Wi-Fi HAL start.
- No `wificond`.
- No `IWifi.start` or `qcwlanstate` write.
- No scan/connect/link-up.
- No credentials.
- No DHCP, route, or external ping.
- No live eSoC ioctl, notify, or BOOT_DONE.
- No `/dev/subsys_esoc0` open.
- No boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs write.
- Cleanup reboot restored healthy native state on attempt 2.

## Validation

Command:

```bash
python3 scripts/revalidation/native_wifi_pm_full_contract_v177_live_v1041.py \
  --out-dir tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
```

Live result:

```text
decision: v1041-pm-full-contract-missing-no-open
pass: True
runtime_domain_guard_matched_count: 4
pm_full_contract_seen: False
pm_full_contract_gap_snapshot_captured: 1
cleanup_reboot_executed: True
subsys_esoc0_open_attempted: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Next

V1044 should be a host-only classifier over V1043 focused fd/wchan evidence,
V1024 Android PM fd evidence, and OSRC/subsystem restart source. The next
question is why native `pm_proxy_helper` blocks in `pil_boot/subsys_powerup`
while Android reaches the `/dev/subsys_modem` fd contract.
