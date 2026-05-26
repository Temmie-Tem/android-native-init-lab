# V1012 after-fd CNSS Service-Manager Matrix Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| plan | `tmp/wifi/v1012-after-fd-cnss-service-manager-matrix-plan/manifest.json` | `v1012-cnss-service-manager-matrix-plan-ready` |
| live proof | `tmp/wifi/v1012-after-fd-cnss-service-manager-matrix-live/manifest.json` | `v1012-reboot-required-cleaned` |
| post-cleanup health | `tmp/v1012-post-bootstatus.txt` | `selftest: pass=11 warn=1 fail=0` |

V1012 preserved the V1010 lower fd predicate, then added service-manager and CNSS
actors after that predicate. The result did not publish the WLFW precondition:
no `/dev/subsys_esoc0` open was attempted, and cleanup reboot restored the
device to a clean native state.

## Key Evidence

| Signal | Value |
| --- | --- |
| helper | `a90_android_execns_probe v171` |
| mode | `wifi-companion-mdm-helper-cnss-service-manager-matrix` |
| service manager order | `after-mdm-helper-esoc-fd` |
| `mdm_helper` `/dev/esoc-0` fd | `seen=1 count=1` |
| service-manager trio | `started=1` |
| `cnss_diag` | `started=1` |
| `cnss-daemon` | `started=1` |
| surface polls | `32` |
| WLFW precondition | `0` |
| `/dev/subsys_esoc0` open | `0` |
| Wi-Fi HAL / scan / credentials / DHCP / external ping | `0` |
| cleanup reboot | `true` |

Post-cleanup health:

```text
boot: BOOT OK shell 4.3s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Interpretation

V1012 answers the V1011 question:

- the reduced fd-positive lower state can be preserved while service-manager
  and CNSS actors are added;
- adding service-manager and CNSS after the fd predicate is not sufficient to
  produce `wlfw_start` or the WLFW precondition;
- because the WLFW gate stayed false, `/dev/subsys_esoc0` stayed closed;
- the cleanup reboot was expected and successful because one actor was not
  proven stopped at postflight.

The next blocker is no longer "can `mdm_helper` hold `/dev/esoc-0` while CNSS is
started?" It can. The remaining blocker is why CNSS still does not emit the
WLFW precondition in this after-fd matrix path.

## Guardrails

V1012 stayed below final Wi-Fi bring-up:

- no Wi-Fi HAL;
- no `wificond`;
- no `qcwlanstate`;
- no `IWifi.start`;
- no Wi-Fi scan/connect/link-up;
- no credential use;
- no DHCP/routes;
- no external ping;
- no controller eSoC notify or BOOT_DONE spoofing;
- no boot image, partition, firmware, GPIO, sysfs, or debugfs mutation.

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_after_fd_cnss_matrix_v1012.py
python3 scripts/revalidation/native_wifi_after_fd_cnss_matrix_v1012.py \
  --out-dir tmp/wifi/v1012-after-fd-cnss-service-manager-matrix-plan \
  plan
python3 scripts/revalidation/native_wifi_after_fd_cnss_matrix_v1012.py \
  --allow-mountsystem-ro \
  --allow-selinuxfs-mount \
  --allow-mdm-helper-cnss-service-manager-matrix \
  --allow-cleanup-reboot \
  --assume-yes \
  run
python3 scripts/revalidation/a90ctl.py --timeout 45 bootstatus
python3 scripts/revalidation/a90ctl.py --timeout 20 selftest
python3 scripts/revalidation/a90ctl.py --timeout 20 exposure
```

Result:

```text
decision: v1012-reboot-required-cleaned
pass: True
mdm_helper_esoc0_fd_seen: 1
service_manager_started: 1
cnss_daemon_started: 1
wlfw_precondition_observed: 0
subsys_esoc0_open_attempted: 0
cleanup_reboot_executed: True
```

## Next

Plan V1013 as a host-only CNSS/WLFW precondition gap classifier using V1012,
V1008, V1010, and Android V1000/V966 timing evidence. The classifier should
decide whether to add a minimal next actor (`wificond` or Wi-Fi HAL legacy/ext)
after the fd-positive CNSS matrix, or whether the gap is still lower than those
actors.
