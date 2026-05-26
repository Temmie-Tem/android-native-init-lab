# V1004 Service-window Subsystem Trigger Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| SELinuxfs mount | `tmp/wifi/v1004-v401-selinuxfs-mount/manifest.json` | `toybox-selinuxfs-mount-live-executor-run-pass` |
| SELinux policy load | `tmp/wifi/v1004-v490-native-selinux-policy-load-proof/manifest.json` | `v490-selinux-policy-load-proof-pass` |
| current-boot domain proof | `tmp/wifi/v1004-v997-current-boot-selinux-domain-proof/manifest.json` | `v491-post-load-domain-handoff-present` |
| service-window subsystem trigger gate | `tmp/wifi/v1004-android-service-window-subsys-trigger-live/manifest.json` | `v1004-mdm-helper-esoc-fd-missing-no-trigger` |
| post-live health | `tmp/wifi/v1004-post-bootstatus.txt` | `selftest: pass=11 warn=1 fail=0` |

V1004 completed as a classified no-trigger pass. The Android service-window
actors were started and observed, but `mdm_helper` did not hold `/dev/esoc-0`
inside the native service window. Because the fd gate stayed closed, V1004 did
not start the `/dev/subsys_esoc0` trigger child.

## Live Sequence

V1004 refreshed the current boot state before running the trigger gate:

1. Mounted SELinuxfs with the V401 bounded toybox path.
2. Mounted system read-only with `mountsystem ro`.
3. Loaded native SELinux policy with the V490 proof gate.
4. Proved current-boot Android service domains with V997.
5. Ran helper `v170` mode
   `wifi-companion-android-wifi-service-window-subsys-trigger-capture`.

The remote helper matched the V1002 artifact:

```text
a90_android_execns_probe v170
sha256: edbccfef2fd117c5264c140ff5b2f4cec5424c917151607cecc309268cd9c254
```

## Observed Contract

Selected V1004 live markers:

```text
service_manager_start_executed: true
wifi_hal_start_executed: true
wificond_start_executed: true
mdm_helper_start_executed: true
cnss_daemon_start_executed: true
subsys_esoc0_open_attempted: false
subsys_trigger_started: false
wlfw_precondition_observed: false
decision: v1004-mdm-helper-esoc-fd-missing-no-trigger
reason: service-window-gate-did-not-see-dev-esoc-0
```

This means V1004 reached the intended Android service-window actor set, but the
new safety predicate did not observe the Android-positive `mdm_helper`
`/dev/esoc-0` fd condition. The absence of that fd is now the immediate blocker;
blindly opening `/dev/subsys_esoc0` without the predicate remains rejected.

## Guardrails

V1004 preserved the required safety boundaries:

- no `qcwlanstate` write;
- no `IWifi.start`;
- no live eSoC ioctl;
- no Wi-Fi scan, connect, credential use, DHCP, route mutation, or external ping;
- no boot image, partition, or rollback mutation;
- no `/dev/subsys_esoc0` open in the actual live run because the fd gate stayed
  closed.

The service-window helper did start Wi-Fi HAL service processes as part of the
bounded parity gate, but it did not perform Wi-Fi bring-up.

## Post-live Health

Post-live device health remained acceptable:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

No cleanup reboot was required by V1004.

## Interpretation

V1004 rules out the simple path "start Android service-window actors, see
`mdm_helper` hold `/dev/esoc-0`, then trigger `/dev/subsys_esoc0`." The native
window does not currently reproduce the Android-positive `mdm_helper` fd hold
condition.

The most likely remaining classes are:

- the fd is transient and V1004 sampled too late;
- `mdm_helper` needs an Android boot/runtime input not yet reproduced in native;
- the Android-positive `/dev/esoc-0` fd depends on earlier boot timing that
  cannot be reconstructed by late service-window start alone.

## Next

Use V1005 to avoid another blind trigger retry. The next gate should compare the
Android-positive boot evidence against V1004 with a focused
`mdm_helper`/eSoC/GPIO timing classifier:

- Android dmesg focus:
  `mdm|esoc|gpio|ap2mdm|mdm2ap|pmic|pm8150|subsys|wlfw|icnss`;
- Android `/proc/interrupts` and GPIO snapshots when available;
- native V1004 actor/fd timeline and `mdm_helper` `/dev/esoc-0` polling window;
- decision on whether helper `v171` needs repeated fd polling rather than a
  single post-spawn fd scan.

Magisk module capture remains optional. The faster first step is normal Android
boot plus immediate ADB dmesg/proc capture, because dmesg should preserve the
early eSoC/GPIO sequence even if `post-fs-data.sh` would start later.
