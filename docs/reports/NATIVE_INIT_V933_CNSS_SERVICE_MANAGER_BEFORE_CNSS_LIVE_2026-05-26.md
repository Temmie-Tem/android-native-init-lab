# Native Init V933 CNSS Service-Manager Before-CNSS Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| live wrapper | `scripts/revalidation/native_wifi_cnss_service_manager_before_cnss_live_v933.py` | `py_compile pass` |
| bounded live proof | `tmp/wifi/v933-cnss-service-manager-before-cnss-live/manifest.json` | `v933-wlfw-precondition-missing-no-open` |

V933 ran helper `v154` with `service_manager_order=before-cnss`. This was the
highest-value order selected by V932 because V601/V603 showed Binder failures
can clear when service managers are started before CNSS.

The run remained safe and passed fail-closed: service-manager processes,
`pm-service`, `mdm_helper`, `cnss_diag`, and `cnss-daemon` were started, the
`mdm_helper` `/dev/esoc-0` fd appeared, but WLFW precondition did not appear.
The `/dev/subsys_esoc0` child-open gate therefore stayed closed.

## Findings

| Marker | Value |
| --- | --- |
| helper marker | `a90_android_execns_probe v154` |
| service-manager order | `before-cnss` |
| service-manager start phase | `before-cnss` |
| `servicemanager` start attempted | `true` |
| `hwservicemanager` start attempted | `true` |
| `vndservicemanager` start attempted | `true` |
| `mdm_helper` start attempted | `true` |
| `mdm_helper` `/dev/esoc-0` fd seen | `true` |
| `cnss_diag` start attempted | `true` |
| `cnss-daemon` start attempted | `true` |
| `cnss-daemon` Binder failures in post dmesg | `18` |
| CNSS `cld80211` dmesg hits | `20` |
| service-notifier `180` hits | `0` |
| WLFW hits | `0` |
| BDF hits | `0` |
| `wlan0` hits | `0` |
| `/dev/subsys_esoc0` open attempted | `false` |
| cleanup reboot required | `false` |

## Interpretation

The `before-cnss` order preserves the `mdm_helper` lower fd window but does not
reproduce the V601/V603 Binder-cleared condition in the current helper `v154`
matrix environment. This rules out simple service-manager ordering as the
remaining blocker.

The blocker is now narrower:

1. service-manager processes can be spawned and hold binder device nodes;
2. CNSS can reach `cld80211`;
3. `mdm_helper` can hold `/dev/esoc-0`;
4. but `cnss-daemon` still sees Binder transaction failures and no WLFW
   precondition appears.

The next useful unit is host-only V934: compare V601/V603 service-manager
readiness with V931/V933 matrix evidence. Specifically, classify whether the
current matrix service managers are only "process-started" but not equivalent
to Android init readiness, for example due to missing readiness property timing,
SELinux service-manager class visibility, Binder context-manager state,
or service registration differences.

## Guardrails

- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credentials.
- No DHCP, route mutation, or external ping.
- No controller eSoC notify.
- No controller `BOOT_DONE`.
- No `/dev/subsys_esoc0` open.
- No module load/unload.
- No boot image write.
- No partition write.
- No firmware mutation.
- No GPIO, sysfs, or debugfs write.

## Device Health

Post-run serial checks confirmed:

- `bootstatus`: `BOOT OK`, `selftest: pass=11 warn=1 fail=0`;
- `selftest`: `pass=11 warn=1 fail=0`;
- `netservice`: flag disabled, `ncm0=present`, `tcpctl=stopped`;
- cleanup reboot: not required.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_cnss_service_manager_before_cnss_live_v933.py
python3 scripts/revalidation/native_wifi_cnss_service_manager_before_cnss_live_v933.py plan
python3 scripts/revalidation/native_wifi_cnss_service_manager_before_cnss_live_v933.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
python3 scripts/revalidation/a90ctl.py bootstatus
python3 scripts/revalidation/a90ctl.py selftest
python3 scripts/revalidation/a90ctl.py netservice status
```

Evidence:

- `tmp/wifi/v933-cnss-service-manager-before-cnss-live/summary.md`
- `tmp/wifi/v933-cnss-service-manager-before-cnss-live/manifest.json`
- `tmp/wifi/v933-cnss-service-manager-before-cnss-live/native/mdm-helper-cnss-before-esoc.txt`
- `tmp/wifi/v933-cnss-service-manager-before-cnss-live/native/post-dmesg-wifi-esoc-tail.txt`

## Next

V934 should be host-only. Compare service-manager readiness between:

- V601/V603, where Binder transaction failures cleared;
- V931/V933, where service-manager processes start but Binder failures remain.

Do not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external
ping until WLFW/BDF/`wlan0` progresses.
