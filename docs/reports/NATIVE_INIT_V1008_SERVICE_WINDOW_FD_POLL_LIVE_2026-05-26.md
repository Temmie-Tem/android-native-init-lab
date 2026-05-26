# V1008 Service-window fd Poll Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| SELinuxfs mount | `tmp/wifi/v1008-v401-selinuxfs-mount/manifest.json` | `toybox-selinuxfs-mount-live-executor-run-pass` |
| SELinux policy load | `tmp/wifi/v1008-v490-native-selinux-policy-load-proof/manifest.json` | `v490-selinux-policy-load-proof-pass` |
| current-boot domain proof | `tmp/wifi/v1008-v997-current-boot-selinux-domain-proof/manifest.json` | `v491-post-load-domain-handoff-present` |
| service-window fd-poll live gate | `tmp/wifi/v1008-android-service-window-fd-poll-live/manifest.json` | `v1008-mdm-helper-esoc-fd-missing-no-trigger` |
| post-live health | `tmp/v1008-post-bootstatus.txt` | `selftest: pass=11 warn=1 fail=0` |

V1008 ran helper `v171` with the repaired service-window fd-poll support. The
fd-poll result was fully negative: `mdm_helper` did not hold `/dev/esoc-0` at
any sampled point, so `/dev/subsys_esoc0` remained closed.

## Live Contract

Selected markers:

```text
helper_version: a90_android_execns_probe v171
child_started: 14
service_manager_start_executed: true
wifi_hal_start_executed: true
wificond_start_executed: true
mdm_helper_start_executed: true
cnss_daemon_start_executed: true
fd_poll.after_mdm_helper_spawn.polls: 2
fd_poll.after_mdm_helper_spawn.seen: 0
fd_poll.after_cnss_daemon_spawn.polls: 14
fd_poll.after_cnss_daemon_spawn.seen: 0
mdm_helper_esoc0_fd_poll_seen: 0
mdm_helper_esoc0_fd_poll_max_count: 0
mdm_helper_esoc0_fd_count: 0
subsys_trigger_start_attempted: 0
subsys_esoc0_open_attempted: 0
result: subsys-trigger-not-attempted-no-mdm-helper-esoc-fd
```

The v171 timing repair did work as instrumentation: it captured the early
post-`mdm_helper` and post-`cnss-daemon` windows. The result is not a missed
late scan. Native service-window `mdm_helper` never opened `/dev/esoc-0` in the
bounded poll window.

## Guardrails

V1008 preserved the required boundaries:

- no `qcwlanstate` write;
- no `IWifi.start`;
- no eSoC ioctl;
- no Wi-Fi scan/connect/link-up;
- no credential use;
- no DHCP/routes;
- no external ping;
- no boot image, partition, firmware, GPIO, sysfs, or debugfs mutation;
- no `/dev/subsys_esoc0` open because the fd gate stayed closed.

No cleanup reboot was required. Actor cleanup was postflight-safe.

## Post-live Health

Post-live device health remained acceptable:

```text
boot: BOOT OK shell 4.2s
selftest: pass=11 warn=1 fail=0
exposure: guard=ok warn=0 fail=0 ncm=absent tcpctl=stopped rshell=stopped boundary=usb-local
```

## Interpretation

V1008 closes the "single late scan missed a transient fd" hypothesis for this
native service-window route. The blocker is now the difference between:

- V911 reduced native `mdm_helper` runtime-contract path, where `mdm_helper`
  reaches `/dev/esoc-0` and waits in `ESOC_WAIT_FOR_REQ`;
- V1008 full Android service-window path, where `mdm_helper` starts in the right
  domain but never opens `/dev/esoc-0`.

The next useful work is host-only comparison of the V911 and V1008 execution
contracts before another live retry. The likely deltas are service-window
environment, argv/env, property shim state, process identity/groups, and whether
another actor changes the eSoC/request-engine state before `mdm_helper` starts.

## Next

Plan V1009 as a host-only V911-versus-V1008 contract comparator:

1. compare helper command lines, mode flags, property root, private root, and
   SELinux context mode;
2. compare `mdm_helper` uid/gid/groups/caps and preexec status;
3. compare `/dev/esoc-0`, `/dev/subsys_esoc0`, MHI, property-service, and
   private `/data/vendor/wifi` path materialization;
4. compare actor order around `per_mgr`, `wificond`, `mdm_helper`, and
   `cnss-daemon`;
5. select either a smaller service-window route that preserves the V911 positive
   fd behavior, or a precise missing-runtime repair.
