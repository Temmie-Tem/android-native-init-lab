# Native Init v249 CNSS Runtime Gap Classifier Plan

## Summary

- target: v249 no-start CNSS runtime gap classifier
- baseline: v248 `cnss-runtime-primitives-ready-for-live-approval`
- new host tool: `scripts/revalidation/wifi_cnss_runtime_gap_classifier.py`
- boot image change: none
- daemon start: not executed

v248 proved the v247 helper path is ready for a bounded live start-only approval
review, but the runtime gaps are still coarse. v249 narrows the gaps without
starting `cnss-daemon`: property service/property area, SELinux null, QRTR, diag,
and global/private namespace expectations.

## References

- Android init creates and listens on the property service socket with
  `CreateSocket(PROP_SERVICE_NAME, ...)` and a property service thread:
  <https://android.googlesource.com/platform/system/core/+/refs/heads/android11-release/init/property_service.cpp>
- bionic system properties select serialized/split property contexts based on
  `/dev/__properties__/property_info`:
  <https://android.googlesource.com/platform/bionic/+/cc9b100/libc/system_properties/system_properties.cpp>
- Linux QRTR is Qualcomm IPC Router support; kernel Kconfig notes it is used to
  communicate with services from other hardware blocks and needs userspace
  service listing for lookups:
  <https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/refs/heads/master/net/qrtr/Kconfig>

## Scope

Collect and classify only read-only/no-start evidence:

- v248 manifest decision and current `cnss-daemon` absence
- `/proc/net/protocols` for `QIPCRTR`
- `/proc/net/unix`, `/proc/net/netlink`, `/proc/modules`
- `/dev/socket`, `/dev/socket/property_service`, `/dev/__properties__`
- property context/build property/init rc hints from mounted Android partitions
- `/sys/fs/selinux/null` and helper private `dev-null-selinux` no-allow variant
- `/dev/diag`, `/dev/qrtr`, `/sys` QRTR/QMI/CNSS/WLAN hints

## Explicit Non-Goals

v249 must not do any of the following:

- start `/vendor/bin/cnss-daemon`
- pass `--allow-cnss-start-only`
- run `cnss_diag`
- create a fake property service
- write property area files
- unblock rfkill
- link up `wlan*`
- scan/connect Wi-Fi
- start supplicant/HAL/wificond/hostapd
- bind/unbind ICNSS
- write Android partitions
- reboot automatically

## Output

Recommended output directory:

```text
tmp/wifi/v249-cnss-runtime-gap-classifier/
├── manifest.json
├── runtime-gap-classification.json
├── live-captures.json
├── helper-selinux-null-noallow.txt
├── summary.md
└── captures/*.txt
```

Decision labels:

- `cnss-runtime-gaps-classified`: current gaps are classified and no new blocker
  prevents an approval discussion for the first bounded start-only run.
- `cnss-runtime-gaps-blocked`: control path, v248 prerequisite, helper guard,
  daemon absence, or QRTR kernel-family evidence failed.
- `cnss-runtime-gaps-manual-review`: no-start evidence is internally consistent
  but an expected optional primitive changed state and needs review.

## Expected Classification

- property service/property area: Android-init-owned runtime primitive; do not
  fake in native init before a dedicated read-only property shim plan.
- SELinux null: private helper materialization can be tested with
  `--null-device-mode dev-null-selinux`, but Android SELinux domain transition
  is still not reproduced.
- QRTR: `/proc/net/protocols` decides whether the kernel socket family exists;
  `/dev/qrtr` absence alone is not enough to call QRTR missing.
- diag: missing `/dev/diag` remains a `cnss_diag` phase2 blocker, not necessarily
  a primary `cnss-daemon -n -l` start-only blocker.

## Validation Plan

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_cnss_runtime_gap_classifier.py
git diff --check
```

Live read-only validation:

```bash
python3 scripts/revalidation/wifi_cnss_runtime_gap_classifier.py \
  --out-dir tmp/wifi/v249-cnss-runtime-gap-classifier
```

Post-check:

```bash
python3 scripts/revalidation/a90ctl.py run /cache/bin/toybox pidof cnss-daemon || true
```

Acceptance:

- `daemon_start_executed=false`
- `cnss-daemon` is absent before and after collection
- v248 prerequisite remains PASS
- helper no-allow `dev-null-selinux` variant does not execute target and remains
  `start-only-blocked`
- `QIPCRTR` is either present or explicitly classified as a blocker
- no Wi-Fi scan/connect/link-up/credential/DHCP/routing action is attempted
