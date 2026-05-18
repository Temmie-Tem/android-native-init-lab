# Native Init v249 CNSS Runtime Gap Classifier Report

## Summary

- status: PASS
- decision: `cnss-runtime-gaps-classified`
- boot image change: none
- daemon start: not executed
- output: `tmp/wifi/v249-cnss-runtime-gap-classifier/`
- host tool: `scripts/revalidation/wifi_cnss_runtime_gap_classifier.py`

v249 refined the v248 runtime gap matrix without starting `cnss-daemon`. It
confirmed the QRTR kernel socket family exists, tested the helper's private
`/sys/fs/selinux/null` materialization path, and separated primary start-only
risks from later scan/connect or `cnss_diag` blockers.

## Validation

Static checks:

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_runtime_gap_classifier.py
git diff --check
```

Live read-only collection:

```bash
python3 scripts/revalidation/wifi_cnss_runtime_gap_classifier.py \
  --out-dir tmp/wifi/v249-cnss-runtime-gap-classifier
```

Result:

```text
decision: cnss-runtime-gaps-classified
pass: True
```

Post-check:

```bash
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
```

Result: `pidof` returned rc=1, so `cnss-daemon` was not running after v249.

## Runtime Checks

| Check | Result | Notes |
| --- | --- | --- |
| v248 prerequisite | PASS | `cnss-runtime-primitives-ready-for-live-approval` |
| required control captures | PASS | required cmdv1 captures returned rc=0/status=ok |
| cnss-daemon absent | PASS | `pidof cnss-daemon` returned rc=1 |
| QRTR kernel family | PASS | `QIPCRTR` present in `/proc/net/protocols` |
| helper no-allow namespace | PASS | `helper_status=namespace-ready` |
| helper no-allow guard | PASS | `cnss_start.result=start-only-blocked`, `exec_attempted=0` |
| private SELinux null | PASS | `dev-null-selinux` helper mode materialized private char device |
| helper SHA recorded | PASS | `77fbdcdcbc6774abe5e34712097496edbac4a4ed763d87c82cf02effb88cd319` |

## Gap Classification

| Gap | State | Classification | Next |
| --- | --- | --- | --- |
| property service | missing | Android-init-owned runtime gap | do not fake before dedicated property shim plan |
| property area | missing | Android-init-owned runtime gap | collect exact property-read failure only if live start logs prove it |
| SELinux null | private materialization PASS | helper-compatible but no Android domain transition | live start-only can consider `dev-null-selinux` mode |
| QRTR | kernel family present | userspace nameservice/endpoint gap | add no-start AF_QIPCRTR socket/nameservice probe if needed |
| diag | missing | `cnss_diag` phase2 blocker | keep `cnss_diag` blocked |
| init rc hints | present | Android service model reference only | do not replay Android service manager in PID1 |

## Reference Basis

- Android property service is an init-owned socket/thread path. Native PID1
  should not blindly fake it without a dedicated shim design.
- bionic system properties expect `/dev/__properties__/property_info` for
  serialized property contexts.
- Linux QRTR support is a kernel protocol for communicating with services from
  other hardware blocks; service lookup also needs userspace service listing.

References:

- <https://android.googlesource.com/platform/system/core/+/refs/heads/android11-release/init/property_service.cpp>
- <https://android.googlesource.com/platform/bionic/+/cc9b100/libc/system_properties/system_properties.cpp>
- <https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/refs/heads/master/net/qrtr/Kconfig>

## Guardrails Preserved

- no `--allow-cnss-start-only`
- no `cnss-daemon` execution
- no `cnss_diag`
- no property service emulation or property area writes
- no rfkill unblock, `wlan*` link-up, scan/connect, credentials, DHCP, or routing
- no ICNSS bind/unbind, firmware mutation, Android partition write, or reboot

## Next Step

The first bounded live start-only attempt is still approval-gated. If approval is
not given, the next no-start candidate is a tiny AF_QIPCRTR socket/nameservice
probe that opens the socket family without sending Wi-Fi control traffic.
